# 三维平衡边界算法 — BND Boundary Manager

**MindCore Memory 的核心推演引擎。**

这是世界上第一个将「正反公式」编码为可执行算法的边界评估系统。每条记忆写入时自动经过四维评分（TRJ/EVO/COG/BALANCE），反推公式实时检测衰减链，低于阈值的记忆被过滤，触发反推链的记忆被降权 50%。

---

## 算法原理

### 正推公式（正向循环）

```
轨迹(TRJ) = 边界(BND) = 进化(EVO) = 认知(COG) = 边界(BND)
```

每走一步画一条边界，每条边界是一次进化，每次进化是一层认知，每层认知又画出新的边界。

### 反推公式（衰减断裂链）

```
无序 → 未知 → 风险 → 伤害 → 消亡
```

断掉任何一个等号，就能活。算法检测 2+ 环的连环触发并自动降权。

---

## 四维评分

```
BND_score = 0.28·TRJ + 0.28·EVO + 0.28·COG + 0.16·BALANCE
```

### 维度说明

| 维度 | 评估内容 | 关键词/模式 |
|------|---------|-----------|
| **TRJ 轨迹** | 连续性、进展性、引用关联 | "基于上次"、"继续推进"、"完成" |
| **EVO 进化** | 增长信号、量化改进、版本跃迁 | "修复"、"提升30%"、"v2.0" |
| **COG 认知** | 根因分析、因果推理、标签丰富度 | "根因在于"、"因为...所以..." |
| **BALANCE** | 三维方差归一化 | balance = 1/(1+var×6) |

### 平衡度计算

```python
variance = Var([TRJ, EVO, COG])
balance = 1.0 / (1.0 + variance * 6.0)
```

方差越小（三维越均衡），balance 越高。维度失衡的记忆（如只有 EVO 维度高）会自动降低平衡分。

---

## 反推公式检测

扫描记忆内容，匹配五环衰减链关键词：

| 环 | 关键词 | 权重 |
|----|--------|------|
| 无序 | 混乱、无序、矛盾、不可控 | 触发警报 |
| 未知 | 未知、不确定、缺失 | 连环触发→降权 |
| 风险 | 风险、危险、隐患、漏洞 | 连环触发→降权 |
| 伤害 | 崩溃、失败、损坏 | 连环触发→降权 |
| 消亡 | 废弃、过时、淘汰 | 连环触发→降权 |

**触发规则**: 2+ 环同时命中 → BND_score × 0.5

---

## 决策规则

```
BND_score >= 0.40 → ACCEPT → 进入 BND 版本链
BND_score <  0.40 → REJECT → 仅保留 EXP 经验层
反推链 2+ 环触发  → PENALTY → 降权 50% 后重新判定
```

---

## 使用方式

### Python API

```python
from mindcore_memory import BNDManager

bnd = BNDManager()

# 评估一条记忆
result = bnd.evaluate(
    "基于之前修复的BM25问题，理解到根因在于重要性污染，提升准确率30%",
    importance=4,
    confidence=0.9,
    tags=["修复", "根因分析"],
)

print(f"BND: {result.bnd_score:.3f}")       # 0.750
print(f"TRJ: {result.trj_score:.3f}")       # 0.630
print(f"EVO: {result.evo_score:.3f}")       # 0.540
print(f"COG: {result.cog_score:.3f}")       # 0.610
print(f"Balance: {result.balance:.3f}")     # 0.980
print(f"Accepted: {result.accepted}")        # True
```

### MCP Tool

```json
{
  "tool": "bnd_check",
  "arguments": {
    "content": "内容文本",
    "importance": 3,
    "confidence": 0.7,
    "tags": ["标签1", "标签2"]
  }
}
```

### 自动集成

MemoryEngine 在创建时注入 BNDManager，每条 `store()` 自动执行四维评估：

```python
from mindcore_memory import MemoryEngine, BNDManager

engine = MemoryEngine(bnd_manager=BNDManager())
engine.store("...")  # 自动走BND评估，结果存入metadata
```

---

## 性能

- **纯算法驱动**: 零 LLM 调用，零网络请求
- **单次评估耗时**: < 1ms（关键词匹配 + 正则 + 方差计算）
- **不阻塞存储**: 评估失败降级为 INFO 日志，不影响主流程
- **无外部依赖**: 仅使用 Python 标准库（re, math, dataclasses）

---

## 设计哲学

1. **正推为魂** — 轨迹→边界→进化→认知→边界，循环不息
2. **反推为盾** — 无序必被检测，衰减链必须断裂
3. **先认知后动手** — BND 评估是写入前的最后一道认知关
4. **纯算法不调LLM** — 推理引擎做模式识别，不做LLM调用

---

## 与 Bee Memory 的关系

Bee Memory v5.x 的「五维记忆池(EXP/TRJ/COG/BND/CTX)」是概念原型：
- EXP → 当前 `memory_store` 的存储层
- TRJ/COG/BND → 已在 BNDManager 中实现为三维评分
- CTX → 对应 `memory_context` 工具
- 虚空引擎(碰撞择优) → 对应 DeductionEngine 的模式提取

**mindcore-memory 是 Bee Memory 的工业化升级版。**
