# Qwen (通义千问) 配置指南

## 为什么只使用 Qwen?

1. **成本优势**: Qwen 的 API 费用比 OpenAI 和 Anthropic 低 50-80%
2. **中文理解**: 对中文金融术语理解更好
3. **稳定性**: 国内服务，访问稳定，不受网络限制
4. **性能优秀**: qwen3.5-max 和 qwen3.5-plus 在金融分析任务中表现优异

## 快速配置

### 1. 申请 DashScope API Key

访问：https://dashscope.console.aliyun.com/

1. 注册/登录阿里云账号
2. 开通 DashScope 服务
3. 创建 API Key
4. 复制 Key 备用

### 2. 填写配置

#### 方式 A: 通过 Web 界面 (推荐)

1. 启动 Web 服务：`python server.py`
2. 访问：http://localhost:8000
3. 点击左侧「交易配置」
4. 系统已默认使用 Qwen3.5 系列，只需填入 DashScope API Key
5. 点击「保存配置」

#### 方式 B: 通过.env 文件

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```bash
# 只需填写这一个 Key
DASHSCOPE_API_KEY=sk-你的真实 APIKey

# Bitget API (如果需要实盘交易)
BITGET_API_KEY=bg_xxxxx
BITGET_SECRET=xxxxx
BITGET_PASSPHRASE=xxxxx
BITGET_SANDBOX=true
```

### 3. 模型说明

系统自动使用两个 Qwen3.5 系列模型:

| 角色 | 模型 | 用途 |
|------|------|------|
| **深度思考** | qwen3.5-max | 研究经理、投资组合经理 (最终决策) |
| **快速思考** | qwen3.5-plus | 市场分析师、宏观/链上分析师 |

> **提示**: qwen3.5-max 分析质量更高，qwen3.5-plus 速度快适合大量并行分析任务

### 4. 验证配置

#### Web 界面验证:
1. 访问 http://localhost:8000
2. 点击「交易配置」页面
3. 点击「测试飞书」旁边应该能看到连接状态

#### 命令行验证:
```bash
python crypto_main.py --once --no-execute
```

观察日志输出，如果看到 AI 分析结果，说明配置成功。

## 常见问题

### Q: 如何查看 API 调用情况？
A: 登录 https://dashscope.console.aliyun.com/ 查看调用量和余额

### Q: qwen3.5-max 和 qwen3.5-plus 的区别？
A:
- **qwen3.5-max**: 更强的推理能力，适合复杂决策 (研究经理、组合管理)
- **qwen3.5-plus**: 速度快成本低，适合大量重复任务 (分析师、数据获取)

### Q: 费用大概多少？
A: 每次完整分析周期 (10 个 Agent) 大约:
- qwen3.5-max: 2 次调用 ≈ ¥0.5-1
- qwen3.5-plus: 8 次调用 ≈ ¥0.2-0.5
- **总计**: 每次分析约 ¥1-2

### Q: 可以只用一个模型吗？
A: 可以，但不推荐。如果只想用一个:
- 编辑 `.tradingbot/config.json`
- 把 `deep_think_llm` 和 `quick_think_llm` 都设为 `qwen3.5-plus`

## 完整配置示例

`.tradingbot/config.json` (系统自动生成):

```json
{
  "timeframe": "4h",
  "capital_usdt": 1000,
  "crypto_symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
  "interval_hours": 4,
  "auto_execute": false,
  "sandbox_mode": true,
  "account_type": "classic",
  "feishu_webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  "output_language": "Chinese"
}
```

环境变量 (从 Web 界面保存时自动处理):
- `DASHSCOPE_API_KEY` → 系统自动使用

## 下一步

配置完成后:

1. **启动机器人**: 点击 Web 界面右上角「▶ 启动」
2. **查看飞书**: 应该会收到详细的 AI 分析报告 (包含所有角色的分析)
3. **观察日志**: 点击左侧「运行日志」查看实时分析过程

祝交易顺利！🚀
