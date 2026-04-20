#!/usr/bin/env python3
"""
回测配置快速切换工具

用法:
    python backtest_config.py  # 交互式选择配置
    python backtest_config.py --mode daily      # 日线回测模式
    python backtest_config.py --mode 4h-plus    # 4H + qwen-plus
    python backtest_config.py --mode 4h-max     # 4H + qwen-max（默认）
    python backtest_config.py --mode mock       # Mock 模式（零成本）
    python backtest_config.py --show            # 显示当前配置
"""

import argparse
import os
import sys
from pathlib import Path

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

def show_current_config():
    """显示当前配置"""
    print_header("当前配置")
    
    # 读取 .env 文件
    env_path = Path('.env')
    if env_path.exists():
        print(f"{Colors.BOLD}.env 配置:{Colors.END}")
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if 'KEY' in key or 'SECRET' in key or 'PASSPHRASE' in key:
                            value = '***hidden***'
                        print(f"  {key}={value}")
    
    # 读取 default_config.py
    config_path = Path('tradingagents/default_config.py')
    if config_path.exists():
        print(f"\n{Colors.BOLD}default_config.py 配置:{Colors.END}")
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if '"deep_think_llm"' in content:
                import re
                deep_match = re.search(r'"deep_think_llm":\s*"([^"]+)"', content)
                quick_match = re.search(r'"quick_think_llm":\s*"([^"]+)"', content)
                timeframe_match = re.search(r'"timeframe":\s*os\.getenv\("TIMEFRAME",\s*"([^"]+)"\)', content)
                
                if deep_match:
                    print(f"  deep_think_llm: {deep_match.group(1)}")
                if quick_match:
                    print(f"  quick_think_llm: {quick_match.group(1)}")
                if timeframe_match:
                    print(f"  timeframe: {timeframe_match.group(1)}")
    
    print()

def apply_config(mode):
    """应用配置"""
    config_path = Path('tradingagents/default_config.py')
    env_path = Path('.env')
    
    if not config_path.exists():
        print_error("找不到 tradingagents/default_config.py")
        return False
    
    # 配置映射
    configs = {
        'daily': {
            'name': '日线回测模式',
            'timeframe': '1d',
            'deep_think_llm': 'qwen-plus',
            'quick_think_llm': 'qwen-plus',
            'cost_estimate': '¥15-25/月',
            'description': '最省钱，适合策略初步验证'
        },
        '4h-plus': {
            'name': '4H + qwen-plus 模式',
            'timeframe': '4h',
            'deep_think_llm': 'qwen-plus',
            'quick_think_llm': 'qwen-plus',
            'cost_estimate': '¥144-216/月',
            'description': '平衡方案，适合回测 + 调参'
        },
        '4h-max': {
            'name': '4H + qwen-max 模式（默认）',
            'timeframe': '4h',
            'deep_think_llm': 'qwen-max',
            'quick_think_llm': 'qwen-plus',
            'cost_estimate': '¥324-540/月',
            'description': '完整精度，适合最终测试和实盘'
        },
        'mock': {
            'name': 'Mock 模式',
            'timeframe': '4h',
            'deep_think_llm': 'mock',
            'quick_think_llm': 'mock',
            'cost_estimate': '¥0',
            'description': '零成本，仅测试流程'
        }
    }
    
    if mode not in configs:
        print_error(f"未知模式：{mode}")
        print_info("可用模式：daily, 4h-plus, 4h-max, mock")
        return False
    
    config = configs[mode]
    
    # 修改 default_config.py
    print(f"正在配置：{config['name']}")
    print(f"描述：{config['description']}")
    print(f"预估成本：{config['cost_estimate']}")
    print()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换配置
    import re
    
    # 替换 timeframe
    content = re.sub(
        r'"timeframe":\s*os\.getenv\("TIMEFRAME",\s*"[^"]+"\)',
        f'"timeframe": os.getenv("TIMEFRAME", "{config["timeframe"]}")',
        content
    )
    
    # 替换 deep_think_llm
    content = re.sub(
        r'"deep_think_llm":\s*"[^"]+"',
        f'"deep_think_llm": "{config["deep_think_llm"]}"',
        content
    )
    
    # 替换 quick_think_llm
    content = re.sub(
        r'"quick_think_llm":\s*"[^"]+"',
        f'"quick_think_llm": "{config["quick_think_llm"]}"',
        content
    )
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print_success(f"已更新 tradingagents/default_config.py")
    
    # 修改 .env 文件
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找并替换 TIMEFRAME
        timeframe_found = False
        for i, line in enumerate(lines):
            if line.startswith('TIMEFRAME='):
                lines[i] = f'TIMEFRAME={config["timeframe"]}\n'
                timeframe_found = True
                break
        
        if not timeframe_found:
            lines.append(f'\nTIMEFRAME={config["timeframe"]}\n')
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print_success(f"已更新 .env 文件")
    
    print()
    print(f"{Colors.GREEN}{Colors.BOLD}配置完成！{Colors.END}")
    print()
    print("下一步:")
    print(f"  1. 运行测试：python crypto_main.py --once --no-execute")
    print(f"  2. 查看日志：cat crypto_trading.log")
    print()
    
    return True

def show_menu():
    """显示菜单"""
    print_header("回测配置选择")
    
    print("可选模式:\n")
    print(f"  {Colors.GREEN}1. 日线回测模式{Colors.END}")
    print(f"     配置：TIMEFRAME=1d, LLM=qwen-plus")
    print(f"     成本：¥15-25/月（省 83%）")
    print(f"     适用：策略初步验证\n")
    
    print(f"  {Colors.BLUE}2. 4H + qwen-plus 模式{Colors.END}")
    print(f"     配置：TIMEFRAME=4h, LLM=qwen-plus")
    print(f"     成本：¥144-216/月（省 55%）")
    print(f"     适用：回测 + 参数调优\n")
    
    print(f"  {Colors.CYAN}3. 4H + qwen-max 模式（默认）{Colors.END}")
    print(f"     配置：TIMEFRAME=4h, LLM=qwen-max + qwen-plus")
    print(f"     成本：¥324-540/月")
    print(f"     适用：最终测试、实盘交易\n")
    
    print(f"  {Colors.YELLOW}4. Mock 模式{Colors.END}")
    print(f"     配置：TIMEFRAME=4h, LLM=mock")
    print(f"     成本：¥0（零成本）")
    print(f"     适用：流程测试\n")
    
    choice = input("请选择模式 [1-4, 直接回车退出]: ").strip()
    
    mode_map = {
        '1': 'daily',
        '2': '4h-plus',
        '3': '4h-max',
        '4': 'mock'
    }
    
    if choice in mode_map:
        return mode_map[choice]
    elif choice == '':
        return None
    else:
        print_error("无效选择")
        return None

def main():
    parser = argparse.ArgumentParser(description='回测配置快速切换工具')
    parser.add_argument('--mode', type=str, choices=['daily', '4h-plus', '4h-max', 'mock'],
                        help='配置模式')
    parser.add_argument('--show', action='store_true', help='显示当前配置')
    
    args = parser.parse_args()
    
    if args.show:
        show_current_config()
        return
    
    if args.mode:
        apply_config(args.mode)
        return
    
    # 交互模式
    mode = show_menu()
    if mode:
        apply_config(mode)
    else:
        print_info("已退出")

if __name__ == '__main__':
    main()
