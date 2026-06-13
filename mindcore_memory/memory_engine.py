"""
MindCore Memory Engine - Production-grade long-term memory for AI agents.

Key design decisions:
- User owns their data (stored in local filesystem, not vendor lock-in)
- JSON-based storage for transparency and portability
- Semantic similarity search via embedding-free keyword matching
- Context window optimization: only recall what's relevant
- Confidence scoring for each memory retrieval
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class MemoryImportance(Enum):
    """Memory importance levels."""
    EPISODIC = 1   # Momentary, short-lived context
    WORKING = 2    # Current task context
    SEMANTIC = 3   # Long-term knowledge
    CRITICAL = 4   # Key facts, user preferences


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    importance: int  # 1-4
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0
    session_id: Optional[str] = None
    confidence: float = 0.5  # 0.0-1.0, how confident we are this memory is accurate
    source: str = "agent"  # "agent" | "user" | "tool"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        return cls(**data)


@dataclass
class RetrievalResult:
    """Memory retrieval result with confidence."""
    memory: MemoryEntry
    relevance_score: float  # 0.0-1.0, how relevant to the query
    confidence: float       # 0.0-1.0, how confident the memory is accurate
    snippet: str            # Relevant excerpt


class MemoryEngine:
    """
    Production-grade memory engine.
    
    Stores memories as JSON files in user-controlled directory.
    Supports semantic search, importance weighting, and confidence tracking.
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_memories: int = 10000,
        recall_limit: int = 20,
    ):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # Default: ~/.mindcore/memory/
            self.storage_path = Path.home() / ".mindcore" / "memory"
        
        self.max_memories = max_memories
        self.recall_limit = recall_limit
        self._memories: dict[str, MemoryEntry] = {}
        self._index: dict[str, set[str]] = {}  # tag -> memory_ids
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.storage_path / "memories.jsonl"
        
        # Load existing memories
        self._load()
        
        logger.info(
            "memory_engine_initialized",
            storage_path=str(self.storage_path),
            memory_count=len(self._memories),
        )

    def _load(self) -> None:
        """Load memories from disk."""
        if not self.memory_file.exists():
            return
        
        count = 0
        with open(self.memory_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        entry = MemoryEntry.from_dict(data)
                        self._memories[entry.id] = entry
                        for tag in entry.tags:
                            if tag not in self._index:
                                self._index[tag] = set()
                            self._index[tag].add(entry.id)
                        count += 1
                    except Exception as e:
                        logger.warning("failed_to_load_memory", error=str(e))
        
        logger.info("memories_loaded", count=count)

    def _save(self, entry: MemoryEntry) -> None:
        """Append memory to disk (append-only for durability)."""
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def store(
        self,
        content: str,
        importance: int = 2,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        confidence: float = 0.5,
        source: str = "agent",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Store a new memory.
        
        Returns the memory ID.
        """
        # Enforce max memories (LRU eviction of lowest importance)
        if len(self._memories) >= self.max_memories:
            self._evict_low_importance()
        
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            importance=max(1, min(4, importance)),
            tags=tags or [],
            session_id=session_id,
            confidence=confidence,
            source=source,
            metadata=metadata or {},
        )
        
        self._memories[entry.id] = entry
        for tag in entry.tags:
            if tag not in self._index:
                self._index[tag] = set()
            self._index[tag].add(entry.id)
        
        self._save(entry)
        
        logger.info(
            "memory_stored",
            memory_id=entry.id,
            importance=entry.importance,
            tags=entry.tags,
        )
        
        return entry.id

    def recall(
        self,
        query: str,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[RetrievalResult]:
        """
        Recall relevant memories based on query and filters.
        
        Uses keyword matching + importance weighting + recency boost.
        """
        limit = limit or self.recall_limit
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        candidates: list[tuple[str, float]] = []
        
        for mem_id, mem in self._memories.items():
            # Filter by session
            if session_id and mem.session_id and mem.session_id != session_id:
                continue
            
            # Filter by tags
            if tags:
                if not any(tag in mem.tags for tag in tags):
                    continue
            
            # Compute relevance score
            relevance = 0.0
            
            # Keyword match (simple but fast)
            content_words = set(mem.content.lower().split())
            overlap = query_words & content_words
            if overlap:
                relevance = len(overlap) / max(len(query_words), 1) * 0.4
            
            # Tag match bonus
            if tags and any(tag in mem.tags for tag in tags):
                relevance += 0.3
            
            # Importance bonus (exponential)
            relevance += mem.importance * 0.1
            
            # Recency boost (last 1 hour = bonus)
            try:
                last_access = datetime.fromisoformat(mem.last_accessed)
                age_hours = (datetime.utcnow() - last_access).total_seconds() / 3600
                if age_hours < 1:
                    relevance += 0.15
                elif age_hours < 24:
                    relevance += 0.05
            except Exception:
                pass
            
            if relevance > 0:
                candidates.append((mem_id, relevance))
        
        # Sort by relevance
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for mem_id, relevance in candidates[:limit]:
            mem = self._memories[mem_id]
            # Update access stats
            mem.access_count += 1
            mem.last_accessed = datetime.utcnow().isoformat()
            
            # Truncate snippet
            snippet = mem.content[:200] + "..." if len(mem.content) > 200 else mem.content
            
            results.append(RetrievalResult(
                memory=mem,
                relevance_score=min(relevance, 1.0),
                confidence=mem.confidence,
                snippet=snippet,
            ))
        
        logger.info(
            "memory_recalled",
            query=query[:50],
            results_count=len(results),
        )
        
        return results

    def get_context_window(
        self,
        query: str,
        max_tokens: int = 4000,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Build a context window optimized for the current query.
        
        Fills up to max_tokens with the most relevant memories,
        prioritizing: CRITICAL > SEMANTIC > WORKING > EPISODIC.
        """
        results = self.recall(query, session_id=session_id, limit=50)
        
        context_parts = []
        current_tokens = 0
        
        # Sort by importance then relevance
        sorted_results = sorted(
            results,
            key=lambda r: (r.memory.importance, r.relevance_score),
            reverse=True,
        )
        
        for result in sorted_results:
            mem = result.memory
            # Rough token estimate: ~4 chars per token
            mem_tokens = len(mem.content) // 4
            
            if current_tokens + mem_tokens > max_tokens:
                continue
            
            context_parts.append(f"[{mem.importance}★] {mem.content}")
            current_tokens += mem_tokens
        
        if not context_parts:
            return ""
        
        return "\n\n".join(context_parts)

    def _evict_low_importance(self) -> None:
        """Evict lowest importance memories when storage is full."""
        if not self._memories:
            return
        
        # Find lowest importance, oldest memories
        sorted_memories = sorted(
            self._memories.items(),
            key=lambda x: (x[1].importance, -x[1].access_count),
        )
        
        # Evict 10% of memories
        evict_count = max(1, len(self._memories) // 10)
        to_evict = [mid for mid, _ in sorted_memories[:evict_count]]
        
        for mid in to_evict:
            del self._memories[mid]
        
        # Rebuild index
        self._index.clear()
        for mem_id, mem in self._memories.items():
            for tag in mem.tags:
                if tag not in self._index:
                    self._index[tag] = set()
                self._index[tag].add(mem_id)
        
        logger.warning("memories_evicted", count=evict_count, remaining=len(self._memories))

    def update_confidence(self, memory_id: str, confidence: float) -> bool:
        """Update confidence score for a memory (e.g., after user correction)."""
        if memory_id not in self._memories:
            return False
        
        mem = self._memories[memory_id]
        mem.confidence = max(0.0, min(1.0, confidence))
        mem.last_accessed = datetime.utcnow().isoformat()
        
        # Note: We don't rewrite the JSONL file (append-only design)
        # Confidence updates are tracked in memory only
        logger.info("memory_confidence_updated", memory_id=memory_id, confidence=confidence)
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get memory system statistics."""
        total = len(self._memories)
        by_importance = {}
        for imp in range(1, 5):
            by_importance[imp] = sum(1 for m in self._memories.values() if m.importance == imp)
        
        avg_confidence = (
            sum(m.confidence for m in self._memories.values()) / total
            if total > 0 else 0.0
        )
        
        return {
            "total_memories": total,
            "max_memories": self.max_memories,
            "by_importance": by_importance,
            "avg_confidence": round(avg_confidence, 3),
            "tag_count": len(self._index),
            "storage_path": str(self.storage_path),
        }
