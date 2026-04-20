# tradingagents/execution/shadow_executor.py
"""
影子执行器 —— 将交易信号转换为影子账户操作

功能：
1. 解析 SignalParser 输出的交易信号
2. 在影子账户中执行虚拟交易
3. 模拟真实订单执行（含手续费、滑点）
4. 返回 ExecutionResult 格式（与真实执行器兼容）

使用场景：
- 实盘数据 + 虚拟交易
- 策略验证和回测
- 风险控制测试
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

from .shadow_account import ShadowAccountManager, ShadowPosition
from .binance_executor import TradeSignal, ExecutionResult, SignalParser

logger = logging.getLogger(__name__)


@dataclass
class ShadowExecutionResult:
    """影子执行结果"""
    success: bool
    signal: TradeSignal
    orders: list = field(default_factory=list)  # 模拟订单列表
    error: Optional[str] = None
    positions_before: list = field(default_factory=list)
    positions_after: list = field(default_factory=list)
    pnl: float = 0.0  # 本次交易盈亏
    fees_paid: float = 0.0  # 本次交易手续费
    slippage_cost: float = 0.0  # 本次交易滑点成本


class ShadowExecutor:
    """
    影子执行器
    
    用法：
    >>> executor = ShadowExecutor(initial_balance=1000.0)
    >>> signal = SignalParser.parse(decision_text)
    >>> result = executor.execute(signal, symbol="BTC/USDT", capital_usdt=1000.0, current_price=50000)
    >>> print(f"PnL: {result.pnl:.2f} USDT, Fees: {result.fees_paid:.4f} USDT")
    """
    
    def __init__(self, initial_balance: float = 1000.0, slippage: float = 0.0005):
        """
        Args:
            initial_balance: 初始资金（USDT）
            slippage: 滑点（0.0005 = 0.05%）
        """
        self.account = ShadowAccountManager(initial_balance=initial_balance, slippage=slippage)
        self.initial_balance = initial_balance
        logger.info(f"ShadowExecutor initialized: balance={initial_balance} USDT")
    
    def execute(
        self,
        signal: TradeSignal,
        symbol: str,
        capital_usdt: float,
        current_price: float,
    ) -> ShadowExecutionResult:
        """
        执行交易信号（虚拟）
        
        Args:
            signal: 交易信号
            symbol: 交易对
            capital_usdt: 总资金（USDT）
            current_price: 当前价格
        
        Returns:
            影子执行结果
        """
        positions_before = list(self.account.get_all_positions().values())
        
        try:
            if signal.direction == "CLOSE":
                result = self._close_position(signal, symbol, current_price)
            elif signal.direction in ("LONG", "LONG-LITE", "SHORT", "SHORT-LITE"):
                result = self._open_position(signal, symbol, capital_usdt, current_price)
            else:
                raise ValueError(f"Unknown direction: {signal.direction}")
            
            positions_after = list(self.account.get_all_positions().values())
            
            return ShadowExecutionResult(
                success=True,
                signal=signal,
                orders=result.get("orders", []),
                positions_before=[vars(p) for p in positions_before],
                positions_after=[vars(p) for p in positions_after],
                pnl=result.get("pnl", 0.0),
                fees_paid=result.get("fees_paid", 0.0),
                slippage_cost=result.get("slippage_cost", 0.0),
            )
            
        except Exception as e:
            logger.exception("Shadow execution error")
            return ShadowExecutionResult(
                success=False,
                signal=signal,
                error=str(e),
                positions_before=[vars(p) for p in positions_before],
                positions_after=[vars(p) for p in positions_before],
            )
    
    def _open_position(
        self,
        signal: TradeSignal,
        symbol: str,
        capital_usdt: float,
        current_price: float,
    ) -> dict:
        """开仓（虚拟）"""
        side = "long" if signal.direction.startswith("LONG") else "short"
        leverage = signal.leverage or 1
        
        # 计算仓位大小
        notional_usdt = capital_usdt * signal.position_size_pct * leverage
        size = notional_usdt / current_price
        
        # 执行开仓
        open_result = self.account.open_position(
            symbol=symbol,
            side=side,
            size=size,
            price=current_price,
            leverage=leverage,
            stop_loss=signal.stop_loss,
            take_profit_1=signal.take_profit_1,
            take_profit_2=signal.take_profit_2,
        )
        
        if not open_result["success"]:
            raise Exception(open_result.get("error", "Unknown error"))
        
        logger.info(
            f"[SHADOW] OPEN {side.upper()} {symbol}: "
            f"size={size:.6f}, price={current_price:.4f}, "
            f"leverage={leverage}x, fee={open_result['fee']:.4f} USDT"
        )
        
        # 创建模拟订单（兼容真实执行器格式）
        orders = [
            {
                "id": open_result["order_id"],
                "symbol": symbol,
                "side": "buy" if side == "long" else "sell",
                "type": signal.entry_type.lower(),
                "amount": size,
                "price": current_price,
                "filled": size,
                "status": "closed",
                "fee": open_result["fee"],
            }
        ]
        
        return {
            "orders": orders,
            "pnl": 0,  # 开仓时无盈亏
            "fees_paid": open_result["fee"],
            "slippage_cost": open_result["slippage"],
        }
    
    def _close_position(
        self,
        signal: TradeSignal,
        symbol: str,
        current_price: float,
    ) -> dict:
        """平仓（虚拟）"""
        # 执行平仓
        close_result = self.account.close_position(
            symbol=symbol,
            price=current_price,
        )
        
        if not close_result["success"]:
            # 如果没有仓位，跳过
            if "No open position" in close_result.get("error", ""):
                logger.warning(f"[SHADOW] No position to close for {symbol}")
                return {"orders": [], "pnl": 0, "fees_paid": 0, "slippage_cost": 0}
            raise Exception(close_result.get("error", "Unknown error"))
        
        logger.info(
            f"[SHADOW] CLOSE {symbol}: "
            f"size={close_result['close_size']:.6f}, price={current_price:.4f}, "
            f"PnL={close_result['pnl']:.2f} USDT, fee={close_result['fee']:.4f} USDT"
        )
        
        # 创建模拟订单
        orders = [
            {
                "id": close_result["order_id"],
                "symbol": symbol,
                "side": "sell" if close_result.get("side") == "long" else "buy",
                "type": "market",
                "amount": close_result["close_size"],
                "price": current_price,
                "filled": close_result["close_size"],
                "status": "closed",
                "fee": close_result["fee"],
                "pnl": close_result["pnl"],
            }
        ]
        
        return {
            "orders": orders,
            "pnl": close_result["pnl"],
            "fees_paid": close_result["fee"],
            "slippage_cost": close_result["slippage"],
        }
    
    def get_account_state(self, prices: dict = None) -> dict:
        """获取账户状态"""
        return self.account.get_state(prices or {})
    
    def get_trade_history(self, limit: int = 50) -> list:
        """获取交易历史"""
        return self.account.get_trade_history(limit)
    
    def reset(self, initial_balance: float = 1000.0):
        """重置账户"""
        self.account.reset(initial_balance)
        logger.info(f"Shadow account reset: initial_balance={initial_balance} USDT")
    
    def print_summary(self, prices: dict):
        """打印账户摘要"""
        from .shadow_account import print_shadow_account_summary
        print_shadow_account_summary(self.account, prices)
