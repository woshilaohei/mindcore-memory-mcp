# MindCore Memory MCP

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

### `memory_stats` - System status
```python
# View memory statistics: total/distribution/confidence
stats = memory_stats()
```

## Project Structure

```
mindcore-memory-mcp/
├── mindcore_memory/          # Python package (pip install entry)
│   ├── __init__.py
│   ├── memory_engine.py      # Core memory engine
│   ├── server.py             # MCP Server (stdio + HTTP dual transport)
│   ├── http_app.py           # HTTP endpoint (production deploy)
│   └── eval_framework.py     # Evaluation framework
├── tests/
│   └── test_memory.py        # Unit tests
├── examples/
│   └── basic_usage.py        # Usage examples
├── pyproject.toml
├── README.md
└── LICENSE
```

## Integration

### Claude Desktop
```json
{
  "mcpServers": {
    "mindcore-memory": {
      "command": "pip",
      "args": ["install", "mindcore-memory"]
    }
  }
}
```

### VS Code AI
Search `MindCore Memory` in the extension marketplace.

### HTTP API (Production)
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"memory_store","arguments":{"content":"test"}},"id":1}'
```

## Production Standards

| Standard | Implementation |
|----------|---------------|
| **JSON-RPC 2.0** | stdio + HTTP dual transport |
| **Bearer Token Auth** | Optional auth for HTTP endpoints |
| **Input Validation** | Pydantic schemas |
| **CI/CD** | GitHub Actions |
| **Unit Tests** | pytest + coverage |
| **Eval Framework** | 5 core metrics |
| **Observability** | structlog complete logging |
| **Data Sovereignty** | JSONL local files, no vendor lock-in |

## Open Source

This project is open source (MIT License). The code is completely free. Storage uses local JSON files with no cloud service dependency and no data collection.

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=woshilaohei/mindcore-memory-mcp&type=Timeline)](https://star-history.com/#woshilaohei/mindcore-memory-mcp&Timeline)

---

<p align="center">
  <strong>Give AI memory. Make humans trust AI more.</strong>
</p>

---

## Collaborate With Me

I'm actively developing AI safety architecture projects including:

1. **Cerebellum Evolution Engine** - AI safety & evolution framework
2. **MindCore** - Cognitive memory architecture for AI systems
3. **Border Guard** - Self-evolving security operating system
4. **Ternary Balance Boundary Algorithm** - Novel equilibrium theory with 3 papers
5. **MindCore Memory MCP** - This project: production-grade long-term memory server

**Interested in collaborating?** Reach out:

- Email: [1410770089@qq.com](mailto:1410770089@qq.com)
- GitHub: [@woshilaohei](https://github.com/woshilaohei)

**Author:** Lao Hei
