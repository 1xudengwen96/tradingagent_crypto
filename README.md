# TradingAgents Crypto — 加密货币合约交易机器人

> **重要说明**：本文档根据实际代码逻辑编写，完整披露交易策略、盈利逻辑和风险机制。

---

## 📌 目录

1. [系统概述](#系统概述)
2. [交易逻辑详解](#交易逻辑详解)
3. [盈利逻辑](#盈利逻辑)
4. [风险管理](#风险管理)
5. [系统架构](#系统架构)
6. [安装指南](#安装指南)
7. [配置说明](#配置说明)
8. [使用方法](#使用方法)
9. [常见问题](#常见问题)

---

## 系统概述

这是一个**基于多智能体 AI 的加密货币永续合约交易系统**，使用通义千问（Qwen）大模型作为决策核心，通过 Bitget 交易所执行交易。

### 核心特性

- **交易对**：BTC/USDT、ETH/USDT 永续合约（可扩展）
- **交易周期**：4 小时线（默认）或日线
- **执行模式**：沙盒模拟 / 实盘交易
- **通知系统**：飞书机器人多角色推送
- **决策机制**：AI 多智能体分析 + Python 硬编码风控

### 关键设计原则

1. **AI 只负责方向判断**：LLM 仅输出交易方向（LONG/SHORT/CLOSE）和信心评分
2. **Python 硬编码风控**：仓位大小、止损、止盈由数学公式计算，LLM 无法干预
3. **BTC 200 日均线拦截器**：BTC 跌破 200 日均线时，强制禁止做多（系统性风险保护）

---

## 交易逻辑详解

### 1. 决策流程（10 步流水线）

```
┌─────────────────────────────────────────────────────────────────┐
│  每 4 小时自动触发（或手动触发）                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1-3: 数据获取                                               │
│  - 从 Bitget 获取 OHLCV K 线数据（200 根 4H/1D 蜡烛）              │
│  - 计算技术指标：SMA/EMA/MACD/RSI/布林带/ATR14/VWMA              │
│  - 获取资金费率、订单簿、未平仓量、宏观新闻                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4-5: 分析师智能体                                           │
│  📈 技术面分析师：分析 K 线形态、指标信号、成交量异常               │
│  🌍 宏观/链上分析师：分析订单簿、资金费率、未平仓量、宏观新闻      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6-7: 研究经理汇总                                           │
│  ⚖️ 综合两份分析报告，识别一致性和分歧                            │
│  输出结构化研究报告（不做交易决策）                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 8: 交易员建议                                               │
│  💼 基于研究报告生成初步交易计划                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 9: 风险辩论（可选）                                         │
│  🛡️ 激进派 vs 保守派辩论仓位和风险                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 10: 投资组合经理（最终决策者）                               │
│  🎯 LLM 输出：方向 + 信心评分 + 理由                               │
│  📐 Python 计算：仓位大小、止损、止盈（ATR 数学模型）               │
│  🚫 BTC 拦截器：检查 BTC 是否在 200 日均线上方                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 执行层（如果 auto_execute=True）                                 │
│  - 解析 LLM 决策文本                                              │
│  - 设置杠杆倍数                                                   │
│  - 计算仓位大小（USDT）                                           │
│  - 下单：市价单 + 止损单 + 2 个止盈单                               │
│  - 发送飞书通知                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 信号类型

| 信号 | 含义 | 仓位系数 |
|------|------|----------|
| `LONG` | 强烈做多 | 100% |
| `LONG-LITE` | 谨慎做多 | 50% |
| `SHORT` | 强烈做空 | 100% |
| `SHORT-LITE` | 谨慎做空 | 50% |
| `CLOSE` | 平仓/观望 | 0% |

### 3. LLM 输出格式

```
DIRECTION: LONG-LITE
CONVICTION: 7
RATIONALE: 技术面显示突破整理形态，但宏观情绪偏中性，建议轻仓试多
```

---

## 盈利逻辑

### 1. 核心盈利公式

本系统采用**趋势跟踪 + 均值回归**混合策略，盈利来源：

1. **趋势捕捉**：通过技术指标（MACD、EMA、布林带）识别趋势方向
2. **盈亏比优势**：每笔交易至少 2:1 盈亏比（止盈 1）和 3.5:1（止盈 2）
3. **仓位管理**：根据 ATR 波动率动态调整仓位，避免过度暴露

### 2. 数学模型（硬编码）

#### A. 止损距离计算

```python
stop_loss_distance = ATR_MULTIPLIER × ATR14
# 默认：ATR_MULTIPLIER = 1.5
# 例如：ATR14 = 1000 USD → 止损距离 = 1500 USD
```

#### B. 仓位大小计算

```python
# 1. 计算信念因子（根据 LLM 信心评分）
conviction_factor = clamp(conviction_score / 10, 0.5, 1.0)
# 信心 1-4 → 0.5, 信心 5-10 → 0.5-1.0

# 2. 计算止损百分比
stop_loss_pct = stop_loss_distance / entry_price

# 3. 反推仓位（保证单笔最大亏损不超过总资金的 RISK_PER_TRADE）
position_usdt = (capital × RISK_PER_TRADE × conviction_factor) / stop_loss_pct

# 4. 仓位上限保护
position_usdt = min(position_usdt, capital × MAX_POSITION_PCT)
# 默认：MAX_POSITION_PCT = 30%

# 5. LITE 信号额外缩半
if direction in ("LONG-LITE", "SHORT-LITE"):
    position_usdt *= 0.5
```

#### C. 止盈价格计算

```python
if LONG:
    stop_loss = entry_price - stop_loss_distance
    take_profit_1 = entry_price + 2.0 × stop_loss_distance   # 2R
    take_profit_2 = entry_price + 3.5 × stop_loss_distance   # 3.5R
else:  # SHORT
    stop_loss = entry_price + stop_loss_distance
    take_profit_1 = entry_price - 2.0 × stop_loss_distance
    take_profit_2 = entry_price - 3.5 × stop_loss_distance
```

#### D. 出场策略

- **TP1（50% 仓位）**：2R 盈亏比 → 锁定一半利润
- **TP2（50% 仓位）**：3.5R 盈亏比 → 让利润奔跑
- **止损**：1.5R 反向 → 严格止损

### 3. 期望收益模型

假设胜率 45%（趋势跟踪策略典型值）：

```
单笔期望 = (胜率 × 平均盈利) - (败率 × 平均亏损)
         = (0.45 × 2.5R) - (0.55 × 1R)
         = 1.125R - 0.55R
         = 0.575R

每笔平均盈利 = 0.575 × (总资金 × 1%) = 0.575% 总资金
```

**年化预期**（每 4 小时交易一次，年交易 2190 次）：
```
年收益 = 2190 × 0.575% ≈ 12.6 倍（理论值，实际受胜率和交易频率影响）
```

### 4. BTC 200 日均线拦截器

**硬性规则**：当 BTC 价格跌破 200 日均线时，系统强制禁止做多任何币种。

```python
if btc_price < btc_ma200 and direction in ("LONG", "LONG-LITE"):
    direction = "CLOSE"  # 强制平仓
```

**逻辑**：BTC 跌破 200 日均线通常预示熊市来临，此时做多风险极高。

---

## 风险管理

### 1. 核心风控参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RISK_PER_TRADE` | 1% | 单笔最大亏损（总资金的 1%） |
| `ATR_MULTIPLIER` | 1.5 | 止损 = 1.5 × ATR14 |
| `MAX_POSITION_PCT` | 30% | 单笔仓位上限 |
| `LITE_POSITION_SCALE` | 0.5 | LITE 信号仓位缩半 |
| `default_leverage` | 1x | 默认不使用杠杆 |

### 2. 三层风控机制

#### 第一层：仓位控制
- 单笔最大亏损固定为总资金的 1%
- 即使连续亏损 10 次，总亏损也仅为 10%

#### 第二层：止损保护
- 每笔交易必须设置止损（1.5×ATR）
- 止损单在开仓时同步下达（reduceOnly）

#### 第三层：系统性风险拦截
- BTC 200 日均线拦截器
- ATR 数据获取失败时强制降级为 CLOSE

### 3. 杠杆策略

**默认不使用杠杆**（1x），通过仓位大小控制风险暴露。

如需使用杠杆，LLM 可输出 2-5x，但系统会限制：
```python
leverage = min(leverage, 125)  # Bitget 最大杠杆限制
```

---

## 系统架构

### 组件图

```
┌─────────────────────────────────────────────────────────────────┐
│                        crypto_main.py                           │
│                    主入口 + 调度器 + 通知                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              CryptoTradingAgentsGraph                           │
│         多智能体图编排（LangGraph）                              │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   分析师智能体    │ │   研究经理        │ │   投资组合经理    │
│  - 技术面         │ │  - 汇总报告       │ │  - 最终决策       │
│  - 宏观/链上      │ │  - 信号质量评估   │ │  - 仓位计算       │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BitgetExecutor                               │
│                  订单执行层（CCXT）                              │
│  - 解析 LLM 决策文本                                             │
│  - 设置杠杆 + 保证金模式                                         │
│  - 下单：入场 + 止损 + 止盈                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Bitget API                                 │
│                   （沙盒 / 实盘）                                │
└─────────────────────────────────────────────────────────────────┘
```

### 智能体角色

| 角色 | 职责 | LLM 模型 |
|------|------|----------|
| 📈 技术面分析师 | K 线、指标、成交量分析 | Qwen-Plus |
| 🌍 宏观/链上分析师 | 订单簿、资金费率、宏观新闻 | Qwen-Plus |
| ⚖️ 研究经理 | 综合两份报告，输出研究结论 | Qwen-Max |
| 💼 交易员 | 生成初步交易计划 | Qwen-Plus |
| 🛡️ 风险经理 | 风险评估（可选） | Qwen-Plus |
| 🎯 投资组合经理 | 最终决策 + 仓位计算 | Qwen-Max |

---

## 安装指南

### 前置要求

- Python 3.10+
- 通义千问 API Key（https://dashscope.console.aliyun.com/）
- Bitget API Key（https://www.bitget.com/zh-CN/account/newcreate）
- （可选）飞书机器人 Webhook

### Step 1: 克隆项目

```bash
git clone <your-repo-url>
cd tradingagent_crypto
```

### Step 2: 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

### Step 3: 安装依赖

```bash
pip install -r requirements.txt
```

或（如果有 uv）：

```bash
uv sync
```

### Step 4: 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# 通义千问 API Key（必填）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Bitget API Key（必填）
BITGET_API_KEY=bg_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BITGET_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BITGET_PASSPHRASE=your_passphrase_here

# 沙盒模式（推荐测试时开启）
BITGET_SANDBOX=true

# 飞书通知（可选）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxxxxxxxxxxxxxxxx

# 交易参数（可选）
CAPITAL_USDT=1000
TIMEFRAME=4h
```

### Step 5: 验证安装

```bash
python crypto_main.py --once --no-execute
```

如果看到分析输出，说明安装成功。

---

## 配置说明

### 核心配置文件

1. **`.env`**：敏感信息（API Key、交易参数）
2. **`tradingagents/default_config.py`**：默认配置（可通过环境变量覆盖）

### 关键配置项

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 交易对 | - | BTC/USDT, ETH/USDT | 可在 `CRYPTO_CONFIG` 中修改 |
| 时间周期 | `TIMEFRAME` | 4h | 4h 或 1d |
| 资金量 | `CAPITAL_USDT` | 1000 | 每笔交易使用的 USDT |
| 沙盒模式 | `BITGET_SANDBOX` | true | true=沙盒，false=实盘 |
| 调试模式 | `DEBUG` | false | true=输出详细日志 |
| 风控参数 | - | 见上文 | 在 `CRYPTO_CONFIG` 中修改 |

### 修改交易对

编辑 `tradingagents/default_config.py`：

```python
CRYPTO_CONFIG = {
    "crypto_symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"],
    # ...
}
```

---

## 使用方法

### 1. 运行一次分析（不执行交易）

```bash
python crypto_main.py --once --no-execute
```

### 2. 运行一次分析并执行交易

```bash
python crypto_main.py --once
```

### 3. 定时运行（每 4 小时）

```bash
python crypto_main.py
```

按 `Ctrl+C` 停止。

### 4. 只分析单个币种

```bash
python crypto_main.py --symbol BTC/USDT:USDT --once
```

### 5. 修改时间周期

```bash
TIMEFRAME=1d python crypto_main.py --once
```

### 6. 查看账户余额

程序启动时会自动显示账户余额（如果 `auto_execute=True`）。

---

## 常见问题

### Q1: 为什么我的交易没有执行？

**可能原因**：
1. `--no-execute` 参数被设置
2. `BITGET_SANDBOX=true` 但未在 Bitget 沙盒账户中开启 Demo Trading
3. API Key 配置错误
4. ATR 数据获取失败（系统自动降级为 CLOSE）

**解决方法**：
- 检查 `.env` 中的 API Key 是否正确
- 登录 Bitget 沙盒账户，确认已开启 Demo Trading
- 查看日志文件 `crypto_trading.log`

### Q2: 如何切换到实盘交易？

**警告**：实盘交易有风险，请确保充分理解策略后再切换。

1. 在 `.env` 中设置：
   ```ini
   BITGET_SANDBOX=false
   ```
2. 确认 API Key 有交易权限
3. 先用小资金测试（`CAPITAL_USDT=100`）

### Q3: 如何调整风险参数？

编辑 `tradingagents/default_config.py` 中的 `CRYPTO_CONFIG`：

```python
CRYPTO_CONFIG = {
    "risk_per_trade": 0.02,      # 改为 2%
    "atr_multiplier": 2.0,       # 改为 2×ATR
    "max_position_pct": 0.50,    # 改为 50%
    # ...
}
```

### Q4: 飞书通知不工作？

1. 确认 Webhook 地址正确（包含完整的 `https://`）
2. 确认飞书机器人已添加到群聊
3. 检查防火墙是否允许出站 HTTPS 请求

### Q5: 如何查看历史交易记录？

交易记录保存在 `~/.tradingbot/trade_history.json`：

```bash
cat ~/.tradingbot/trade_history.json | jq
```

### Q6: 胜率太低怎么办？

本系统设计为**趋势跟踪策略**，典型胜率 40-50%，依靠高盈亏比盈利。

如果胜率持续低于 35%：
1. 检查是否在市场震荡期运行（趋势策略在震荡市会失效）
2. 考虑切换到日线周期（`TIMEFRAME=1d`）
3. 增加 BTC 200 日均线过滤（已内置）

---

## 免责声明

**本软件仅供学习和研究使用，不构成投资建议。**

加密货币合约交易具有极高风险，可能导致本金全部损失。使用本软件进行交易的一切后果由用户自行承担。

作者不对任何直接或间接损失承担责任。请在充分理解策略逻辑和风险后再考虑是否使用实盘资金。

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 联系方式

- 项目地址：[GitHub Repo]
- 问题反馈：[Issues]
