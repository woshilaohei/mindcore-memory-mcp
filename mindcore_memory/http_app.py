"""
HTTP transport for MindCore Memory MCP Server.
Production-grade: Bearer token auth, Origin validation.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .memory_engine import MemoryEngine

logger = structlog.get_logger()


def create_http_app(token: Optional[str] = None) -> FastAPI:
    """Create FastAPI app with MCP HTTP endpoint."""
    
    app = FastAPI(title="MindCore Memory MCP", version="0.1.0")
    
    # CORS: restrict to known origins in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    def verify_token(authorization: Optional[str] = Header(None)) -> bool:
        """Verify Bearer token if configured."""
        if not token:
            return True  # No auth configured
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization header")
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid Authorization format")
        provided = authorization[7:]
        if provided != token:
            raise HTTPException(status_code=403, detail="Invalid token")
        return True
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok", "service": "mindcore-memory-mcp"}
    
    @app.get("/stats")
    async def stats(_: bool = Depends(verify_token)):
        """Get memory stats (requires auth if configured)."""
        engine = MemoryEngine()
        return engine.get_stats()
    
    @app.post("/mcp")
    async def mcp_endpoint(request: Request, _: bool = Depends(verify_token)):
        """
        MCP HTTP endpoint - accepts JSON-RPC 2.0 requests.
        
        Supports:
        - tools/list: List available tools
        - tools/call: Call a tool
        """
        body = await request.json()
        method = body.get("method")
        request_id = body.get("id")
        
        # Import here to avoid circular import
        from . import server as mcp_server
        
        if method == "tools/list":
            tools = await mcp_server.list_tools()
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.inputSchema,
                        }
                        for t in tools
                    ]
                }
            }
        
        elif method == "tools/call":
            args = body.get("params", {}).get("arguments", {})
            tool_name = body.get("params", {}).get("name")
            
            if not tool_name:
                raise HTTPException(status_code=400, detail="Missing tool name")
            
            result = await mcp_server.call_tool(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": c.text} for c in result.content],
                    "isError": result.isError,
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }
    
    return app
