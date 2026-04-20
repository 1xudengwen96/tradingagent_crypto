#!/usr/bin/env python3
"""
Qwen 模型连接验证测试脚本

测试 qwen3-max 和 qwen3.6-plus 模型是否可以正常连接和调用。
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

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


def test_model_connection(model_name: str, test_prompt: str = "你好，请用一句话介绍你自己。") -> bool:
    """测试指定模型的连接和响应。"""
    print(f"\n正在测试模型：{Colors.BOLD}{model_name}{Colors.END}")
    print("-" * 50)
    
    try:
        from tradingagents.llm_clients import create_llm_client
        
        # 创建客户端
        print("  1. 创建 LLM 客户端... ", end="")
        client = create_llm_client(provider="qwen", model=model_name)
        print_success("成功")
        
        # 获取 LLM 实例
        print("  2. 初始化 LLM 实例... ", end="")
        llm = client.get_llm()
        print_success("成功")
        
        # 发送测试消息
        print("  3. 发送测试消息... ", end="")
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=test_prompt)]
        print_success("已发送")
        
        # 获取响应
        print("  4. 等待模型响应... ", end="")
        response = llm.invoke(messages)
        print_success("成功")
        
        # 显示响应
        print(f"\n  {Colors.GREEN}模型响应:{Colors.END}")
        print(f"  {Colors.CYAN}{response.content}{Colors.END}\n")
        
        return True
        
    except Exception as e:
        print_error(f"失败：{str(e)}")
        return False


def test_api_key() -> bool:
    """验证 API Key 是否配置。"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        print_error("未找到 DASHSCOPE_API_KEY 环境变量")
        print_info("请检查 .env 文件是否配置了 DASHSCOPE_API_KEY")
        return False
    
    # 检查 API Key 格式
    if not api_key.startswith("sk-"):
        print_warning(f"API Key 格式可能不正确：{api_key[:10]}...")
        return False
    
    print_success(f"API Key 已配置：{api_key[:10]}...{api_key[-5:]}")
    return True


def main():
    print_header("Qwen 模型连接验证测试")
    
    # 测试配置
    models_to_test = [
        "qwen3-max",      # 深度思考模型
        "qwen3.6-plus",   # 快速思考模型
    ]
    
    # 1. 检查 API Key
    print(f"{Colors.BOLD}步骤 1: 检查 API Key 配置{Colors.END}")
    if not test_api_key():
        print_error("\nAPI Key 未配置，无法继续测试")
        sys.exit(1)
    
    # 2. 测试各个模型
    print(f"\n{Colors.BOLD}步骤 2: 测试模型连接{Colors.END}")
    
    results = {}
    for model in models_to_test:
        results[model] = test_model_connection(model)
    
    # 3. 显示测试结果
    print_header("测试结果汇总")
    
    all_passed = True
    for model, passed in results.items():
        status = f"{Colors.GREEN}✓ 通过{Colors.END}" if passed else f"{Colors.RED}✗ 失败{Colors.END}"
        print(f"  {model}: {status}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print_success("所有模型测试通过！配置正确。")
        print_info("\n下一步:")
        print("  运行：python crypto_main.py --once --no-execute")
        print("  开始实际交易分析！")
    else:
        print_error("部分模型测试失败")
        print_info("\n可能的原因:")
        print("  1. API Key 无效或余额不足")
        print("  2. 模型名称不正确（请查看阿里云百炼平台文档）")
        print("  3. 网络连接问题")
        print("\n建议:")
        print("  访问 https://dashscope.console.aliyun.com/ 查看模型列表和余额")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
