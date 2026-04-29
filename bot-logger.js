const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_KEY
);

class BotLogger {
  async logTrade(trade) {
    const { data, error } = await supabase.from('trades').insert([{
      timestamp: new Date().toISOString(),
      symbol: trade.symbol,
      side: trade.side,
      price: trade.price,
      quantity: trade.quantity,
      pnl: trade.pnl || null,
      status: trade.status || 'open'
    }]);
    
    if (error) console.error('Failed to log trade:', error);
    return data;
  }

  async updateMarketData(markets) {
    for (const market of markets) {
      const { error } = await supabase.from('market_data').upsert({
        symbol: market.symbol,
        price: market.price,
        change24h: market.change24h,
        volume: market.volume,
        high24h: market.high24h,
        low24h: market.low24h,
        updated_at: new Date().toISOString()
      });
      
      if (error) console.error('Failed to update market data:', error);
    }
  }

  async updateOrderBook(bids, asks) {
    const { error } = await supabase.from('order_book').upsert({
      id: 1,
      bids: bids.slice(0, 20),
      asks: asks.slice(0, 20),
      updated_at: new Date().toISOString()
    });
    
    if (error) console.error('Failed to update order book:', error);
  }

  async logCandle(candle) {
    const { error } = await supabase.from('candles').upsert({
      time: candle.time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
      volume: candle.volume || 0,
      symbol: candle.symbol || 'BTC/USDT',
      timeframe: candle.timeframe || '1m'
    });
    
    if (error) console.error('Failed to log candle:', error);
  }
}

module.exports = new BotLogger();
