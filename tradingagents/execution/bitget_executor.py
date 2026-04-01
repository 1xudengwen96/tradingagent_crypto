# tradingagents/execution/bitget_executor.py
"""
Bitget合约执行层
解析投资组合管理者的文本决策，转换为Bitget API可执行的合约交易指令。
支持沙盒和实盘两种模式。
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field

import ccxt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TradeSignal:
    """Parsed trading signal from portfolio manager output."""
    direction: str          # "LONG" | "SHORT" | "CLOSE" | "LONG-LITE" | "SHORT-LITE"
    leverage: int           # e.g. 10
    position_size_pct: float  # fraction of capital, e.g. 0.20 for 20%
    entry_type: str         # "MARKET" | "LIMIT"
    entry_price: Optional[float]  # None for MARKET orders
    stop_loss: Optional[float]
    take_profit_1: Optional[float]
    take_profit_2: Optional[float]
    time_horizon: str       # descriptive string, e.g. "4-12 hours"
    raw_text: str           # original LLM output for logging


@dataclass
class ExecutionResult:
    """Result of an order placement attempt."""
    success: bool
    signal: TradeSignal
    orders: list = field(default_factory=list)   # list of ccxt order dicts
    error: Optional[str] = None
    positions_before: list = field(default_factory=list)
    positions_after: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Signal Parser
# ---------------------------------------------------------------------------

class SignalParser:
    """
    Extracts structured trading parameters from free-form LLM text.

    The portfolio manager outputs text matching (approximately):

        ## 1. Final Decision
        LONG-LITE

        ## 2. Execution Parameters
        - Direction: LONG
        - Leverage: 8x
        - Position Size: 18% of capital
        - Entry: MARKET
        - Stop-Loss: 61200
        - Take-Profit 1: 64500
        - Take-Profit 2: 67000
        - Time Horizon: 4-12 hours
    """

    # Direction keywords (order matters — check hyphenated variants first)
    DIRECTION_PATTERNS = [
        (r'\b(LONG-LITE)\b', 'LONG-LITE'),
        (r'\b(SHORT-LITE)\b', 'SHORT-LITE'),
        (r'\b(LONG)\b', 'LONG'),
        (r'\b(SHORT)\b', 'SHORT'),
        (r'\b(CLOSE)\b', 'CLOSE'),
        (r'\b(FLAT)\b', 'CLOSE'),
    ]

    @classmethod
    def parse(cls, text: str) -> TradeSignal:
        """Parse LLM decision text into a TradeSignal."""
        direction = cls._extract_direction(text)
        leverage = cls._extract_leverage(text)
        position_size_pct = cls._extract_position_size(text)
        entry_type, entry_price = cls._extract_entry(text)
        stop_loss = cls._extract_price_field(text, r'stop.?loss', 'stop_loss')
        tp1 = cls._extract_price_field(text, r'take.?profit\s*1?', 'tp1')
        tp2 = cls._extract_price_field(text, r'take.?profit\s*2', 'tp2')
        time_horizon = cls._extract_time_horizon(text)

        logger.info(
            "Parsed signal: direction=%s leverage=%sx size=%.0f%% entry=%s/%s sl=%s tp1=%s tp2=%s",
            direction, leverage, position_size_pct * 100,
            entry_type, entry_price, stop_loss, tp1, tp2,
        )

        return TradeSignal(
            direction=direction,
            leverage=leverage,
            position_size_pct=position_size_pct,
            entry_type=entry_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            time_horizon=time_horizon,
            raw_text=text,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _extract_direction(cls, text: str) -> str:
        # First look inside "Final Decision" section
        section_match = re.search(
            r'final\s+decision.*?\n(.*?)(?:\n##|\Z)',
            text, re.IGNORECASE | re.DOTALL
        )
        search_zone = section_match.group(1) if section_match else text

        for pattern, canonical in cls.DIRECTION_PATTERNS:
            if re.search(pattern, search_zone, re.IGNORECASE):
                return canonical

        # Fallback: search entire text
        for pattern, canonical in cls.DIRECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return canonical

        logger.warning("Could not parse direction from text; defaulting to CLOSE")
        return "CLOSE"

    @classmethod
    def _extract_leverage(cls, text: str) -> int:
        # Matches: "Leverage: 10x", "10x leverage", "leverage of 10x"
        patterns = [
            r'leverage[:\s]+(\d+)\s*x',
            r'(\d+)\s*x\s+leverage',
            r'leverage.*?(\d+)x',
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = int(m.group(1))
                # Sanity-clamp to Bitget's max perpetual leverage
                return min(max(val, 1), 125)
        logger.warning("Could not parse leverage; defaulting to 5x")
        return 5

    @classmethod
    def _extract_position_size(cls, text: str) -> float:
        # Matches: "Position Size: 20%", "20% of capital"
        patterns = [
            r'position\s+size[:\s]+([\d.]+)\s*%',
            r'([\d.]+)\s*%\s+of\s+(?:capital|portfolio|account)',
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                pct = float(m.group(1))
                # Clamp to reasonable range
                return min(max(pct / 100.0, 0.01), 1.0)
        logger.warning("Could not parse position size; defaulting to 10%%")
        return 0.10

    @classmethod
    def _extract_entry(cls, text: str) -> tuple[str, Optional[float]]:
        # Check for MARKET keyword near "Entry"
        m = re.search(r'entry[:\s]+MARKET', text, re.IGNORECASE)
        if m:
            return "MARKET", None

        # Try to extract a limit price
        m = re.search(r'entry[:\s]+([\d,]+\.?\d*)', text, re.IGNORECASE)
        if m:
            price_str = m.group(1).replace(',', '')
            try:
                return "LIMIT", float(price_str)
            except ValueError:
                pass

        return "MARKET", None

    @classmethod
    def _extract_price_field(cls, text: str, label_pattern: str, field_name: str) -> Optional[float]:
        pattern = rf'{label_pattern}[:\s*]+([\d,]+\.?\d*)'
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            price_str = m.group(1).replace(',', '')
            try:
                return float(price_str)
            except ValueError:
                pass
        logger.debug("Could not parse %s from text", field_name)
        return None

    @classmethod
    def _extract_time_horizon(cls, text: str) -> str:
        m = re.search(r'time\s+horizon[:\s]+([^\n\-]+)', text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return "unknown"


# ---------------------------------------------------------------------------
# BitgetExecutor
# ---------------------------------------------------------------------------

class BitgetExecutor:
    """
    Translates a TradeSignal into live (or sandbox) Bitget API calls.

    Usage
    -----
    executor = BitgetExecutor(
        api_key="...", secret="...", passphrase="...",
        sandbox=True,
    )
    result = executor.execute(signal, symbol="BTC/USDT:USDT", capital_usdt=1000.0)
    """

    def __init__(
        self,
        api_key: str,
        secret: str,
        passphrase: str,
        sandbox: bool = True,
        margin_mode: str = "isolated",   # "isolated" | "cross"
        default_leverage: int = 5,
    ):
        self.sandbox = sandbox
        self.margin_mode = margin_mode
        self.default_leverage = default_leverage

        self._exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': secret,
            'password': passphrase,
            'options': {
                'defaultType': 'swap',   # perpetual futures
            },
        })

        if sandbox:
            self._exchange.set_sandbox_mode(True)
            logger.info("BitgetExecutor running in SANDBOX mode")
        else:
            logger.warning("BitgetExecutor running in LIVE mode — real funds at risk!")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        signal: TradeSignal,
        symbol: str,
        capital_usdt: float,
    ) -> ExecutionResult:
        """
        Execute a TradeSignal on Bitget perpetual futures.

        Parameters
        ----------
        signal : TradeSignal
            Parsed signal from SignalParser.
        symbol : str
            e.g. "BTC/USDT:USDT"
        capital_usdt : float
            Total account capital in USDT used to compute position sizing.
        """
        positions_before = self._safe_fetch_positions(symbol)

        try:
            if signal.direction == "CLOSE":
                orders = self._close_all_positions(symbol, positions_before)
            elif signal.direction in ("LONG", "LONG-LITE", "SHORT", "SHORT-LITE"):
                orders = self._open_position(signal, symbol, capital_usdt)
            else:
                raise ValueError(f"Unknown direction: {signal.direction}")

            positions_after = self._safe_fetch_positions(symbol)
            return ExecutionResult(
                success=True,
                signal=signal,
                orders=orders,
                positions_before=positions_before,
                positions_after=positions_after,
            )

        except ccxt.InsufficientFunds as e:
            logger.error("Insufficient funds: %s", e)
            return ExecutionResult(success=False, signal=signal, error=f"InsufficientFunds: {e}")
        except ccxt.InvalidOrder as e:
            logger.error("Invalid order parameters: %s", e)
            return ExecutionResult(success=False, signal=signal, error=f"InvalidOrder: {e}")
        except ccxt.NetworkError as e:
            logger.error("Network error communicating with Bitget: %s", e)
            return ExecutionResult(success=False, signal=signal, error=f"NetworkError: {e}")
        except ccxt.ExchangeError as e:
            logger.error("Exchange error: %s", e)
            return ExecutionResult(success=False, signal=signal, error=f"ExchangeError: {e}")
        except Exception as e:
            logger.exception("Unexpected error during execution")
            return ExecutionResult(success=False, signal=signal, error=str(e))

    # ------------------------------------------------------------------
    # Internal execution helpers
    # ------------------------------------------------------------------

    def _open_position(
        self,
        signal: TradeSignal,
        symbol: str,
        capital_usdt: float,
    ) -> list:
        """Set leverage, margin mode, compute size, place entry order."""
        leverage = signal.leverage or self.default_leverage
        side = "buy" if signal.direction.startswith("LONG") else "sell"

        # 1. Set margin mode
        try:
            self._exchange.set_margin_mode(self.margin_mode, symbol)
            logger.info("Set margin mode to %s for %s", self.margin_mode, symbol)
        except ccxt.ExchangeError as e:
            # Some exchanges throw if mode is already set — log and continue
            logger.warning("set_margin_mode warning (may already be set): %s", e)

        # 2. Set leverage
        try:
            self._exchange.set_leverage(leverage, symbol)
            logger.info("Set leverage to %sx for %s", leverage, symbol)
        except ccxt.ExchangeError as e:
            logger.warning("set_leverage warning: %s", e)

        # 3. Compute position size in contracts
        ticker = self._exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        notional_usdt = capital_usdt * signal.position_size_pct * leverage
        market = self._exchange.market(symbol)
        contract_size = market.get('contractSize', 1.0)  # e.g. 0.001 BTC per contract
        amount_contracts = notional_usdt / (current_price * contract_size)
        amount_contracts = self._exchange.amount_to_precision(symbol, amount_contracts)

        logger.info(
            "Placing %s order: %s contracts of %s @ leverage=%sx "
            "(notional=%.2f USDT, price=%.4f)",
            side.upper(), amount_contracts, symbol, leverage, notional_usdt, current_price,
        )

        # 4. Place entry order
        orders = []
        if signal.entry_type == "MARKET":
            order = self._exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=float(amount_contracts),
                params={'tdMode': self.margin_mode},
            )
        else:
            order = self._exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=float(amount_contracts),
                price=signal.entry_price,
                params={'tdMode': self.margin_mode},
            )
        orders.append(order)
        logger.info("Entry order placed: %s", order.get('id'))

        # 5. Place stop-loss order (opposite side, reduce-only)
        if signal.stop_loss:
            sl_side = "sell" if side == "buy" else "buy"
            try:
                sl_order = self._exchange.create_order(
                    symbol=symbol,
                    type='stop',
                    side=sl_side,
                    amount=float(amount_contracts),
                    price=signal.stop_loss,
                    params={
                        'stopPrice': signal.stop_loss,
                        'reduceOnly': True,
                        'tdMode': self.margin_mode,
                    },
                )
                orders.append(sl_order)
                logger.info("Stop-loss order placed at %s: %s", signal.stop_loss, sl_order.get('id'))
            except ccxt.ExchangeError as e:
                logger.warning("Could not place stop-loss order: %s", e)

        # 6. Place take-profit orders
        tp_side = "sell" if side == "buy" else "buy"
        half_amount = float(amount_contracts) / 2.0

        if signal.take_profit_1:
            try:
                tp1_amount = half_amount if signal.take_profit_2 else float(amount_contracts)
                tp1_order = self._exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side=tp_side,
                    amount=tp1_amount,
                    price=signal.take_profit_1,
                    params={
                        'reduceOnly': True,
                        'tdMode': self.margin_mode,
                    },
                )
                orders.append(tp1_order)
                logger.info("TP1 order placed at %s: %s", signal.take_profit_1, tp1_order.get('id'))
            except ccxt.ExchangeError as e:
                logger.warning("Could not place TP1 order: %s", e)

        if signal.take_profit_2:
            try:
                tp2_order = self._exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side=tp_side,
                    amount=half_amount,
                    price=signal.take_profit_2,
                    params={
                        'reduceOnly': True,
                        'tdMode': self.margin_mode,
                    },
                )
                orders.append(tp2_order)
                logger.info("TP2 order placed at %s: %s", signal.take_profit_2, tp2_order.get('id'))
            except ccxt.ExchangeError as e:
                logger.warning("Could not place TP2 order: %s", e)

        return orders

    def _close_all_positions(self, symbol: str, positions: list) -> list:
        """Market-close all open positions for the symbol and cancel open orders."""
        orders = []

        # Cancel all open orders first
        try:
            self._exchange.cancel_all_orders(symbol)
            logger.info("Cancelled all open orders for %s", symbol)
        except ccxt.ExchangeError as e:
            logger.warning("Could not cancel orders: %s", e)

        for pos in positions:
            size = abs(float(pos.get('contracts', 0) or 0))
            if size == 0:
                continue

            # Determine close side
            pos_side = pos.get('side', '')  # 'long' or 'short'
            close_side = 'sell' if pos_side == 'long' else 'buy'

            try:
                order = self._exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=close_side,
                    amount=size,
                    params={'reduceOnly': True},
                )
                orders.append(order)
                logger.info(
                    "Closed %s position of %s contracts: order %s",
                    pos_side, size, order.get('id'),
                )
            except ccxt.ExchangeError as e:
                logger.error("Failed to close %s position: %s", pos_side, e)

        if not orders:
            logger.info("No open positions to close for %s", symbol)

        return orders

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _safe_fetch_positions(self, symbol: str) -> list:
        """Fetch open positions, returning empty list on error."""
        try:
            all_positions = self._exchange.fetch_positions([symbol])
            return [p for p in all_positions if float(p.get('contracts', 0) or 0) != 0]
        except Exception as e:
            logger.warning("Could not fetch positions: %s", e)
            return []

    def fetch_account_balance(self) -> dict:
        """Return USDT balance summary."""
        try:
            balance = self._exchange.fetch_balance({'type': 'swap'})
            usdt = balance.get('USDT', {})
            return {
                'total': usdt.get('total', 0.0),
                'free': usdt.get('free', 0.0),
                'used': usdt.get('used', 0.0),
            }
        except Exception as e:
            logger.error("Could not fetch balance: %s", e)
            return {'total': 0.0, 'free': 0.0, 'used': 0.0}
