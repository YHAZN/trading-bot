#!/usr/bin/env python3
"""Live trading executor - places real orders on Kraken"""

import json
import time
import hmac
import hashlib
import base64
import requests
from pathlib import Path
from datetime import datetime

class LiveTrader:
    def __init__(self, credentials_path="~/.openclaw/credentials/kraken-live.json"):
        creds_path = Path(credentials_path).expanduser()
        with open(creds_path) as f:
            self.creds = json.load(f)
        
        self.api_url = "https://api.kraken.com"
        self.trades = []
    
    def _sign(self, urlpath, data):
        """Generate Kraken API signature"""
        postdata = "&".join([f"{k}={v}" for k, v in data.items()])
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(
            base64.b64decode(self.creds["api_secret"]),
            message,
            hashlib.sha512
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _request(self, endpoint, data=None):
        """Make authenticated API request"""
        urlpath = f"/0/private/{endpoint}"
        url = self.api_url + urlpath
        
        if data is None:
            data = {}
        data['nonce'] = str(int(time.time() * 1000))
        
        headers = {
            "API-Key": self.creds["api_key"],
            "API-Sign": self._sign(urlpath, data)
        }
        
        resp = requests.post(url, data=data, headers=headers)
        return resp.json()
    
    def get_balance(self):
        """Get account balance"""
        result = self._request("Balance")
        if result.get("error"):
            return {"success": False, "error": result["error"]}
        return {"success": True, "balance": result["result"]}
    
    def buy(self, symbol, price, qty):
        """Place a real buy order"""
        # Convert symbol format (BTC -> XXBTZUSD)
        pair = f"X{symbol}ZUSD" if len(symbol) == 3 else f"XX{symbol}ZUSD"
        
        data = {
            "pair": pair,
            "type": "buy",
            "ordertype": "limit",
            "price": str(price),
            "volume": str(qty)
        }
        
        result = self._request("AddOrder", data)
        
        if result.get("error"):
            return {"success": False, "error": result["error"]}
        
        trade = {
            "type": "BUY",
            "symbol": symbol,
            "price": price,
            "qty": qty,
            "order_id": result["result"]["txid"][0],
            "time": datetime.now().isoformat()
        }
        self.trades.append(trade)
        
        return {"success": True, "trade": trade}
    
    def sell(self, symbol, price, qty):
        """Place a real sell order"""
        pair = f"X{symbol}ZUSD" if len(symbol) == 3 else f"XX{symbol}ZUSD"
        
        data = {
            "pair": pair,
            "type": "sell",
            "ordertype": "limit",
            "price": str(price),
            "volume": str(qty)
        }
        
        result = self._request("AddOrder", data)
        
        if result.get("error"):
            return {"success": False, "error": result["error"]}
        
        trade = {
            "type": "SELL",
            "symbol": symbol,
            "price": price,
            "qty": qty,
            "order_id": result["result"]["txid"][0],
            "time": datetime.now().isoformat()
        }
        self.trades.append(trade)
        
        return {"success": True, "trade": trade}
    
    def get_open_orders(self):
        """Get open orders"""
        result = self._request("OpenOrders")
        if result.get("error"):
            return {"success": False, "error": result["error"]}
        return {"success": True, "orders": result["result"]["open"]}
    
    def cancel_order(self, order_id):
        """Cancel an order"""
        result = self._request("CancelOrder", {"txid": order_id})
        if result.get("error"):
            return {"success": False, "error": result["error"]}
        return {"success": True}

if __name__ == "__main__":
    trader = LiveTrader()
    
    # Test balance check
    result = trader.get_balance()
    print("Balance:", json.dumps(result, indent=2))
