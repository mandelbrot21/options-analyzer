import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import time

st.set_page_config(layout="wide")
st.title("📊 Options Analyzer")

# Input ticker
ticker = st.text_input("Ticker", "AAPL").upper().strip()

if ticker:
    try:
        # Mostra un messaggio di caricamento
        with st.spinner(f"🔍 Cerco {ticker}..."):
            stock = yf.Ticker(ticker)
            
            # Prova a prendere info base per verificare che esista
            info = stock.info
            
            # Verifica che il ticker esista
            if 'regularMarketPrice' not in info and 'currentPrice' not in info:
                st.error(f"❌ Ticker '{ticker}' non trovato")
                st.info("💡 Prova con: AAPL, TSLA, MSFT, GOOGL, AMZN, SPY")
                st.stop()
            
            # Prezzo spot
            spot = stock.history(period='2d', interval='1d')['Close'].iloc[-1]
            
            st.success(f"✅ Trovato: {info.get('longName', ticker)}")
            
            # Mostra prezzo
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Prezzo Spot", f"${spot:.2f}")
            with col2:
                st.metric("📈 Settore", info.get('sector', 'N/A'))
            with col3:
                st.metric("🏢 Market Cap", f"${info.get('marketCap', 0):,.0f}")
            
            # Verifica opzioni disponibili
            if not stock.options:
                st.error(f"⚠️ Nessuna opzione disponibile per {ticker}")
                st.info("Alcuni ticker non hanno opzioni. Prova con: AAPL, TSLA, SPY")
                st.stop()
            
            # Scelta scadenza
            expiry = st.selectbox("📅 Data Scadenza", stock.options)
            
            # Scarica option chain
            with st.spinner(f"Caricamento option chain per {expiry}..."):
                chain = stock.option_chain(expiry)
            
            # Scegli tipo
            option_type = st.radio("📌 Tipo Opzione", ["CALL", "PUT"], horizontal=True)
            
            # Seleziona DataFrame
            df = chain.calls if option_type == "CALL" else chain.puts
            
            # Filtra opzioni valide
            df = df[df['bid'] >= 0].head(20)
            
            if len(df) > 0:
                # Tabella
                st.subheader("📋 Option Chain")
                display_df = df[['strike', 'bid', 'ask', 'impliedVolatility', 'volume']].copy()
                display_df['impliedVolatility'] = display_df['impliedVolatility'] * 100
                
                st.dataframe(
                    display_df.style.format({
                        'strike': '${:.2f}',
                        'bid': '${:.2f}',
                        'ask': '${:.2f}',
                        'impliedVolatility': '{:.1f}%',
                        'volume': '{:,}'
                    }),
                    use_container_width=True
                )
                
                # Grafico
                st.subheader("📊 Volatility Smile")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df['strike'],
                    y=df['impliedVolatility'] * 100,
                    mode='lines+markers',
                    name='IV'
                ))
                fig.add_vline(x=spot, line_dash="dash", line_color="red", 
                             annotation_text=f"Spot: ${spot:.2f}")
                fig.update_layout(
                    title=f"Volatility Smile - {ticker} ({expiry})",
                    xaxis_title="Strike Price",
                    yaxis_title="Implied Volatility (%)",
                    height=450
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Nessuna opzione disponibile per questa scadenza")
                
    except Exception as e:
        st.error(f"❌ Errore: {str(e)}")
        st.info("💡 Suggerimenti:\n- Prova con ticker come AAPL, TSLA, MSFT\n- Controlla di aver scritto bene il ticker\n- Aspetta qualche secondo e riprova")

else:
    st.info("👈 Inserisci un ticker per iniziare")
    st.markdown("""
    ### 📖 Ticker che funzionano:
    - **AAPL** - Apple
    - **TSLA** - Tesla  
    - **MSFT** - Microsoft
    - **GOOGL** - Google
    - **AMZN** - Amazon
    - **SPY** - S&P 500 ETF
    - **QQQ** - Nasdaq ETF
    - **NVDA** - NVIDIA
    """)

st.caption("🚀 Powered by Yahoo Finance")
