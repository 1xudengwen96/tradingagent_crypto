# 加密货币合约交易系统 — 改造进度表

## 项目目标
将 TradingAgents 多智能体股票交易框架改造为专门交易 BTC/USDT:USDT 和 ETH/USDT:USDT 永续合约的系统，部署在 Bitget 交易所（沙盒模式）。

---

## 总体架构

```
数据层(CCXT/Bitget) → 工具层(@tool) → 智能体层(LangGraph) → 执行层(BitgetExecutor)
         ↑                                        ↑
   bitget_vendor.py                    CryptoTradingAgentsGraph
   crypto_tools.py                       crypto_main.py (APScheduler)
```

**双 LLM 配置：**
- 深度思考：Claude Opus 4.6（研究经理 + 组合管理者）
- 快速响应：GPT-4o-mini（分析师 + 交易员 + 辩论者）

**决策输出格式：**
`LONG / LONG-LITE / SHORT / SHORT-LITE / CLOSE` + 杠杆 + 止损 + 止盈1/2 + 仓位大小

---

## 任务进度

### ✅ Task 1 & 2 — Bitget 数据层
**文件：** `tradingagents/dataflows/bitget_vendor.py`

实现函数：
- `get_bitget_exchange()` — CCXT 单例，支持沙盒模式
- `get_crypto_ohlcv(symbol, timeframe, limit)` — K线数据
- `get_crypto_indicators(symbol, timeframe, limit)` — SMA/EMA/MACD/RSI/BB/ATR/VWMA（pandas 自计算）
- `get_funding_rate(symbol)` — 当前 + 历史资金费率
- `get_orderbook(symbol, depth)` — 买卖盘压力分析
- `get_open_interest(symbol)` — 持仓量 + 趋势解读
- `get_crypto_ticker(symbol)` — 价格快照
- `get_crypto_news(coin, limit)` — CryptoPanic API
- `get_crypto_global_news(limit)` — 全球加密新闻

---

### ✅ Task 3 — LangChain 工具层
**文件：** `tradingagents/agents/utils/crypto_tools.py`

8个 `@tool` 装饰器函数，通过 `route_to_vendor()` 路由到 Bitget 数据层。

**文件：** `tradingagents/dataflows/interface.py`（已修改）
- 新增 `crypto_data` 分类到 `TOOLS_CATEGORIES`
- 新增 `bitget` 到 `VENDOR_LIST`
- 新增 8 个 crypto 方法到 `VENDOR_METHODS`

---

### ✅ Task 4 — 所有智能体（加密货币版 Prompt）

| 文件 | 智能体 | 输出字段 |
|------|--------|---------|
| `agents/analysts/crypto_market_analyst.py` | 技术分析师 | `market_report` |
| `agents/analysts/crypto_sentiment_analyst.py` | 情绪分析师 | `sentiment_report` |
| `agents/analysts/crypto_news_analyst.py` | 新闻分析师 | `news_report` |
| `agents/analysts/crypto_onchain_analyst.py` | 链上/微观结构分析师 | `fundamentals_report` |
| `agents/researchers/crypto_bull_researcher.py` | 多头研究员 | `investment_debate_state` |
| `agents/researchers/crypto_bear_researcher.py` | 空头研究员 | `investment_debate_state` |
| `agents/managers/crypto_research_manager.py` | 研究主管（Claude Opus） | `investment_plan` |
| `agents/trader/crypto_trader.py` | 交易员 | `trader_investment_plan` |
| `agents/risk_mgmt/crypto_aggressive_debator.py` | 激进风险分析师 | `risk_debate_state` |
| `agents/risk_mgmt/crypto_conservative_debator.py` | 保守风险分析师 | `risk_debate_state` |
| `agents/risk_mgmt/crypto_neutral_debator.py` | 中立风险分析师 | `risk_debate_state` |
| `agents/managers/crypto_portfolio_manager.py` | 组合管理者（Claude Opus） | `final_trade_decision` |

---

### ✅ Task 5 — Bitget 合约执行器
**文件：** `tradingagents/execution/bitget_executor.py`
**文件：** `tradingagents/execution/__init__.py`

- `SignalParser.parse(text)` — 正则提取方向/杠杆/仓位/入场/止损/止盈
- `BitgetExecutor.execute(signal, symbol, capital_usdt)` — 调用 CCXT API
  - `set_margin_mode()` → `set_leverage()` → 计算合约数量 → `create_order()`
  - 止损单（stop-loss, reduce-only）
  - 止盈单 TP1（50%仓位）+ TP2（剩余仓位）
  - `close_all_positions()` — 市价平仓 + 撤销所有挂单

---

### ✅ Task 6 — 配置、图结构和主入口

| 文件 | 状态 | 说明 |
|------|------|------|
| `tradingagents/default_config.py` | ✅ 完成 | 新增 `CRYPTO_CONFIG` 字典（符号/API密钥/沙盒/杠杆/LLM配置） |
| `tradingagents/graph/crypto_setup.py` | ✅ 完成 | `CryptoGraphSetup` — 装配加密货币版 StateGraph |
| `tradingagents/graph/crypto_trading_graph.py` | ✅ 完成 | `CryptoTradingAgentsGraph` — 主类，`run(symbol)` 一键分析+执行 |
| `tradingagents/agents/__init__.py` | ✅ 完成 | 新增所有 crypto agent 工厂函数的导出 |
| `crypto_main.py` | ✅ 完成 | 主入口，APScheduler 定时（默认每4小时），支持 `--once` / `--no-execute` |

---

## 待办 / 已知问题

### ⚠️ 尚未验证（需要 API 密钥才能完整测试）
- [ ] `bitget_vendor.py` 中的 CCXT 调用（需要 Bitget sandbox API key）
- [ ] `BitgetExecutor` 止损单参数格式是否与 Bitget API 完全兼容（不同交易所 stop order 参数有差异）
- [ ] CryptoPanic API 速率限制（无 key 时 60次/小时）

### 🔧 运行前需要设置的环境变量
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export BITGET_API_KEY="your_sandbox_api_key"
export BITGET_SECRET="your_sandbox_secret"
export BITGET_PASSPHRASE="your_sandbox_passphrase"
export CRYPTOPANIC_API_KEY="optional_for_higher_rate_limit"
```

### 📦 依赖安装
```bash
pip install ccxt apscheduler langchain-anthropic requests pandas numpy
```

---

## 运行方式

```bash
# 立即分析一次（不下单）
python crypto_main.py --once --no-execute

# 立即分析一次（沙盒下单）
python crypto_main.py --once

# 定时运行（每4小时，沙盒下单）
python crypto_main.py

# 只看 BTC，每2小时
python crypto_main.py --symbol BTC/USDT:USDT --interval-hours 2

# 关闭自动下单
python crypto_main.py --no-execute
```

---

## 文件树（新增/修改的文件）

```
TradingAgents/
├── crypto_main.py                          ✅ 新增
└── tradingagents/
    ├── default_config.py                   ✅ 修改（新增 CRYPTO_CONFIG）
    ├── agents/
    │   ├── __init__.py                     ✅ 修改（新增 crypto 导出）
    │   ├── analysts/
    │   │   ├── crypto_market_analyst.py    ✅ 新增
    │   │   ├── crypto_sentiment_analyst.py ✅ 新增
    │   │   ├── crypto_news_analyst.py      ✅ 新增
    │   │   └── crypto_onchain_analyst.py   ✅ 新增
    │   ├── researchers/
    │   │   ├── crypto_bull_researcher.py   ✅ 新增
    │   │   └── crypto_bear_researcher.py   ✅ 新增
    │   ├── managers/
    │   │   ├── crypto_research_manager.py  ✅ 新增
    │   │   └── crypto_portfolio_manager.py ✅ 新增
    │   ├── trader/
    │   │   └── crypto_trader.py            ✅ 新增
    │   ├── risk_mgmt/
    │   │   ├── crypto_aggressive_debator.py  ✅ 新增
    │   │   ├── crypto_conservative_debator.py ✅ 新增
    │   │   └── crypto_neutral_debator.py    ✅ 新增
    │   └── utils/
    │       └── crypto_tools.py             ✅ 新增
    ├── dataflows/
    │   ├── bitget_vendor.py                ✅ 新增
    │   └── interface.py                    ✅ 修改（新增 crypto_data + bitget）
    ├── execution/
    │   ├── __init__.py                     ✅ 新增
    │   └── bitget_executor.py              ✅ 新增
    └── graph/
        ├── crypto_setup.py                 ✅ 新增
        └── crypto_trading_graph.py         ✅ 新增
```

---

*最后更新：2026-04-01*
