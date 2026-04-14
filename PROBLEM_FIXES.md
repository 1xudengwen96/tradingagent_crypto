# 问题诊断和修复说明

## 修复时间
2026-04-14

---

## 已修复的问题

### ✅ 问题1: 飞书通知 - 多个角色独立发言（多机器人模式）

**原因**: 原来的系统将所有角色的报告合并成一条消息，由一个飞书机器人发送。用户希望每个角色（市场分析师、研究经理、风险经理、交易员等）都能作为独立的机器人在飞书群里发言。

**修复**:
- **crypto_main.py**:
  - 新增 `_send_feishu_card()` 内部辅助函数，用于发送飞书交互式卡片
  - 新增 `_get_webhook()` 函数，从环境变量获取 Webhook URL
  - 新增 `send_feishu_multi_notifications()` 函数，实现多角色独立通知：
    - 📈 市场分析师 → `FEISHU_WEBHOOK_ANALYST`（技术分析报告）
    - 😊 情绪分析师 → `FEISHU_WEBHOOK_SENTIMENT`（情绪分析，可选）
    - 📰 新闻分析师 → `FEISHU_WEBHOOK_NEWS`（新闻分析，可选）
    - 💎 基本面分析师 → `FEISHU_WEBHOOK_FUNDAMENTALS`（基本面/链上数据，可选）
    - ⚖️ 研究经理 → `FEISHU_WEBHOOK_MANAGER`（研究经理裁决，含多空辩论摘要）
    - 💼 交易员 → `FEISHU_WEBHOOK_TRADER`（交易员建议）
    - 🛡️ 风险经理 → `FEISHU_WEBHOOK_RISK`（风险评估）
    - 🎯 最终决策 → `FEISHU_WEBHOOK_TRADER`（最终交易决策+执行状态）
  - 保留原有 `send_feishu_notification()` 函数作为向后兼容和降级方案
  - 如果未配置任何角色专属 Webhook，系统仍会发送汇总卡片到 `FEISHU_WEBHOOK_URL`

- **server.py**:
  - `DEFAULT_CONFIG` 增加 7 个新 Webhook 字段
  - `load_config()` 增加对应环境变量映射
  - `masked_config()` 暴露新字段给前端
  - `ConfigRequest` Pydantic 模型增加新字段
  - `BotProcess.start()` 传递新环境变量到子进程

- **.env.example**:
  - 更新注释，说明多角色机器人配置方法
  - 增加 7 个新 Webhook 环境变量

---

### ✅ 问题2: Open Interest 数据在沙盒模式不可用

**原因**: Bitget 的沙盒（Demo Trading）环境不支持未平仓合约量（Open Interest）数据。原来的代码会尝试获取但返回空数据，导致 LLM 分析时提示数据缺失。

**修复**:
- **tradingagents/dataflows/bitget_vendor.py**:
  - 在 `get_open_interest()` 函数中增加沙盒模式检测
  - 如果是沙盒模式，直接返回友好提示信息，说明该数据在实盘模式下可用
  - 避免尝试调用 API 导致空响应或错误

- **tradingagents/agents/analysts/crypto_market_analyst.py**:
  - 更新系统提示词，告知 LLM 在沙盒模式下 OI 数据可能不可用
  - 要求 LLM 在报告中明确说明这一点，并聚焦于其他可用指标

---

### ✅ 问题3: 强制中文输出

**原因**: 虽然配置了 `output_language: "Chinese"`，但 LLM 有时仍然用英文回复。原来的语言指令 `"Write your entire response in {lang}."` 不够强制。

**修复**:
- **tradingagents/agents/utils/agent_utils.py**:
  - 增强 `get_language_instruction()` 函数
  - 使用更强的中文指令：`"【语言强制要求】你必须且只能使用{lang}撰写所有输出内容。包括报告标题、段落、表格、注释等全部文本。禁止使用任何其他语言。这是强制性要求，不可违反。"`
  - 该指令附加到系统提示词末尾，确保 LLM 严格遵守

- **tradingagents/default_config.py**:
  - 将 `DEFAULT_CONFIG["output_language"]` 默认值从 `"English"` 改为 `"Chinese"`
  - 将 `CRYPTO_CONFIG["output_language"]` 默认值从 `"English"` 改为 `"Chinese"`

---

## 如何使用

### 1. 配置多角色飞书通知

#### 步骤 1: 在飞书群内创建多个自定义机器人
按照 `FEISHU_MULTI_BOT_GUIDE.md` 的指引，在同一个飞书群内创建以下自定义机器人：
- 📈 市场分析师
- 😊 情绪分析师（可选）
- 📰 新闻分析师（可选）
- 💎 基本面分析师（可选）
- ⚖️ 研究经理
- 🛡️ 风险经理
- 🎯 交易员

#### 步骤 2: 复制 Webhook URL
每个机器人创建后，复制其 Webhook URL。

#### 步骤 3: 配置 .env 文件
```bash
cp .env.example .env
# 编辑 .env 文件，填入对应的 Webhook URL
```

```env
# 通用通知（后备）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx-general

# 角色专属通知
FEISHU_WEBHOOK_ANALYST=https://open.feishu.cn/open-apis/bot/v2/hook/xxx-analyst
FEISHU_WEBHOOK_MANAGER=https://open.feishu.cn/open-apis/bot/v2/hook/xxx-manager
FEISHU_WEBHOOK_RISK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx-risk
FEISHU_WEBHOOK_TRADER=https://open.feishu.cn/open-apis/bot/v2/hook/xxx-trader
```

#### 步骤 4: 重启机器人
```bash
python server.py --port 8000
```

### 2. 启动服务器
```bash
cd /home/forwhat/tradingagent_crypto
python server.py --port 8000
```

### 3. 访问网页
打开浏览器访问: http://localhost:8000

### 4. 配置交易对和API
1. 点击左侧菜单 "交易配置"
2. 选择交易品种 (BTC 或 ETH)
3. 填入飞书 Webhook URL (可选，支持多角色)
4. 点击 "保存配置"

### 5. 启动机器人
1. 点击右上角 "▶ 启动" 按钮
2. 系统会立即开始分析当前交易对
3. 分析完成后，各角色会独立发送报告到飞书

### 6. 查看分析过程
- **日志**: 点击左侧 "运行日志" 菜单
- **飞书**: 查看收到的各角色详细报告
- **终端**: 查看 `crypto_trading.log` 文件

---

## 修改的文件清单

1. `crypto_main.py` - 实现多角色飞书通知系统
2. `server.py` - 增加新 Webhook 字段支持
3. `.env.example` - 更新多角色 Webhook 配置说明
4. `tradingagents/dataflows/bitget_vendor.py` - 修复沙盒模式 OI 数据问题
5. `tradingagents/agents/analysts/crypto_market_analyst.py` - 更新提示词处理 OI 数据缺失
6. `tradingagents/agents/utils/agent_utils.py` - 增强中文输出强制指令
7. `tradingagents/default_config.py` - 默认语言改为中文

---

## 常见问题

### Q: 为什么我只收到一条飞书消息，而不是多个角色的独立消息？
A: 检查以下几点：
1. 确保在 `.env` 文件中配置了至少一个角色专属 Webhook（如 `FEISHU_WEBHOOK_ANALYST`）
2. 确保每个 Webhook URL 对应飞书群内不同的自定义机器人
3. 如果只配置了 `FEISHU_WEBHOOK_URL`，系统会发送汇总消息（向后兼容模式）

### Q: Open Interest 数据为什么显示不可用？
A: 这是因为你当前处于沙盒（Demo Trading）模式。Bitget 沙盒环境不提供 OI 数据。切换到实盘模式（`BITGET_SANDBOX=false`）后，该数据将自动可用。

### Q: LLM 仍然用英文回复怎么办？
A: 系统已经使用强强制中文指令。如果仍有问题，检查：
1. 配置文件中 `output_language` 是否设置为 `"Chinese"`
2. 重启机器人使配置生效
3. 检查日志确认配置已正确加载

### Q: 如何验证配置已保存？
A: 保存成功后会显示 "配置已保存" 的提示。刷新页面后你选择的交易对应该保持不变。

### Q: 飞书通知没有收到？
A: 检查:
1. Webhook URL 是否正确
2. 点击 "测试飞书" 按钮验证连接
3. 查看日志中是否有 "Feishu card sent" 或 "Feishu notification sent" 的记录
