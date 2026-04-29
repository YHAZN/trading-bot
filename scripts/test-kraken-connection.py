#!/usr/bin/env python3
"""Test Kraken API connection"""

import json
import requests
import time
import hmac
import hashlib
import base64
from pathlib import Path

def load_credentials():
    """Load Kraken demo credentials"""
    cred_path = Path.home() / ".openclaw/credentials/kraken-live.json"
    if not cred_path.exists():
        print("❌ Credentials not found at:", cred_path)
        print("\nCreate the file with:")
        print('{"api_key": "YOUR_KEY", "api_secret": "YOUR_SECRET"}')
        return None
    
    with open(cred_path) as f:
        return json.load(f)

def get_kraken_signature(urlpath, data, secret):
    """Generate Kraken API signature"""
    postdata = "&".join([f"{k}={v}" for k, v in data.items()])
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

def test_public_api():
    """Test public API (no auth needed)"""
    print("🔍 Testing public API...")
    
    try:
        # Get BTC/USD price
        resp = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD")
        data = resp.json()
        
        if data.get("error"):
            print(f"❌ Error: {data['error']}")
            return False
        
        price = float(data["result"]["XXBTZUSD"]["c"][0])
        print(f"✅ BTC/USD price: ${price:,.2f}")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_private_api(creds):
    """Test private API (requires auth)"""
    print("\n🔐 Testing private API...")
    
    if not creds:
        return False
    
    try:
        # Get account balance
        url = "https://api.kraken.com/0/private/Balance"
        nonce = str(int(time.time() * 1000))
        data = {"nonce": nonce}
        
        headers = {
            "API-Key": creds["api_key"],
            "API-Sign": get_kraken_signature("/0/private/Balance", data, creds["api_secret"])
        }
        
        resp = requests.post(url, data=data, headers=headers)
        result = resp.json()
        
        if result.get("error"):
            print(f"❌ Auth failed: {result['error']}")
            return False
        
        balance = result.get("result", {})
        print(f"✅ Connected to Kraken")
        print(f"✅ Account balance: {json.dumps(balance, indent=2)}")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Kraken API Connection Test")
    print("=" * 60)
    
    # Test public API
    public_ok = test_public_api()
    
    # Test private API
    creds = load_credentials()
    private_ok = test_private_api(creds)
    
    print("\n" + "=" * 60)
    if public_ok and private_ok:
        print("✅ All tests passed! Ready to trade.")
    elif public_ok:
        print("⚠️  Public API works, but auth failed.")
        print("   Set up credentials in ~/.openclaw/credentials/kraken-live.json")
    else:
        print("❌ Connection failed. Check your internet.")
    print("=" * 60)

if __name__ == "__main__":
    main()
