# tradingagents/agents/managers/crypto_research_manager.py
"""
加密货币研究经理（重构版）- 简化汇总角色

重构要点：
1. 移除多空辩论逻辑，改为简单汇总技术面和宏观面分析
2. 输出综合研究报告（不直接产生交易信号，交给 Portfolio Manager 决策）
3. 保留记忆功能用于复盘
"""

import logging
from typing import Dict, Any
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction

logger = logging.getLogger(__name__)


def create_crypto_research_manager(llm, memory):
    """
    创建研究经理节点
    
    职责：
    - 综合技术面分析师和宏观链上分析师的报告
    - 识别两个报告之间的一致性和分歧
    - 输出结构化综合研究报告
    - 不直接产生交易信号（交给 Portfolio Manager）
    
    Args:
        llm: LLM 客户端（使用深度思考模型 Qwen-Max）
        memory: 记忆存储器
    
    Returns:
        research_manager_node 函数
    """
    
    def research_manager_node(state) -> Dict[str, Any]:
        symbol = state["company_of_interest"]
        instrument_context = build_instrument_context(symbol)
        
        # 获取两个分析师的报告
        technical_report = state.get("technical_report", "")
        macro_onchain_report = state.get("macro_onchain_report", "")
        
        # 获取记忆
        curr_situation = f"{technical_report}\n\n{macro_onchain_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)
        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"
        
        system_message_template = """你是一家加密货币量化基金的研究经理。你的职责是将技术面和宏观/链上分析综合成一份全面的研究报告。

**你的职责：**
1. 综合技术面分析师和宏观/链上分析师的报告
2. 识别两种视角之间的一致性和分歧
3. 评估整体信号质量和置信度
4. 生成结构化的研究总结（不是交易决策——那是投资组合经理的工作）

**输入报告：**
- 技术面分析报告：{technical_report}
- 宏观/链上分析报告：{macro_onchain_report}

**过往研究经验：**
{past_memory_str}

**输出格式（结构化 JSON）：**
```json
{{
  "synthesis": {{
    "technical_summary": "<3-4 句话总结技术面设置>",
    "macro_summary": "<3-4 句话总结宏观/链上设置>",
    "signal_alignment": "ALIGNED|DIVERGENT|MIXED",
    "alignment_notes": "<解释信号是否一致或有冲突>"
  }},
  "combined_evidence": {{
    "bullish_factors": ["<看涨因素 1>", "<看涨因素 2>", ...],
    "bearish_factors": ["<看跌因素 1>", "<看跌因素 2>", ...],
    "neutral_factors": ["<中性因素 1>", ...]
  }},
  "signal_quality": {{
    "data_completeness": "HIGH|MODERATE|LOW",
    "signal_clarity": "CLEAR|MIXED|AMBIGUOUS",
    "confidence_level": <1-10 整数>
  }},
  "key_risks": ["<风险 1>", "<风险 2>", ...],
  "research_conclusion": "<2-3 段全面的总结，供投资组合经理使用>"
}}

**重要：**
- 不要做出交易决策（方向、仓位大小等）
- 专注于客观综合证据
- 突出任何数据缺口或冲突信号
- 本报告将直接输入给投资组合经理用于决策

{instrument_context}
"""
        lang_instruction = get_language_instruction()
        system_message = system_message_template.format(
            technical_report=technical_report,
            macro_onchain_report=macro_onchain_report,
            past_memory_str=past_memory_str,
            instrument_context=instrument_context
        ) + lang_instruction

        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}"),
            MessagesPlaceholder(variable_name="messages"),
        ])

        chain = prompt.partial(system_message=system_message) | llm
        result = chain.invoke({"messages": state["messages"]})

        research_report = result.content

        # 保存到记忆 - 使用 add_situations 方法（暂时禁用，避免 BM25 空文档错误）
        # memory.add_situations([(curr_situation, research_report)])

        return {
            "research_report": research_report,
            "investment_plan": research_report,  # 兼容现有 state 字段
        }
    
    return research_manager_node
