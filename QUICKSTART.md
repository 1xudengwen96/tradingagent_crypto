# 🚀 TradingAgents Crypto 快速上手指南

> 5 分钟快速启动你的 AI 加密货币交易机器人

---

## 📝 第一步：安装依赖

```bash
# 进入项目目录
cd tradingagent_crypto

# 使用 uv 安装依赖（推荐）
uv sync

# 或使用 pip
pip install -e .
```

---

## 🔑 第二步：配置 API Key

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填写你的 API Key
```

**必须填写的 3 个 Key：**

```bash
# 1. 通义千问 API Key（AI 大脑）
# 获取：https://dashscope.console.aliyun.com/
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# 2. Bitget API Key（交易所）
# 获取：https://www.bitget.com/zh-CN/account/newcreate
# 记得开启沙盒模式（Demo Trading）
BITGET_API_KEY=bg_xxxxxxxxxxxx
BITGET_SECRET=xxxxxxxxxxxxxxxx
BITGET_PASSPHRASE=your_passphrase

# 3. 飞书 Webhook（通知推送，可选但推荐）
# 在飞书群添加自定义机器人，复制 Webhook 地址
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx
```

---

## 🎯 第三步：运行

### 方式一：Web 界面（推荐新手）

```bash
python server.py
```

浏览器打开 `http://localhost:8000`，在网页中配置和启动机器人。

**优点**：可视化界面，实时日志，一键启停

---

### 方式二：命令行

```bash
# 首次运行：只分析，不下单（推荐先测试）
python crypto_main.py --once --no-execute

# 确认无误后：分析并下单（沙盒模式）
python crypto_main.py --once

# 定时运行：每 4 小时自动分析一次
python crypto_main.py

# 自定义间隔：每 2 小时一次
python crypto_main.py --interval-hours 2
```

---

## 📊 查看运行结果

### 1. 终端输出

```
============================================================
  SYMBOL : BTC/USDT:USDT
  TIME   : 2026-04-17 08:00 UTC
============================================================

📊 市场分析：...
📰 新闻分析：...
😊 情绪分析：...

🎯 最终决策：
─────────────────
DIRECTION: LONG
LEVERAGE: 5x
STOP_LOSS: 65000
TAKE_PROFIT_1: 68000
TAKE_PROFIT_2: 71000
POSITION_SIZE: 20%
─────────────────

✅ Orders placed: [12345678, 12345679, 12345680]
```

### 2. 飞书通知

分析完成后，飞书群自动收到 AI 决策卡片。

### 3. 日志文件

- 实时日志：`crypto_trading.log`
- 交易历史：`~/.tradingbot/trade_history.json`

---

## ⚙️ 常用操作

### 修改交易对

编辑 `tradingagents/default_config.py`，修改 `crypto_symbols`：

```python
CRYPTO_CONFIG = {
    "crypto_symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"],
}
```

### 修改分析间隔

命令行模式：
```bash
python crypto_main.py --interval-hours 6  # 每 6 小时
```

Web 模式：
在「交易设置」页面选择间隔 → 保存 → 重启机器人

### 切换实盘

**⚠️ 警告：务必先在沙盒充分测试！**

1. 在 Bitget 创建 **实盘 API Key**（非沙盒）
2. 修改 `.env`：
   ```bash
   BITGET_SANDBOX=false
   BITGET_API_KEY=实盘 API Key
   BITGET_SECRET=实盘 Secret
   BITGET_PASSPHRASE=实盘 Passphrase
   ```
3. 重启机器人

---

## ❓ 遇到问题？

### 查看日志

```bash
# 实时查看日志
tail -f crypto_trading.log
```

### 测试 API 连接

Web 界面 → API 配置 → 点击「测试连接」

### 飞书通知失效

Web 界面 → 交易设置 → 点击「测试飞书通知」

### LLM API 调用失败

1. 检查 `DASHSCOPE_API_KEY` 是否正确
2. 确认账户有足够余额
3. 查看 https://status.aliyun.com/ 服务状态

---

## 📚 进阶阅读

- **完整文档**: [README_CN.md](./README_CN.md)
- **飞书多机器人配置**: [FEISHU_MULTI_BOT_GUIDE.md](./FEISHU_MULTI_BOT_GUIDE.md)
- **开发进度**: [CRYPTO_PROGRESS.md](./CRYPTO_PROGRESS.md)

---

## ⚠️ 风险提示

- 加密货币合约交易风险极高，可能损失全部本金
- AI 决策不保证盈利
- 请先在沙盒模式充分测试
- 只投入你能承受损失的资金
- 设置合理止损，谨慎使用高杠杆

**祝交易顺利！🎉**
