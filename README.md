# TradingAgents Crypto — AI 多智能体加密货币合约交易系统

> 基于 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) v0.2.3 扩展开发  
> 论文：[TradingAgents: Multi-Agents LLM Financial Trading Framework](https://arxiv.org/abs/2412.20138)

将原始股票交易框架改造为专门交易 **BTC/ETH/SOL/XRP/DOGE/BNB/XAU/XAG 永续合约**的 AI 系统，部署在 Bitget 交易所（支持沙盒/实盘），并提供 Web 管理界面和飞书通知。

---

## 核心架构

```
Bitget 行情数据
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                   分析师层（串行）                    │
│  📊 市场分析师   📰 新闻分析师                        │
│  💬 情绪分析师   🔗 链上/微观结构分析师                │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────┴────────┐
              │   研究员辩论     │
              │  🐂 多头研究员   │
              │  🐻 空头研究员   │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  研究经理（Claude Sonnet）  │  ← 综合研究报告
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │     交易员       │  ← 生成初始交易计划
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              │   风险辩论三方   │
              │  ⚡ 激进分析师   │
              │  🛡️ 保守分析师   │
              │  ⚖️ 中立分析师   │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │ 组合管理者（Claude Sonnet）│  ← 最终交易决策
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  BitgetExecutor  │  ← 解析信号 + 下单
              │  市价单 + 止损   │
              │  止盈TP1 + TP2   │
              └─────────────────┘
                       │
              ┌────────▼────────┐
              │  飞书 Webhook    │  ← 推送分析结果到飞书群
              └─────────────────┘
```

**决策输出格式示例：**
```
DIRECTION: LONG
LEVERAGE: 5x
ENTRY: 市价
STOP_LOSS: 65000
TAKE_PROFIT_1: 68000  (平仓 50% 仓位)
TAKE_PROFIT_2: 71000  (平仓剩余仓位)
POSITION_SIZE: 20%
```

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 🤖 AI 多智能体分析 | 4 位分析师 → 研究员辩论 → 交易员 → 风险辩论 → 组合管理者 |
| 📊 Web 管理界面 | 仪表盘、API 配置、交易设置、持仓查看、日志查看 |
| 🔔 飞书通知 | 每次分析结果自动推送到飞书群（含决策 + 订单状态） |
| 📈 合约交易 | 支持 BTC/ETH/SOL/XRP/DOGE/BNB/XAU/XAG 永续合约 |
| 🎮 沙盒/实盘 | 模拟盘测试策略，确认后一键切换实盘 |
| ⏰ 定时调度 | 可自定义分析间隔（1h/2h/4h/6h/12h/24h） |
| 🏗️ 多 LLM 支持 | Anthropic Claude / OpenAI GPT / 通义千问 Qwen |

---

## 技术栈

| 层次 | 技术 |
|------|------|
| AI 框架 | LangChain + LangGraph（StateGraph 多智能体编排） |
| LLM（深度分析） | Claude Sonnet（研究经理 + 组合管理者） |
| LLM（快速决策） | Claude Haiku（分析师 + 交易员 + 辩论者） |
| 交易所 | Bitget 永续合约（via CCXT） |
| 数据源 | Bitget OHLCV、资金费率、订单簿、持仓量 |
| 新闻数据 | CryptoPanic API |
| 技术指标 | pandas 自计算（SMA/EMA/MACD/RSI/BB/ATR/VWMA） |
| 定时调度 | APScheduler |
| Web 后端 | FastAPI + Uvicorn |
| Web 前端 | 单页应用（SSE 日志流） |
| 消息通知 | 飞书 Webhook（Interactive Card） |
| Python | ≥ 3.10 |

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/1xudengwen96/tradingagent_crypto.git
cd tradingagent_crypto
```

### 2. 安装依赖

推荐使用 `uv`（项目自带 uv.lock 锁文件）：

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# 安装所有项目依赖（自动创建虚拟环境 .venv/）
uv sync

# 安装加密货币额外依赖
uv pip install ccxt apscheduler requests fastapi uvicorn
```

或使用 pip：

```bash
pip install -e .
pip install ccxt apscheduler requests fastapi uvicorn
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少填写以下内容：

```bash
# LLM（推荐同时填写，仅填 Anthropic 也可运行）
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx        # 可选

# Bitget API（沙盒或实盘均可）
BITGET_API_KEY=bg_xxxxx
BITGET_SECRET=xxxxx
BITGET_PASSPHRASE=xxxxx
BITGET_SANDBOX=true            # 测试时保持 true
```

> **如何获取 Bitget Sandbox API Key：**
> 1. 注册 [Bitget](https://www.bitget.com) 账号
> 2. 切换到 **Demo Trading（模拟交易）** 模式
> 3. 进入 API 管理 → 创建 API Key，选择永续合约读写权限

### 4. 运行

#### 命令行模式

```bash
# 推荐：首次运行，只分析不下单，看看 AI 决策质量
uv run python crypto_main.py --once --no-execute

# 分析并在沙盒模式下单（需要 Bitget API Key）
uv run python crypto_main.py --once

# 只分析 BTC，不下单
uv run python crypto_main.py --once --no-execute --symbol BTC/USDT:USDT

# 定时运行（默认每 4 小时自动分析一次）
uv run python crypto_main.py

# 每 2 小时运行一次
uv run python crypto_main.py --interval-hours 2
```

#### Web UI 模式（推荐）

```bash
# 启动 Web 服务（默认 0.0.0.0:8000）
python server.py

# 自定义端口
python server.py --port 9000
```

然后浏览器打开 `http://localhost:8000`，在 Web 界面中完成所有配置和管理。

---

## Web 界面说明

Web 界面包含以下功能模块：

| 模块 | 功能 |
|------|------|
| 📊 仪表盘 | 账户余额、可用余额、持仓数量、运行时间、快速启停 |
| 🔑 API 配置 | Bitget API 密钥、LLM API 密钥、连接测试 |
| ⚙️ 交易设置 | 交易模式（沙盒/实盘）、交易对多选、资金量、分析间隔、LLM 选择、飞书 Webhook |
| 📈 持仓 | 当前持仓列表（方向、数量、开仓价、标记价、未实现盈亏、杠杆） |
| 📝 日志 | 实时 SSE 日志流，支持按级别过滤和下载 |

### 交易对多选

在「交易设置」页面，通过多选下拉框选择要交易品种：
- BTC/USDT（比特币）
- ETH/USDT（以太坊）
- SOL/USDT（Solana）
- XRP/USDT（瑞波）
- DOGE/USDT（狗狗币）
- BNB/USDT（币安币）
- XAU/USDT（黄金）
- XAG/USDT（白银）

### 飞书通知

1. 在飞书群中添加自定义机器人，获取 Webhook URL
2. 在「交易设置」页面填入飞书 Webhook URL
3. 点击「测试飞书通知」验证连接
4. 每次 AI 分析完成后，分析结果自动推送到飞书群

### 分析间隔

选择分析间隔后，**需要停止并重新启动 Bot** 才能生效。例如选择「每 1 小时」后：
1. 点击「停止机器人」
2. 点击「保存设置」
3. 点击「启动机器人」

---

## 项目结构

```
tradingagent_crypto/
├── crypto_main.py                           # 主入口（APScheduler 定时驱动 + 飞书通知）
├── server.py                                # Web 后端（FastAPI API + 前端服务）
├── .env.example                             # 环境变量配置模板
├── pyproject.toml                           # 项目依赖声明
├── CRYPTO_PROGRESS.md                       # 开发进度记录
│
└── tradingagents/
    ├── default_config.py                    # 默认配置（含 CRYPTO_CONFIG）
    │
    ├── agents/
    │   ├── analysts/
    │   │   ├── crypto_market_analyst.py     # 技术分析师（K线 + 指标）
    │   │   ├── crypto_sentiment_analyst.py  # 情绪分析师（资金费率 + 新闻情绪）
    │   │   ├── crypto_news_analyst.py       # 新闻分析师（宏观 + 币种新闻）
    │   │   └── crypto_onchain_analyst.py    # 链上/微观结构分析师（订单簿 + OI）
    │   ├── researchers/
    │   │   ├── crypto_bull_researcher.py    # 多头研究员（做多论据）
    │   │   └── crypto_bear_researcher.py    # 空头研究员（做空论据）
    │   ├── managers/
    │   │   ├── crypto_research_manager.py   # 研究经理（综合研究裁决）
    │   │   └── crypto_portfolio_manager.py  # 组合管理者（最终交易决策）
    │   ├── trader/
    │   │   └── crypto_trader.py             # 交易员（初始交易计划）
    │   ├── risk_mgmt/
    │   │   ├── crypto_aggressive_debator.py # 激进风险分析师
    │   │   ├── crypto_conservative_debator.py # 保守风险分析师
    │   │   └── crypto_neutral_debator.py    # 中立风险分析师
    │   └── utils/
    │       └── crypto_tools.py              # LangChain @tool 数据工具集
    │
    ├── dataflows/
    │   ├── bitget_vendor.py                 # Bitget 数据层（CCXT 封装）
    │   └── interface.py                     # 数据路由接口
    │
    ├── execution/
    │   └── bitget_executor.py               # 信号解析 + Bitget 合约下单执行器
    │
    └── graph/
        ├── crypto_setup.py                  # LangGraph StateGraph 装配器
        └── crypto_trading_graph.py          # 主图类（CryptoTradingAgentsGraph）
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取当前配置（密钥已脱敏） |
| GET | `/api/config/full` | 获取完整配置（含密钥） |
| POST | `/api/config` | 保存配置 |
| POST | `/api/config/validate` | 测试 API 密钥连通性 |
| POST | `/api/bot/start` | 启动 Bot |
| POST | `/api/bot/stop` | 停止 Bot |
| GET | `/api/bot/status` | 获取 Bot 状态 |
| GET | `/api/account/balance` | 获取合约账户余额 |
| GET | `/api/account/positions` | 获取当前持仓 |
| GET | `/api/logs/tail` | 获取最近 N 行日志 |
| GET | `/api/logs/stream` | SSE 实时日志流 |
| POST | `/api/feishu/test` | 测试飞书 Webhook 连通性 |

---

## 配置说明

所有核心参数在 `tradingagents/default_config.py` 的 `CRYPTO_CONFIG` 中调整：

```python
CRYPTO_CONFIG = {
    # 交易对（Bitget 永续合约格式）
    "crypto_symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],

    # 交易所设置
    "sandbox_mode": True,          # False = 切换实盘（危险！）
    "margin_mode": "isolated",     # "isolated"（逐仓）| "cross"（全仓）
    "default_leverage": 5,         # 解析失败时的兜底杠杆

    # 数据设置
    "timeframe": "1h",             # K 线周期：1m/5m/15m/1h/4h/1d
    "candle_limit": 200,           # 每次拉取的 K 线数量

    # 资金管理
    "capital_usdt": 1000.0,        # 账户总资金（用于计算仓位大小）

    # LLM 配置
    "deep_think_llm": "claude-sonnet-4-5",   # 研究经理 + 组合管理者
    "quick_think_llm": "claude-haiku-4-5",   # 分析师 + 交易员 + 辩论者

    # 辩论轮次（增大可提升决策质量，但会增加 API 消耗）
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
}
```

---

## 数据工具说明

| 工具函数 | 数据来源 | 用途 |
|---------|---------|------|
| `get_crypto_ohlcv` | Bitget CCXT | K 线数据（OHLCV） |
| `get_crypto_indicators` | pandas 自计算 | SMA/EMA/MACD/RSI/布林带/ATR/VWMA |
| `get_crypto_ticker` | Bitget CCXT | 实时价格快照 |
| `get_funding_rate` | Bitget CCXT | 当前 + 历史资金费率（多空博弈信号）|
| `get_orderbook` | Bitget CCXT | 买卖盘深度分析（流动性判断）|
| `get_open_interest` | Bitget CCXT | 持仓量 + 趋势（市场情绪强弱）|
| `get_crypto_news` | CryptoPanic API | 特定币种新闻 |
| `get_crypto_global_news` | CryptoPanic API | 全球加密市场宏观新闻 |

---

## 执行层说明

`BitgetExecutor` 收到组合管理者的决策文本后自动执行：

1. **`SignalParser.parse()`** — 正则提取方向 / 杠杆 / 止损 / 止盈 / 仓位比例
2. 计算合约数量：`capital × position_pct ÷ entry_price ÷ contract_size`
3. 设置保证金模式 + 杠杆
4. 市价开仓
5. 设置止损单（`reduce-only`，保护本金）
6. 设置止盈 TP1（平仓 50% 仓位）+ TP2（平仓剩余仓位）

**CLOSE 信号处理**：市价平仓所有当前持仓 + 撤销所有挂单

---

## 飞书通知格式

每次分析完成后，飞书群会收到一条交互式卡片消息：

```
📊 BTC/USDT:USDT 分析报告

[AI 分析决策内容...]
─────────────────
执行状态：✅ 已下单 / ⏸️ 仅分析 / ❌ 下单失败
时间：2026-04-06 12:00 UTC
```

---

## 运行日志

每次分析结果自动保存到以下位置：

| 位置 | 内容 |
|------|------|
| 终端 stdout | 实时进度 + 最终决策摘要 |
| `crypto_trading.log` | 追加模式的完整日志 |
| Web 界面「日志」页 | 实时 SSE 日志流 |
| `crypto_results/<symbol>/logs/state_<datetime>.json` | 每个智能体的完整输出（便于调试审计）|

---

## 常见问题

**Q: 只有 Anthropic API Key，没有 OpenAI Key 怎么办？**  
A: 在 `tradingagents/default_config.py` 中，`CRYPTO_CONFIG` 的 `quick_think_llm_provider` 已设为 `"anthropic"`，所有智能体都会使用 Claude，无需 OpenAI Key。

**Q: CryptoPanic 新闻拉取失败？**  
A: 无 API Key 时公共接口限速 60次/小时。建议在 [cryptopanic.com](https://cryptopanic.com/developers/api/) 免费申请 Key 后填入 `CRYPTOPANIC_API_KEY`。

**Q: Bitget 止损单下单报错？**  
A: 不同 ccxt 版本的 stop order 参数格式可能有差异。请检查 ccxt 版本（`ccxt.__version__`）并参考 [CCXT Bitget 文档](https://docs.ccxt.com/#/?id=bitget)。

**Q: 如何切换到实盘？**  
A: 在 Web 界面「交易设置」页面关闭沙盒开关，并换用实盘 API Key，确保账户有足够 USDT 保证金。**请务必充分测试后再切换！**

**Q: 修改分析间隔后没有生效？**  
A: 需要停止并重新启动 Bot 才会使用新的间隔。修改间隔 → 保存设置 → 停止 Bot → 启动 Bot。

**Q: 飞书通知收不到？**  
A: 检查 Webhook URL 是否正确，点击「测试飞书通知」按钮验证。确认飞书群的机器人权限已开启。

---

## 免责声明

> ⚠️ **风险提示**：本项目仅供学习和研究使用。加密货币合约交易存在极高风险，AI 决策不保证盈利。在使用实盘模式前，请充分了解杠杆交易风险，设置合理的止损，并只投入自己能承受损失的资金。

---

## License

MIT License

基于 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) 开源项目扩展开发，原始框架论文：[arXiv:2412.20138](https://arxiv.org/abs/2412.20138)。
