"""
Tests for BND Boundary Manager + Deduction Engine — v1.0

Coverage:
- BND: 正推公式四维评分 (TRJ/EVO/COG/BALANCE)
- BND: 反推公式衰减链检测
- BND: 接受/拒绝决策
- Deduction: 高质量记忆过滤
- Deduction: 关键词提取和共现发现
- Deduction: 推理合成
- Integration: MemoryEngine + BND auto-evaluate
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mindcore_memory.bnd import BNDManager, BNDResult


# =============================================================================
# BND Manager Tests
# =============================================================================

class TestBNDDimensions:
    """四维评分测试"""

    def test_high_all_dimensions(self):
        """高轨迹+高进化+高认知 = 高BND评分, 通过"""
        bnd = BNDManager()
        result = bnd.evaluate(
            "基于之前修复的BM25问题，这次继续优化了检索算法，"
            "理解到根因在于重要性分数污染了关键词相关性，"
            "改进后准确率提升30%到97%。",
            importance=4,
            confidence=0.9,
            tags=["优化", "根因分析", "算法"],
        )
        assert result.bnd_score > 0.5
        assert result.accepted
        assert result.trj_score > 0.4
        assert result.evo_score > 0.4
        assert result.cog_score > 0.4

    def test_low_all_dimensions(self):
        """纯数据dump: 无轨迹、无进化、无认知 → 极低BND评分"""
        bnd = BNDManager()
        result = bnd.evaluate(
            "今天天气不错，吃了碗面。",
            importance=1,
            confidence=0.3,
        )
        # 无轨迹无进化无认知 → BND应该非常低
        assert result.bnd_score < 0.45
        assert result.trj_score < 0.4
        assert result.evo_score < 0.4
        assert result.cog_score < 0.35

    def test_balance_high(self):
        """三维均衡→balance高"""
        bnd = BNDManager()
        result = bnd.evaluate(
            "基于前次认知，继续推进并完成了优化，理解了原理提升了效果。",
            importance=3,
            confidence=0.8,
        )
        assert result.balance > 0.5  # 三维均衡

    def test_balance_low(self):
        """三维不均衡→balance低"""
        bnd = BNDManager()
        result = bnd.evaluate(
            "完成了bug修复。",  # 只有进化维度高
            importance=2,
            confidence=0.5,
        )
        # TRJ低、EVO中、COG低 → 方差大 → balance相对低
        assert result.balance < 0.96


class TestAntiChain:
    """反推公式检测测试"""

    def test_anti_chain_triggered(self):
        """无序+风险 连环触发"""
        bnd = BNDManager()
        result = bnd.evaluate(
            "系统出现未知混乱，存在崩溃风险，可能导致数据损坏。",
            importance=3,
            confidence=0.6,
        )
        assert result.anti_chain_triggered
        assert len(result.anti_chain_detail) > 0
        assert result.bnd_score < 0.5  # 被降权

    def test_anti_chain_not_triggered(self):
        """无衰减链关键词"""
        bnd = BNDManager()
        result = bnd.evaluate(
            "操作系统升级完成，所有功能测试通过。",
            importance=2,
            confidence=0.8,
        )
        assert not result.anti_chain_triggered
        assert result.anti_chain_detail == ""

    def test_full_anti_chain(self):
        """完整的五环衰减链"""
        bnd = BNDManager()
        result = bnd.evaluate(
            "系统核心模块出现无序混乱，未知问题导致风险急剧升高，"
            "可能造成严重损坏，最终导致模块被废弃淘汰。",
        )
        assert result.anti_chain_triggered
        # 应该触发了至少3环
        assert "→" in result.anti_chain_detail


class TestBNDStats:
    """统计信息测试"""

    def test_stats_accumulate(self):
        """多次评估后统计准确"""
        bnd = BNDManager()
        for i in range(10):
            bnd.evaluate(
                f"完成了第{i}次优化，理解到根因并修复",
                importance=3,
                confidence=0.7,
            )
        stats = bnd.stats
        assert stats["total_evaluated"] == 10
        assert 0 <= stats["acceptance_rate"] <= 1
        assert "weights" in stats

    def test_tune_weights(self):
        """动态调权"""
        bnd = BNDManager()
        bnd.tune_weights(trj=0.5, evo=0.3, cog=0.2)
        # 检查归一化
        total = bnd.TRJ_WEIGHT + bnd.EVO_WEIGHT + bnd.COG_WEIGHT
        assert abs(total - (1.0 - bnd.BALANCE_WEIGHT)) < 0.01


# =============================================================================
# Deduction Engine Tests
# =============================================================================

class TestDeductionEngine:
    """推理引擎测试"""

    @pytest.fixture
    def ded_engine(self):
        from mindcore_memory.deduction import DeductionEngine
        from mindcore_memory.bnd import BNDManager
        ded = DeductionEngine()
        ded.set_bnd_manager(BNDManager())
        return ded

    @pytest.fixture
    def high_quality_memories(self):
        """模拟一组高质量认知记忆"""
        return [
            {
                "content": "修复了BM25重要性污染问题，理解到根因在于importance score污染keyword relevance",
                "importance": 4,
                "confidence": 0.9,
                "tags": ["修复", "BM25", "根因分析"],
                "bnd_score": 0.75,
                "dimensions": {"cog": 0.8},
            },
            {
                "content": "基于上次修复，继续优化检索算法，将RRF替换为确定性路由",
                "importance": 3,
                "confidence": 0.8,
                "tags": ["优化", "检索", "路由"],
                "bnd_score": 0.70,
                "dimensions": {"cog": 0.7},
            },
            {
                "content": "发现检索准确率从91%提升到97%，归因于BM25修复和路由优化",
                "importance": 4,
                "confidence": 0.9,
                "tags": ["检索", "性能", "指标"],
                "bnd_score": 0.80,
                "dimensions": {"cog": 0.85},
            },
            {
                "content": "模式识别：所有检索问题最终都指向了两个根本原因——重要性污染和时间噪声",
                "importance": 4,
                "confidence": 0.95,
                "tags": ["模式", "根因分析", "检索"],
                "bnd_score": 0.85,
                "dimensions": {"cog": 0.9},
            },
        ]

    def test_deduce_success(self, ded_engine, high_quality_memories):
        """足够的高质量记忆应产生推理"""
        result = ded_engine.deduce(high_quality_memories, query="检索系统优化")
        assert result is not None
        assert result.insight.startswith("[Deduction]")
        assert result.source_count >= 3
        assert result.confidence > 0.4
        assert result.validated  # 应该通过BND

    def test_deduce_insufficient(self, ded_engine):
        """不足3条高质量记忆应跳过"""
        memories = [
            {"content": "一个普通记忆", "importance": 1, "confidence": 0.3,
             "tags": [], "bnd_score": 0.2, "dimensions": {"cog": 0.1}},
        ]
        result = ded_engine.deduce(memories, query="test")
        assert result is None

    def test_keyword_extraction(self, ded_engine):
        """关键词提取基本功能"""
        kws = ded_engine._extract_keywords(
            "修复了BM25重要性污染问题，理解到根因在于importance"
        )
        assert len(kws) > 0
        # 检查中英文混合提取
        has_chinese = any('\u4e00' <= c <= '\u9fff' for kw in kws for c in kw)
        has_english = any(kw.isascii() and len(kw) > 2 for kw in kws)
        assert has_chinese or has_english

    def test_co_occurrence(self, ded_engine, high_quality_memories):
        """共现模式发现"""
        all_keywords = []
        for m in high_quality_memories:
            all_keywords.append(
                ded_engine._extract_keywords(m["content"]) + m.get("tags", [])
            )
        co_occur = ded_engine._find_co_occurrence(all_keywords)
        # 应该有跨记忆共现的词
        assert len(co_occur) > 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestBNDIntegration:
    """BND + MemoryEngine 集成测试"""

    def test_engine_with_bnd(self):
        """MemoryEngine + BND auto-evaluate"""
        from mindcore_memory.memory_engine import MemoryEngine
        from mindcore_memory.bnd import BNDManager

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            bnd = BNDManager()
            engine = MemoryEngine(storage_path=tmpdir, bnd_manager=bnd)

            # Store 一条高质量记忆
            mid = engine.store(
                content="基于之前修复，继续优化并理解到根因在于算法设计缺陷，改进后准确率提升20%",
                importance=4,
                confidence=0.9,
                tags=["优化", "根因分析"],
            )

            # 验证 BND 评估结果在 metadata 中
            mem = engine._memories[mid]
            assert "bnd_score" in mem.metadata
            assert "bnd_accepted" in mem.metadata
            assert "bnd_dimensions" in mem.metadata

    def test_engine_without_bnd(self):
        """没有BND管理器时不崩溃"""
        from mindcore_memory.memory_engine import MemoryEngine
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = MemoryEngine(storage_path=tmpdir)
            mid = engine.store("一条普通记忆")
            assert mid is not None
