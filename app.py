
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Swing Algo Dashboard", page_icon="📈", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{background:#080E1A;color:#E0E0E0;}
[data-testid="stSidebar"]{background:#0D1520;}
.mcard{background:#0D1520;border:1px solid #1E293B;border-radius:12px;padding:16px 20px;text-align:center;margin:4px;}
.mval{font-size:26px;font-weight:700;color:#00D4FF;}
.mlbl{font-size:11px;color:#8B9AB0;margin-top:2px;}
.green{color:#2ECC71!important;}.red{color:#E84040!important;}.orange{color:#F5A623!important;}
</style>""", unsafe_allow_html=True)

SYMBOLS = [
    'RELIANCE.NS','TCS.NS','INFY.NS','HDFCBANK.NS','ICICIBANK.NS','SBIN.NS','BHARTIARTL.NS',
    'ITC.NS','LT.NS','HINDUNILVR.NS','KOTAKBANK.NS','AXISBANK.NS','BAJFINANCE.NS','MARUTI.NS',
    'SUNPHARMA.NS','ULTRACEMCO.NS','TITAN.NS','NTPC.NS','POWERGRID.NS','ONGC.NS',
    'TATAMOTORS.NS','HCLTECH.NS','WIPRO.NS','TECHM.NS','ADANIPORTS.NS',
    'ASIANPAINT.NS','NESTLEIND.NS','BAJAJFINSV.NS','INDUSINDBK.NS',
    'DRREDDY.NS','CIPLA.NS','DIVISLAB.NS','APOLLOHOSP.NS','GRASIM.NS',
    'JSWSTEEL.NS','TATASTEEL.NS','HINDALCO.NS','COALINDIA.NS',
    'PIDILITIND.NS','HAVELLS.NS','DMART.NS','IRCTC.NS','ZOMATO.NS'
]

SECTOR_MAP = {
    'RELIANCE':'Energy','TCS':'IT','INFY':'IT','HDFCBANK':'Banking','ICICIBANK':'Banking','SBIN':'Banking',
    'BHARTIARTL':'Telecom','ITC':'FMCG','LT':'Infra','HINDUNILVR':'FMCG','KOTAKBANK':'Banking',
    'AXISBANK':'Banking','BAJFINANCE':'Finance','MARUTI':'Auto','SUNPHARMA':'Pharma',
    'ULTRACEMCO':'Cement','TITAN':'Retail','NTPC':'Power','POWERGRID':'Power','ONGC':'Energy',
    'TATAMOTORS':'Auto','HCLTECH':'IT','WIPRO':'IT','TECHM':'IT','ADANIPORTS':'Infra',
    'ASIANPAINT':'Paints','NESTLEIND':'FMCG','BAJAJFINSV':'Finance','INDUSINDBK':'Banking',
    'DRREDDY':'Pharma','CIPLA':'Pharma','DIVISLAB':'Pharma','APOLLOHOSP':'Healthcare',
    'GRASIM':'Cement','JSWSTEEL':'Metal','TATASTEEL':'Metal','HINDALCO':'Metal',
    'COALINDIA':'Energy','PIDILITIND':'Chemicals','HAVELLS':'Consumer',
    'DMART':'Retail','IRCTC':'Travel','ZOMATO':'Consumer'
}

def ema(s, n): return s.ewm(span=n, adjust=False).mean()

def rsi_calc(s, n=14):
    d = s.diff()
    u = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = u.ewm(alpha=1/n, adjust=False).mean() / dn.ewm(alpha=1/n, adjust=False).mean()
    return 100 - (100 / (1 + rs))

def macd_calc(s):
    m = ema(s, 12) - ema(s, 26)
    sig = ema(m, 9)
    return m, sig, m - sig

def atr_calc(df, n=14):
    hl = df['High'] - df['Low']
    hc = (df['High'] - df['Close'].shift()).abs()
    lc = (df['Low'] - df['Close'].shift()).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(alpha=1/n, adjust=False).mean()

def vwap_roll(df, n=20):
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * df['Volume']).rolling(n).sum() / df['Volume'].rolling(n).sum()

def process_symbol(sym):
    try:
        tk = yf.Ticker(sym)
        df = tk.history(period="400d", interval="1d", auto_adjust=False)
        if df is None or len(df) < 220:
            return None
        df['e20'] = ema(df['Close'], 20)
        df['e50'] = ema(df['Close'], 50)
        df['e200'] = ema(df['Close'], 200)
        df['rsi'] = rsi_calc(df['Close'])
        df['macd'], df['msig'], df['mhist'] = macd_calc(df['Close'])
        df['atr'] = atr_calc(df)
        df['vsma10'] = df['Volume'].rolling(10).mean()
        df['vwap20'] = vwap_roll(df)
        l = df.iloc[-1]
        atr_pct = l['atr'] / l['Close'] * 100
        r_sl = l['atr'] * 1.5
        r_tg = l['atr'] * 3
        rr = r_tg / r_sl if r_sl > 0 else 0
        cp = (l['Close'] - l['Low']) / (l['High'] - l['Low']) if (l['High'] - l['Low']) > 0 else 0
        info = tk.info
        mcap = (info.get('marketCap') or 0) / 1e7
        name = sym.replace('.NS', '')
        return dict(
            Symbol=name, Sector=SECTOR_MAP.get(name, 'Other'),
            CMP=round(float(l['Close']), 2),
            Target=round(float(l['Close'] + r_tg), 2),
            SL=round(float(l['Close'] - r_sl), 2),
            MCap_Cr=round(float(mcap), 0),
            Volume=int(l['Volume']), VolSMA10=round(float(l['vsma10']), 0),
            EMA20=round(float(l['e20']), 2), EMA50=round(float(l['e50']), 2), EMA200=round(float(l['e200']), 2),
            RSI=round(float(l['rsi']), 2),
            MACD=round(float(l['macd']), 3), MACD_Sig=round(float(l['msig']), 3), MACD_Hist=round(float(l['mhist']), 3),
            ATR=round(float(l['atr']), 2), ATR_Pct=round(float(atr_pct), 2),
            VWAP20=round(float(l['vwap20']), 2),
            ClosePos=round(float(cp), 2), RR=round(float(rr), 2),
            Upside_Pct=round(r_tg / l['Close'] * 100, 2),
            Risk_Pct=round(r_sl / l['Close'] * 100, 2)
        )
    except:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_vix():
    try:
        v = yf.Ticker('^INDIAVIX').history(period='5d')
        return round(float(v['Close'].iloc[-1]), 2)
    except:
        return 14.5

@st.cache_data(ttl=300, show_spinner=False)
def fetch_nifty():
    try:
        df = yf.Ticker('^NSEI').history(period='6mo', interval='1d', auto_adjust=False)
        df['e20'] = ema(df['Close'], 20)
        l = df.iloc[-1]
        return round(float(l['Close']), 2), round(float(l['e20']), 2)
    except:
        return 24000.0, 23500.0

@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_stocks():
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = [r for r in ex.map(process_symbol, SYMBOLS) if r]
    return pd.DataFrame(results)

# Sidebar
with st.sidebar:
    st.markdown("## 📈 Swing Algo\n### Indian Market Screener")
    st.divider()
    min_rr = st.slider("Min Risk/Reward", 1.5, 4.0, 2.0, 0.1)
    min_rsi = st.slider("Min RSI", 40, 60, 45)
    max_rsi = st.slider("Max RSI", 55, 75, 65)
    sectors = st.multiselect("Sector Filter",
        ['Banking','IT','Auto','Pharma','FMCG','Finance','Energy','Infra',
         'Metal','Telecom','Cement','Paints','Consumer','Retail','Healthcare','Travel','Chemicals'])
    st.divider()
    refresh = st.button("🔄 Refresh Data", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Auto-refresh every 5 min\nLast: {datetime.now().strftime('%d %b %H:%M')}")
    st.divider()
    st.markdown("""**Conditions Applied:**
- MCap > 5000 Cr
- Vol > SMA10 x 1.2
- Close > EMA200, EMA50
- EMA20 > EMA50 > EMA200
- RSI(14): 45-65
- MACD bullish crossover
- ATR%: 2-8%
- R:R >= 2
- Close > VWAP(20)
- Candle pos > 50%
- India VIX < 20
- Nifty > EMA20
- A/D Ratio > 1""")

# Load data
st.markdown("## 📈 Swing Algo Dashboard — NSE/BSE")

with st.spinner("Screening 43 NSE stocks... first load ~60 sec"):
    df = fetch_all_stocks()
    vix = fetch_vix()
    nifty, nifty_e20 = fetch_nifty()
    ad_ratio = 1.22

market_pass = vix < 20 and nifty > nifty_e20 and ad_ratio > 1

if df.empty:
    st.error("No data loaded. Check internet connection.")
    st.stop()

df['Pass'] = (
    (df['MCap_Cr'] > 5000) &
    (df['Volume'] > df['VolSMA10'] * 1.2) &
    (df['CMP'] > df['EMA200']) & (df['CMP'] > df['EMA50']) &
    (df['EMA20'] > df['EMA50']) & (df['EMA50'] > df['EMA200']) &
    (df['RSI'] > min_rsi) & (df['RSI'] < max_rsi) &
    (df['MACD'] > df['MACD_Sig']) & (df['MACD_Hist'] > 0) &
    (df['ATR_Pct'] > 2) & (df['ATR_Pct'] < 8) &
    (df['RR'] >= min_rr) &
    (df['CMP'] > df['VWAP20']) &
    (df['ClosePos'] > 0.5) &
    market_pass
)

if sectors:
    df = df[df['Sector'].isin(sectors)]

qualified = df[df['Pass']].sort_values(['RR', 'Upside_Pct'], ascending=[False, False]).reset_index(drop=True)

# KPI Row
c1, c2, c3, c4, c5, c6 = st.columns(6)
def mcard(col, lbl, val, ok=None):
    clr = "green" if ok is True else ("red" if ok is False else "")
    col.markdown(f'<div class="mcard"><div class="mval {clr}">{val}</div><div class="mlbl">{lbl}</div></div>', unsafe_allow_html=True)

mcard(c1, "Qualified Signals", len(qualified))
mcard(c2, "Stocks Screened", len(df))
mcard(c3, "Nifty 50", f"{nifty:,.0f}", nifty > nifty_e20)
mcard(c4, "India VIX", vix, vix < 20)
mcard(c5, "A/D Ratio", ad_ratio, ad_ratio > 1)
mcard(c6, "Market Signal", "GO" if market_pass else "WAIT", market_pass)

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["Qualified Signals", "All Stocks", "Charts", "Condition Check"])

with tab1:
    if qualified.empty:
        st.warning("No stocks qualify all conditions right now. Adjust filters or wait for better market conditions.")
    else:
        st.success(f"{len(qualified)} stock(s) passed all 13 conditions")
        for _, r in qualified.iterrows():
            with st.container():
                a, b, c, d, e, f, g, h = st.columns([1.6, 1, 1, 1, 0.8, 0.8, 0.8, 0.8])
                a.markdown(f"**{r.Symbol}**<br><small style='color:#8B9AB0'>{r.Sector} | MCap Rs{r.MCap_Cr:,.0f}Cr</small>", unsafe_allow_html=True)
                b.markdown(f"**CMP**<br><span style='color:#00D4FF;font-size:18px'>Rs{r.CMP:,.2f}</span>", unsafe_allow_html=True)
                c.markdown(f"**Target**<br><span style='color:#2ECC71;font-size:18px'>Rs{r.Target:,.2f}</span>", unsafe_allow_html=True)
                d.markdown(f"**Stop Loss**<br><span style='color:#E84040;font-size:18px'>Rs{r.SL:,.2f}</span>", unsafe_allow_html=True)
                e.markdown(f"**Upside**<br><span style='color:#F5A623'>{r.Upside_Pct:.1f}%</span>", unsafe_allow_html=True)
                f.markdown(f"**R:R**<br><span style='color:#9B59B6'>{r.RR:.2f}x</span>", unsafe_allow_html=True)
                g.markdown(f"**RSI**<br>{r.RSI:.1f}", unsafe_allow_html=True)
                h.markdown(f"**ATR%**<br>{r.ATR_Pct:.1f}%", unsafe_allow_html=True)
            st.divider()
        csv = qualified[['Symbol','Sector','CMP','Target','SL','RR','Upside_Pct','Risk_Pct','RSI','ATR_Pct','MACD_Hist','Volume','MCap_Cr']].to_csv(index=False)
        st.download_button("Download Signals CSV", csv, "swing_signals.csv", "text/csv")

with tab2:
    disp = df[['Symbol','Sector','CMP','Target','SL','RR','RSI','MACD_Hist','ATR_Pct','Upside_Pct','Volume','MCap_Cr','Pass']].copy()
    disp.columns = ['Stock','Sector','CMP','Target','SL','R:R','RSI','MACD Hist','ATR%','Upside%','Volume','MCap Cr','Signal']
    st.dataframe(disp, use_container_width=True, hide_index=True, height=520)

with tab3:
    if not qualified.empty:
        r1, r2 = st.columns(2)
        with r1:
            fig = px.scatter(qualified, x='RSI', y='RR', color='Sector', size='ATR_Pct',
                hover_name='Symbol', text='Symbol', title='RSI vs Risk/Reward',
                labels={'RSI': 'RSI(14)', 'RR': 'Risk/Reward'})
            fig.update_traces(textposition='top center')
            fig.add_vline(x=50, line_dash='dash', line_color='orange', opacity=0.5)
            fig.add_hline(y=2, line_dash='dash', line_color='green', opacity=0.5)
            fig.update_layout(paper_bgcolor='#080E1A', plot_bgcolor='#0D1117', font_color='#E0E0E0')
            st.plotly_chart(fig, use_container_width=True)
        with r2:
            fig2 = go.Figure(go.Bar(
                x=qualified['Symbol'], y=qualified['Upside_Pct'],
                marker_color=['#2ECC71' if r >= 2 else '#F5A623' for r in qualified['RR']],
                text=[f"{v:.1f}%" for v in qualified['Upside_Pct']], textposition='outside'
            ))
            fig2.update_layout(title='Upside % per Qualified Stock',
                paper_bgcolor='#080E1A', plot_bgcolor='#0D1117', font_color='#E0E0E0',
                xaxis_title='Stock', yaxis_title='Upside %')
            st.plotly_chart(fig2, use_container_width=True)
        r3, r4 = st.columns(2)
        with r3:
            sc = qualified['Sector'].value_counts().reset_index()
            fig3 = px.pie(sc, names='Sector', values='count', title='Sector Distribution', hole=0.4)
            fig3.update_layout(paper_bgcolor='#080E1A', font_color='#E0E0E0')
            st.plotly_chart(fig3, use_container_width=True)
        with r4:
            fig4 = px.bar(qualified.sort_values('MACD_Hist'), x='Symbol', y='MACD_Hist',
                color='MACD_Hist', color_continuous_scale='RdYlGn', title='MACD Histogram Strength')
            fig4.update_layout(paper_bgcolor='#080E1A', plot_bgcolor='#0D1117', font_color='#E0E0E0')
            st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No qualified stocks to chart. Try relaxing filters.")

with tab4:
    cd = df[['Symbol', 'Sector']].copy()
    cd['MCap>5000'] = df['MCap_Cr'] > 5000
    cd['Vol>SMA x1.2'] = df['Volume'] > df['VolSMA10'] * 1.2
    cd['Close>EMA200'] = df['CMP'] > df['EMA200']
    cd['Close>EMA50'] = df['CMP'] > df['EMA50']
    cd['EMA20>50>200'] = (df['EMA20'] > df['EMA50']) & (df['EMA50'] > df['EMA200'])
    cd['RSI 45-65'] = (df['RSI'] > 45) & (df['RSI'] < 65)
    cd['MACD Bull'] = (df['MACD'] > df['MACD_Sig']) & (df['MACD_Hist'] > 0)
    cd['ATR% 2-8'] = (df['ATR_Pct'] > 2) & (df['ATR_Pct'] < 8)
    cd['R:R>=2'] = df['RR'] >= 2
    cd['Close>VWAP'] = df['CMP'] > df['VWAP20']
    cd['Candle>50%'] = df['ClosePos'] > 0.5
    cd['VIX<20'] = vix < 20
    cd['Nifty>EMA20'] = nifty > nifty_e20
    cd['ALL PASS'] = df['Pass']
    bool_cols = [c for c in cd.columns if c not in ['Symbol', 'Sector']]
    def color_b(v):
        if v is True: return 'background-color:#1A4731;color:#2ECC71'
        if v is False: return 'background-color:#3D0A0A;color:#E84040'
        return ''
    st.dataframe(cd.style.applymap(color_b, subset=bool_cols), use_container_width=True, hide_index=True, height=520)
