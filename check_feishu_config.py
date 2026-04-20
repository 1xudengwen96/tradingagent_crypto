#!/usr/bin/env python3
"""
飞书 Webhook 配置检查工具
检查并显示当前飞书通知配置状态
"""

import os
from dotenv import load_dotenv

# 强制重新加载 .env 文件
load_dotenv(override=True)

print("=" * 60)
print("📱 飞书 Webhook 配置检查")
print("=" * 60)

webhooks = {
    "📈 市场分析师": "FEISHU_WEBHOOK_ANALYST",
    "😊 情绪分析师": "FEISHU_WEBHOOK_SENTIMENT",
    "📰 新闻分析师": "FEISHU_WEBHOOK_NEWS",
    "💎 宏观/链上分析师": "FEISHU_WEBHOOK_FUNDAMENTALS",
    "⚖️ 研究经理": "FEISHU_WEBHOOK_MANAGER",
    "🛡️ 风险经理": "FEISHU_WEBHOOK_RISK",
    "🎯 交易员": "FEISHU_WEBHOOK_TRADER",
    "📢 通用通知": "FEISHU_WEBHOOK_URL",
}

configured = []
not_configured = []

for role, env_var in webhooks.items():
    value = os.getenv(env_var, "")
    if value and value.startswith("https://"):
        configured.append((role, env_var, value))
        print(f"\n✅ {role}")
        print(f"   环境变量：{env_var}")
        print(f"   Webhook: {value[:50]}...")
    else:
        not_configured.append((role, env_var))
        print(f"\n❌ {role}")
        print(f"   环境变量：{env_var} - 未配置")

print("\n" + "=" * 60)
print(f"配置统计：{len(configured)} 个已配置，{len(not_configured)} 个未配置")
print("=" * 60)

if not_configured:
    print("\n💡 建议：")
    print("1. 如需为每个角色配置独立 webhook，请在 .env 文件中填写对应的 WEBHOOK_URL")
    print("2. 如需所有角色发送到同一个群，可将所有未配置的 webhook 设为相同值")
    print("3. 或者运行以下命令快速配置：")
    print()
    
    # 如果已有至少一个配置的 webhook，建议使用它作为默认值
    if configured:
        default_webhook = configured[0][2]
        print(f"   # 使用 {configured[0][0]} 的 webhook 作为默认值")
        for role, env_var in not_configured:
            if env_var != "FEISHU_WEBHOOK_URL":  # 跳过通用通知
                print(f"   {env_var}={default_webhook}")
    else:
        print("   请先至少配置一个 webhook URL")

print("\n" + "=" * 60)
