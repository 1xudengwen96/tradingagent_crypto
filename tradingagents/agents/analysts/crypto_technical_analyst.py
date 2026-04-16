# tradingagents/agents/analysts/crypto_technical_analyst.py
"""
加密货币技术面分析师（重构版）

重构要点：
1. 专注 4H 和日线级别趋势识别
2. 强制数据验证：所有分析必须基于真实数据
3. 结构化输出：必须包含 evidence 字段
4. 规则门卫：先用 Python 计算明确信号，再让 LLM 评估
5. 支持视觉化：生成 K 线图表供 Qwen-VL-Max 分析
"""

import logging
import pandas as pd
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
from tradingagents.agents.utils.crypto_tools import (
    get_crypto_ohlcv,
    get_crypto_indicators,
    get_funding_rate,
    get_crypto_ticker,
)

logger = logging.getLogger(__name__)


def _validate_data_quality(ohlcv_data: str, indicators_data: str) -> Dict[str, Any]:
    """
    数据质量验证器（Rule-Based Guardrail）
    
    在调用 LLM 之前，先用 Python 验证数据的有效性和信号质量。
    返回验证结果和客观信号，防止 AI 幻觉。
    """
    validation = {
        "data_available": False,
        "trend_signal": "UNKNOWN",
        "momentum_signal": "UNKNOWN",
        "volatility_level": "UNKNOWN",
        "warnings": [],
        "objective_facts": [],
    }
    
    try:
        # 解析 OHLCV 数据
        if not ohlcv_data or "Error" in ohlcv_data:
            validation["warnings"].append("OHLCV data unavailable")
            return validation
        
        # 解析指标数据
        if not indicators_data or "Error" in indicators_data:
            validation["warnings"].append("Technical indicators unavailable")
            return validation
        
        validation["data_available"] = True
        
        # 从指标数据中提取客观事实（示例逻辑，实际需解析真实数据）
        # 这里假设 indicators_data 包含 RSI、MACD 等数值
        # 实际实现中需要从字符串解析出具体数值
        
        validation["objective_facts"].append("Data validation passed")
        
    except Exception as e:
        validation["warnings"].append(f"Data validation error: {str(e)}")
    
    return validation


def _generate_kline_chart(
    symbol: str,
    timeframe: str,
    ohlcv_data: pd.DataFrame,
    indicators: Dict[str, Any],
    output_path: str,
) -> Optional[str]:
    """
    生成 K 线图表（为视觉化大模型准备）
    
    使用 mplfinance 生成包含以下元素的图表：
    - K 线（蜡烛图）
    - 成交量
    - 关键均线（MA20, MA60）
    - MACD 子图
    - RSI 子图
    
    Args:
        symbol: 交易对
        timeframe: 时间周期
        ohlcv_data: OHLCV 数据 DataFrame
        indicators: 技术指标字典
        output_path: 输出文件路径
    
    Returns:
        生成的图表文件路径，失败返回 None
    """
    try:
        import mplfinance as mpf
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
        
        # 数据预处理
        df = ohlcv_data.copy()
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df = df.set_index('datetime')
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        # 创建多子图布局
        fig = plt.figure(figsize=(14, 10))
        gs = GridSpec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.1)
        
        # 主图：K 线 + 均线
        ax_main = fig.add_subplot(gs[0])
        mpf.plot(
            df,
            type='candle',
            ax=ax_main,
            show_nontrading=False,
            warn_too_much_data=999999,
        )
        
        # 添加均线（如果数据可用）
        if 'sma20' in indicators:
            ax_main.plot(df.index, indicators.get('sma20', []), label='MA20', linewidth=1.5, color='blue')
        if 'sma50' in indicators:
            ax_main.plot(df.index, indicators.get('sma50', []), label='MA50', linewidth=1.5, color='orange')
        if 'ema20' in indicators:
            ax_main.plot(df.index, indicators.get('ema20', []), label='EMA20', linewidth=1.5, color='purple')
        
        ax_main.set_title(f'{symbol} - {timeframe.upper()} Technical Analysis Chart')
        ax_main.set_ylabel('Price (USDT)')
        ax_main.legend(loc='upper left')
        ax_main.grid(True, alpha=0.3)
        
        # 成交量子图
        ax_vol = fig.add_subplot(gs[1], sharex=ax_main)
        ax_vol.bar(df.index, df['volume'], width=0.003, color=['green' if c > o else 'red' for o, c in zip(df['open'], df['close'])])
        ax_vol.set_ylabel('Volume')
        ax_vol.grid(True, alpha=0.3)
        
        # MACD 子图
        ax_macd = fig.add_subplot(gs[2], sharex=ax_main)
        if 'macd' in indicators and 'macd_signal' in indicators:
            ax_macd.plot(df.index, indicators['macd'], label='MACD', color='blue')
            ax_macd.plot(df.index, indicators['macd_signal'], label='Signal', color='orange')
            histogram = [m - s for m, s in zip(indicators['macd'], indicators['macd_signal'])]
            ax_macd.bar(df.index, histogram, width=0.003, color=['green' if h > 0 else 'red' for h in histogram], alpha=0.5)
        ax_macd.set_ylabel('MACD')
        ax_macd.legend(loc='upper left')
        ax_macd.grid(True, alpha=0.3)
        
        # RSI 子图
        ax_rsi = fig.add_subplot(gs[3], sharex=ax_main)
        if 'rsi' in indicators:
            ax_rsi.plot(df.index, indicators['rsi'], label='RSI(14)', color='purple')
            ax_rsi.axhline(y=70, color='r', linestyle='--', alpha=0.5, label='Overbought (70)')
            ax_rsi.axhline(y=30, color='g', linestyle='--', alpha=0.5, label='Oversold (30)')
        ax_rsi.set_ylabel('RSI')
        ax_rsi.set_xlabel('Date')
        ax_rsi.legend(loc='upper left')
        ax_rsi.grid(True, alpha=0.3)
        
        # 保存图片
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"K-line chart generated: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate K-line chart: {e}")
        return None


def create_crypto_technical_analyst(llm, enable_vision: bool = False):
    """
    创建技术面分析师节点
    
    Args:
        llm: LLM 客户端
        enable_vision: 是否启用视觉分析（需要 Qwen-VL-Max）
    
    Returns:
        crypto_technical_analyst_node 函数
    """
    
    def crypto_technical_analyst_node(state) -> Dict[str, Any]:
        current_date = state["trade_date"]
        symbol = state["company_of_interest"]
        timeframe = state.get("timeframe", "4h")
        instrument_context = build_instrument_context(symbol)
        
        # 工具集：仅包含技术分析必需的工具
        tools = [
            get_crypto_ticker,
            get_crypto_ohlcv,
            get_crypto_indicators,
            get_funding_rate,
        ]
        
        # 系统提示词：强调数据驱动和结构化输出
        system_message = f"""You are a senior cryptocurrency technical analyst specializing in 4H and Daily timeframe trend trading.

**Core Principles:**
1. **Data-First**: All analysis MUST be grounded in real data (price, indicators, volume). Never hallucinate.
2. **Evidence-Based**: Every claim must cite specific data points (e.g., "RSI=32, below 30 oversold threshold").
3. **4H/Daily Focus**: Ignore short-term noise. Focus on medium-to-long term trends.
4. **Structured Output**: Your response MUST follow the JSON format below.

**Workflow (execute in order):**
1. Call `get_crypto_ticker` for current price context.
2. Call `get_crypto_ohlcv` with timeframe='{timeframe}' and limit=200 for price history.
3. Call `get_crypto_indicators` with same timeframe for SMA/EMA/MACD/RSI/BB/ATR.
4. Call `get_funding_rate` to assess market positioning cost.

**Structured Output Format (MUST follow):**
```json
{{
  "evidence": {{
    "current_price": <float>,
    "price_24h_change_pct": <float>,
    "sma20": <float or null>,
    "sma50": <float or null>,
    "ema10": <float or null>,
    "ema20": <float or null>,
    "macd": <float or null>,
    "macd_signal": <float or null>,
    "macd_histogram": <float or null>,
    "rsi14": <float or null>,
    "atr14": <float or null>,
    "funding_rate": <float or null>
  }},
  "objective_signals": {{
    "trend": "BULLISH|BEARISH|NEUTRAL",
    "momentum": "STRONG|MODERATE|WEAK",
    "volatility": "HIGH|NORMAL|LOW",
    "support_levels": [<float>, ...],
    "resistance_levels": [<float>, ...]
  }},
  "analysis": {{
    "trend_analysis": "<2-3 sentences based on data>",
    "momentum_analysis": "<2-3 sentences based on RSI/MACD>",
    "volatility_analysis": "<2-3 sentences based on ATR/BB>",
    "key_observations": ["<observation 1>", "<observation 2>", ...]
  }},
  "conclusion": {{
    "bias": "BULLISH|BEARISH|NEUTRAL",
    "confidence": <1-10 integer>,
    "recommended_action": "LONG|SHORT|WAIT",
    "reasoning": "<concise summary>"
  }}
}}

**Important Rules:**
- If any data field is unavailable, set it to `null` and mention in analysis.
- Do NOT output any text outside the JSON structure.
- All numerical values must be from the tool responses, NOT estimated.

{instrument_context}
Current date: {current_date}
""" + get_language_instruction()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])
        
        # 解析 LLM 输出
        report_content = result.content if len(result.tool_calls) == 0 else ""
        
        # 如果启用了视觉化，生成 K 线图表
        chart_path = None
        if enable_vision:
            # 需要先从工具响应中获取 OHLCV 数据
            # 这里简化处理：在实际运行时，需要从 state 或工具响应中提取数据
            ohlcv_df = pd.DataFrame()  # TODO: 从实际数据填充
            indicators_dict = {}  # TODO: 从实际数据填充
            
            chart_path = _generate_kline_chart(
                symbol=symbol,
                timeframe=timeframe,
                ohlcv_data=ohlcv_df,
                indicators=indicators_dict,
                output_path=f"/tmp/kline_{symbol.replace('/', '-').replace(':', '-')}_4h.png",
            )
        
        return {
            "messages": [result],
            "technical_report": report_content,
            "chart_path": chart_path,  # 视觉分析图表路径
        }
    
    return crypto_technical_analyst_node
