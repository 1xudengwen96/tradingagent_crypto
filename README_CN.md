# TradingAgents Crypto — AI 多智能体加密货币合约交易系统

> **基于 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) v0.2.3 扩展开发**  
> **论文**: [TradingAgents: Multi-Agents LLM Financial Trading Framework](https://arxiv.org/abs/2412.20138)

将原始股票交易框架改造为专门交易 **BTC/ETH/SOL/XRP/DOGE/BNB/XAU/XAG 永续合约** 的 AI 系统，部署在 Bitget 交易所（支持沙盒/实盘），并提供 Web 管理界面和飞书通知。

---

## 📋 目录

- [核心架构](#核心架构)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [Web 界面使用指南](#web 界面使用指南)
- [命令行使用指南](#命令行使用指南)
- [配置说明](#配置说明)
- [飞书通知配置](#飞书通知配置)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [风险提示](#风险提示)

---

## 🏗️ 核心架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        Bitget 行情数据源                          │
│              OHLCV | 资金费率 | 订单簿 | 持仓量 | 新闻            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      分析师层（串行执行）                         │
│  📊 市场分析师 → 📰 新闻分析师 → 😊 情绪分析师 → 🔗 链上分析师   │
│     (K 线 + 指标)   (宏观 + 新闻)   (资金费率)    (订单簿+OI)      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                        研究员辩论层                               │
│                    🐂 多头研究员 vs 🐻 空头研究员                  │
│                    （多轮辩论生成投资论据）                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      研究经理（Qwen-Max）                         │
│              综合多空辩论，生成中立研究报告                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                        交易员（Qwen-Plus）                        │
│              根据研究报告生成初始交易计划                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      风险辩论层（三方辩论）                       │
│           ⚡ 激进分析师  vs  🛡️ 保守分析师  vs  ⚖️ 中立分析师    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   组合管理者（Qwen-Max）                          │
│              综合风险评估，生成最终交易决策                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      BitgetExecutor 执行器                       │
│   解析信号 → 计算仓位 → 设置保证金模式 + 杠杆 → 市价开仓          │
│              → 设置止损单 → 设置止盈 TP1/TP2                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    飞书 Webhook 通知                             │
│              推送分析结果和订单状态到飞书群                        │
└──────────────────────────────────────────────────────────────────┘
```

### 决策输出格式示例

```
交易对：BTC/USDT:USDT
时间：2026-04-17 08:00 UTC

📊 市场分析：...
📰 新闻分析：...
😊 情绪分析：...

🐂 多头观点：...
🐻 空头观点：...
⚖️ 研究经理裁决：...

💼 交易员建议：...

🛡️ 风险评估：...

🎯 最终决策：
─────────────────
DIRECTION: LONG
LEVERAGE: 5x
ENTRY: 市价
STOP_LOSS: 65000
TAKE_PROFIT_1: 68000  (平仓 50% 仓位)
TAKE_PROFIT_2: 71000  (平仓剩余仓位)
POSITION_SIZE: 20%
─────────────────

执行状态：✅ 已下单
订单 ID: 12345678, 12345679, 12345680
```

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🤖 **AI 多智能体分析** | 4 位分析师 → 研究员辩论 → 交易员 → 风险辩论 → 组合管理者，模拟真实投行决策流程 |
| 📊 **Web 管理界面** | 仪表盘、API 配置、交易设置、持仓查看、日志查看，一站式管理 |
| 🔔 **飞书通知** | 每次分析结果自动推送到飞书群（含决策 + 订单状态），支持多角色独立通知 |
| 📈 **合约交易** | 支持 BTC/ETH/SOL/XRP/DOGE/BNB/XAU/XAG 永续合约 |
| 🎮 **沙盒/实盘** | 模拟盘测试策略，确认后一键切换实盘 |
| ⏰ **定时调度** | 可自定义分析间隔（1h/2h/4h/6h/12h/24h），4H/1D 中线交易专用 |
| 🏗️ **多 LLM 支持** | 通义千问 Qwen（qwen-max 深度分析 + qwen-plus 快速决策） |
| 📝 **日志持久化** | 实时日志流 + 文件存储 + 交易历史记录，便于复盘审计 |

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/1xudengwen96/tradingagent_crypto.git
cd tradingagent_crypto
```

### 2. 安装依赖

**推荐使用 `uv`**（项目自带 uv.lock 锁文件，安装更快更稳定）：

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# 安装所有项目依赖（自动创建虚拟环境 .venv/）
uv sync
```

**或使用 pip**：

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e .
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，**至少填写以下内容**：

```bash
# =============================================================================
# 1. LLM API - 通义千问（唯一 AI 提供商）
# 获取地址：https://dashscope.console.aliyun.com/
# =============================================================================
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# =============================================================================
# 2. Bitget 交易所 API（沙盒或实盘）
# 获取地址：https://www.bitget.com/zh-CN/account/newcreate
# =============================================================================
BITGET_API_KEY=bg_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BITGET_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BITGET_PASSPHRASE=your_passphrase_here

# true = 沙盒模式（推荐测试时使用），false = 实盘交易（谨慎！）
BITGET_SANDBOX=true

# =============================================================================
# 3. 飞书通知（可选，但强烈推荐）
# 获取地址：在飞书群聊中添加自定义机器人，复制 Webhook 地址
# =============================================================================
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxxxxxxxxxxxxxxxx
```

> **💡 如何获取 Bitget Sandbox API Key：**
> 1. 注册 [Bitget](https://www.bitget.com) 账号
> 2. 切换到 **Demo Trading（模拟交易）** 模式
> 3. 进入 **API 管理** → 创建 API Key，选择永续合约读写权限

### 4. 运行

#### 方式一：Web UI 模式（推荐新手）

```bash
# 启动 Web 服务（默认 0.0.0.0:8000）
python server.py

# 自定义端口
python server.py --port 9000
```

然后浏览器打开 `http://localhost:8000`，在 Web 界面中完成所有配置和管理。

#### 方式二：命令行模式

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

---

## 🖥️ Web 界面使用指南

启动 `python server.py` 后，浏览器访问 `http://localhost:8000`。

### 1. 仪表盘

显示核心信息：
- 账户总余额（USDT）
- 可用余额
- 持仓数量
- 运行时间
- 机器人状态（运行中/已停止）
- 快速启停按钮

### 2. API 配置

**敏感配置，仅后端存储，前端不显示明文**：

| 字段 | 说明 | 获取方式 |
|------|------|----------|
| Bitget API Key | 交易所 API 密钥 | Bitget API 管理 |
| Bitget Secret | API 密钥密码 | Bitget API 管理 |
| Bitget Passphrase | API 密钥口令 | Bitget API 管理 |
|  DashScope API Key | 通义千问 API 密钥 | 阿里云百炼控制台 |

填写后点击 **「测试连接」** 验证 API 密钥有效性。

### 3. 交易设置

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| 交易模式 | 沙盒/实盘切换 | 新手保持沙盒 |
| 交易对 | 多选：BTC/ETH/SOL/XRP/DOGE/BNB/XAU/XAG | BTC + ETH |
| 账户总资金 | 用于计算仓位大小（USDT） | 1000 |
| 分析间隔 | 定时分析频率 | 4 小时 |
| K 线周期 | 技术分析周期 | 4h / 1d |
| 深度分析模型 | 研究经理 + 组合管理者使用的模型 | qwen-max |
| 快速决策模型 | 分析师 + 交易员使用的模型 | qwen-plus |
| 飞书 Webhook | 通知推送地址 | 可选 |

**注意**：修改分析间隔后，**需要停止并重新启动 Bot** 才能生效。

### 4. 持仓

显示当前所有持仓：
- 交易对
- 方向（多/空）
- 持仓数量
- 开仓均价
- 标记价格
- 未实现盈亏
- 杠杆倍数

### 5. 日志

- **实时日志流**：SSE 实时推送分析进度
- **日志级别过滤**：INFO / WARNING / ERROR
- **下载日志**：导出最近日志文件

---

## 💻 命令行使用指南

### 基本用法

```bash
# 定时运行（每 4 小时分析一次）
python crypto_main.py

# 只运行一次，然后退出
python crypto_main.py --once

# 只分析，不下单（推荐首次测试）
python crypto_main.py --once --no-execute

# 只分析特定币种
python crypto_main.py --once --symbol BTC/USDT:USDT

# 自定义分析间隔（每 2 小时）
python crypto_main.py --interval-hours 2
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--once` | 只运行一次后退出 | 否 |
| `--symbol` | 指定交易对 | 配置文件全部 |
| `--no-execute` | 只分析，不下单 | 否 |
| `--interval-hours` | 分析间隔（小时） | 4 |

---

## ⚙️ 配置说明

所有核心参数在 `tradingagents/default_config.py` 的 `CRYPTO_CONFIG` 中：

```python
CRYPTO_CONFIG = {
    # 交易对（Bitget 永续合约格式）
    "crypto_symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],

    # 交易所设置
    "sandbox_mode": True,          # False = 切换实盘（危险！）
    "margin_mode": "isolated",     # "isolated"（逐仓）| "cross"（全仓）
    "default_leverage": 1,         # 不使用杠杆（通过仓位控制风险）

    # 数据设置
    "timeframe": "4h",             # K 线周期：4h / 1d
    "candle_limit": 200,           # 每次拉取的 K 线数量

    # 资金管理
    "capital_usdt": 1000.0,        # 账户总资金（用于计算仓位大小）
    "risk_per_trade": 0.01,        # 单笔最大亏损（总资金的 1%）
    "atr_multiplier": 1.5,         # 止损 = 1.5 × ATR14
    "tp1_risk_reward": 2.0,        # 止盈 1 盈亏比
    "tp2_risk_reward": 3.5,        # 止盈 2 盈亏比
    "max_position_pct": 0.30,      # 单笔仓位上限（30%）

    # LLM 配置
    "deep_think_llm": "qwen-max",   # 研究经理 + 组合管理者
    "quick_think_llm": "qwen-plus", # 分析师 + 交易员 + 辩论者
    "dashscope_api_key": "",        # 通义千问 API Key

    # 辩论轮次（增大可提升决策质量，但会增加 API 消耗）
    "max_debate_rounds": 0,
    "max_risk_discuss_rounds": 0,

    # CryptoPanic 新闻 API（可选）
    "cryptopanic_api_key": "",
}
```

---

## 🔔 飞书通知配置

### 单一通知模式（简单）

1. 在飞书群中添加 **自定义机器人**
2. 复制 Webhook URL
3. 在 `.env` 或 Web 界面填入 `FEISHU_WEBHOOK_URL`

### 多角色通知模式（推荐）

为不同角色创建独立机器人，实现精细化通知：

| 角色 | Webhook 环境变量 | 通知内容 |
|------|------------------|----------|
| 📈 市场分析师 | `FEISHU_WEBHOOK_ANALYST` | 技术分析报告 |
| 📰 新闻分析师 | `FEISHU_WEBHOOK_NEWS` | 新闻分析报告 |
| 😊 情绪分析师 | `FEISHU_WEBHOOK_SENTIMENT` | 情绪分析结果 |
| 💎 基本面分析师 | `FEISHU_WEBHOOK_FUNDAMENTALS` | 基本面/链上数据 |
| ⚖️ 研究经理 | `FEISHU_WEBHOOK_MANAGER` | 多空辩论综合裁决 |
| 🛡️ 风险经理 | `FEISHU_WEBHOOK_RISK` | 风险评估 |
| 🎯 交易员 | `FEISHU_WEBHOOK_TRADER` | 最终交易决策 |
| 通用通知 | `FEISHU_WEBHOOK_URL` | 后备通知渠道 |

**详细搭建指南**：参考 `FEISHU_MULTI_BOT_GUIDE.md`

---

## 📁 项目结构

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
    │   │   ├── crypto_market_analyst.py     # 技术分析师（K 线 + 指标）
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

## ❓ 常见问题

### Q: 只有通义千问 API Key，没有 OpenAI/Claude Key 怎么办？

**A**: 本项目已完全适配通义千问，无需其他 LLM Key。在 `tradingagents/default_config.py` 中，`CRYPTO_CONFIG` 已默认配置为使用 Qwen。

### Q: CryptoPanic 新闻拉取失败？

**A**: 无 API Key 时公共接口限速 60 次/小时。建议在 [cryptopanic.com](https://cryptopanic.com/developers/api/) 免费申请 Key 后填入 `CRYPTOPANIC_API_KEY`。

### Q: Bitget 止损单下单报错？

**A**: 不同 ccxt 版本的 stop order 参数格式可能有差异。请检查 ccxt 版本（`ccxt.__version__`）并参考 [CCXT Bitget 文档](https://docs.ccxt.com/#/?id=bitget)。

### Q: 如何切换到实盘？

**A**: 
1. 在 Web 界面「交易设置」页面关闭沙盒开关
2. 换用实盘 API Key（**不要使用沙盒 Key**）
3. 确保账户有足够 USDT 保证金
4. **请务必充分测试后再切换！**

### Q: 修改分析间隔后没有生效？

**A**: 需要 **停止并重新启动 Bot** 才会使用新的间隔。操作流程：修改间隔 → 保存设置 → 停止 Bot → 启动 Bot。

### Q: 飞书通知收不到？

**A**: 
1. 检查 Webhook URL 是否正确
2. 点击 Web 界面「测试飞书通知」按钮验证
3. 确认飞书群的机器人权限已开启

### Q: 如何查看历史交易记录？

**A**: 交易记录保存在 `~/.tradingbot/trade_history.json`，可通过 Web 界面「日志」页面查看，或直接打开文件。

---

## ⚠️ 风险提示

> **加密货币合约交易存在极高风险，可能导致本金全部损失。**

- 本项目仅供 **学习和研究** 使用
- AI 决策 **不保证盈利**，历史表现不代表未来收益
- 使用实盘模式前，请 **充分了解杠杆交易风险**
- 设置 **合理的止损**，只投入 **自己能承受损失的资金**
- 建议先在 **沙盒模式充分测试** 后再考虑实盘
- 市场波动剧烈时，请 **谨慎使用高杠杆**

---

## 📄 License

MIT License

基于 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) 开源项目扩展开发，原始框架论文：[arXiv:2412.20138](https://arxiv.org/abs/2412.20138)。

---

## 🔗 相关链接

- **GitHub 仓库**: https://github.com/1xudengwen96/tradingagent_crypto
- **TradingAgents 原项目**: https://github.com/TauricResearch/TradingAgents
- **通义千问 API**: https://dashscope.console.aliyun.com/
- **Bitget 交易所**: https://www.bitget.com
- **CCXT 文档**: https://docs.ccxt.com/
- **飞书开放平台**: https://open.feishu.cn/
