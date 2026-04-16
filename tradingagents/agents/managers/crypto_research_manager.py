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
        
        system_message = f"""You are the Research Manager for a crypto quantitative fund. Your role is to synthesize technical and macro/on-chain analysis into a comprehensive research report.

**Your Responsibilities:**
1. Synthesize the Technical Analyst and Macro/On-chain Analyst reports
2. Identify consistencies and divergences between the two perspectives
3. Assess overall signal quality and confidence
4. Produce a structured research summary (NOT a trading decision — that's the Portfolio Manager's job)

**Input Reports:**
- Technical Analysis Report: {technical_report}
- Macro/On-chain Analysis Report: {macro_onchain_report}

**Past Research Lessons:**
{past_memory_str}

**Output Format (structured JSON):**
```json
{{
  "synthesis": {{
    "technical_summary": "<3-4 sentence summary of technical setup>",
    "macro_summary": "<3-4 sentence summary of macro/on-chain setup>",
    "signal_alignment": "ALIGNED|DIVERGENT|MIXED",
    "alignment_notes": "<explain if signals agree or conflict>"
  }},
  "combined_evidence": {{
    "bullish_factors": ["<factor 1>", "<factor 2>", ...],
    "bearish_factors": ["<factor 1>", "<factor 2>", ...],
    "neutral_factors": ["<factor 1>", ...]
  }},
  "signal_quality": {{
    "data_completeness": "HIGH|MODERATE|LOW",
    "signal_clarity": "CLEAR|MIXED|AMBIGUOUS",
    "confidence_level": <1-10 integer>
  }},
  "key_risks": ["<risk 1>", "<risk 2>", ...],
  "research_conclusion": "<2-3 paragraph comprehensive summary for Portfolio Manager>"
}}

**Important:**
- Do NOT make trading decisions (direction, position size, etc.)
- Focus on synthesizing evidence objectively
- Highlight any data gaps or conflicting signals
- This report feeds directly into the Portfolio Manager's decision process

{instrument_context}
""" + get_language_instruction()
        
        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
        ])
        
        chain = prompt | llm
        result = chain.invoke({})
        
        research_report = result.content
        
        # 保存到记忆
        memory.save_memory(curr_situation, research_report)
        
        return {
            "research_report": research_report,
            "investment_plan": research_report,  # 兼容现有 state 字段
        }
    
    return research_manager_node
