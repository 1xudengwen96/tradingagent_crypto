# tradingagents/execution/shadow_account.py
"""
影子账户系统 —— 虚拟交易模拟

功能：
1. 使用真实 Binance 行情数据
2. 本地维护虚拟账户（初始 1000 USDT）
3. 模拟真实交易：手续费、滑点、盈亏计算
4. 完整的仓位管理和 PnL 追踪

适用于：
- 策略回测验证
- 实盘前模拟交易
- 风险控制测试
"""

import json
import os
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# 常量定义
# ============================================================================

# Binance 永续合约手续费（Maker/Taker）
# 参考：https://www.binance.com/en/fee/schedule
FEE_MAKER = 0.0002   # 0.02% (挂单)
FEE_TAKER = 0.0005   # 0.05% (吃单)

# 默认滑点（0.05% - 0.1%，根据流动性调整）
DEFAULT_SLIPPAGE = 0.0005

# 影子账户持久化文件
SHADOW_ACCOUNT_FILE = Path.home() / ".tradingbot" / "shadow_account.json"


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class ShadowPosition:
    """虚拟仓位"""
    symbol: str
    side: str  # "long" or "short"
    size: float  # 合约数量
    entry_price: float  # 开仓均价
    leverage: int  # 杠杆倍数
    opened_at: str  # 开仓时间
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    
    def notional_value(self, current_price: float) -> float:
        """仓位名义价值（USDT）"""
        return self.size * current_price
    
    def unrealized_pnl(self, current_price: float) -> float:
        """未实现盈亏（USDT）"""
        if self.side == "long":
            return (current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - current_price) * self.size
    
    def unrealized_pnl_pct(self, current_price: float) -> float:
        """未实现盈亏百分比"""
        if self.side == "long":
            return (current_price / self.entry_price - 1) * 100
        else:
            return (1 - current_price / self.entry_price) * 100
    
    def liquidation_price(self) -> float:
        """强平价格（简化计算，不考虑维持保证金）"""
        if self.side == "long":
            # 多头强平价 = 开仓价 × (1 - 1/杠杆)
            return self.entry_price * (1 - 0.95 / self.leverage)
        else:
            # 空头强平价 = 开仓价 × (1 + 1/杠杆)
            return self.entry_price * (1 + 0.95 / self.leverage)


@dataclass
class ShadowTrade:
    """虚拟交易记录"""
    trade_id: str
    symbol: str
    side: str  # "buy" or "sell"
    action: str  # "open" or "close"
    size: float
    price: float
    fee: float
    slippage: float
    pnl: float  # 仅 close 时有值
    timestamp: str
    order_id: str  # 模拟订单 ID


@dataclass
class ShadowAccountState:
    """影子账户状态"""
    initial_balance: float = 1000.0
    balance: float = 1000.0  # 可用余额
    total_deposits: float = 1000.0
    total_withdrawals: float = 0.0
    total_realized_pnl: float = 0.0
    total_fees_paid: float = 0.0
    positions: List[Dict] = field(default_factory=list)
    trade_history: List[Dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def total_equity(self, positions: List[ShadowPosition], prices: Dict[str, float]) -> float:
        """总权益 = 余额 + 未实现盈亏"""
        unrealized_pnl = sum(
            pos.unrealized_pnl(prices.get(pos.symbol, pos.entry_price))
            for pos in positions
        )
        return self.balance + unrealized_pnl
    
    def total_unrealized_pnl(self, positions: List[ShadowPosition], prices: Dict[str, float]) -> float:
        """总未实现盈亏"""
        return sum(
            pos.unrealized_pnl(prices.get(pos.symbol, pos.entry_price))
            for pos in positions
        )


# ============================================================================
# 影子账户管理器
# ============================================================================

class ShadowAccountManager:
    """
    影子账户管理器
    
    用法：
    >>> manager = ShadowAccountManager(initial_balance=1000.0)
    >>> manager.open_position("BTC/USDT", "long", 0.1, 50000, leverage=10)
    >>> manager.close_position("BTC/USDT", 0.1, 51000)
    >>> state = manager.get_state()
    >>> print(f"Total Equity: {state['total_equity']} USDT")
    """
    
    def __init__(self, initial_balance: float = 1000.0, slippage: float = DEFAULT_SLIPPAGE):
        """
        Args:
            initial_balance: 初始资金（USDT）
            slippage: 默认滑点（0.0005 = 0.05%）
        """
        self.initial_balance = initial_balance
        self.slippage = slippage
        self._positions: Dict[str, ShadowPosition] = {}  # 先初始化
        self.state = self._load_or_create_state()

        # 恢复仓位
        for pos_data in self.state.positions:
            pos = ShadowPosition(**pos_data)
            self._positions[pos.symbol] = pos

        logger.info(f"ShadowAccount initialized: balance={initial_balance} USDT, slippage={slippage*100:.2f}%")
    
    def _load_or_create_state(self) -> ShadowAccountState:
        """加载或创建账户状态"""
        try:
            if SHADOW_ACCOUNT_FILE.exists():
                with open(SHADOW_ACCOUNT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                state = ShadowAccountState(**data)
                logger.info(f"Loaded shadow account from {SHADOW_ACCOUNT_FILE}")
                return state
        except Exception as e:
            logger.warning(f"Failed to load shadow account: {e}")
        
        # 创建新账户
        state = ShadowAccountState(initial_balance=self.initial_balance)
        self._save_state(state)
        return state
    
    def _save_state(self, state: Optional[ShadowAccountState] = None):
        """保存账户状态到文件"""
        if state:
            self.state = state
        
        # 更新 positions
        self.state.positions = [asdict(pos) for pos in self._positions.values()]
        self.state.updated_at = datetime.now(timezone.utc).isoformat()
        
        # 确保目录存在
        SHADOW_ACCOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(SHADOW_ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.state), f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Shadow account saved to {SHADOW_ACCOUNT_FILE}")
    
    def open_position(
        self,
        symbol: str,
        side: str,  # "long" or "short"
        size: float,
        price: float,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profit_1: Optional[float] = None,
        take_profit_2: Optional[float] = None,
    ) -> Dict:
        """
        开仓（虚拟）
        
        Args:
            symbol: 交易对，如 "BTC/USDT"
            side: "long" 或 "short"
            size: 合约数量
            price: 开仓价格
            leverage: 杠杆倍数
            stop_loss: 止损价
            take_profit_1: 止盈 1
            take_profit_2: 止盈 2
        
        Returns:
            交易结果字典
        """
        # 检查是否已有仓位
        if symbol in self._positions:
            existing = self._positions[symbol]
            if existing.side != side:
                return {
                    "success": False,
                    "error": f"Cannot open {side} position: existing {existing.side} position exists",
                    "symbol": symbol,
                }
            # 加仓：更新均价
            total_size = existing.size + size
            avg_price = (existing.size * existing.entry_price + size * price) / total_size
            existing.size = total_size
            existing.entry_price = avg_price
            existing.leverage = max(existing.leverage, leverage)
            logger.info(f"Added to {symbol} {side}: size={total_size}, avg_price={avg_price:.4f}")
        else:
            # 新开仓
            position = ShadowPosition(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=price,
                leverage=leverage,
                opened_at=datetime.now(timezone.utc).isoformat(),
                stop_loss=stop_loss,
                take_profit_1=take_profit_1,
                take_profit_2=take_profit_2,
            )
            self._positions[symbol] = position
            logger.info(f"Opened {symbol} {side}: size={size}, price={price:.4f}, leverage={leverage}x")
        
        # 计算手续费和滑点
        notional = size * price
        fee = notional * FEE_TAKER  # 开仓默认 Taker
        slippage_cost = notional * self.slippage
        
        # 更新账户状态
        self.state.total_fees_paid += fee
        self.state.balance -= fee  # 手续费从余额扣除
        
        # 记录交易
        trade = ShadowTrade(
            trade_id=self._generate_trade_id(),
            symbol=symbol,
            side="buy" if side == "long" else "sell",
            action="open",
            size=size,
            price=price,
            fee=fee,
            slippage=slippage_cost,
            pnl=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            order_id=f"SHADOW_{len(self.state.trade_history) + 1:06d}",
        )
        self.state.trade_history.append(asdict(trade))
        
        # 保持历史记录在 1000 条以内
        if len(self.state.trade_history) > 1000:
            self.state.trade_history = self.state.trade_history[-1000:]
        
        self._save_state()
        
        return {
            "success": True,
            "action": "OPEN",
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price,
            "leverage": leverage,
            "fee": fee,
            "slippage": slippage_cost,
            "order_id": trade.order_id,
            "position": asdict(position),
        }
    
    def close_position(
        self,
        symbol: str,
        size: Optional[float] = None,  # None = 全平
        price: float = 0,
    ) -> Dict:
        """
        平仓（虚拟）
        
        Args:
            symbol: 交易对
            size: 平仓数量（None = 全部）
            price: 平仓价格
        
        Returns:
            交易结果字典
        """
        if symbol not in self._positions:
            return {
                "success": False,
                "error": f"No open position for {symbol}",
                "symbol": symbol,
            }
        
        position = self._positions[symbol]
        
        # 确定平仓数量
        close_size = size if size is not None else position.size
        close_size = min(close_size, position.size)  # 不能超过持仓
        
        if close_size <= 0:
            return {
                "success": False,
                "error": "Invalid close size",
                "symbol": symbol,
            }
        
        # 计算盈亏
        if position.side == "long":
            pnl = (price - position.entry_price) * close_size
        else:
            pnl = (position.entry_price - price) * close_size
        
        # 计算手续费
        notional = close_size * price
        fee = notional * FEE_TAKER
        slippage_cost = notional * self.slippage
        
        # 更新余额
        self.state.balance += pnl - fee  # 盈亏减去手续费
        self.state.total_realized_pnl += pnl
        self.state.total_fees_paid += fee
        
        # 更新或移除仓位
        position.size -= close_size
        if position.size <= 0:
            del self._positions[symbol]
        else:
            # 部分平仓：调整均价（简化处理，保持原均价）
            pass
        
        # 记录交易
        trade = ShadowTrade(
            trade_id=self._generate_trade_id(),
            symbol=symbol,
            side="sell" if position.side == "long" else "buy",
            action="close",
            size=close_size,
            price=price,
            fee=fee,
            slippage=slippage_cost,
            pnl=pnl,
            timestamp=datetime.now(timezone.utc).isoformat(),
            order_id=f"SHADOW_{len(self.state.trade_history) + 1:06d}",
        )
        self.state.trade_history.append(asdict(trade))
        
        # 保持历史记录在 1000 条以内
        if len(self.state.trade_history) > 1000:
            self.state.trade_history = self.state.trade_history[-1000:]
        
        self._save_state()
        
        logger.info(
            f"Closed {symbol} {position.side}: size={close_size}, price={price:.4f}, "
            f"PnL={pnl:.2f} USDT, fee={fee:.4f} USDT"
        )
        
        return {
            "success": True,
            "action": "CLOSE",
            "symbol": symbol,
            "side": position.side,
            "close_size": close_size,
            "close_price": price,
            "pnl": pnl,
            "fee": fee,
            "slippage": slippage_cost,
            "order_id": trade.order_id,
            "remaining_size": position.size if symbol in self._positions else 0,
        }
    
    def get_position(self, symbol: str) -> Optional[ShadowPosition]:
        """获取指定交易对的仓位"""
        return self._positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, ShadowPosition]:
        """获取所有仓位"""
        return self._positions.copy()
    
    def get_state(self, prices: Optional[Dict[str, float]] = None) -> Dict:
        """
        获取账户状态
        
        Args:
            prices: 当前价格字典 {symbol: price}
        
        Returns:
            账户状态字典
        """
        positions = list(self._positions.values())
        prices = prices or {}
        
        total_equity = self.state.total_equity(positions, prices)
        total_unrealized_pnl = self.state.total_unrealized_pnl(positions, prices)
        
        return {
            "initial_balance": self.state.initial_balance,
            "balance": self.state.balance,
            "total_equity": total_equity,
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_realized_pnl": self.state.total_realized_pnl,
            "total_fees_paid": self.state.total_fees_paid,
            "total_deposits": self.state.total_deposits,
            "total_withdrawals": self.state.total_withdrawals,
            "positions_count": len(positions),
            "positions": [asdict(p) for p in positions],
            "trade_count": len(self.state.trade_history),
            "updated_at": self.state.updated_at,
        }
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """获取交易历史"""
        return self.state.trade_history[-limit:]
    
    def reset(self, initial_balance: float = 1000.0):
        """重置账户"""
        self._positions.clear()
        self.state = ShadowAccountState(initial_balance=initial_balance)
        self._save_state()
        logger.info(f"Shadow account reset: initial_balance={initial_balance} USDT")
    
    def _generate_trade_id(self) -> str:
        """生成交易 ID"""
        return f"TRD_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{len(self.state.trade_history) + 1:04d}"
    
    def export_report(self, output_path: str = "shadow_account_report.json"):
        """导出账户报告"""
        report = {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "account_state": asdict(self.state),
            "positions": [asdict(p) for p in self._positions.values()],
            "recent_trades": self.get_trade_history(100),
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Shadow account report exported to {output_path}")
        return report


# ============================================================================
# 工具函数
# ============================================================================

def get_shadow_account() -> ShadowAccountManager:
    """获取全局影子账户实例"""
    return ShadowAccountManager()


def print_shadow_account_summary(account: ShadowAccountManager, prices: Dict[str, float]):
    """打印影子账户摘要"""
    state = account.get_state(prices)
    
    print("\n" + "=" * 60)
    print("📊 影子账户概览")
    print("=" * 60)
    print(f"初始资金：     {state['initial_balance']:.2f} USDT")
    print(f"可用余额：     {state['balance']:.2f} USDT")
    print(f"总权益：       {state['total_equity']:.2f} USDT")
    print(f"未实现盈亏：   {state['total_unrealized_pnl']:+.2f} USDT")
    print(f"已实现盈亏：   {state['total_realized_pnl']:+.2f} USDT")
    print(f"总收益率：     {(state['total_equity'] / state['initial_balance'] - 1) * 100:+.2f}%")
    print(f"手续费支出：   {state['total_fees_paid']:.4f} USDT")
    print(f"持仓数量：     {state['positions_count']}")
    print(f"交易次数：     {state['trade_count']}")
    print("=" * 60)
    
    if state['positions']:
        print("\n📦 当前持仓:")
        for pos_data in state['positions']:
            pos = ShadowPosition(**pos_data)
            current_price = prices.get(pos.symbol, pos.entry_price)
            print(f"  {pos.symbol}: {pos.side.upper()} {pos.size} @ {pos.entry_price:.4f}")
            print(f"    当前价：{current_price:.4f} | 盈亏：{pos.unrealized_pnl(current_price):+.2f} USDT ({pos.unrealized_pnl_pct(current_price):+.2f}%)")
            print(f"    杠杆：{pos.leverage}x | 强平价：{pos.liquidation_price():.4f}")
            if pos.stop_loss:
                print(f"    止损：{pos.stop_loss:.4f}")
            if pos.take_profit_1:
                print(f"    止盈 1: {pos.take_profit_1:.4f}")
            if pos.take_profit_2:
                print(f"    止盈 2: {pos.take_profit_2:.4f}")
    print()
