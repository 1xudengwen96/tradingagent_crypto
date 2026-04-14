# 飞书多角色机器人搭建完整指南

## 📋 目录
- [一、需求分析](#一需求分析)
- [二、架构设计](#二架构设计)
- [三、创建飞书机器人（详细步骤）](#三创建飞书机器人详细步骤)
- [四、权限配置](#四权限配置)
- [五、代码集成](#五代码集成)
- [六、测试验证](#六测试验证)
- [七、常见问题](#七常见问题)

---

## 一、需求分析

### 当前状态
你的系统已经有基本的飞书 Webhook 通知功能（单机器人），每次分析完成后推送一条卡片消息到飞书群。

### 目标状态
创建 **多个飞书机器人**，分别对应交易系统中的不同角色，在同一个群内展示各自的决策过程：

| 角色 | 职责 | 推送内容 |
|------|------|----------|
| 📊 **市场分析师** (Market Analyst) | 分析市场趋势、技术指标 | K线分析、指标信号、市场情绪 |
| 💬 **辩论员** (Debater) | 多空观点辩论 | 看多理由 vs 看空理由 |
| 🛡️ **风控官** (Risk Manager) | 评估风险、计算仓位 | 风险等级、仓位建议、止损止盈 |
| 💰 **交易员** (Trader) | 最终执行决策 | 开仓/平仓指令、订单状态 |

### 难度评估：⭐⭐ (简单)
- ✅ 飞书原生支持多机器人入群
- ✅ 每个角色只需独立的 Webhook URL
- ✅ 代码改动量小（只需增加几个发送函数）
- ✅ 无需复杂权限，只需基础的「自定义机器人」权限

---

## 二、架构设计

### 2.1 消息流转图

```
┌─────────────────────────────────────────────────────────────┐
│                      交易系统 (crypto_main.py)               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Market       │  │ Debater      │  │ Risk         │      │
│  │ Analyst Agent│  │ Agent        │  │ Manager Agent│      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         ▼                 ▼                 ▼               │
│  ┌──────────────────────────────────────────────────┐      │
│  │          TradingAgentsGraph (决策流程)             │      │
│  └──────────────────────────────────────────────────┘      │
│                            │                               │
│                            ▼                               │
│                    ┌──────────────┐                        │
│                    │ Trader Agent │                        │
│                    └──────┬───────┘                        │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │ 飞书机器人   │  │ 飞书机器人   │  │ 飞书机器人   │
   │ 市场分析师   │  │ 辩论员       │  │ 风控官       │
   │ Webhook #1  │  │ Webhook #2  │  │ Webhook #3  │
   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                  ┌─────────────┐
                  │ 飞书机器人   │
                  │ 交易员       │
                  │ Webhook #4  │
                  └──────┬──────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   飞书群（决策群）    │
              │  你可以看到所有角色   │
              │  的讨论和决策过程     │
              └─────────────────────┘
```

### 2.2 环境变量设计

在 `.env` 文件中增加多个 Webhook URL：

```bash
# 飞书 Webhook URLs（每个角色一个）
FEISHU_WEBHOOK_ANALYST="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-analyst"
FEISHU_WEBHOOK_DEBATER="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-debater"
FEISHU_WEBHOOK_RISK="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-risk"
FEISHU_WEBHOOK_TRADER="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-trader"

# 保留原有的（可选，作为通用通知）
FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-general"
```

---

## 三、创建飞书机器人（详细步骤）

### 3.1 前置条件

- ✅ 你有一个飞书账号（个人或企业版均可）
- ✅ 你有一个飞书群（或准备新建一个群）
- ✅ 你是该群的群主或管理员（部分权限需要管理员）

### 3.2 创建第一个机器人：市场分析师 📊

#### 步骤 1：打开群设置

1. 打开飞书桌面客户端或网页版
2. 进入你的目标群聊（如果没有，先创建一个，命名为 "交易决策群" 或类似）
3. 点击右上角的 **群设置** 图标（齿轮图标 ⚙️）

![群设置入口](https://example.com/feishu-group-settings.png)
> 📷 截图说明：右上角齿轮图标 → 群设置

#### 步骤 2：添加机器人

1. 在群设置页面中，找到 **「机器人」** 选项
2. 点击 **「添加机器人」** 按钮
3. 在弹出的机器人列表中，选择 **「自定义机器人」** (Custom Bot)
   - 如果找不到，可以点击「更多」或搜索 "自定义"

![添加机器人](https://example.com/feishu-add-bot.png)
> 📷 截图说明：群设置 → 机器人 → 添加机器人 → 自定义机器人

#### 步骤 3：配置机器人信息

在弹出的配置页面中，填写以下信息：

| 字段 | 填写内容 | 说明 |
|------|----------|------|
| **名称** | `📊 市场分析师` | 显示在群内的机器人名称 |
| **描述** | `负责技术分析和市场趋势判断` | 可选，方便识别 |
| **头像** | 选择一个图标（建议用 📊 或图表类图标） | 方便区分不同角色 |

![配置机器人](https://example.com/feishu-bot-config.png)
> 📷 截图说明：填写名称、描述、选择头像

#### 步骤 4：获取 Webhook URL

1. 配置完成后，飞书会生成一个 **Webhook 地址**
2. **复制这个 URL**，它看起来像：
   ```
   https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```
3. **立即保存这个 URL** 到你的 `.env` 文件中：
   ```bash
   FEISHU_WEBHOOK_ANALYST="粘贴你复制的URL"
   ```

> ⚠️ **重要提示**：
> - 这个 URL 是保密的，不要泄露给他人
> - 一旦离开这个页面，你就无法再次查看完整的 URL
> - 如果丢失，需要重新创建机器人

#### 步骤 5：完成

点击 **「完成」** 或 **「保存」** 按钮。现在你的群内应该可以看到 `📊 市场分析师` 机器人了。

---

### 3.3 创建第二个机器人：辩论员 💬

**重复上述步骤 3.2 中的 步骤 1 ~ 步骤 5**，但使用不同的配置：

| 字段 | 填写内容 |
|------|----------|
| **名称** | `💬 辩论员` |
| **描述** | `负责多空观点辩论，提供不同视角` |
| **头像** | 选择 💬 或辩论类图标 |
| **环境变量** | `FEISHU_WEBHOOK_DEBATER` |

---

### 3.4 创建第三个机器人：风控官 🛡️

**重复上述步骤**，配置如下：

| 字段 | 填写内容 |
|------|----------|
| **名称** | `🛡️ 风控官` |
| **描述** | `负责风险评估和仓位管理` |
| **头像** | 选择 🛡️ 或盾牌类图标 |
| **环境变量** | `FEISHU_WEBHOOK_RISK` |

---

### 3.5 创建第四个机器人：交易员 💰

**重复上述步骤**，配置如下：

| 字段 | 填写内容 |
|------|----------|
| **名称** | `💰 交易员` |
| **描述** | `负责执行最终交易决策` |
| **头像** | 选择 💰 或货币类图标 |
| **环境变量** | `FEISHU_WEBHOOK_TRADER` |

---

### 3.6 最终验证

创建完成后，你的群设置 → 机器人列表中应该显示：

```
🤖 群内机器人：
  ├─ 📊 市场分析师
  ├─ 💬 辩论员
  ├─ 🛡️ 风控官
  └─ 💰 交易员
```

你的 `.env` 文件应该包含：

```bash
# 飞书 Webhook URLs
FEISHU_WEBHOOK_ANALYST="https://open.feishu.cn/open-apis/bot/v2/hook/xxx-analyst"
FEISHU_WEBHOOK_DEBATER="https://open.feishu.cn/open-apis/bot/v2/hook/xxx-debater"
FEISHU_WEBHOOK_RISK="https://open.feishu.cn/open-apis/bot/v2/hook/xxx-risk"
FEISHU_WEBHOOK_TRADER="https://open.feishu.cn/open-apis/bot/v2/hook/xxx-trader"
```

---

## 四、权限配置

### 4.1 自定义机器人权限（最低要求）

飞书「自定义机器人」**默认已经拥有以下权限**，**无需额外配置**：

| 权限 | 状态 | 说明 |
|------|------|------|
| 发送消息到群 | ✅ 默认开启 | 通过 Webhook 发送卡片消息 |
| 接收群消息 | ❌ 不支持 | 自定义机器人只能发送，不能接收 |
| 读取群成员列表 | ❌ 不支持 | 不需要此权限 |
| @提及用户 | ✅ 支持 | 可以在消息中使用 @用户名 |

### 4.2 群管理员需要开启的设置

**群主或管理员** 需要确保以下设置已开启：

1. 打开 **群设置** → **群管理**
2. 确保 **「允许添加机器人」** 已开启（如果已添加完成，此项不影响）
3. 确保 **「机器人可以发送消息」** 已开启（默认开启）

> ⚠️ **如果你的飞书是企业版**，可能需要企业管理员在后台开启「自定义机器人」功能：
> 
> 1. 登录飞书管理后台 (https://admin.feishu.cn)
> 2. 进入 **「安全管理」** → **「数据防泄漏」**
> 3. 确保 **「自定义机器人」** 未被禁用
> 4. 如果有「机器人白名单」策略，将你的群加入白名单

### 4.3 不需要配置的权限

以下权限 **不需要** 配置（常见误区）：

- ❌ 不需要创建飞书开放平台应用
- ❌ 不需要配置 OAuth 权限范围
- ❌ 不需要申请 API 调用权限
- ❌ 不需要企业管理员审批（个人版飞书）

> 💡 **总结**：自定义机器人是最简单的方式，**开箱即用**，只需复制 Webhook URL 即可。

---

## 五、代码集成

### 5.1 新增环境变量加载

修改 `crypto_main.py`，在现有 `send_feishu_notification` 函数附近增加多角色通知支持。

#### 方案 A：简单方案（推荐）

为每个角色创建独立的通知函数：

```python
import os
import requests
import logging

logger = logging.getLogger("crypto_main")

def send_feishu_message(webhook_env_var: str, title: str, content: str, fields: list = None) -> None:
    """通用飞书消息发送函数，支持任意 Webhook。
    
    Args:
        webhook_env_var: 环境变量名称（如 FEISHU_WEBHOOK_ANALYST）
        title: 卡片标题
        content: 卡片正文内容
        fields: 可选，字段列表 [{'is_short': True, 'text': {...}}, ...]
    """
    webhook_url = os.getenv(webhook_env_var, "")
    if not webhook_url:
        logger.warning("Webhook URL not configured for %s", webhook_env_var)
        return

    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": content[:1500],  # 飞书消息长度限制
            },
        }
    ]

    if fields:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "fields": fields,
        })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": elements,
        },
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Feishu message sent to %s", webhook_env_var)
        else:
            logger.warning("Feishu webhook returned HTTP %d for %s", resp.status_code, webhook_env_var)
    except Exception:
        logger.exception("Failed to send Feishu message for %s", webhook_env_var)


# ===== 各角色专用通知函数 =====

def send_analyst_report(symbol: str, analysis_text: str) -> None:
    """📊 市场分析师发送分析报告"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    send_feishu_message(
        "FEISHU_WEBHOOK_ANALYST",
        f"📊 {symbol} 市场分析报告",
        analysis_text,
        [
            {
                "is_short": True,
                "text": {"tag": "lark_md", "content": f"**角色**\n📊 市场分析师"},
            },
            {
                "is_short": True,
                "text": {"tag": "lark_md", "content": f"**时间**\n{now}"},
            },
        ]
    )


def send_debate_result(symbol: str, debate_text: str, side: str = "neutral") -> None:
    """💬 辩论员发送辩论结果"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    # 根据辩论立场选择卡片颜色
    template = "blue"
    if "看多" in debate_text or "bull" in debate_text.lower():
        template = "green"
    elif "看空" in debate_text or "bear" in debate_text.lower():
        template = "red"
    
    webhook_url = os.getenv("FEISHU_WEBHOOK_DEBATER", "")
    if not webhook_url:
        return

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"💬 {symbol} 多空辩论"},
                "template": template,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "plain_text", "content": debate_text[:1500]},
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**角色**\n💬 辩论员"},
                        },
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**时间**\n{now}"},
                        },
                    ],
                },
            ],
        },
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Feishu debate result sent for %s", symbol)
    except Exception:
        logger.exception("Failed to send Feishu debate for %s", symbol)


def send_risk_assessment(symbol: str, risk_text: str, risk_level: str = "MEDIUM") -> None:
    """🛡️ 风控官发送风险评估"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    # 根据风险等级选择卡片颜色
    template = "blue"
    if risk_level in ("HIGH", "CRITICAL"):
        template = "red"
    elif risk_level in ("LOW", "SAFE"):
        template = "green"
    
    webhook_url = os.getenv("FEISHU_WEBHOOK_RISK", "")
    if not webhook_url:
        return

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"🛡️ {symbol} 风险评估"},
                "template": template,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "plain_text", "content": risk_text[:1500]},
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**角色**\n🛡️ 风控官"},
                        },
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**风险等级**\n{risk_level}"},
                        },
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**时间**\n{now}"},
                        },
                    ],
                },
            ],
        },
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Feishu risk assessment sent for %s", symbol)
    except Exception:
        logger.exception("Failed to send Feishu risk for %s", symbol)


def send_trade_execution(symbol: str, trade_text: str, success: bool = True) -> None:
    """💰 交易员发送交易执行结果"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    webhook_url = os.getenv("FEISHU_WEBHOOK_TRADER", "")
    if not webhook_url:
        return

    template = "green" if success else "red"
    status_emoji = "✅ 执行成功" if success else "❌ 执行失败"

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"💰 {symbol} 交易执行"},
                "template": template,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "plain_text", "content": trade_text[:1500]},
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**角色**\n💰 交易员"},
                        },
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**状态**\n{status_emoji}"},
                        },
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**时间**\n{now}"},
                        },
                    ],
                },
            ],
        },
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Feishu trade execution sent for %s", symbol)
    except Exception:
        logger.exception("Failed to send Feishu trade for %s", symbol)
```

### 5.2 集成到现有代码

在你现有的 `crypto_main.py` 中，找到 `run_analysis` 函数，将原来的：

```python
# Send Feishu notification
send_feishu_notification(symbol, decision_text, execution_result)
```

**替换为**（或在其后增加）：

```python
# 假设你的 TradingAgentsGraph 返回了各角色的分析结果
# 以下是示例，具体根据你的 graph.run() 返回值调整

# 1. 市场分析报告
if hasattr(final_state, 'analyst_report'):
    send_analyst_report(symbol, final_state.analyst_report)

# 2. 辩论结果
if hasattr(final_state, 'debate_summary'):
    send_debate_result(symbol, final_state.debate_summary)

# 3. 风险评估
if hasattr(final_state, 'risk_assessment'):
    risk_level = getattr(final_state, 'risk_level', 'MEDIUM')
    send_risk_assessment(symbol, final_state.risk_assessment, risk_level)

# 4. 交易执行结果
if execution_result is not None:
    trade_details = f"信号: {execution_result.signal.direction}\n"
    trade_details += f"杠杆: {execution_result.signal.leverage}x\n"
    if execution_result.success:
        trade_details += f"订单: {[o.get('id') for o in execution_result.orders]}"
    else:
        trade_details += f"失败原因: {execution_result.error}"
    
    send_trade_execution(symbol, trade_details, execution_result.success)

# 保留原有的通用通知（可选）
send_feishu_notification(symbol, decision_text, execution_result)
```

### 5.3 更新 server.py（Web UI 配置页）

在 `server.py` 的 `DEFAULT_CONFIG` 中增加新的环境变量：

```python
DEFAULT_CONFIG = {
    # ... 现有配置 ...
    "feishu_webhook_url": "",          # 保留，通用通知
    "feishu_webhook_analyst": "",      # 新增：市场分析师
    "feishu_webhook_debater": "",      # 新增：辩论员
    "feishu_webhook_risk": "",         # 新增：风控官
    "feishu_webhook_trader": "",       # 新增：交易员
}
```

更新 `masked_config` 函数以暴露这些新字段：

```python
def masked_config(cfg: dict) -> dict:
    safe_keys = {
        "timeframe", "capital_usdt", "crypto_symbols", "interval_hours",
        "auto_execute", "sandbox_mode", "account_type",
        "feishu_webhook_url", "feishu_webhook_analyst", "feishu_webhook_debater",
        "feishu_webhook_risk", "feishu_webhook_trader",
        "output_language",
    }
    return {k: v for k, v in cfg.items() if k in safe_keys}
```

更新 `ConfigRequest` Pydantic 模型：

```python
class ConfigRequest(BaseModel):
    # ... 现有字段 ...
    feishu_webhook_url: str = ""
    feishu_webhook_analyst: str = ""
    feishu_webhook_debater: str = ""
    feishu_webhook_risk: str = ""
    feishu_webhook_trader: str = ""
    output_language: str = "Chinese"
```

更新 `BotProcess.start()` 方法中的环境变量传递：

```python
env["FEISHU_WEBHOOK_URL"] = config.get("feishu_webhook_url", "")
env["FEISHU_WEBHOOK_ANALYST"] = config.get("feishu_webhook_analyst", "")
env["FEISHU_WEBHOOK_DEBATER"] = config.get("feishu_webhook_debater", "")
env["FEISHU_WEBHOOK_RISK"] = config.get("feishu_webhook_risk", "")
env["FEISHU_WEBHOOK_TRADER"] = config.get("feishu_webhook_trader", "")
```

---

## 六、测试验证

### 6.1 快速测试

创建完机器人后，立即测试 Webhook 是否工作：

#### 方法 1：使用 curl 命令行测试

```bash
# 测试市场分析师 Webhook
curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR-ANALYST-WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{
    "msg_type": "text",
    "content": {
      "text": "📊 市场分析师机器人测试 - 如果收到此消息，说明配置正确！"
    }
  }'
```

> 将 `YOUR-ANALYST-WEBHOOK` 替换为你从飞书获取的实际 Webhook URL 的最后部分。

**预期结果**：你的飞书群内应该立即收到一条文本消息。

#### 方法 2：使用 Web UI 测试

1. 启动服务器：`python server.py`
2. 打开浏览器访问 `http://localhost:8000`
3. 进入「交易设置」页面
4. 在各个 Webhook 输入框中填入对应的 URL
5. 点击「测试飞书通知」（需要为每个角色添加测试按钮）

### 6.2 完整测试流程

```bash
# 1. 确保 .env 文件中配置正确
cat .env | grep FEISHU_WEBHOOK

# 2. 运行一次分析（单次模式）
python crypto_main.py --once

# 3. 检查日志中是否有 "Feishu message sent to FEISHU_WEBHOOK_XXX" 字样
tail -f crypto_trading.log

# 4. 打开飞书群，检查是否收到对应的卡片消息
```

### 6.3 验证清单

| 检查项 | 预期结果 | 状态 |
|--------|----------|------|
| `.env` 文件中 4 个 Webhook URL 已配置 | 每个 URL 以 `https://open.feishu.cn` 开头 | ☐ |
| curl 测试消息能发送到群内 | 群内出现测试消息 | ☐ |
| 运行一次分析后，群内收到分析师报告 | 📊 格式的卡片消息 | ☐ |
| 辩论结果能推送到群 | 💬 格式的卡片消息 | ☐ |
| 风险评估能推送到群 | 🛡️ 格式的卡片消息 | ☐ |
| 交易执行结果能推送到群 | 💰 格式的卡片消息 | ☐ |

---

## 七、常见问题

### Q1: 我可以一个机器人发多个群吗？

**答**：不可以。每个自定义机器人的 Webhook URL **只能发送到创建它的群**。如果你要发送到多个群，需要在每个群内都创建对应的机器人，并收集所有 Webhook URL。

### Q2: Webhook URL 泄露了怎么办？

**答**：立即在群设置中**移除该机器人**，然后重新创建一个新的。旧的 URL 会立即失效。

### Q3: 飞书群内消息太多，能过滤吗？

**答**：自定义机器人无法过滤消息（它只能发送，不能接收）。但你可以在代码中增加发送频率控制，例如：
- 只在重大信号时发送（过滤小波动）
- 合并多个角色消息为一条总结消息

### Q4: 能不能让机器人之间"对话"？

**答**：不能直接对话（自定义机器人无法读取群消息）。但你可以通过代码逻辑模拟"讨论"效果：
1. 市场分析师先发送分析报告
2. 辩论员基于分析师的结果，发送多空辩论
3. 风控官综合前两者的结果，发送风险评估
4. 交易员最后发送执行结果

在飞书群内，你会看到这些消息按时间顺序出现，**看起来就像角色之间在讨论**。

### Q5: 企业版飞书有额外限制吗？

**答**：可能有的企业管理员会在后台禁用「自定义机器人」。如果遇到此情况：
1. 联系企业管理员，申请开启「自定义机器人」权限
2. 或者使用飞书开放平台的「应用机器人」（需要开发，复杂度更高）

### Q6: 消息发送频率有限制吗？

**答**：飞书 Webhook 有频率限制（约 100 条/分钟），但对于你的交易系统（每 4 小时分析一次），**完全不会触发限制**。

### Q7: 能发送带按钮的交互式卡片吗？

**答**：自定义机器人**只能发送静态卡片**，不支持按钮交互。如果需要按钮（如"确认下单"、"撤销订单"），需要使用飞书开放平台的「应用机器人」+ 事件回调。这会增加复杂度，需要单独评估。

---

## 八、进阶方案（可选）

如果你后续需要更高级的功能，可以考虑：

### 8.1 飞书开放平台应用机器人

**适用场景**：
- 需要接收群内消息（如你回复"确认"后机器人执行下单）
- 需要按钮交互
- 需要更丰富的消息格式

**复杂度**：⭐⭐⭐⭐ (中等偏高)
- 需要创建飞书开放平台应用
- 需要配置权限范围和事件回调
- 需要部署一个公网可达的回调 URL 服务

### 8.2 消息队列 + 多 Worker

**适用场景**：
- 多个交易对同时分析
- 高并发消息处理
- 消息优先级排序

**架构**：
```
Redis/RabbitMQ → 消息队列
    ↓
[Analyst Worker] [Debater Worker] [Risk Worker] [Trader Worker]
    ↓
各自独立的 Webhook
```

---

## 九、总结

| 项目 | 状态 |
|------|------|
| **难度** | ⭐⭐ (简单) |
| **预计耗时** | 30 分钟（创建 4 个机器人 + 代码修改） |
| **代码改动量** | 约 200 行（新增通知函数 + 环境变量） |
| **权限要求** | 最低（只需群内添加自定义机器人） |
| **成本** | 免费 |
| **维护成本** | 极低 |

**建议立即执行以下步骤**：

1. ✅ 在飞书群内创建 4 个自定义机器人
2. ✅ 将 Webhook URL 保存到 `.env` 文件
3. ✅ 修改 `crypto_main.py` 增加多角色通知函数
4. ✅ 运行一次测试，验证消息推送
5. ✅ 更新 Web UI 配置页面（可选）

祝搭建顺利！如有问题，参考本文档第七部分的常见问题解答。
