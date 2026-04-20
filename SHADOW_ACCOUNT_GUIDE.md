# 影子账户（Shadow Account）使用指南

## 📖 什么是影子账户？

影子账户是一种**虚拟交易模式**，让你：
- ✅ 使用**真实的 Binance 市场数据**
- ✅ 在本地维护一个**虚拟账户**（初始 1000 USDT）
- ✅ 模拟**真实交易**：手续费、滑点、盈亏计算
- ✅ **零风险**验证策略效果

### 与真实交易的区别

| 项目 | 影子账户 | 真实交易 |
|------|---------|---------|
| 数据来源 | Binance 实时行情 | Binance 实时行情 |
| 资金 | 虚拟 1000 USDT | 你的真实资金 |
| 下单 | 本地模拟，不上链 | 真实 API 下单 |
| 盈亏 | 本地记录 | 真实盈亏 |
| 风险 | 零风险 | 可能亏损 |
| 手续费 | 模拟计算 | 真实扣除 |

---

## 🚀 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# Binance API（用于获取真实行情）
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET=your_binance_secret_here

# 影子账户配置
SHADOW_MODE=true              # 启用影子账户
SHADOW_INITIAL_BALANCE=1000   # 初始资金 1000 USDT
SHADOW_SLIPPAGE=0.0005        # 滑点 0.05%

# 其他配置
TIMEFRAME=4h
DASHSCOPE_API_KEY=sk-xxx      # 通义千问 API Key
FEISHU_WEBHOOK_URL=xxx        # 飞书通知（可选）
```

### 2. 获取 Binance API Key

1. 访问 https://www.binance.com/zh-CN/support/faq/360002502072
2. 登录账户 → API 管理 → 创建 API
3. 启用「永续合约」权限
4. 复制 API Key 和 Secret Key 到 `.env` 文件

> ⚠️ **重要**：即使在影子模式下，也需要提供 Binance API Key 来获取真实行情数据。但不会实际下单。

### 3. 运行

```bash
# 运行一次分析（影子模式）
python crypto_main.py --once

# 查看影子账户报告
cat ~/.tradingbot/shadow_account.json
```

---

## 📊 影子账户功能

### 自动模拟的内容

1. **仓位管理**
   - 开仓/平仓
   - 加仓/减仓
   - 仓位均价计算

2. **费用计算**
   - 交易手续费（Maker: 0.02%, Taker: 0.05%）
   - 滑点成本（默认 0.05%）

3. **盈亏追踪**
   - 未实现盈亏（持仓盈亏）
   - 已实现盈亏（平仓盈亏）
   - 总收益率

4. **风险控制**
   - 强平价格计算
   - 止损/止盈追踪

### 输出示例

```
============================================================
📊 影子账户概览
============================================================
初始资金：     1000.00 USDT
可用余额：     850.32 USDT
总权益：       923.45 USDT
未实现盈亏：   +45.67 USDT
已实现盈亏：   -121.23 USDT
总收益率：     -7.66%
手续费支出：   3.4567 USDT
持仓数量：     1
交易次数：     15
============================================================

📦 当前持仓:
  BTC/USDT: LONG 0.15 @ 52340.50
    当前价：53120.00 | 盈亏：+117.00 USDT (+1.49%)
    杠杆：5x | 强平价：42156.30
    止损：51000.00
    止盈 1: 55000.00
    止盈 2: 58000.00
```

---

## 🔧 高级配置

### 调整滑点

滑点模拟市场冲击成本，默认 0.05%：

```bash
# 高流动性币种（如 BTC）
SHADOW_SLIPPAGE=0.0003  # 0.03%

# 低流动性币种
SHADOW_SLIPPAGE=0.001   # 0.1%
```

### 调整初始资金

```bash
SHADOW_INITIAL_BALANCE=5000  # 5000 USDT
```

### 切换到真实交易（⚠️ 高风险）

```bash
SHADOW_MODE=false  # 禁用影子账户
BINANCE_SANDBOX=false  # 使用真实网络
```

> ⚠️ **警告**：切换到真实交易模式后，AI 的决策将实际下单到 Binance，可能导致真实资金亏损。

---

## 📁 数据持久化

影子账户数据保存在：

```bash
~/.tradingbot/shadow_account.json
```

包含：
- 账户余额和历史
- 当前持仓
- 交易记录（最近 1000 条）

### 重置账户

```bash
rm ~/.tradingbot/shadow_account.json
# 下次运行时会自动创建新账户
```

### 导出报告

```python
from tradingagents.execution.shadow_account import get_shadow_account

account = get_shadow_account()
account.export_report("my_trading_report.json")
```

---

## 🆚 三种模式对比

| 模式 | 配置 | 用途 |
|------|------|------|
| **影子账户** | `SHADOW_MODE=true`<br>`BINANCE_API_KEY=xxx` | 策略验证、模拟交易 |
| **测试网** | `SHADOW_MODE=false`<br>`BINANCE_SANDBOX=true` | 接近实盘的测试 |
| **实盘交易** | `SHADOW_MODE=false`<br>`BINANCE_SANDBOX=false` | 真实交易（高风险） |

---

## ❓ 常见问题

### Q: 影子账户的盈亏准确吗？

A: 非常接近真实交易：
- ✅ 使用真实 Binance 行情数据
- ✅ 计算手续费（Maker/Taker）
- ✅ 计算滑点成本
- ❌ 不包含资金费率（永续合约特有）
- ❌ 极端行情下可能有价格偏差

### Q: 可以同时运行多个影子账户吗？

A: 可以，但需要修改持久化文件路径：

```python
from tradingagents.execution.shadow_account import ShadowAccountManager

account = ShadowAccountManager(initial_balance=1000.0)
# 手动指定文件路径
account.SHADOW_ACCOUNT_FILE = "/path/to/custom_account.json"
```

### Q: 影子账户可以用于实盘吗？

A: 不能直接用于实盘，但可以：
1. 先用影子账户验证策略
2. 当影子账户稳定盈利后
3. 切换到 `SHADOW_MODE=false` 进行实盘

### Q: 为什么需要 Binance API Key？

A: 影子账户需要获取真实的：
- 当前价格（用于开仓/平仓）
- 订单簿深度（用于滑点计算）
- 资金费率（用于持仓成本）

但**不会**使用 API Key 进行任何实际交易操作。

---

## 📝 总结

影子账户模式是**最安全的交易测试方式**：

```bash
# 推荐配置（影子账户）
SHADOW_MODE=true
BINANCE_API_KEY=xxx
BINANCE_SECRET=xxx

# 运行
python crypto_main.py --once

# 查看结果
cat ~/.tradingbot/shadow_account.json
```

祝交易顺利！🚀
