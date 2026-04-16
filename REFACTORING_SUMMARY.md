# Crypto Trading Agent v2.0 Refactoring Summary

## 重构概述

根据 `problem.md` 和 `problem1.md` 的要求，对 Crypto Trading Agent 系统进行了全面重构，专注于 **4H/日线级别** 的中长线交易，消除 AI"天马行空"问题，确保所有分析基于真实数据。

---

## 核心变更

### 1. 精简智能体架构（Three-in-One）

**删除的冗余角色：**
- ❌ 所有 Debators（Aggressive/Conservative/Neutral）
- ❌ Bull/Bear Researchers（多空辩论者）
- ❌ Social Media Analyst
- ❌ Fundamentals Analyst
- ❌ News Analyst
- ❌ Sentiment Analyst
- ❌ Trader（交易员）

**新架构（仅 4 个核心节点）：**
```
START
  │
  ▼
Technical Analyst（技术面分析师）←→ tools_technical
  │
  ▼ Msg Clear Technical
Macro Onchain Analyst（宏观链上分析师）←→ tools_macro
  │
  ▼ Msg Clear Macro
Research Manager（研究经理 - 汇总）
  │
  ▼
Portfolio Manager（组合管理者 - LLM 定向 + Python 仓位）
  │
  ▼
END
```

---

### 2. 新增核心功能

#### 2.1 技术面分析师（crypto_technical_analyst.py）
- **专注 4H/日线级别** 趋势识别
- **强制数据验证**：所有分析必须基于真实数据
- **结构化输出**：必须包含 `evidence` 字段（JSON 格式）
- **规则门卫**：先用 Python 计算明确信号，再让 LLM 评估
- **视觉化支持**：生成 K 线图表供 Qwen-VL-Max 分析（可选配置）

#### 2.2 宏观链上分析师（crypto_macro_onchain_analyst.py）
- 合并原有的 News、Sentiment、Onchain Analyst 职能
- 只关注对 4H/1D 有实质影响的大事件（ETF、美联储决议、大户爆仓）
- 结构化输出：必须包含 `evidence` 字段

#### 2.3 成交量异常检测（detect_volume_anomaly）
**新增 4H/1D 核心数据维度：**
- Z-score 方法检测成交量异常
- 识别异常放量/缩量（±2σ阈值）
- 量价关系分析（确认突破 vs 假突破）
- 主力资金进场/离场信号

**使用示例：**
```python
detect_volume_anomaly("BTC/USDT:USDT", timeframe="4h", lookback_period=50)
```

#### 2.4 规则门卫系统（Rule-Based Guardrails）
**防止 AI 幻觉的三重约束：**
1. **数据验证器**：在调用 LLM 之前，先用 Python 验证数据质量
2. **结构化输出校验**：所有分析必须包含 `evidence` 字段，否则重试
3. **客观信号生成**：Python 计算明确的趋势/动量/波动率信号

---

### 3. 数据源优化

**移除的数据源：**
- ❌ Alpha Vantage（不适用于 Crypto）
- ❌ yfinance（美股数据源，延迟高）

**唯一数据源：**
- ✅ **Bitget via CCXT**（交易所原生 API，准确实时）

**新增数据维度：**
- ✅ 成交量异常检测（Volume Anomaly Detection）
- ✅ 资金费率（Funding Rate）- 已存在
- ✅ 未平仓量（Open Interest）- 已存在
- ✅ 订单簿深度（Orderbook）- 已存在

---

### 4. 视觉化分析（Vision-Based Analysis）

**支持 Qwen-VL-Max 视觉模型：**
- 使用 `mplfinance` 生成专业 K 线图表
- 包含：K 线、成交量、均线（MA20/MA60）、MACD、RSI
- 图表直接发送给视觉模型进行形态识别
- 可配置启用/禁用（`enable_vision_analysis`）

**启用方式：**
```python
# In default_config.py
"enable_vision_analysis": True,
"vision_llm": "qwen-vl-max",
```

---

### 5. 配置优化（default_config.py）

**4H/1D 专用配置：**
```python
CRYPTO_CONFIG = {
    "timeframe": "4h",              # 核心周期：4h 或 1d
    "candle_limit": 200,            # K 线数量
    "schedule_hour": "*/4",         # 每 4 小时执行一次
    "default_leverage": 1,          # 不使用杠杆（通过仓位控制风险）
    
    # 交易策略参数
    "risk_per_trade": 0.01,         # 单笔最大亏损 1%
    "atr_multiplier": 1.5,          # 止损 = 1.5 × ATR14
    "tp1_risk_reward": 2.0,         # 止盈 1 盈亏比
    "tp2_risk_reward": 3.5,         # 止盈 2 盈亏比
    "max_position_pct": 0.30,       # 单笔仓位上限 30%
}
```

---

## 文件变更清单

### 新增文件
```
tradingagents/agents/analysts/crypto_technical_analyst.py
tradingagents/agents/analysts/crypto_macro_onchain_analyst.py
```

### 重构文件
```
tradingagents/agents/managers/crypto_research_manager.py  # 移除辩论逻辑，改为简单汇总
tradingagents/graph/crypto_setup.py                       # 更新图拓扑
tradingagents/graph/crypto_trading_graph.py               # 更新工具节点
tradingagents/graph/conditional_logic.py                  # 新增 should_continue_technical/macro
tradingagents/default_config.py                           # 4H/1D 专用配置
tradingagents/dataflows/bitget_vendor.py                  # 新增 detect_volume_anomaly
tradingagents/agents/utils/crypto_tools.py                # 新增 volume_anomaly 工具
tradingagents/dataflows/interface.py                      # 路由更新
```

### 删除文件
```
tradingagents/agents/analysts/social_media_analyst.py
tradingagents/agents/analysts/fundamentals_analyst.py
tradingagents/agents/analysts/market_analyst.py
tradingagents/agents/analysts/news_analyst.py
tradingagents/agents/researchers/bull_researcher.py
tradingagents/agents/researchers/bear_researcher.py
tradingagents/agents/researchers/crypto_bull_researcher.py
tradingagents/agents/researchers/crypto_bear_researcher.py
tradingagents/agents/risk_mgmt/aggressive_debator.py
tradingagents/agents/risk_mgmt/conservative_debator.py
tradingagents/agents/risk_mgmt/neutral_debator.py
tradingagents/agents/risk_mgmt/crypto_aggressive_debator.py
tradingagents/agents/risk_mgmt/crypto_conservative_debator.py
tradingagents/agents/risk_mgmt/crypto_neutral_debator.py
tradingagents/agents/managers/research_manager.py
tradingagents/agents/managers/portfolio_manager.py
tradingagents/agents/trader/crypto_trader.py
tradingagents/agents/trader/trader.py
```

### 清理的旧分析师文件
```
tradingagents/agents/analysts/crypto_market_analyst.py
tradingagents/agents/analysts/crypto_news_analyst.py
tradingagents/agents/analysts/crypto_onchain_analyst.py
tradingagents/agents/analysts/crypto_sentiment_analyst.py
```

---

## 使用示例

### 命令行模式
```bash
# 运行一次分析（4H 周期）
uv run python crypto_main.py --once --symbol BTC/USDT:USDT

# 日线周期
uv run python crypto_main.py --once --timeframe 1d
```

### Web UI 模式
```bash
# 启动 Web 服务
python3 server.py

# 浏览器访问 http://localhost:8000
# 在「交易设置」页面选择：
# - 交易对：BTC/USDT, ETH/USDT
# - 分析间隔：每 4 小时
# - 时间周期：4h 或 1d
```

---

## 盈利策略实现

### 周期共振策略
- **日线（Daily）**：锁定大趋势方向
- **4 小时（4H）**：寻找最佳入场点
- **过滤 90% 短线噪音**，只交易明确趋势

### 动态止损（ATR 模型）
```python
Stop_Loss_Distance = 1.5 × ATR14
Position_Size = (Capital × 1%) / Stop_Loss_Distance
```

### 盈亏比优化
- TP1: 2R（平仓 50%）
- TP2: 3.5R（平仓剩余）
- 达到 1R 后止损上移至开仓价（保本）

---

## 如何确保 AI 不"天马行空"

### 1. 数据驱动（Data Grounding）
- AI 不直接生成价格预测
- 所有分析必须引用真实数据（RSI、MACD、ATR 等）
- Prompt 强制要求：`"All numerical values must be from tool responses, NOT estimated."`

### 2. 结构化输出校验
```json
{
  "evidence": {
    "current_price": <float>,
    "rsi14": <float or null>,
    "macd": <float or null>,
    ...
  },
  "objective_signals": {
    "trend": "BULLISH|BEARISH|NEUTRAL",
    "momentum": "STRONG|MODERATE|WEAK",
    ...
  }
}
```

### 3. Python 规则门卫
在调用 LLM 之前，先用 Python 计算：
- 数据质量验证
- 客观信号生成（趋势、动量、波动率）
- 异常检测（成交量、价格偏离）

### 4. 仓位计算硬编码
- LLM **只负责方向**（LONG/SHORT/CLOSE）和**信心评分**（1-10）
- **Python 硬编码计算**：仓位大小、止损、止盈
- LLM **无法干预**数学结果

---

## 视觉化分析（可选）

### 启用视觉分析
```python
# In default_config.py
"enable_vision_analysis": True,
"vision_llm": "qwen-vl-max",
```

### 生成的图表元素
- K 线（蜡烛图）
- 成交量柱状图
- 均线（MA20, MA60）
- MACD 子图（含柱状图）
- RSI 子图（含超买超卖线）

### 视觉分析优势
- **直观识别形态**：头肩底、双顶、趋势线突破
- **支撑阻力密集区**：一眼看出关键价位
- **量价关系**：图表比数字更直观

---

## 下一步开发建议

### 阶段 1：测试验证
1. 沙盒模式运行 1 周，记录所有分析结果
2. 对比 AI 建议 vs 实际市场走势
3. 调整 ATR 参数和仓位模型

### 阶段 2：视觉化集成
1. 测试 Qwen-VL-Max 图表分析准确性
2. 优化图表生成（添加斐波那契回撤位）
3. 对比纯文本 vs 视觉分析的决策质量

### 阶段 3：实盘部署
1. 切换到实盘 API Key
2. 从小仓位开始（10% 资本）
3. 监控实际执行滑点和手续费

---

## 风险声明

⚠️ **重要提示**：
- 本系统仅供学习和研究使用
- 加密货币合约交易存在极高风险
- AI 决策不保证盈利
- 在使用实盘模式前，请充分了解杠杆交易风险
- 设置合理止损，只投入能承受损失的资金

---

## 参考文档

- [problem.md](./problem.md) - 深度细化方案
- [problem1.md](./problem1.md) - 架构诊断与重构报告
- [CRYPTO_PROGRESS.md](./CRYPTO_PROGRESS.md) - 开发进度记录

---

**重构完成日期**: 2026-04-16  
**版本**: v2.0 (Refactored)  
**架构**: Three-in-One (Technical + Macro + Portfolio)
