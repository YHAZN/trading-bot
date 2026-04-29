# Kraken Setup Guide

## Why Kraken?

- ✅ US-compliant (no VPN needed)
- ✅ Lower fees than Coinbase (0.16% maker / 0.26% taker)
- ✅ Good API for algo trading
- ✅ Futures available (Phase 2)
- ✅ Demo environment for testing

---

## Step 1: Create Kraken Account

1. Go to https://www.kraken.com
2. Sign up with email
3. Complete KYC verification (required for trading)
4. Enable 2FA (required for API access)

---

## Step 2: Get API Keys (Demo/Testnet)

**For Paper Trading (Demo):**

1. Go to https://demo.kraken.com
2. Create demo account (separate from main)
3. Settings → API → Create New Key
4. Permissions needed:
   - ✅ Query Funds
   - ✅ Query Open Orders & Trades
   - ✅ Query Closed Orders & Trades
   - ✅ Create & Modify Orders
   - ✅ Cancel/Close Orders
5. Copy API Key and Private Key
6. Save to `~/.openclaw/credentials/kraken-demo.json`:

```json
{
  "api_key": "YOUR_DEMO_API_KEY",
  "api_secret": "YOUR_DEMO_PRIVATE_KEY"
}
```

---

## Step 3: Get API Keys (Live - After Testing)

**⚠️ ONLY after 2+ weeks of successful paper trading**

1. Go to https://www.kraken.com
2. Settings → API → Create New Key
3. Same permissions as demo
4. **Set IP whitelist** (optional but recommended)
5. Save to `~/.openclaw/credentials/kraken-live.json`

---

## Step 4: Test Connection

```bash
cd ~/Workspace/trading-bot
python3 scripts/test-kraken-connection.py
```

Should output:
```
✅ Connected to Kraken Demo
✅ Account balance: $100,000 (demo funds)
✅ BTC/USD price: $XX,XXX
✅ WebSocket connected
```

---

## Step 5: Fund Demo Account

Demo account comes with **$100,000 fake USD** automatically.

For live account (later):
- Deposit via bank transfer (ACH - free, 1-3 days)
- Or wire transfer (faster, $5-25 fee)

---

## Kraken API Quirks

**Pair naming:**
- BTC/USD = `XXBTZUSD` (not `BTCUSD`)
- ETH/USD = `XETHZUSD` (not `ETHUSD`)

**Rate limits:**
- 15 requests/second
- 60 requests/minute
- WebSocket preferred for live data

**Order types:**
- Market, Limit, Stop-Loss, Take-Profit
- Post-only orders available (maker-only)

---

## Next Steps

1. Create Kraken demo account
2. Get demo API keys
3. Save to credentials file
4. Run connection test
5. Start building data pipeline

---

## Resources

- **API Docs:** https://docs.kraken.com/rest/
- **WebSocket Docs:** https://docs.kraken.com/websockets/
- **Demo Trading:** https://demo.kraken.com
- **Support:** https://support.kraken.com

---

**Remember:** Always test on demo first. Never trade live until strategies are proven profitable.
