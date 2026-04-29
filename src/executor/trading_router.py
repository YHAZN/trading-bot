from pathlib import Path
#!/usr/bin/env python3
"""Trading router - switches between paper and live trading"""

import json
from pathlib import Path
from paper_trader import PaperTrader
from live_trader import LiveTrader

class TradingRouter:
    def __init__(self, config_path=str(Path(__file__).parent.parent.parent / "config/mode.json")):
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.mode = self.config["mode"]
        
        if self.mode == "paper":
            self.executor = PaperTrader(config_path)
            print("🧪 Paper trading mode - No real money at risk")
        elif self.mode == "live":
            self.executor = LiveTrader()
            print("💰 LIVE trading mode - REAL MONEY")
            self._check_safety()
        else:
            raise ValueError(f"Invalid mode: {self.mode}")
    
    def _check_safety(self):
        """Safety checks before live trading"""
        live_config = self.config["live"]
        
        print("\n⚠️  LIVE TRADING SAFETY CHECKS:")
        print(f"  - Max position size: {live_config['max_position_size']*100}%")
        print(f"  - Daily loss limit: {live_config['daily_loss_limit']*100}%")
        print(f"  - Max drawdown: {live_config['max_drawdown']*100}%")
        print(f"  - Confirmation required: {live_config['require_confirmation']}")
        print()
    
    def buy(self, symbol, price, qty):
        """Route buy order to appropriate executor"""
        # Apply risk checks
        risk_config = self.config["risk"]
        
        if self.mode == "live":
            # Extra confirmation for live trades
            if self.config["live"]["require_confirmation"]:
                print(f"\n⚠️  CONFIRM LIVE BUY:")
                print(f"  Symbol: {symbol}")
                print(f"  Price: ${price:,.2f}")
                print(f"  Quantity: {qty}")
                print(f"  Cost: ${price * qty:,.2f}")
                confirm = input("\nType 'YES' to confirm: ")
                if confirm != "YES":
                    return {"success": False, "error": "Trade cancelled by user"}
        
        return self.executor.buy(symbol, price, qty)
    
    def sell(self, symbol, price):
        """Route sell order to appropriate executor"""
        if self.mode == "live":
            if self.config["live"]["require_confirmation"]:
                print(f"\n⚠️  CONFIRM LIVE SELL:")
                print(f"  Symbol: {symbol}")
                print(f"  Price: ${price:,.2f}")
                confirm = input("\nType 'YES' to confirm: ")
                if confirm != "YES":
                    return {"success": False, "error": "Trade cancelled by user"}
        
        return self.executor.sell(symbol, price)
    
    def get_balance(self):
        """Get balance from executor"""
        if self.mode == "paper":
            return self.executor.get_balance()
        else:
            result = self.executor.get_balance()
            return result.get("balance", {})
    
    def get_stats(self):
        """Get trading stats"""
        if self.mode == "paper":
            return self.executor.get_stats()
        else:
            # For live mode, would query Kraken for actual stats
            return {"mode": "live", "message": "Check Kraken dashboard"}
    
    def switch_mode(self, new_mode):
        """Switch between paper and live (requires restart)"""
        if new_mode not in ["paper", "live"]:
            return {"success": False, "error": "Invalid mode"}
        
        self.config["mode"] = new_mode
        with open("config/mode.json", "w") as f:
            json.dump(self.config, f, indent=2)
        
        return {
            "success": True,
            "message": f"Mode switched to {new_mode}. Restart the bot to apply."
        }

if __name__ == "__main__":
    # Test the router
    router = TradingRouter()
    
    print(f"\nCurrent mode: {router.mode}")
    print(f"Balance: {router.get_balance()}")
    
    # Test a paper trade
    if router.mode == "paper":
        print("\n--- Testing paper trade ---")
        result = router.buy("BTC", 76800, 0.05)
        print(f"Buy result: {result}")
        
        result = router.sell("BTC", 77000)
        print(f"Sell result: {result}")
        
        print(f"\nStats: {json.dumps(router.get_stats(), indent=2)}")
