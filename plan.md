TradingAgents-CN 动态合约交易系统改造方案 (Bitget 专用)

1. 核心设计变更：从“静态”到“动态”

1.1 动态品种识别

系统不再固定为 ETH，而是支持用户通过 CLI 或 Web 界面输入任意 Bitget 支持的永续合约代码。

输入规范： 统一使用 品种/USDT:USDT 格式（如 BTC/USDT:USDT, SOL/USDT:USDT, XAU/USDT:USDT）。

自动发现： 系统启动时自动调用 Bitget fetch_markets 接口，验证用户输入的品种是否存在且是否为永续合约。

1.2 引入“Bitget Skill”集成

如果你有 Bitget 的 API 特性文档或 Skill 定义，请将其放在项目根目录（如 bitget_skills.md），Claude Code 会自动读取并根据这些规则编写 bitget_provider.py。

2. Claude Code 交互式开发指令 (Prompts)

请按以下顺序，通过 Claude Code 终端逐步执行：

Phase 1: 基础设施通用化 (Generative Infrastructure)

目标： 让系统支持任意资产，而不仅仅是股票。

👉 执行指令 1：

"Claude，我们要把系统改造成通用的 Bitget 合约交易工具。

移除 akshare, baostock 等股票库，安装 ccxt, pandas-ta。

修改 stock_data_models.py 为 asset_data_models.py。

关键任务：在配置类中增加一个 TARGET_SYMBOLS 列表，允许从环境变量或配置文件动态读取。

实现一个 AssetValidator 类，用于在系统启动时通过 ccxt 检查 Bitget 是否支持这些品种。"

Phase 2: 编写基于“Bitget Skill”的数据层

目标： 接入 Bitget 的实时数据流。

👉 执行指令 2：

"Claude，参考我提供的 Bitget API 规范（或直接使用 ccxt），在 providers/crypto/ 下实现 bitget_universal_provider.py：

初始化支持 V2 API 的 Bitget 客户端。

实现 get_market_data(symbol)：自动获取该品种的 K 线、当前资金费率、深度图数据。

实现 get_account_risk(symbol)：获取该品种当前的仓位、强平价和未实现盈亏。"

Phase 3: 智能体决策“通用化”升级

目标： 让 AI 能够分析任何你输入的品种。

👉 执行指令 3：

"Claude，修改 market_analyst.py 和 Prompt 模板：

动态上下文：让 LLM 根据当前输入的 symbol 自动调整分析策略（如果是 Crypto 则看链上数据和 BTC 相关性；如果是 XAU 则自动搜索宏观经济数据）。

交易指令标准化：LLM 必须输出标准的合约操作 JSON：{"action": "OPEN_LONG/OPEN_SHORT/CLOSE/WAIT", "symbol": "...", "leverage": 10, "sl": 123.4, "tp": 130.0}。"

Phase 4: “代码死守”风控引擎 (Hardcoded Guardrail)

目标： 无论用户输入什么品种，系统都要保证不被爆仓。

👉 执行指令 4：

"Claude，重写 risk_manager.py。我们需要一个品种无关的通用风控逻辑：

动态杠杆限额：不同品种设置不同最大杠杆（如 Crypto 20x, 黄金 50x）。

全自动仓位计算：根据账户总净值和该品种的 ATR（平均真实波幅），自动计算该下多少个单位，确保单笔止损只亏损总资金的 1%-2%。

强平距离检查：如果计算出的止损价低于强平价，直接禁止开仓。"

Phase 5: 交互式交易员 (Interactive Trader)

目标： 实现真正的 Bitget 接口下单。

👉 执行指令 5：

"Claude，重构 trader.py。

对接 Bitget 的 create_order。支持市价下单以确保在波动中能成交。

必须实现 TP/SL (止盈止损) 的同步挂单（Bitget V2 API 支持在下单时带上这些参数）。

增强模拟模式：在 paper.py 中实现完整的保证金/杠杆/爆仓结算逻辑，让我可以先在本地模拟任何品种。"

3. 你需要提供给 Claude Code 的“Bitget Skill”

为了让 Claude 做得更好，建议你在对话开始前，将以下信息保存为一个文件（如 bitget_info.txt）并告诉它：

API 权限要求： 提醒它需要 "Futures Trading" 权限。

核心接口名： 如果你使用的是 Bitget V2 API，告诉它关注 /api/v2/mix/order/place-order 这种路径。

特殊参数： 例如 Bitget 切换杠杆需要单独调用接口，或者切换逐仓/全仓模式。

4. 为什么这个“动态方案”更强大？

灵活性： 你今天想做 ETH，明天想做黄金，后天想做 SOL，只需要在 .env 里改一下 TARGET_SYMBOLS。

可扩展性： 通过 ccxt，未来如果你想从 Bitget 扩展到 Binance 或 OKX，代码改动量极小。

安全性： 将复杂的保证金计算写进 Python 代码，而不是依赖 AI 的口算，这在合约交易中是救命的。

准备好了吗？把 Bitget 的 API 信息准备好，喂给 Claude Code 就可以开搞了！
