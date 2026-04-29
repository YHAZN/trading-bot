const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

class SupabaseLogger {
  async logPrice(price, indicators) {
    await supabase.from('price_data').insert({
      timestamp: new Date().toISOString(),
      price,
      zscore: indicators.zscore,
      rsi: indicators.rsi,
      adx: indicators.adx,
      regime: indicators.regime
    });
  }

  async logTrade(type, price, amount, pnl = null) {
    await supabase.from('trades').insert({
      timestamp: new Date().toISOString(),
      type,
      price,
      amount,
      pnl
    });
  }

  async logEvent(message, type = 'info') {
    await supabase.from('logs').insert({
      timestamp: new Date().toISOString(),
      message,
      type
    });
  }

  async updateStats(balance, pnl, trades, winRate, openPositions) {
    await supabase.from('stats').upsert({
      id: 1,
      balance,
      pnl,
      trades,
      win_rate: winRate,
      open_positions: openPositions,
      updated_at: new Date().toISOString()
    });
  }
}

module.exports = new SupabaseLogger();
