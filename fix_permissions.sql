-- Grant permissions to anon role for real-time access
GRANT SELECT, INSERT, UPDATE ON public.trades TO anon;
GRANT SELECT, INSERT ON public.bot_logs TO anon;

-- Enable realtime for both tables
ALTER PUBLICATION supabase_realtime ADD TABLE trades;
ALTER PUBLICATION supabase_realtime ADD TABLE bot_logs;
