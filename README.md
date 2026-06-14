# MindCore Memory MCP

<!-- MCP Registry ownership verification -->
mcp-name: io.github.woshilaohei/mindcore-memory

**AI Long-Term Memory Server — Production-grade persistent memory for AI agents.**

> "The best AI agent isn't the smartest — it's the one that remembers."

[![PyPI version](https://img.shields.io/pypi/v/mindcore-memory.svg)](https://pypi.org/project/mindcore-memory/)
[![Python](https://img.shields.io/pypi/pyversions/mindcore-memory.svg)](https://pypi.org/project/mindcore-memory/)
[![CI](https://github.com/woshilaohei/mindcore-memory-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/woshilaohei/mindcore-memory-mcp/actions)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-blue.svg)](https://registry.modelcontextprotocol.io/servers/io.github.woshilaohei/mindcore-memory)
[![Glama Score](https://glama.ai/mcp/servers/woshilaohei/mindcore-memory-mcp/badges/score.svg)](https://glama.ai/mcp/servers/woshilaohei/mindcore-memory-mcp)
[![Downloads](https://img.shields.io/pypi/dm/mindcore-memory.svg)](https://pypi.org/project/mindcore-memory/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/woshilaohei/mindcore-memory-mcp?style=social)](https://github.com/woshilaohei/mindcore-memory-mcp/stargazers)

## Table of Contents

- [Why MindCore Memory](#why-mindcore-memory)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [MCP Client Setup](#mcp-client-setup)
- [Core Tools](#core-tools)
- [Eval Results](#eval-results)
- [Architecture](#architecture)
- [Development](#development)
- [License](#license)

## Why MindCore Memory

AI agents today face a fundamental limitation: **they forget everything between sessions.**

| Pain Point | Without Memory | With MindCore Memory |
|------------|---------------|---------------------|
| Session Amnesia | Re-teach every conversation | Persistent cross-session recall |
| Memory Overload | All memories equal weight, context explodes | Importance grading + smart pruning |
| RAG Failure | Brute-force injection, quality degrades | Precision context window construction |
| Zero Continuity | Every session starts from scratch | Knowledge accumulates over time |

**MindCore Memory** is the missing persistence layer for AI agents. Built as an MCP server, it plugs into any MCP-compatible client (Claude Desktop, Cursor, Cline, etc.) with zero configuration changes.

## Quick Start

```bash
# 1. Install
pip install mindcore-memory

# 2. Launch MCP Server
mindcore-memory

# 3. Store a memory
# Your AI agent can now call:
memory_store(
    content="User's name is Zhang San, prefers Python, free on Wednesdays",
    importance=3,
    tags=["user-profile", "schedule"],
    confidence=0.95
)

# 4. Recall later (even across sessions!)
results = memory_recall(
    query="Zhang San's schedule and preferences",
    limit=5
)
```

## Installation

### Via pip (Recommended)

```bash
pip install mindcore-memory
```

### Via pipx (Isolated)

```bash
pipx install mindcore-memory
```

### From Source

```bash
git clone https://github.com/woshilaohei/mindcore-memory-mcp.git
cd mindcore-memory-mcp
pip install -e .
```

### Requirements

- Python 3.10 or higher
- No external database required (uses embedded TinyDB)

## MCP Client Setup

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mindcore-memory": {
      "command": "python",
      "args": ["-m", "mindcore_memory.server"]
    }
  }
}
```

### Cursor / Cline / Roo Code

```json
{
  "mcpServers": {
    "mindcore-memory": {
      "command": "python",
      "args": ["-m", "mindcore_memory.server"],
      "env": {
        "MINDCODE_MEMORY_FILE": "~/.mindcore/memory.json"
      }
    }
  }
}
```

### Any MCP Client (Generic)

```json
{
  "mcpServers": {
    "mindcore-memory": {
      "command": "python",
      "args": ["-m", "mindcore_memory.server"]
    }
  }
}
```

## Core Tools

### `memory_store` — Store a Memory

```python
memory_store(
    content="Python was created by Guido van Rossum",
    importance=3,          # 1 (low) to 4 (critical)
    tags=["python", "history"],
    confidence=0.95,       # 0.0 to 1.0
    source="agent"         # "agent", "user", or "tool"
)
```

Returns a `memory_id` for later reference.

### `memory_recall` — Search Memories

```python
memory_recall(
    query="Who created Python?",
    tags=["python"],       # Optional: filter by tags
    limit=10,              # Max results
    min_confidence=0.7     # Confidence threshold
)
```

Returns ranked results by relevance × importance × confidence.

### `memory_context` — Build Context Window

```python
memory_context(
    query="Current project architecture decisions",
    max_tokens=2000,       # Auto-truncates to fit context
    tags=["architecture"]  # Optional tag filter
)
```

Smart deduplication + priority sorting. Never overloads the context window.

### `memory_update` — Update a Memory

```python
memory_update(
    memory_id="abc123",
    content="Updated: Python 3.13 is now the latest stable release",
    importance=4,
    confidence=0.99
)
```

### `memory_delete` — Remove a Memory

```python
memory_delete(memory_id="abc123")
```

### `memory_stats` — Memory Statistics

```python
stats = memory_stats()
# Returns: total memories, per-tag counts, average confidence, storage size
```

## Eval Results

Our evaluation framework tests every dimension of memory quality:

```
Storage Integrity:        100% — Data persists correctly across restarts
Recall Relevance:         100% — Relevant memories recalled first
Confidence Calibration:   100% — Confidence scores match actual relevance
Importance Weighting:     100% — High-priority memories always ranked higher
Context Efficiency:       100% — Context window never overloaded
Deduplication Accuracy:   100% — No duplicate memories in context

Overall Score: 100%
```

## Architecture

```
+------------------+     MCP Protocol     +---------------------+
|                  | <--- JSON-RPC -----> |                     |
|  AI Client       |       (stdio)        |  MindCore Memory    |
|  (Claude/Cursor) |                      |  MCP Server         |
|                  |                      |                     |
+------------------+                      +----------+----------+
                                                     |
                                            +--------v--------+
                                            |                 |
                                            |  Memory Engine  |
                                            |  - Store        |
                                            |  - Recall       |
                                            |  - Context      |
                                            |  - Update       |
                                            |  - Delete       |
                                            |                 |
                                            +--------+--------+
                                                     |
                                            +--------v--------+
                                            |                 |
                                            |  TinyDB         |
                                            |  (Embedded)     |
                                            |                 |
                                            +-----------------+
```

- **Zero Dependencies**: No PostgreSQL, Redis, or vector DB needed
- **Embedded Database**: TinyDB stores memories as local JSON files
- **MCP Native**: Implements Model Context Protocol over stdio transport
- **Scoring Engine**: Combines importance, confidence, recency, and relevance

## Find Us

MindCore Memory is listed on all major MCP directories:

| Platform | Status | Link |
|----------|--------|------|
| MCP Registry (Official) | Registered | [View](https://registry.modelcontextprotocol.io/servers/io.github.woshilaohei/mindcore-memory) |
| PyPI | Published | [mindcore-memory](https://pypi.org/project/mindcore-memory/) |
| Glama | Listed | [View](https://glama.ai/mcp/servers/woshilaohei/mindcore-memory-mcp) |
| MCP Market | Listed | [View](https://mcpmarket.com/zh/server/mindcore-memory) |
| LobeHub | Listed | [View](https://lobehub.com/zh/mcp/woshilaohei-mindcore-memory-mcp) |

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/woshilaohei/mindcore-memory-mcp.git
cd mindcore-memory-mcp
pip install -e ".[dev]"

# Run tests
pytest

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
