import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(
    page_title="Stock Technical Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Interactive Stock Price & EMA Dashboard")
st.markdown("Enter a stock ticker (e.g., `RELIANCE.NS`, `TCS.NS`, `AAPL`), select your preferred time frame, and analyze trends with custom **Exponential Moving Averages (EMAs)**.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Configuration")

# 1. Ticker Input (Default set to an Indian stock example)
ticker_symbol = st.sidebar.text_input("Stock Ticker (e.g., RELIANCE.NS, TCS.NS, AAPL)", value="RELIANCE.NS").upper()

# Determine currency symbol based on exchange suffix
is_indian_stock = ".NS" in ticker_symbol or ".BO" in ticker_symbol or ticker_symbol.startswith("^")
currency_symbol = "₹" if is_indian_stock else "$"

# 2. Time Frame Selection Mapping
timeframe_mapping = {
    "1 Month": {"period": "1mo", "interval": "1d"},
    "6 Months": {"period": "6mo", "interval": "1d"},
    "1 Year": {"period": "1y", "interval": "1d"},
    "5 Years": {"period": "5y", "interval": "1wk"},
    "Max": {"period": "max", "interval": "1mo"}
}

selected_timeframe = st.sidebar.selectbox("Select Time Frame", list(timeframe_mapping.keys()), index=2)

# 3. EMA Inputs
st.sidebar.subheader("EMA Settings")
enable_ema1 = st.sidebar.checkbox("Enable EMA 1", value=True)
ema1_span = st.sidebar.number_input("EMA 1 Period", min_value=1, max_value=200, value=20)

enable_ema2 = st.sidebar.checkbox("Enable EMA 2", value=True)
ema2_span = st.sidebar.number_input("EMA 2 Period", min_value=1, max_value=200, value=50)


# --- DATA FETCHING WITH CACHING ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_stock_data(ticker, period, interval):
    """Fetches historical stock data from Yahoo Finance safely."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        info = stock.info
        return df, info, None
    except Exception as e:
        return None, None, str(e)

# Fetch settings based on selection
current_period = timeframe_mapping[selected_timeframe]["period"]
current_interval = timeframe_mapping[selected_timeframe]["interval"]

with st.spinner(f"Fetching data for {ticker_symbol}..."):
    df, stock_info, error = fetch_stock_data(ticker_symbol, current_period, current_interval)

if error or df is None or df.empty:
    st.error(f"Could not retrieve data for ticker symbol: `{ticker_symbol}`. Please ensure you include the exchange suffix for Indian stocks (e.g., `.NS` for NSE or `.BO` for BSE).")
else:
    # --- DATA PROCESSING (EMA Calculation) ---
    if enable_ema1:
        df[f"EMA_{ema1_span}"] = df["Close"].ewm(span=ema1_span, adjust=False).mean()
    if enable_ema2:
        df[f"EMA_{ema2_span}"] = df["Close"].ewm(span=ema2_span, adjust=False).mean()

    # --- TOP METRICS DISPLAY ---
    current_price = df["Close"].iloc[-1]
    price_change = current_price - df["Close"].iloc[-2]
    price_change_pct = (price_change / df["Close"].iloc[-2]) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"{currency_symbol}{current_price:,.2f}", f"{price_change:+,.2f} ({price_change_pct:+.2f}%)")
    col2.metric("Company / Asset Name", stock_info.get("longName", ticker_symbol))
    col3.metric("Sector", stock_info.get("sector", "N/A"))

    # --- PLOTTING WITH PLOTLY ---
    fig = go.Figure()

    # Plot Close Price Line
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df["Close"], 
        mode="lines", 
        name="Close Price",
        line=dict(color="#2962FF", width=2)
    ))

    # Plot EMA 1
    if enable_ema1 and f"EMA_{ema1_span}" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df[f"EMA_{ema1_span}"], 
            mode="lines", 
            name=f"EMA {ema1_span}",
            line=dict(color="#FF6D00", width=1.5)
        ))

    # Plot EMA 2
    if enable_ema2 and f"EMA_{ema2_span}" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df[f"EMA_{ema2_span}"], 
            mode="lines", 
            name=f"EMA {ema2_span}",
            line=dict(color="#00E676", width=1.5)
        ))

    # Layout Customization
    fig.update_layout(
        title=f"{ticker_symbol} Price Chart ({selected_timeframe})",
        xaxis_title="Date",
        yaxis_title=f"Price ({currency_symbol})",
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- RAW DATA EXPANDER ---
    with st.expander("View Raw Data Table"):
        st.dataframe(df.sort_index(ascending=False))
