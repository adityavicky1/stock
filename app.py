import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Configuration
st.set_page_config(
    page_title="Advanced Stock Technical & Fundamental Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Advanced Stock Analysis & Technical Dashboard")
st.markdown("Perform comprehensive technical chart analysis, momentum indicators review, and fundamental metric inspection for global and Indian equities (e.g., `RELIANCE.NS`, `TCS.NS`, `AAPL`).")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("1. Asset & Timeframe")
ticker_symbol = st.sidebar.text_input("Stock Ticker", value="RELIANCE.NS").upper()

# Exchange handling
is_indian_stock = ".NS" in ticker_symbol or ".BO" in ticker_symbol or ticker_symbol.startswith("^")
currency_symbol = "₹" if is_indian_stock else "$"

timeframe_mapping = {
    "1 Month": {"period": "1mo", "interval": "1d"},
    "6 Months": {"period": "6mo", "interval": "1d"},
    "1 Year": {"period": "1y", "interval": "1d"},
    "5 Years": {"period": "5y", "interval": "1wk"},
    "Max": {"period": "max", "interval": "1mo"}
}
selected_timeframe = st.sidebar.selectbox("Select Time Frame", list(timeframe_mapping.keys()), index=2)

st.sidebar.header("2. Technical Indicators")
show_candlestick = st.sidebar.checkbox("Use Candlestick Chart", value=True)

# Moving Averages
enable_ema1 = st.sidebar.checkbox("Enable EMA 1", value=True)
ema1_span = st.sidebar.number_input("EMA 1 Period", min_value=1, max_value=200, value=20)

enable_ema2 = st.sidebar.checkbox("Enable EMA 2", value=True)
ema2_span = st.sidebar.number_input("EMA 2 Period", min_value=1, max_value=200, value=50)

# Oscillators & Subplots
show_rsi = st.sidebar.checkbox("Show RSI (14)", value=True)
show_volume = st.sidebar.checkbox("Show Volume Subplot", value=True)


# --- DATA FETCHING ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_stock_data(ticker, period, interval):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        info = stock.info
        return df, info, None
    except Exception as e:
        return None, None, str(e)

current_period = timeframe_mapping[selected_timeframe]["period"]
current_interval = timeframe_mapping[selected_timeframe]["interval"]

with st.spinner(f"Pulling live data for {ticker_symbol}..."):
    df, stock_info, error = fetch_stock_data(ticker_symbol, current_period, current_interval)

if error or df is None or df.empty:
    st.error(f"Could not retrieve valid data for `{ticker_symbol}`. Please check if the ticker symbol includes the correct suffix (e.g., `.NS` for NSE).")
else:
    # --- TECHNICAL CALCULATIONS ---
    # EMAs
    if enable_ema1:
        df[f"EMA_{ema1_span}"] = df["Close"].ewm(span=ema1_span, adjust=False).mean()
    if enable_ema2:
        df[f"EMA_{ema2_span}"] = df["Close"].ewm(span=ema2_span, adjust=False).mean()

    # RSI (14)
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # --- TOP FINANCIAL METRICS ---
    current_price = df["Close"].iloc[-1]
    price_change = current_price - df["Close"].iloc[-2]
    price_change_pct = (price_change / df["Close"].iloc[-2]) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"{currency_symbol}{current_price:,.2f}", f"{price_change:+,.2f} ({price_change_pct:+.2f}%)")
    col2.metric("Market Cap", f"{currency_symbol}{stock_info.get('marketCap', 0):,}" if stock_info.get('marketCap') else "N/A")
    col3.metric("P/E Ratio", stock_info.get("trailingPE", "N/A"))
    col4.metric("52-Wk High / Low", f"{currency_symbol}{stock_info.get('fiftyTwoWeekHigh', 0):,.2f} / {currency_symbol}{stock_info.get('fiftyTwoWeekLow', 0):,.2f}")

    # --- MULTI-ROW PLOTLY SUBPLOTS ---
    # Determine rows based on user options
    row_count = 1
    row_heights = [0.7]
    specs = [[{"secondary_y": True}]]

    if show_volume:
        row_count += 1
        row_heights.append(0.15)
        specs.append([{"secondary_y": False}])

    if show_rsi:
        row_count += 1
        row_heights.append(0.15)
        specs.append([{"secondary_y": False}])

    # Normalize row heights
    total_h = sum(row_heights)
    row_heights = [h / total_h for h in row_heights]

    fig = make_subplots(
        rows=row_count, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=row_heights,
        specs=specs
    )

    # Row 1: Price / Candlestick & Moving Averages
    if show_candlestick:
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="OHLC"
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color="#2962FF", width=2)), row=1, col=1)

    if enable_ema1 and f"EMA_{ema1_span}" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[f"EMA_{ema1_span}"], mode='lines', name=f"EMA {ema1_span}", line=dict(color="#FF6D00", width=1.5)), row=1, col=1)

    if enable_ema2 and f"EMA_{ema2_span}" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[f"EMA_{ema2_span}"], mode='lines', name=f"EMA {ema2_span}", line=dict(color="#00E676", width=1.5)), row=1, col=1)

    # Current active row tracker
    current_row = 2

    # Row 2: Volume Subplot
    if show_volume:
        colors = ['#00E676' if row['Close'] >= row['Open'] else '#FF5252' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name="Volume"), row=current_row, col=1)
        current_row += 1

    # Row 3: RSI Subplot
    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name="RSI (14)", line=dict(color="#E040FB", width=1.5)), row=current_row, col=1)
        # Add Overbought / Oversold reference lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)

    # Layout Setup
    fig.update_layout(
        title=f"{stock_info.get('longName', ticker_symbol)} - Technical Chart",
        template="plotly_dark",
        height=750,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- FUNDAMENTALS & RAW DATA TABS ---
    tab1, tab2 = st.tabs(["🏢 Fundamental Overview", "📋 Historical Data Table"])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Company Profile**")
            st.write(f"- **Sector:** {stock_info.get('sector', 'N/A')}")
            st.write(f"- **Industry:** {stock_info.get('industry', 'N/A')}")
            st.write(f"- **Country:** {stock_info.get('country', 'N/A')}")
            st.write(f"- **Employees:** {stock_info.get('fullTimeEmployees', 'N/A'):,}" if stock_info.get('fullTimeEmployees') else "- **Employees:** N/A")
        with col_b:
            st.write("**Valuation & Profitability**")
            st.write(f"- **Forward P/E:** {stock_info.get('forwardPE', 'N/A')}")
            st.write(f"- **Dividend Yield:** {stock_info.get('dividendYield', 0) * 100:.2f}%" if stock_info.get('dividendYield') else "- **Dividend Yield:** N/A")
            st.write(f"- **Profit Margins:** {stock_info.get('profitMargins', 0) * 100:.2f}%" if stock_info.get('profitMargins') else "- **Profit Margins:** N/A")
            st.write(f"- **Beta:** {stock_info.get('beta', 'N/A')}")

    with tab2:
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
