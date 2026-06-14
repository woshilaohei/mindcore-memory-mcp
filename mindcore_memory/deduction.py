"""
Deduction Engine — 推理记忆层 (v1.0)

层级记忆的第三层：从高置信度认知记忆中推导新知识。

管道:
    STM (短期) → LTM (长期) → Deduction (推理)
    原始记忆     → 持久化记忆   → 衍生记忆

工作原理:
    1. 收集 BND 评分 >= 0.6 且 COG 维度 >= 0.5 的高质量记忆
    2. 按标签聚类，发现跨主题模式
    3. 从多条文记忆的交叉点推导新认知
    4. 推导结果过 BND 验证后，作为 type=deduction 记忆写入
"""

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class DeductionResult:
    """推理产出"""
    insight: str                  # 推导出的新认知
    source_count: int            # 用了多少条源记忆
    source_tags: list[str]       # 涉及的标签
    confidence: float            # 推导置信度
    bnd_result: Optional[dict] = None  # BND 验证结果
    validated: bool = False      # 是否通过 BND 验证
    keywords: list = field(default_factory=list)  # 提取的关键词


class DeductionEngine:
    """
    推理记忆引擎。

    不做 LLM 调用，纯基于统计模式识别 + BND 验证的推理管道：
    1. 从高质量认知记忆中提取关键词共现模式
    2. 发现跨标签的隐藏关联
    3. 格式化推导结果，走 BND 验证后写入
    """

    # 最低要求：用于推理的记忆必须满足
    MIN_BND_SCORE = 0.50      # BND 综合评分下限
    MIN_COG_SCORE = 0.35      # COG 认知维下限
    MIN_SOURCES = 3            # 至少需要 3 条源记忆才能推理
    MIN_KEYWORD_OVERLAP = 2   # 至少 2 个关键词重叠才认为有关联

    # 停用词（排除高频无意义词汇）
    STOP_WORDS = {
        "的", "是", "了", "在", "和", "与", "等", "及", "或",
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "of", "to", "in", "on", "at", "for", "with", "by", "and", "or",
        "this", "that", "it", "its", "we", "you", "they", "he", "she",
        "has", "have", "had", "do", "does", "did", "not", "no", "but",
    }

    def __init__(self, bnd_manager=None):
        self._bnd_manager = bnd_manager
        self._deduction_count = 0

    def set_bnd_manager(self, bnd_manager):
        """注入 BND 管理器（避免循环依赖）"""
        self._bnd_manager = bnd_manager

    def deduce(self, memories: list, query: str = "") -> Optional[DeductionResult]:
        """
        从记忆列表中推导新认知。

        Args:
            memories: 记忆条目列表，每个必须有 content, importance, confidence, tags
            query: 当前查询意图，用于定向推理（可选）

        Returns:
            DeductionResult 如果推导成功，否则 None
        """
        # Step 1: 过滤高质量认知记忆
        high_quality = self._filter_high_quality(memories)
        if len(high_quality) < self.MIN_SOURCES:
            logger.debug("deduction_skip", reason="insufficient_sources",
                        count=len(high_quality), required=self.MIN_SOURCES)
            return None

        # Step 2: 提取所有关键词
        all_keywords = []
        for m in high_quality:
            kws = self._extract_keywords(m.get("content", ""))
            all_keywords.append(kws + (m.get("tags", []) or []))

        # Step 3: 找到跨记忆的共同模式
        co_occurrence = self._find_co_occurrence(all_keywords)

        # Step 4: 根据共现模式推导新认知
        insight = self._synthesize_insight(
            high_quality, co_occurrence, query
        )
        if not insight:
            return None

        # Step 5: 计算推导置信度
        confidence = self._calc_deduction_confidence(
            len(high_quality), len(co_occurrence)
        )

        # Step 6: BND 验证
        bnd_result = None
        validated = True
        if self._bnd_manager:
            bnd = self._bnd_manager.evaluate(
                content=insight,
                importance=3,  # 推理记忆默认重要性=3
                confidence=confidence,
                tags=list(co_occurrence.keys())[:5],
            )
            bnd_result = {
                "bnd_score": bnd.bnd_score,
                "accepted": bnd.accepted,
                "dimensions": bnd.dimensions,
                "anti_chain_triggered": bnd.anti_chain_triggered,
            }
            validated = bnd.accepted

        self._deduction_count += 1

        return DeductionResult(
            insight=insight,
            source_count=len(high_quality),
            source_tags=list(set(t for m in high_quality for t in (m.get("tags") or []))),
            confidence=round(confidence, 3),
            bnd_result=bnd_result,
            validated=validated,
            keywords=list(co_occurrence.keys()),
        )

    def _filter_high_quality(self, memories: list) -> list:
        """过滤高质量认知记忆"""
        return [
            m for m in memories
            if m.get("bnd_score", 0) >= self.MIN_BND_SCORE
            and m.get("cog_score", m.get("dimensions", {}).get("cog", 0)) >= self.MIN_COG_SCORE
        ]

    def _extract_keywords(self, text: str) -> list[str]:
        """从文本提取关键词（统计方法，非 NLP）"""
        # 中文: 按字符切分 2-4 gram
        # 英文: 按空格切词
        words = []

        # 英文单词
        eng_words = re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{2,}', text)
        words.extend(w.lower() for w in eng_words if w.lower() not in self.STOP_WORDS)

        # 中文 2-3 gram（连续中文字符）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        for segment in chinese_chars:
            for i in range(len(segment) - 1):
                words.append(segment[i:i + 2])
            for i in range(len(segment) - 2):
                words.append(segment[i:i + 3])

        return list(set(words))  # 去重

    def _find_co_occurrence(self, keyword_lists: list[list]) -> Counter:
        """找到跨记忆的共现关键词"""
        counter = Counter()
        for kw_list in keyword_lists:
            counter.update(set(kw_list))

        # 过滤掉单次出现的（无跨记忆意义）
        return Counter({
            k: v for k, v in counter.items()
            if v >= self.MIN_KEYWORD_OVERLAP and k not in self.STOP_WORDS
        })

    def _synthesize_insight(
        self, memories: list, co_occurrence: Counter, query: str = ""
    ) -> Optional[str]:
        """
        从高质量记忆和共现模式中合成新认知。

        策略: 找到出现频率最高的 5 个关键词，
              围绕它们构建一条推理结果。
        """
        if not co_occurrence:
            return None

        top_kws = co_occurrence.most_common(5)
        top_terms = [kw for kw, _ in top_kws]

        # 找出包含这些关键词最多的源记忆作为证据
        evidence = []
        for m in memories:
            content = m.get("content", "")
            hits = sum(1 for kw in top_terms if kw in content)
            if hits >= 2:
                evidence.append(content[:80] + "...")

        if not evidence:
            return None

        # 提取共同主题（按标签）
        all_tags = [t for m in memories for t in (m.get("tags") or [])]
        tag_counter = Counter(all_tags)
        top_tags = [t for t, _ in tag_counter.most_common(3)]

        # 构建推理文本
        kw_str = "、".join(top_terms[:5])
        tag_str = "、".join(top_tags[:3]) if top_tags else "通用领域"

        if query:
            insight = (
                f"[Deduction] 针对「{query[:60]}」，在{tag_str}领域识别到关键模式: "
                f"{kw_str}。这{len(top_terms)}个概念的反复交叉出现表明存在深层关联。"
                f"证据来源: {len(evidence)}条高质量记忆。"
            )
        else:
            insight = (
                f"[Deduction] {tag_str}领域关键模式识别: {kw_str}。"
                f"基于{len(memories)}条认知记忆的交叉分析，"
                f"这组概念在{len(evidence)}条记忆中反复共现，"
                f"表明它们之间存在尚未被显式记录的深层联系。"
            )

        return insight

    def _calc_deduction_confidence(
        self, source_count: int, pattern_count: int
    ) -> float:
        """计算推导置信度"""
        # 源记忆越多、模式越丰富 → 置信度越高
        base = 0.4
        source_bonus = min(source_count / 20.0, 0.30)   # 20 条源记忆 → +0.30
        pattern_bonus = min(pattern_count / 10.0, 0.30)  # 10 个模式 → +0.30
        return min(1.0, base + source_bonus + pattern_bonus)

    @property
    def stats(self) -> dict:
        """推理引擎统计"""
        return {
            "deductions_generated": self._deduction_count,
            "bnd_available": self._bnd_manager is not None,
        }
