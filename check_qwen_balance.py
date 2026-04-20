#!/usr/bin/env python3
"""
阿里云百炼平台余额查询工具

功能：
- 查询账户余额
- 查看 Token 用量统计
- 计算预估可用时间
- 设置余额预警提醒

使用方法:
    python check_qwen_balance.py
    
注意：
需要在 .env 文件中配置阿里云 AccessKey：
    ALIYUN_ACCESS_KEY_ID=LTAIxxxxxxxxx
    ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxx
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def load_env():
    """加载环境变量"""
    load_dotenv()
    
    access_key = os.getenv('ALIYUN_ACCESS_KEY_ID')
    secret_key = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
    
    return access_key, secret_key

def check_balance_manual():
    """
    手动查询余额（通过控制台）
    
    由于阿里云 API 需要复杂签名，推荐直接访问控制台查看
    """
    print_header("余额查询方式")
    
    print("推荐方式：访问阿里云控制台\n")
    print(f"  {Colors.GREEN}1. 百炼控制台{Colors.END}")
    print(f"     地址：https://bailian.console.aliyun.com")
    print(f"     路径：费用中心 → 账单详情\n")
    
    print(f"  {Colors.GREEN}2. 阿里云用户中心{Colors.END}")
    print(f"     地址：https://usercenter2.aliyun.com")
    print(f"     查看：可用余额、代金券\n")
    
    print(f"  {Colors.GREEN}3. 阿里云 APP{Colors.END}")
    print(f"     搜索「百炼」或「Model Studio」")
    print(f"     随时查看余额和用量\n")
    
    print("-" * 60)
    print()
    
    # 提供快速链接
    print("快速链接:")
    print(f"  {Colors.CYAN}📊 百炼控制台：https://bailian.console.aliyun.com{Colors.END}")
    print(f"  {Colors.CYAN}💰 费用中心：https://usercenter2.aliyun.com{Colors.END}")
    print(f"  {Colors.CYAN}📱 用量统计：https://bailian.console.aliyun.com/?tab=usage{Colors.END}")
    print()

def estimate_usage():
    """估算 Token 用量和费用"""
    print_header("用量估算工具")
    
    print("请输入你的使用模式:\n")
    
    # 选择模式
    print("1. 日线回测模式（¥15-25/月）")
    print("2. 4H + qwen-plus 模式（¥144-216/月）")
    print("3. 4H + qwen-max 模式（¥324-540/月）")
    print("4. 自定义模式")
    print()
    
    choice = input("请选择 [1-4]: ").strip()
    
    modes = {
        '1': {'cost': 20, 'name': '日线回测'},
        '2': {'cost': 180, 'name': '4H + qwen-plus'},
        '3': {'cost': 430, 'name': '4H + qwen-max'},
    }
    
    if choice in modes:
        monthly_cost = modes[choice]['cost']
        mode_name = modes[choice]['name']
    else:
        print("\n自定义模式:")
        daily_cost = float(input("  预估每日成本 (¥): ") or "10")
        monthly_cost = daily_cost * 30
        mode_name = '自定义'
    
    print()
    print(f"{Colors.BOLD}估算结果（{mode_name}）:{Colors.END}")
    print(f"  预估月成本：¥{monthly_cost:.2f}")
    print(f"  预估日成本：¥{monthly_cost/30:.2f}")
    print(f"  预估时成本：¥{monthly_cost/30/24:.2f}")
    print()

def check_remaining_days():
    """计算余额可用天数"""
    print_header("余额可用天数计算")
    
    # 输入当前余额
    balance = input("当前账户余额 (¥): ").strip()
    if not balance:
        print_warning("未输入余额，跳过")
        return
    
    try:
        balance = float(balance)
    except ValueError:
        print_error("无效金额")
        return
    
    # 选择使用模式
    print("\n使用模式:")
    print("1. 日线回测（¥20/月）")
    print("2. 4H + qwen-plus（¥180/月）")
    print("3. 4H + qwen-max（¥430/月）")
    print()
    
    choice = input("请选择 [1-3]: ").strip()
    
    modes = {
        '1': 20,
        '2': 180,
        '3': 430,
    }
    
    monthly_cost = modes.get(choice, 20)
    daily_cost = monthly_cost / 30
    
    remaining_days = balance / daily_cost
    remaining_months = balance / monthly_cost
    
    print()
    print(f"{Colors.GREEN}{Colors.BOLD}计算结果:{Colors.END}")
    print(f"  当前余额：¥{balance:.2f}")
    print(f"  可用天数：{remaining_days:.1f} 天")
    print(f"  可用月数：{remaining_months:.1f} 月")
    
    if remaining_days < 7:
        print(f"\n{Colors.RED}⚠️  警告：余额不足 7 天，建议充值！{Colors.END}")
    elif remaining_days < 30:
        print(f"\n{Colors.YELLOW}⚠️  提醒：余额不足 1 个月，建议充值！{Colors.END}")
    else:
        print(f"\n{Colors.GREEN}✓ 余额充足{Colors.END}")
    
    print()

def show_token_prices():
    """显示 Token 价格"""
    print_header("Qwen 模型价格表（2026 年）")
    
    prices = [
        {
            'model': 'qwen-turbo',
            'input': '¥0.002/1K',
            'output': '¥0.006/1K',
            'desc': '最便宜，适合测试'
        },
        {
            'model': 'qwen-plus',
            'input': '¥0.02/1K',
            'output': '¥0.06/1K',
            'desc': '平衡方案，推荐回测'
        },
        {
            'model': 'qwen-max',
            'input': '¥0.08/1K',
            'output': '¥0.24/1K',
            'desc': '最强能力，推荐实盘'
        },
        {
            'model': 'qwen-vl-max',
            'input': '¥0.05/张 + Token',
            'output': '¥0.15/张 + Token',
            'desc': '视觉分析（可选）'
        },
    ]
    
    print(f"{'模型':<15} {'输入价格':<15} {'输出价格':<15} {'说明':<20}")
    print("-" * 65)
    for p in prices:
        print(f"{p['model']:<15} {p['input']:<15} {p['output']:<15} {p['desc']:<20}")
    
    print()
    print("注：价格为阿里云百炼平台官方定价（2026 年 4 月）")
    print()

def show_usage_commands():
    """显示查询用量的命令"""
    print_header("查询用量的方法")
    
    print(f"{Colors.BOLD}方法 1: 控制台查看（推荐）{Colors.END}")
    print("  1. 访问：https://bailian.console.aliyun.com")
    print("  2. 左侧菜单：费用中心 → 账单详情")
    print("  3. 选择产品：百炼（Model Studio）")
    print("  4. 查看每日/每月 Token 消耗量")
    print()
    
    print(f"{Colors.BOLD}方法 2: API 调用统计{Colors.END}")
    print("  1. 访问：https://bailian.console.aliyun.com/?tab=usage")
    print("  2. 选择时间范围（今日/本周/本月）")
    print("  3. 按模型筛选（qwen-max/plus/turbo）")
    print("  4. 查看调用次数、失败率、延迟")
    print()
    
    print(f"{Colors.BOLD}方法 3: 阿里云 APP{Colors.END}")
    print("  1. 下载阿里云 APP")
    print("  2. 搜索「百炼」或「Model Studio」")
    print("  3. 查看余额和用量统计")
    print()
    
    print(f"{Colors.BOLD}方法 4: 设置预警{Colors.END}")
    print("  1. 访问：https://usercenter2.aliyun.com")
    print("  2. 左侧菜单：预警管理 → 余额预警")
    print("  3. 设置预警阈值（如¥100）")
    print("  4. 选择通知方式（短信 + 邮件 + APP）")
    print()

def quick_start():
    """快速入门指南"""
    print_header("快速入门：3 步查看余额")
    
    print(f"{Colors.GREEN}步骤 1: 登录控制台{Colors.END}")
    print("  地址：https://bailian.console.aliyun.com")
    print()
    
    print(f"{Colors.GREEN}步骤 2: 进入费用中心{Colors.END}")
    print("  左侧菜单 → 费用中心 → 账单详情")
    print()
    
    print(f"{Colors.GREEN}步骤 3: 查看余额和用量{Colors.END}")
    print("  - 可用余额：账户剩余金额")
    print("  - 代金券：可用优惠券")
    print("  - Token 用量：各模型消耗量")
    print()
    
    print(f"{Colors.CYAN}💡 提示：建议设置余额预警，余额低于¥100 时自动通知{Colors.END}")
    print()

def main():
    """主函数"""
    print(f"\n{Colors.BOLD}阿里云百炼平台余额查询工具{Colors.END}")
    print("本工具帮助你查看 Qwen API 余额和用量\n")
    
    while True:
        print(f"{Colors.BOLD}请选择操作:{Colors.END}")
        print()
        print("  1. 📊 查看余额查询方式（控制台链接）")
        print("  2. 💰 计算余额可用天数")
        print("  3. 📈 估算用量和费用")
        print("  4. 💵 查看 Qwen 模型价格表")
        print("  5. 📱 查询用量的方法")
        print("  6. 🚀 快速入门（3 步查看余额）")
        print("  0. 退出")
        print()
        
        choice = input("请选择 [0-6]: ").strip()
        
        if choice == '1':
            check_balance_manual()
        elif choice == '2':
            check_remaining_days()
        elif choice == '3':
            estimate_usage()
        elif choice == '4':
            show_token_prices()
        elif choice == '5':
            show_usage_commands()
        elif choice == '6':
            quick_start()
        elif choice == '0':
            print_info("已退出")
            break
        else:
            print_error("无效选择，请重新输入")
            print()

if __name__ == '__main__':
    main()
