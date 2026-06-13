"""
MindCore Memory MCP Server - Production-grade.

Supports both stdio (local/IDE) and Streamable HTTP transports.
Both transports share the same tool registry for consistency.

Security:
- Bearer token authentication on HTTP
- Origin validation on HTTP
- Input validation via Pydantic
- No arbitrary file system access
"""

from __future__ import annotations

from typing import Any

import argparse
import json
import os

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

from .memory_engine import MemoryEngine

logger = structlog.get_logger()

# Server instance
server = Server("mindcore-memory-mcp")

# Global engine instance
_engine: MemoryEngine | None = None


def get_engine() -> MemoryEngine:
    """Get or create the memory engine."""
    global _engine
    if _engine is None:
        storage_path = os.environ.get("MINDCORE_MEMORY_PATH")
        _engine = MemoryEngine(storage_path=storage_path)
    return _engine


# =============================================================================
# Tool Definitions (MCP Protocol)
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="memory_store",
            description="Store a new memory that should be remembered long-term.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory content to store. Be specific and factual.",
                    },
                    "importance": {
                        "type": "integer",
                        "description": "Importance: 1=episodic, 2=working, 3=semantic, 4=critical",
                        "minimum": 1,
                        "maximum": 4,
                        "default": 2,
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization and retrieval.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier to group related memories.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level 0.0-1.0. Lower if uncertain.",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.5,
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of this memory: 'user', 'agent', or 'tool'.",
                        "default": "agent",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="memory_recall",
            description="Recall memories relevant to the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to search memories.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags (optional).",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Filter by session (optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return. Default: 10",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="memory_context",
            description="Build a context window from relevant memories for LLM input.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What is the current task or question?",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Approximate max tokens for the context. Default: 2000",
                        "default": 2000,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Prioritize memories from this session.",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="memory_update_confidence",
            description="Update a memory confidence score after correction.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The memory ID to update.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "New confidence level 0.0-1.0.",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": ["memory_id", "confidence"],
            },
        ),
        Tool(
            name="memory_stats",
            description="Get stats: total count, importance distribution, avg confidence.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


# =============================================================================
# Tool Implementations
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Execute a tool call."""
    engine = get_engine()
    
    try:
        if name == "memory_store":
            memory_id = engine.store(
                content=arguments["content"],
                importance=arguments.get("importance", 2),
                tags=arguments.get("tags"),
                session_id=arguments.get("session_id"),
                confidence=arguments.get("confidence", 0.5),
                source=arguments.get("source", "agent"),
            )
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({
                    "status": "stored",
                    "memory_id": memory_id,
                }, ensure_ascii=False))],
                isError=False,
            )
        
        elif name == "memory_recall":
            results = engine.recall(
                query=arguments["query"],
                tags=arguments.get("tags"),
                session_id=arguments.get("session_id"),
                limit=arguments.get("limit", 10),
            )
            
            output = {
                "count": len(results),
                "results": [
                    {
                        "memory_id": r.memory.id,
                        "content": r.memory.content,
                        "relevance": round(r.relevance_score, 3),
                        "confidence": round(r.confidence, 3),
                        "importance": r.memory.importance,
                        "tags": r.memory.tags,
                        "created_at": r.memory.created_at,
                        "snippet": r.snippet,
                    }
                    for r in results
                ],
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(output, ensure_ascii=False))],
                isError=False,
            )
        
        elif name == "memory_context":
            context = engine.get_context_window(
                query=arguments["query"],
                max_tokens=arguments.get("max_tokens", 2000),
                session_id=arguments.get("session_id"),
            )
            return CallToolResult(
                content=[TextContent(type="text", text=context)],
                isError=False,
            )
        
        elif name == "memory_update_confidence":
            success = engine.update_confidence(
                memory_id=arguments["memory_id"],
                confidence=arguments["confidence"],
            )
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({
                    "success": success,
                    "memory_id": arguments["memory_id"],
                    "confidence": arguments["confidence"],
                }, ensure_ascii=False))],
                isError=False,
            )
        
        elif name == "memory_stats":
            stats = engine.get_stats()
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(stats, ensure_ascii=False))],
                isError=False,
            )
        
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
    
    except Exception as e:
        logger.error("tool_error", tool=name, error=str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


# =============================================================================
# Entry Points
# =============================================================================

async def main_stdio():
    """Run as stdio MCP server (for Claude Desktop, VS Code, etc.)."""
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging_level=20),
    )
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """CLI entry point."""
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging_level=20),
    )
    
    parser = argparse.ArgumentParser(description="MindCore Memory MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode. stdio for local IDE integration, http for remote.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--token", help="Bearer token for HTTP auth")
    args = parser.parse_args()
    
    if args.transport == "stdio":
        import asyncio
        asyncio.run(main_stdio())
    else:
        # HTTP mode (for remote deployment)
        import uvicorn
        from .http_app import create_http_app
        app = create_http_app(token=args.token)
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
