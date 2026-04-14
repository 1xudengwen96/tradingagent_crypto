# 问题诊断和修复说明

## 已修复的问题

### ✅ 问题1: 保存配置时交易对没有生效

**原因**: 前端 `saveConfig()` 函数没有把选择的交易对(`crypto_symbols`)发送给后端

**修复**: 
- 修改了 `templates/index.html` 中的 `saveConfig()` 函数
- 现在会自动保存你选择的交易对(BTC或ETH)
- 刷新页面时也会恢复你上次选择的交易对

---

### ✅ 问题2: LLM API 403错误 (分析失败)

**原因**: 日志显示 `anthropic.PermissionDeniedError: Error code: 403`
这说明你的 Anthropic API Key 没有权限或者被封禁了

**解决方案** (请选择一种):

#### 方案A: 使用通义千问(Qwen) - 推荐 ⭐
1. 申请 DashScope API Key: https://dashscope.console.aliyun.com/
2. 在网页配置中填入:
   - 深度思考LLM提供商: 选择 `qwen`
   - 深度思考LLM: 选择 `qwen-max`
   - 快速思考LLM提供商: 选择 `qwen`  
   - 快速思考LLM: 选择 `qwen-plus`
   - DashScope API Key: 填入你的Key

#### 方案B: 修复Anthropic API Key
1. 检查你的 Anthropic API Key 是否有效
2. 确认账户余额充足
3. 确认没有被封禁
4. 在网页配置中重新填入

#### 方案C: 使用OpenAI
1. 在网页配置中:
   - 深度思考LLM提供商: 选择 `openai`
   - 深度思考LLM: 选择 `gpt-4`
   - 快速思考LLM提供商: 选择 `openai`
   - 快速思考LLM: 选择 `gpt-4o-mini`
   - OpenAI API Key: 填入你的Key

---

### ✅ 问题3: 飞书通知增强

**改进**:
- 现在飞书通知会包含**各个角色的详细分析报告**(Markdown格式):
  - 📈 市场分析师
  - 😊 情绪分析师  
  - 📰 新闻分析师
  - 💎 基本面分析师
  - 🐂 多头研究员
  - 🐻 空头研究员
  - ⚖️ 研究经理
  - 💼 交易员
  - 🛡️ 风险经理
  - 🎯 最终决策

- 如果分析失败,也会发送错误通知到飞书

---

### ✅ 问题4: 日志输出增强

**改进**:
- 现在运行分析时,日志会显示:
  - 📡 Step 1-3: K线数据和技术指标获取
  - 🤖 Step 4-10: 各个Agent角色的分析过程
- 日志会输出到:
  - 终端标准输出
  - `crypto_trading.log` 文件
  - 网页的"运行日志"页面

---

## 如何使用

### 1. 启动服务器
```bash
cd /home/forwhat/tradingagent_crypto
python server.py --port 8000
```

### 2. 访问网页
打开浏览器访问: http://localhost:8000

### 3. 配置交易对和API
1. 点击左侧菜单 "交易配置"
2. 选择交易品种 (BTC 或 ETH)
3. 填入飞书 Webhook URL (可选)
4. 点击 "保存配置"

### 4. 启动机器人
1. 点击右上角 "▶ 启动" 按钮
2. 系统会立即开始分析当前交易对
3. 分析完成后会发送详细报告到飞书

### 5. 查看分析过程
- **日志**: 点击左侧 "运行日志" 菜单
- **飞书**: 查看收到的详细分析报告
- **终端**: 查看 `crypto_trading.log` 文件

---

## 常见问题

### Q: 为什么启动后没有获取K线和分析?
A: 这是因为LLM API配置有问题。请检查:
1. 至少配置了一种LLM提供商的API Key (Qwen/OpenAI/Anthropic)
2. API Key有效且账户余额充足
3. 配置后保存并重启机器人

### Q: 如何确认配置已保存?
A: 保存成功后会显示 "配置已保存" 的提示。刷新页面后你选择的交易对应该保持不变。

### Q: 飞书通知没有收到?
A: 检查:
1. Webhook URL是否正确
2. 点击 "测试飞书" 按钮验证连接
3. 查看日志中是否有 "Feishu notification sent" 的记录

---

## 修改的文件清单

1. `templates/index.html` - 修复交易对保存和恢复
2. `crypto_main.py` - 增强飞书通知和日志输出
3. `tradingagents/graph/crypto_trading_graph.py` - 增加分析流程日志
