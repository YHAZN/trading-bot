#!/usr/bin/env python3
"""Main trading bot runner"""

import sys
import json
import time
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "executor"))

from trading_router import TradingRouter

def main():
    parser = argparse.ArgumentParser(description="Trading Bot")
    parser.add_argument("--mode", choices=["paper", "live"], help="Trading mode")
    parser.add_argument("--duration", type=int, default=60, help="Run duration in seconds")
    args = parser.parse_args()
    
    # Override mode if specified
    if args.mode:
        config_path = Path("config/mode.json")
        with open(config_path) as f:
            config = json.load(f)
        config["mode"] = args.mode
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    
    # Initialize router
    router = TradingRouter()
    
    print("\n" + "="*60)
    print("TRADING BOT STARTED")
    print("="*60)
    print(f"Mode: {router.mode.upper()}")
    print(f"Starting balance: ${router.get_balance():,.2f}")
    print(f"Duration: {args.duration}s")
    print("="*60 + "\n")
    
    # Main trading loop
    start_time = time.time()
    
    try:
        while time.time() - start_time < args.duration:
            # Get current BTC price
            import requests
            resp = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD")
            data = resp.json()
            
            if data.get("error"):
                print(f"Error fetching price: {data['error']}")
                time.sleep(5)
                continue
            
            btc_price = float(data["result"]["XXBTZUSD"]["c"][0])
            print(f"[{time.strftime('%H:%M:%S')}] BTC: ${btc_price:,.2f}")
            
            # Simple strategy: buy if no position, sell if have position
            stats = router.get_stats()
            
            if router.mode == "paper":
                if stats["open_positions"] == 0:
                    # Buy signal (simplified)
                    print("  → BUY signal")
                    result = router.buy("BTC", btc_price, 0.01)
                    if result["success"]:
                        print(f"  ✅ Bought 0.01 BTC at ${btc_price:,.2f}")
                else:
                    # Sell signal (simplified)
                    print("  → SELL signal")
                    result = router.sell("BTC", btc_price)
                    if result["success"]:
                        pnl = result.get("pnl", 0)
                        print(f"  ✅ Sold BTC at ${btc_price:,.2f} | P&L: ${pnl:,.2f}")
            
            time.sleep(10)
    
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
    
    # Final stats
    print("\n" + "="*60)
    print("FINAL STATS")
    print("="*60)
    stats = router.get_stats()
    print(json.dumps(stats, indent=2))
    print("="*60)

if __name__ == "__main__":
    main()
