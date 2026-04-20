from .utils.agent_utils import create_msg_delete
from .utils.agent_states import AgentState, InvestDebateState, RiskDebateState
from .utils.memory import FinancialSituationMemory

# Stock agents (not available in crypto-only version)
# from .analysts.fundamentals_analyst import create_fundamentals_analyst
# from .analysts.market_analyst import create_market_analyst
# from .analysts.news_analyst import create_news_analyst
# from .analysts.social_media_analyst import create_social_media_analyst
# from .researchers.bear_researcher import create_bear_researcher
# from .researchers.bull_researcher import create_bull_researcher
# from .risk_mgmt.aggressive_debator import create_aggressive_debator
# from .risk_mgmt.conservative_debator import create_conservative_debator
# from .risk_mgmt.neutral_debator import create_neutral_debator
# from .managers.research_manager import create_research_manager
# from .managers.portfolio_manager import create_portfolio_manager
# from .trader.trader import create_trader

# ---- Crypto perpetual futures agents ----
from .analysts.crypto_technical_analyst import create_crypto_technical_analyst
from .analysts.crypto_macro_onchain_analyst import create_crypto_macro_onchain_analyst

# Crypto researchers (not available)
# from .researchers.crypto_bull_researcher import create_crypto_bull_researcher
# from .researchers.crypto_bear_researcher import create_crypto_bear_researcher

# Crypto risk management (not available)
# from .risk_mgmt.crypto_aggressive_debator import create_crypto_aggressive_debator
# from .risk_mgmt.crypto_conservative_debator import create_crypto_conservative_debator
# from .risk_mgmt.crypto_neutral_debator import create_crypto_neutral_debator

# Crypto managers
from .managers.crypto_research_manager import create_crypto_research_manager
from .managers.crypto_portfolio_manager import create_crypto_portfolio_manager

# Crypto trader (not available)
# from .trader.crypto_trader import create_crypto_trader

__all__ = [
    # Shared utilities
    "FinancialSituationMemory",
    "AgentState",
    "create_msg_delete",
    "InvestDebateState",
    "RiskDebateState",
    # Crypto agents
    "create_crypto_technical_analyst",
    "create_crypto_macro_onchain_analyst",
    "create_crypto_research_manager",
    "create_crypto_portfolio_manager",
]
