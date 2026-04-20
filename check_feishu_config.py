#!/usr/bin/env python3
"""
飞书多角色配置检查脚本

运行此脚本检查所有配置是否就绪：
    python check_feishu_config.py
"""

import os
import sys
from pathlib import Path

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def check_env_file():
    """检查 .env 文件是否存在"""
    print_header("步骤 1: 检查 .env 文件")
    
    env_path = Path('.env')
    if not env_path.exists():
        print_error(".env 文件不存在")
        print_info("请运行：cp .env.example .env")
        return False
    
    print_success(".env 文件存在")
    return True

def check_feishu_webhooks():
    """检查飞书 Webhook 配置"""
    print_header("步骤 2: 检查飞书 Webhook 配置")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    webhooks = {
        'FEISHU_WEBHOOK_URL': '通用通知（后备）',
        'FEISHU_WEBHOOK_ANALYST': '📈 市场分析师（✅ 核心角色）',
        'FEISHU_WEBHOOK_SENTIMENT': '😊 情绪分析师（⚠️ 预留）',
        'FEISHU_WEBHOOK_NEWS': '📰 新闻分析师（⚠️ 预留）',
        'FEISHU_WEBHOOK_FUNDAMENTALS': '💎 基本面分析师（⚠️ 预留）',
        'FEISHU_WEBHOOK_MANAGER': '⚖️ 研究经理（✅ 核心角色）',
        'FEISHU_WEBHOOK_RISK': '🛡️ 风险经理（⚠️ 预留）',
        'FEISHU_WEBHOOK_TRADER': '🎯 交易员（✅ 核心角色）',
    }
    
    configured = []
    not_configured = []
    
    for key, description in webhooks.items():
        value = os.getenv(key, '').strip()
        if value:
            # 验证 Webhook 格式
            if value.startswith('https://open.feishu.cn/open-apis/bot/v2/hook/'):
                configured.append((key, description))
                print_success(f"{description} ({key}) - 已配置")
            else:
                print_warning(f"{description} ({key}) - Webhook 格式可能不正确")
                not_configured.append((key, description))
        else:
            not_configured.append((key, description))
            print_error(f"{description} ({key}) - 未配置")
    
    print(f"\n{Colors.BOLD}配置统计:{Colors.END}")
    print(f"  已配置：{len(configured)} 个")
    print(f"  未配置：{len(not_configured)} 个")
    
    # 检查核心角色是否配置
    core_roles = ['FEISHU_WEBHOOK_ANALYST', 'FEISHU_WEBHOOK_MANAGER', 'FEISHU_WEBHOOK_TRADER']
    core_configured = [k for k in core_roles if os.getenv(k, '').strip()]
    
    if len(core_configured) > 0 or os.getenv('FEISHU_WEBHOOK_URL', '').strip():
        print_success(f"核心角色配置：{len(core_configured)}/3")
    else:
        print_warning("\n  至少配置一个核心角色或通用 Webhook 才能接收通知")
        return False
    
    return True

def check_llm_config():
    """检查 LLM 配置"""
    print_header("步骤 3: 检查 LLM 配置")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    dashscope_key = os.getenv('DASHSCOPE_API_KEY', '').strip()
    
    if not dashscope_key:
        print_error("DASHSCOPE_API_KEY 未配置")
        print_info("请在 https://dashscope.console.aliyun.com/ 获取 API Key")
        return False
    
    if dashscope_key.startswith('sk-'):
        print_success("DASHSCOPE_API_KEY 已配置（格式正确）")
        return True
    else:
        print_warning("DASHSCOPE_API_KEY 格式可能不正确（应以 sk- 开头）")
        return False

def check_bitget_config():
    """检查 Bitget 交易所配置"""
    print_header("步骤 4: 检查 Bitget 交易所配置")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('BITGET_API_KEY', '').strip()
    secret = os.getenv('BITGET_SECRET', '').strip()
    passphrase = os.getenv('BITGET_PASSPHRASE', '').strip()
    sandbox = os.getenv('BITGET_SANDBOX', 'true').lower()
    
    if not api_key or not secret or not passphrase:
        print_warning("Bitget API 未完全配置（仅分析模式可以跳过）")
        print_info("如需实盘交易，请在 Bitget 获取 API Key")
        return True  # 不影响分析功能
    
    print_success("Bitget API 已配置")
    
    if sandbox == 'true':
        print_info("当前模式：沙盒模式（模拟交易）")
    else:
        print_warning("当前模式：实盘交易（谨慎！）")
    
    return True

def check_output_language():
    """检查输出语言配置"""
    print_header("步骤 5: 检查输出语言配置")
    
    from tradingagents.default_config import DEFAULT_CONFIG, CRYPTO_CONFIG
    
    lang = DEFAULT_CONFIG.get('output_language', 'English')
    crypto_lang = CRYPTO_CONFIG.get('output_language', 'English')
    
    if lang == 'Chinese':
        print_success(f"系统输出语言：中文")
    else:
        print_warning(f"系统输出语言：{lang}（建议设置为 Chinese）")
    
    if crypto_lang == 'Chinese':
        print_success(f"Crypto 输出语言：中文")
    else:
        print_warning(f"Crypto 输出语言：{crypto_lang}（建议设置为 Chinese）")
    
    return lang == 'Chinese' or crypto_lang == 'Chinese'

def check_documentation():
    """检查文档是否齐全"""
    print_header("步骤 6: 检查文档完整性")
    
    docs = {
        'FEISHU_ROLE_CONFIG_GUIDE.md': '飞书多角色配置指南',
        'FEISHU_MULTI_ROLE_SETUP_COMPLETE.md': '配置完成总结',
        'FEISHU_MULTI_BOT_GUIDE.md': '飞书机器人搭建教程',
        'README.md': '项目说明文档',
    }
    
    for doc, description in docs.items():
        if Path(doc).exists():
            print_success(f"{description} ({doc})")
        else:
            print_error(f"{description} ({doc}) - 文件不存在")
    
    return True

def run_test():
    """询问是否运行测试"""
    print_header("步骤 7: 运行测试")
    
    print_info("是否立即运行一次分析测试？（需要约 1-2 分钟）")
    print("  y - 运行测试（推荐）")
    print("  n - 跳过测试")
    
    choice = input("\n请选择 [y/n]: ").strip().lower()
    
    if choice == 'y':
        print("\n正在运行测试...")
        import subprocess
        result = subprocess.run(
            ['python', 'crypto_main.py', '--once', '--no-execute'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("测试运行成功！")
            print_info("请检查飞书群是否收到通知")
        else:
            print_error("测试运行失败")
            print(result.stderr)
    else:
        print_info("跳过测试。稍后可以手动运行：python crypto_main.py --once --no-execute")
    
    return True

def main():
    """主函数"""
    print(f"\n{Colors.BOLD}飞书多角色配置检查工具{Colors.END}")
    print("本工具将检查所有配置是否就绪\n")
    
    checks = [
        check_env_file,
        check_feishu_webhooks,
        check_llm_config,
        check_bitget_config,
        check_output_language,
        check_documentation,
        run_test,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}检查被用户中断{Colors.END}")
            sys.exit(0)
        except Exception as e:
            print_error(f"检查失败：{str(e)}")
            results.append(False)
    
    # 汇总结果
    print_header("配置检查汇总")
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过检查：{passed}/{total}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有检查通过！系统已就绪{Colors.END}")
        print(f"\n{Colors.BLUE}下一步:{Colors.END}")
        print("  1. 如果还没运行测试，请运行：python crypto_main.py --once --no-execute")
        print("  2. 检查飞书群是否收到通知")
        print("  3. 查看日志文件：cat crypto_trading.log")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ 部分检查未通过，请根据上述提示进行配置{Colors.END}")
    
    print()

if __name__ == '__main__':
    main()
