# MindCore Memory MCP

mcp-name: io.github.woshilaohei/mindcore-memory

**AI Long-Term Memory Server — persistent memory with hybrid search for AI agents.**

> "The best AI agent isn't the smartest — it's the one that remembers."

[![PyPI version](https://img.shields.io/pypi/v/mindcore-memory.svg)](https://pypi.org/project/mindcore-memory/)
[![Python](https://img.shields.io/pypi/pyversions/mindcore-memory.svg)](https://pypi.org/project/mindcore-memory/)
[![CI](https://github.com/woshilaohei/mindcore-memory-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/woshilaohei/mindcore-memory-mcp/actions)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-blue.svg)](https://registry.modelcontextprotocol.io/servers/io.github.woshilaohei/mindcore-memory)
[![Glama Score](https://glama.ai/mcp/servers/woshilaohei/mindcore-memory-mcp/badges/score.svg)](https://glama.ai/mcp/servers/woshilaohei/mindcore-memory-mcp)
[![Downloads](https://img.shields.io/pypi/dm/mindcore-memory.svg)](https://pypi.org/project/mindcore-memory/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/woshilaohei/mindcore-memory-mcp?style=social)](https://github.com/woshilaohei/mindcore-memory-mcp/stargazers)

## Why MindCore Memory

AI agents face a fundamental limitation: **they forget everything between sessions.**

| Pain Point | Without Memory | With MindCore Memory |
|------------|---------------|---------------------|
| Session Amnesia | Re-teach every conversation | Persistent cross-session recall |
| Memory Overload | All memories equal weight | Importance grading + smart pruning |
| Poor Search | Keyword-only, misses semantics | Hybrid: BM25 keyword + FAISS semantic |
| Zero Continuity | Every session starts from scratch | Knowledge accumulates over time |

MindCore Memory is the persistence layer for AI agents. Built as an MCP server, it plugs into any MCP-compatible client (Claude Desktop, Cursor, Cline, etc.).

## Quick Start

```bash
# 1. Install
pip install mindcore-memory

# 2. Launch MCP Server (stdio mode)
mindcore-memory

# 3. Your AI agent can now call:
memory_store(
    content="User's name is Zhang San, prefers Python, free on Wednesdays",
    importance=3,
    tags=["user-profile", "schedule"],
    confidence=0.95
)

# 4. Recall later (even across sessions!)
memory_recall(query="Zhang San's schedule", limit=5)
```

## Installation

### Via pip

```bash
pip install mindcore-memory
```

### Via pipx

```bash
pipx install mindcore-memory
```

### Semantic Search (optional)

For full hybrid search with FAISS embeddings:

```bash
pip install mindcore-memory[semantic]
```

This installs `sentence-transformers`, `faiss-cpu`, and `numpy`. Without it, search falls back to BM25 keyword-only mode.

### From Source

```bash
git clone https://github.com/woshilaohei/mindcore-memory-mcp.git
cd mindcore-memory-mcp
pip install -e .
```

### Requirements

- Python 3.10+
- No external database required (embedded JSONL + optional FAISS)

## MCP Client Setup

### Claude Desktop / Cursor / Cline

```json
{
  "mcpServers": {
    "mindcore-memory": {
      "command": "python",
      "args": ["-m", "mindcore_memory.server"],
      "env": {
        "MINDCORE_MEMORY_PATH": "~/.mindcore/memory"
      }
    }
  }
}
```

### HTTP mode (remote deployment)

```bash
mindcore-memory --transport http --host 0.0.0.0 --port 8080 --token your-secret-token
```

## Core Tools

### memory_store — Store a Memory

```
content:    string (required) — the memory content. Max 100K chars.
importance: int 1-4 (default 2) — 1=episodic, 2=working, 3=semantic, 4=critical
tags:       list of strings — for categorization and filtering
confidence: float 0.0-1.0 (default 0.5) — how certain you are
source:     string (default "agent") — "agent", "user", or "tool"
session_id: string — group related memories by session
```

Returns a `memory_id` for later reference.

### memory_recall — Search Memories

```
query:      string (required) — what you're looking for
tags:       list of strings — optional tag filter
session_id: string — optional session filter
limit:      int 1-100 (default 10) — max results
```

Returns ranked results by hybrid score: **BM25 keyword (40%) + FAISS semantic (50%) + importance (5%) + recency (5%)**.

### memory_context — Build Context Window

```
query:      string (required) — current task or question
max_tokens: int (default 2000) — max context size
session_id: string — prioritize memories from this session
```

Returns a formatted context string ready for LLM injection. Auto-sorts by importance and relevance.

### memory_update_confidence — Adjust Confidence

```
memory_id:  string (required) — the memory to update
confidence: float 0.0-1.0 (required) — new confidence value
```

Use when an agent discovers a memory was wrong or needs reinforcement.

### memory_delete — Remove a Memory

```
memory_id:  string (required) — the memory to delete
```

Irreversible. Use with caution.

### memory_stats — System Statistics

No arguments. Returns total count, importance distribution, average confidence, tag counts, storage path.

## Architecture

```
+-------------------+     MCP / stdio      +------------------------+
|                   | <--- JSON-RPC -----> |                        |
|  AI Client        |                     |  MindCore Memory        |
|  (Claude/Cursor)  |                     |  MCP Server             |
+-------------------+                     +-----------+------------+
                                                       |
                                              +--------v-----------+
                                              |                    |
                                              |  Memory Engine     |
                                              |  Hybrid Search:    |
                                              |  - BM25 keyword    |
                                              |  - FAISS semantic  |
                                              |  (IVF for >500     |
                                              |   memories)        |
                                              +--------+-----------+
                                                       |
                                              +--------v-----------+
                                              |                    |
                                              |  JSONL (append)    |
                                              |  + FAISS index     |
                                              |  (on disk)         |
                                              +--------------------+
```

- **Hybrid Search**: BM25 keyword match + FAISS semantic embeddings for best precision and recall
- **IVF Index**: FAISS inverted file index activates at 500+ memories for O(sqrt N) search
- **Embedded**: No PostgreSQL, Redis, or external services needed
- **MCP Native**: Implements Model Context Protocol over stdio and HTTP transports
- **Input Validation**: Server-level sanitization prevents injection attacks

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MINDCORE_MEMORY_PATH` | `~/.mindcore/memory` | Storage directory for `memories.jsonl` |
| `MINDCORE_MODEL_PATH` | auto-detect | Local path to sentence-transformers model |

## Find Us

| Platform | Status | Link |
|----------|--------|------|
| MCP Registry (Official) | Registered | [View](https://registry.modelcontextprotocol.io/servers/io.github.woshilaohei/mindcore-memory) |
| PyPI | Published | [mindcore-memory](https://pypi.org/project/mindcore-memory/) |
| Glama | Listed | [View](https://glama.ai/mcp/servers/woshilaohei/mindcore-memory-mcp) |
| MCP Market | Listed | [View](https://mcpmarket.com/zh/server/mindcore-memory) |
| LobeHub | Listed | [View](https://lobehub.com/zh/mcp/woshilaohei-mindcore-memory-mcp) |

## Development

```bash
git clone https://github.com/woshilaohei/mindcore-memory-mcp.git
cd mindcore-memory-mcp
pip install -e ".[dev]"

# Run linter
ruff check .

# Run type checker
mypy mindcore_memory/
```

## License

MIT License — Copyright (c) 2025 Lao Hei

## Links

- GitHub: https://github.com/woshilaohei/mindcore-memory-mcp
- PyPI: https://pypi.org/project/mindcore-memory/
- MCP Registry: https://registry.modelcontextprotocol.io/servers/io.github.woshilaohei/mindcore-memory
- Issues: https://github.com/woshilaohei/mindcore-memory-mcp/issues
