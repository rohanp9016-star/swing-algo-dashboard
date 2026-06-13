# Swing Algo Dashboard — NSE/BSE

Real-time swing trading screener for Indian stock market built with Streamlit + yfinance.

## Live Demo
Deploy on Streamlit Cloud: [share.streamlit.io](https://share.streamlit.io)

## Screening Conditions
- Market Cap > 5000 Cr
- Volume > SMA(10) x 1.2
- Close > EMA200 > EMA50
- EMA20 > EMA50 > EMA200
- RSI(14): 45-65
- MACD bullish crossover + Histogram > 0
- ATR%: 2-8%
- Risk/Reward >= 2
- Close > VWAP(20)
- Candle close position > 50%
- India VIX < 20
- Nifty 50 > EMA20
- Advance/Decline Ratio > 1

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
