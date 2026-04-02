import yfinance as yf
import pandas as pd

tickers = ['KVUE', 'JNJ', 'KMB', 'XLP', 'SPY', 'HLN']
data = yf.download(tickers, start='2025-11-03', end='2026-04-02')['Close']
data.to_csv('stock_data.csv')