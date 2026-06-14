# MindCore Memory MCP

<!-- MCP Registry ownership verification -->
mcp-name: io.github.woshilaohei/mindcore-memory

**AI Long-Term Memory Server — Production-grade persistent memory for AI agents.**

> "The best AI agent isn't the smartest — it's the one that remembers."

[![GitHub stars](https://img.shields.io/github/stars/woshilaohei/mindcore-memory-mcp?style=social)](https://github.com/woshilaohei/mindcore-memory-mcp/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![woshilaohei/mindcore-memory-mcp MCP server](https://glama.ai/mcp/servers/woshilaohei/mindcore-memory-mcp/badges/score.svg)](https://glama.ai/mcp/servers/woshilaohei/mindcore-memory-mcp)

## Value Proposition

**MindCore Memory** solves AI Agent's biggest pain point: limited context windows, lost information in long conversations, and broken cross-session memory continuity.

## What Problem It Solves

| Pain Point | Status Quo | MindCore Memory |
|------------|-----------|-----------------|
| AI forgets everything | Conversation ends, all lost | Persistent long-term memory |
| No cross-session recall | Re-teach every session | Cross-session knowledge reuse |
| Memory chaos, no priority | All memories weighted equally | Importance grading + confidence |
| RAG brute-force injection | Context overload, quality drops | Precise context window |

## Quick Start (3 lines)

```bash
# 1. Install
pip install mindcore-memory

# 2. Launch MCP Server
mindcore-memory

# 3. Call from your AI Agent
memory_id = memory_store("User says his name is Zhang San, free on Wednesday")
context = memory_recall("User's schedule")
```

## Eval Framework Results

```
Storage Integrity:     100% (data persistence correct)
Recall Relevance:      100% (relevant memories recalled first)
Confidence Calibration: 100% (confidence correctly calibrated)
Importance Weighting:   100% (high-priority memories ranked higher)
Context Efficiency:    100% (context window not overloaded)

Overall Score: 100%
```

## Core Tools

### `memory_store` - Store memory
```python
memory_store(
    content="Python was created by Guido van Rossum from Netherlands",
    importance=3,        # 1-4 importance level
    tags=["python", "history"],
    confidence=0.95,      # confidence score
    source="agent"       # agent/user/tool
)
```

### `memory_recall` - Recall memory
```python
memory_recall(
    query="Who created Python",
    tags=["python"],      # optional tag filter
    limit=10             # return count
)
```

### `memory_context` - Build context window
```python
# Build optimal context for current task (auto-dedup + priority sort)
context = memory_context(
    query="Current project status",
    max_tokens=2000      # auto-truncate
)
```

## MCP Server Setup

Add to your MCP client configuration:

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

## License

MIT License - Copyright (c) 2025 Lao Hei

## Links

- GitHub: https://github.com/woshilaohei/mindcore-memory-mcp
- PyPI: https://pypi.org/project/mindcore-memory/
- MCP Registry: https://registry.modelcontextprotocol.io/servers/io.github.woshilaohei/mindcore-memory