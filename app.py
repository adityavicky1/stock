import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Configuration
st.set_page_config(
    page_title="Nifty 500 Screener & Technical Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("🔍 Nifty 500 Technical Screener & Analytics Studio")
st.markdown("Scan potential trading setups across major Indian equities, filter by momentum criteria, and click any stock to inspect its interactive chart, indicators, and fundamentals.")

# --- NIFTY 500 SAMPLE / EXTENDED UNIVERSE MAPPING ---
# For a full production run, you can load all 500 symbols via CSV or NSE list. 
# Here is a representative high-liquidity cross-section of Nifty 500 stocks:
NIFTY_500_UNIVERSE = {
    "Reliance Industries": "RELIANCE.NS",
    "Tata Consultancy Services": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Infosys": "INFY.NS",
    "State Bank of India": "SBIN.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "Larsen & Toubro": "LT.NS",
    "ITC Limited": "ITC.NS",
    "Axis Bank": "AXISBANK.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Sun Pharmaceutical": "SUNPHARMA.NS",
    "NTPC Limited": "NTPC.NS",
    "Titan Company": "TITAN.NS",
    "Tata Steel": "TATASTEEL.NS",
    "Power Grid Corp": "POWERGRID.NS",
    "Bajaj Finance": "BAJFINANCE.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "Maruti Suzuki": "MARUTI.NS",
    "HCL Technologies": "HCLTECH.NS",
    "Adani Enterprises": "ADANIENT.NS",
    "Adani Ports": "ADANIPORTS.NS",
    "Zomato": "ZOMATO.NS",
    "Tata Power": "TATAPOWER.NS",
    "Jindal Steel & Power": "JINDALSTEL.NS",
    "Hindalco Industries": "HINDALCO.NS"
}

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("1. Screener Strategy")
scanner_type = st.sidebar.selectbox(
    "Select Scan Filter",
    [
        "All Watched Stocks",
        "Bullish EMA Crossover (EMA 20 > EMA 50)",
        "RSI Oversold (< 40)",
        "Strong Momentum (Price > EMA 20 & RSI > 50)",
        "High Volume Breakout"
    ]
)

st.sidebar.header("2. Chart Configuration")
selected_timeframe = st.sidebar.selectbox("Time Frame", ["1 Month", "6 Months", "1 Year", "5 Years"], index=2)
show_candlestick = st.sidebar.checkbox("Candlestick Chart", value=True)
enable_ema1 = st.sidebar.checkbox("Enable EMA 20", value=True)
enable_ema2 = st.sidebar.checkbox("Enable EMA 50", value=True)

timeframe_mapping = {
    "1 Month": {"period": "1mo", "interval": "1d"},
    "6 Months": {"period": "6mo", "interval": "1d"},
    "1 Year": {"period": "1y", "interval": "1d"},
    "5 Years": {"period": "5y", "interval": "1wk"}
}


# --- CACHED BATCH SCANNER FUNCTION ---
@st.cache_data(ttl=900, show_spinner=True)
def run_market_scanner(universe):
    """Scans the ticker dictionary and computes basic metrics for screening."""
    scan_results = []
    for name, ticker in universe.items():
        try:
            df = yf.download(ticker, period="3mo", interval="1d", progress=False)
            if df.empty or len(df) < 50:
                continue
            
            # Flatten multi-index columns if returned by newer yfinance versions
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            close = df["Close"]
            vol = df["Volume"]
            
            curr_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            change_pct = ((curr_price - prev_price) / prev_price) * 100
            
            ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
            ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
            
            # RSI 14
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            
            avg_vol = float(vol.rolling(window=20).mean().iloc[-1])
            curr_vol = float(vol.iloc[-1])
            vol_spike = curr_vol > (1.5 * avg_vol)

            scan_results.append({
                "Company": name,
                "Ticker": ticker,
                "Price (₹)": round(curr_price, 2),
                "Change (%)": round(change_pct, 2),
                "RSI": round(rsi, 1),
                "EMA 20": round(ema20, 2),
                "EMA 50": round(ema50, 2),
                "Volume Spike": vol_spike,
                "Bullish Crossover": ema20 > ema50
            })
        except Exception:
            continue
            
    return pd.DataFrame(scan_results)


# Run Screener Data
df_scanned = run_market_scanner(NIFTY_500_UNIVERSE)

if df_scanned.empty:
    st.error("Could not fetch scanner data. Please check your network connection.")
else:
    # Apply Filter based on sidebar selection
    if scanner_type == "Bullish EMA Crossover (EMA 20 > EMA 50)":
        df_filtered = df_scanned[df_scanned["Bullish Crossover"] == True]
    elif scanner_type == "RSI Oversold (< 40)":
        df_filtered = df_scanned[df_scanned["RSI"] < 40]
    elif scanner_type == "Strong Momentum (Price > EMA 20 & RSI > 50)":
        df_filtered = df_scanned[(df_scanned["Price (₹)"] > df_scanned["EMA 20"]) & (df_scanned["RSI"] > 50)]
    elif scanner_type == "High Volume Breakout":
        df_filtered = df_scanned[df_scanned["Volume Spike"] == True]
    else:
        df_filtered = df_scanned

    st.subheader(f"📋 Scan Results ({len(df_filtered)} Stocks Found)")
    
    # Interactive Table Selection using st.dataframe / st.altair or selectbox
    # We allow the user to pick a stock from the filtered list
    selected_company_name = st.selectbox(
        "Select a stock from the scan results to view deep-dive analytics & chart:",
        options=df_filtered["Company"].tolist() if not df_filtered.empty else df_scanned["Company"].tolist()
    )
    
    # Resolve selected ticker
    selected_ticker = NIFTY_500_UNIVERSE[selected_company_name]

    # --- FETCH DETAILED DATA FOR SELECTED STOCK ---
    t_period = timeframe_mapping[selected_timeframe]["period"]
    t_interval = timeframe_mapping[selected_timeframe]["interval"]

    @st.cache_data(ttl=600)
    def fetch_detailed_stock(ticker, period, interval):
        stock = yf.Ticker(ticker)
        dff = stock.history(period=period, interval=interval)
        if isinstance(dff.columns, pd.MultiIndex):
            dff.columns = dff.columns.get_level_values(0)
        return dff, stock.info

    with st.spinner(f"Loading analytics for {selected_company_name} ({selected_ticker})..."):
        df_detail, stock_info = fetch_detailed_stock(selected_ticker, t_period, t_interval)

    if df_detail.empty:
        st.warning(f"No historical data available for {selected_ticker}.")
    else:
        # Calculate Indicators on detailed dataframe
        df_detail["EMA_20"] = df_detail["Close"].ewm(span=20, adjust=False).mean()
        df_detail["EMA_50"] = df_detail["Close"].ewm(span=50, adjust=False).mean()
        
        delta = df_detail["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_detail["RSI"] = 100 - (100 / (1 + rs))

        # Top Metric Cards
        cur_p = df_detail["Close"].iloc[-1]
        chg = cur_p - df_detail["Close"].iloc[-2]
        chg_pct = (chg / df_detail["Close"].iloc[-2]) * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"₹{cur_p:,.2f}", f"{chg:+,.2f} ({chg_pct:+.2f}%)")
        m2.metric("Market Cap", f"₹{stock_info.get('marketCap', 0):,}" if stock_info.get('marketCap') else "N/A")
        m3.metric("P/E Ratio", stock_info.get("trailingPE", "N/A"))
        m4.metric("52-Wk High / Low", f"₹{stock_info.get('fiftyTwoWeekHigh', 0):,.2f} / ₹{stock_info.get('fiftyTwoWeekLow', 0):,.2f}")

        # --- PLOTLY SUBPLOTS (Price, Volume, RSI) ---
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=[0.65, 0.17, 0.18],
            specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )

        # Row 1: Price Chart
        if show_candlestick:
            fig.add_trace(go.Candlestick(
                x=df_detail.index, open=df_detail['Open'], high=df_detail['High'], low=df_detail['Low'], close=df_detail['Close'], name="OHLC"
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(x=df_detail.index, y=df_detail['Close'], mode='lines', name='Close Price', line=dict(color="#2962FF", width=2)), row=1, col=1)

        if enable_ema1:
            fig.add_trace(go.Scatter(x=df_detail.index, y=df_detail["EMA_20"], mode='lines', name="EMA 20", line=dict(color="#FF6D00", width=1.5)), row=1, col=1)
        if enable_ema2:
            fig.add_trace(go.Scatter(x=df_detail.index, y=df_detail["EMA_50"], mode='lines', name="EMA 50", line=dict(color="#00E676", width=1.5)), row=1, col=1)

        # Row 2: Volume Subplot
        colors = ['#00E676' if row['Close'] >= row['Open'] else '#FF5252' for _, row in df_detail.iterrows()]
        fig.add_trace(go.Bar(x=df_detail.index, y=df_detail['Volume'], marker_color=colors, name="Volume"), row=2, col=1)

        # Row 3: RSI Subplot
        fig.add_trace(go.Scatter(x=df_detail.index, y=df_detail['RSI'], mode='lines', name="RSI (14)", line=dict(color="#E040FB", width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        fig.update_layout(
            title=f"{selected_company_name} ({selected_ticker}) - {selected_timeframe} Technical Analysis",
            template="plotly_dark",
            height=750,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # --- TABS FOR SCANNER TABLE & FUNDAMENTALS ---
        tab_scan, tab_fund = st.tabs(["📊 Full Screener Table", "🏢 Fundamental Summary"])

        with tab_scan:
            st.dataframe(df_filtered.sort_values(by="Change (%)", ascending=False), use_container_width=True)

        with tab_fund:
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"- **Sector:** {stock_info.get('sector', 'N/A')}")
                st.write(f"- **Industry:** {stock_info.get('industry', 'N/A')}")
                st.write(f"- **Employees:** {stock_info.get('fullTimeEmployees', 'N/A'):,}" if stock_info.get('fullTimeEmployees') else "- **Employees:** N/A")
            with c2:
                st.write(f"- **Dividend Yield:** {stock_info.get('dividendYield', 0) * 100:.2f}%" if stock_info.get('dividendYield') else "- **Dividend Yield:** N/A")
                st.write(f"- **Profit Margins:** {stock_info.get('profitMargins', 0) * 100:.2f}%" if stock_info.get('profitMargins') else "- **Profit Margins:** N/A")
                st.write(f"- **Beta:** {stock_info.get('beta', 'N/A')}")
