#!/usr/bin/env python3
"""Paper trading executor - simulates trades with fake money"""

import json
import time
from datetime import datetime
from pathlib import Path

class PaperTrader:
    def __init__(self, config_path="config/mode.json"):
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.balance = self.config["paper"]["starting_balance"]
        self.positions = {}  # {symbol: {qty, entry_price, entry_time}}
        self.trades = []
        self.pnl = 0.0
        
    def get_balance(self):
        """Get current cash balance"""
        return self.balance
    
    def get_position(self, symbol):
        """Get current position for symbol"""
        return self.positions.get(symbol)
    
    def buy(self, symbol, price, qty):
        """Simulate buying"""
        # Apply slippage (price moves against you)
        slippage = price * (self.config["paper"]["slippage_bps"] / 10000)
        fill_price = price + slippage
        
        # Apply commission
        commission = fill_price * qty * (self.config["paper"]["commission_bps"] / 10000)
        
        cost = (fill_price * qty) + commission
        
        if cost > self.balance:
            return {"success": False, "error": "Insufficient balance"}
        
        # Update balance
        self.balance -= cost
        
        # Update position
        self.positions[symbol] = {
            "qty": qty,
            "entry_price": fill_price,
            "entry_time": datetime.now().isoformat(),
            "commission_paid": commission
        }
        
        trade = {
            "type": "BUY",
            "symbol": symbol,
            "price": fill_price,
            "qty": qty,
            "cost": cost,
            "commission": commission,
            "time": datetime.now().isoformat()
        }
        self.trades.append(trade)
        
        return {"success": True, "trade": trade}
    
    def sell(self, symbol, price):
        """Simulate selling"""
        if symbol not in self.positions:
            return {"success": False, "error": "No position to sell"}
        
        position = self.positions[symbol]
        qty = position["qty"]
        
        # Apply slippage (price moves against you)
        slippage = price * (self.config["paper"]["slippage_bps"] / 10000)
        fill_price = price - slippage
        
        # Apply commission
        commission = fill_price * qty * (self.config["paper"]["commission_bps"] / 10000)
        
        proceeds = (fill_price * qty) - commission
        
        # Calculate P&L
        entry_cost = position["entry_price"] * qty
        pnl = proceeds - entry_cost - position["commission_paid"]
        self.pnl += pnl
        
        # Update balance
        self.balance += proceeds
        
        trade = {
            "type": "SELL",
            "symbol": symbol,
            "price": fill_price,
            "qty": qty,
            "proceeds": proceeds,
            "commission": commission,
            "pnl": pnl,
            "time": datetime.now().isoformat()
        }
        self.trades.append(trade)
        
        # Close position
        del self.positions[symbol]
        
        return {"success": True, "trade": trade, "pnl": pnl}
    
    def get_stats(self):
        """Get trading statistics"""
        if not self.trades:
            return {
                "total_trades": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "balance": self.balance
            }
        
        sells = [t for t in self.trades if t["type"] == "SELL"]
        wins = [t for t in sells if t["pnl"] > 0]
        
        return {
            "total_trades": len(sells),
            "total_pnl": self.pnl,
            "win_rate": len(wins) / len(sells) if sells else 0,
            "winning_trades": len(wins),
            "balance": self.balance,
            "open_positions": len(self.positions),
            "total_value": self.balance + sum(
                p["qty"] * p["entry_price"] for p in self.positions.values()
            )
        }
    
    def save_state(self, path="data/paper_trading_state.json"):
        """Save current state to file"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        state = {
            "balance": self.balance,
            "positions": self.positions,
            "trades": self.trades,
            "pnl": self.pnl,
            "stats": self.get_stats(),
            "last_updated": datetime.now().isoformat()
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

if __name__ == "__main__":
    # Test the paper trader
    trader = PaperTrader()
    
    print("Starting balance:", trader.get_balance())
    
    # Simulate buying BTC
    result = trader.buy("BTC", 76800, 0.1)
    print("\nBuy result:", json.dumps(result, indent=2))
    print("Balance after buy:", trader.get_balance())
    
    # Simulate selling BTC at a profit
    result = trader.sell("BTC", 77500)
    print("\nSell result:", json.dumps(result, indent=2))
    print("Balance after sell:", trader.get_balance())
    
    # Print stats
    print("\nStats:", json.dumps(trader.get_stats(), indent=2))
    
    # Save state
    trader.save_state()
    print("\nState saved to data/paper_trading_state.json")
