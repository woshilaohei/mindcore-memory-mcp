"""
BND Boundary Manager — 三维平衡边界算法 (v1.0)

MindCore 的核心推演引擎，基于正反公式的四维评分体系。

正推公式 (正向循环):
    轨迹 = 边界 = 进化 = 认知 = 边界
    每走一步(TRJ) → 画一条边界(BND) → 一次进化(EVO) → 一层认知(COG) → 新边界

反推公式 (衰减断裂链):
    无序 → 未知 → 风险 → 伤害 → 消亡
    断掉任何一个等号，就能活

四维评分:
    BND_score = w1·TRJ + w2·EVO + w3·COG + w4·BALANCE
    低于阈值 → 拒绝进入 BND 版本链
    触发反推 → 自动降权 50%
"""

import re
import math
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class BNDResult:
    """BND 评估结果 — 四维分数 + 反推检测"""

    trj_score: float       # 轨迹维度 0.0-1.0
    evo_score: float       # 进化维度 0.0-1.0
    cog_score: float       # 认知维度 0.0-1.0
    balance: float         # 三维平衡度 0.0-1.0 (方差归一)
    bnd_score: float       # 综合 BND 评分 0.0-1.0
    accepted: bool         # 是否通过边界，进入 BND 版本链
    anti_chain_triggered: bool    # 是否触发反推公式衰减链
    anti_chain_detail: str = ""   # 反推链详述 "无序 → 未知 → ..."
    dimensions: dict = field(default_factory=dict)


class BNDManager:
    """
    三维平衡边界管理器。

    每个记忆写入时都要经过四维评估：
    1. 轨迹 (TRJ) — 连续性和进展性
    2. 进化 (EVO) — 是否代表增长和改进
    3. 认知 (COG) — 是否代表深层理解
    4. 平衡 (BALANCE) — 三维是否均衡

    同时检测反推公式：如果记忆触发 2+ 环的衰减链，自动降权 50%。
    """

    # 四级权重 — 默认均匀分配，可动态调整
    TRJ_WEIGHT = 0.28
    EVO_WEIGHT = 0.28
    COG_WEIGHT = 0.28
    BALANCE_WEIGHT = 0.16

    # BND 接受阈值
    BND_THRESHOLD = 0.40

    # === 正推公式: 关键词词典 ===

    # 轨迹维度 — 连续性/引用性/进展性
    TRJ_REFERENCE_KW = [
        "基于", "如上", "前述", "上次", "之前", "继续", "跟进",
        "based on", "following", "previously", "continue", "next step",
    ]
    TRJ_PROGRESS_KW = [
        "完成", "通过", "发布", "部署", "上线", "合并", "推送", "提交",
        "completed", "passed", "released", "deployed", "merged", "pushed",
    ]

    # 进化维度 — 增长/修复/量化改进
    EVO_GROWTH_KW = [
        "修复", "优化", "升级", "改进", "突破", "解决", "实现", "完成",
        "fixed", "optimized", "upgraded", "improved", "solved", "completed",
        "resolved", "实现", "达成", "交付",
    ]
    EVO_METRIC_PATTERN = (
        r'(?:提升|提高|增加|增长|降低|减少|improve|increase|decrease|reduce|boost)'
        r'[^\d]*(\d+(?:\.\d+)?)'
    )

    # 认知维度 — 根因分析/模式识别/深层理解
    COG_INSIGHT_KW = [
        "根因", "原理", "本质", "认知", "理解", "发现", "模式", "规律",
        "root cause", "principle", "insight", "pattern", "discovered",
        "认识到", "领悟", "推断", "机制",
    ]
    COG_CAUSAL_KW = [
        "因为", "所以", "导致", "造成", "归因", "因此", "由此可见",
        "because", "therefore", "causes", "due to", "hence",
    ]

    # === 反推公式: 衰减链关键词 ===

    ANTI_CHAIN = {
        "无序(disorder)": ["混乱", "无序", "矛盾", "冲突", "不可控",
                        "chaos", "disorder", "contradiction", "inconsistent"],
        "未知(unknown)": ["未知", "不确定", "不知道", "未覆盖", "无数据",
                        "unknown", "uncertain", "unclear", "missing"],
        "风险(risk)": ["风险", "危险", "隐患", "漏洞", "脆弱",
                      "risk", "danger", "vulnerability", "threat"],
        "伤害(harm)": ["崩溃", "失败", "损坏", "中断", "不可用",
                      "crash", "fail", "broken", "down", "unavailable"],
        "消亡(death)": ["废弃", "过时", "淘汰", "淘汰", "不再维护",
                      "deprecated", "obsolete", "dead", "retired"],
    }

    def __init__(self):
        self._version = 1
        self._accepted_count = 0
        self._rejected_count = 0
        self._anti_chain_triggers = 0
        self._score_history: list[dict] = []  # 最近 100 条评分记录

    def evaluate(
        self,
        content: str,
        importance: int = 2,
        confidence: float = 0.5,
        tags: list = None,
        related_count: int = 0,
    ) -> BNDResult:
        """
        对一条记忆执行四维评分 + 反推检测。

        Args:
            content: 记忆文本内容
            importance: 用户标记的重要性 1-4
            confidence: 置信度 0.0-1.0
            tags: 标签列表（用于检测标签丰富度）
            related_count: 相关记忆数量（轨迹维度引用）

        Returns:
            BNDResult with 4D scores and accept/reject decision
        """
        content_lower = content.lower()

        # === 维度1: 轨迹 TRJ ===
        trj = self._score_trajectory(content_lower, importance, related_count)

        # === 维度2: 进化 EVO ===
        evo = self._score_evolution(content_lower)

        # === 维度3: 认知 COG ===
        cog = self._score_cognition(content_lower, confidence, tags)

        # === 维度4: 平衡度 BALANCE ===
        scores = [trj, evo, cog]
        mean = sum(scores) / 3
        variance = sum((s - mean) ** 2 for s in scores) / 3
        # 方差越大越不平衡 → balance 越低
        balance = 1.0 / (1.0 + variance * 6.0)

        # === 综合 BND 评分 ===
        bnd = (
            self.TRJ_WEIGHT * trj
            + self.EVO_WEIGHT * evo
            + self.COG_WEIGHT * cog
            + self.BALANCE_WEIGHT * balance
        )
        bnd = max(0.0, min(1.0, bnd))

        # === 反推公式检测 ===
        anti_result = self._check_anti_chain(content_lower)

        # 反推触发 → 降权 50%
        if anti_result["triggered"]:
            bnd *= 0.5
            self._anti_chain_triggers += 1

        accepted = bnd >= self.BND_THRESHOLD

        if accepted:
            self._accepted_count += 1
        else:
            self._rejected_count += 1

        # 记录评分历史
        self._score_history.append({
            "trj": round(trj, 3),
            "evo": round(evo, 3),
            "cog": round(cog, 3),
            "balance": round(balance, 3),
            "bnd": round(bnd, 3),
            "accepted": accepted,
            "anti": anti_result["triggered"],
        })
        if len(self._score_history) > 100:
            self._score_history.pop(0)

        return BNDResult(
            trj_score=round(trj, 3),
            evo_score=round(evo, 3),
            cog_score=round(cog, 3),
            balance=round(balance, 3),
            bnd_score=round(bnd, 3),
            accepted=accepted,
            anti_chain_triggered=anti_result["triggered"],
            anti_chain_detail=anti_result["detail"],
            dimensions={
                "trj": round(trj, 3),
                "evo": round(evo, 3),
                "cog": round(cog, 3),
                "balance": round(balance, 3),
            },
        )

    def _score_trajectory(
        self, content_lower: str, importance: int, related_count: int
    ) -> float:
        """评估轨迹维度: 记忆的连续性和进展性"""
        score = 0.35  # baseline

        # 引用性: 是否引用先前知识
        ref_count = sum(1 for kw in self.TRJ_REFERENCE_KW if kw in content_lower)
        score += min(ref_count * 0.10, 0.25)

        # 进展性: 是否记录明确状态变化
        prog_count = sum(1 for kw in self.TRJ_PROGRESS_KW if kw in content_lower)
        score += min(prog_count * 0.08, 0.20)

        # 关联记忆数量 → 轨迹密度高
        if related_count > 0:
            score += min(related_count * 0.03, 0.10)

        # 重要性加权
        score += (importance - 2) * 0.04

        return max(0.0, min(1.0, score))

    def _score_evolution(self, content_lower: str) -> float:
        """评估进化维度: 记忆是否代表增长或改进"""
        score = 0.30  # baseline

        # 增长信号
        growth_count = sum(1 for kw in self.EVO_GROWTH_KW if kw in content_lower)
        score += min(growth_count * 0.12, 0.40)

        # 量化改进 (如 "提升 30%")
        if re.search(self.EVO_METRIC_PATTERN, content_lower):
            score += 0.15

        # 版本升级标记
        versions = re.findall(r'v(\d+\.\d+)', content_lower)
        if versions:
            score += min(len(versions) * 0.06, 0.10)

        # 从 X → Y 的跃迁模式
        if re.search(r'(?:从|from)\s*.+\s*(?:到|→|=>|to)\s*', content_lower):
            score += 0.10

        return max(0.0, min(1.0, score))

    def _score_cognition(
        self, content_lower: str, confidence: float, tags: list = None
    ) -> float:
        """评估认知维度: 记忆是否代表深层理解和知识提炼"""
        score = 0.25  # baseline

        # 洞察关键词
        insight_count = sum(1 for kw in self.COG_INSIGHT_KW if kw in content_lower)
        score += min(insight_count * 0.15, 0.40)

        # 因果推理链
        causal_count = sum(1 for kw in self.COG_CAUSAL_KW if kw in content_lower)
        score += min(causal_count * 0.08, 0.15)

        # 置信度加权: 低置信度的认知不可靠
        score += confidence * 0.12

        # 标签丰富度 → 认知维度高
        if tags and len(tags) >= 3:
            score += 0.08

        return max(0.0, min(1.0, score))

    def _check_anti_chain(self, content_lower: str) -> dict:
        """
        反推公式检测: 无序 → 未知 → 风险 → 伤害 → 消亡

        扫描记忆内容，检测衰减链的触发环数。
        2+ 环连环触发 → 警报
        """
        chain = []

        for label, keywords in self.ANTI_CHAIN.items():
            if any(kw in content_lower for kw in keywords):
                chain.append(label)

        triggered = len(chain) >= 2
        detail = " → ".join(chain) if triggered else ""

        return {"triggered": triggered, "detail": detail}

    def tune_weights(self, trj: float = None, evo: float = None,
                     cog: float = None) -> None:
        """动态调整三维权重，必须和为 1 - BALANCE_WEIGHT"""
        total = self.TRJ_WEIGHT + self.EVO_WEIGHT + self.COG_WEIGHT
        if trj is not None:
            self.TRJ_WEIGHT = trj
        if evo is not None:
            self.EVO_WEIGHT = evo
        if cog is not None:
            self.COG_WEIGHT = cog
        # 归一化
        new_total = self.TRJ_WEIGHT + self.EVO_WEIGHT + self.COG_WEIGHT
        if new_total != total and new_total > 0:
            scale = (1.0 - self.BALANCE_WEIGHT) / new_total
            self.TRJ_WEIGHT *= scale
            self.EVO_WEIGHT *= scale
            self.COG_WEIGHT *= scale

    @property
    def stats(self) -> dict:
        """BND 管理器统计信息"""
        total = max(1, self._accepted_count + self._rejected_count)
        return {
            "version": self._version,
            "accepted": self._accepted_count,
            "rejected": self._rejected_count,
            "total_evaluated": self._accepted_count + self._rejected_count,
            "acceptance_rate": round(self._accepted_count / total, 3),
            "anti_chain_triggers": self._anti_chain_triggers,
            "threshold": self.BND_THRESHOLD,
            "weights": {
                "TRJ": round(self.TRJ_WEIGHT, 3),
                "EVO": round(self.EVO_WEIGHT, 3),
                "COG": round(self.COG_WEIGHT, 3),
                "BALANCE": round(self.BALANCE_WEIGHT, 3),
            },
            "recent_scores": self._score_history[-10:] if self._score_history else [],
        }
