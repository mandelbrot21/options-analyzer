# app.py - Copia tutto questo codice
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configurazione pagina
st.set_page_config(
    page_title="OptionsVibe Analyzer",
    page_icon="📈",
    layout="wide"
)

# Titolo
st.title("📊 OptionsVibe Analyzer")
st.markdown("Analisi opzioni professionale - Nessuna installazione richiesta")

# Sidebar per input
with st.sidebar:
    st.header("📌 Input")
    ticker = st.text_input("Ticker", "AAPL").upper()
    
    # Data scadenza
    expirations = []
    if ticker:
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            if expirations:
                selected_expiry = st.selectbox("Scadenza", expirations)
        except:
            st.error("Ticker non trovato")
            selected_expiry = None
    
    # Tipo opzione
    option_type = st.radio("Tipo Opzione", ["CALL", "PUT"], horizontal=True)
    
    # Colori
    st.markdown("---")
    color_positive = st.color_picker("Colore Profitti", "#00ff00")
    color_negative = st.color_picker("Colore Perdite", "#ff0000")

# Funzioni di calcolo
def black_scholes(S, K, T, r, sigma, option_type='call'):
    """Black-Scholes semplificato"""
    from scipy.stats import norm
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    
    if option_type == 'call':
        price = S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    else:
        price = K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)
    return price

def calculate_greeks(S, K, T, r, sigma, option_type='call'):
    """Calcolo Greci"""
    from scipy.stats import norm
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    
    delta = norm.cdf(d1) if option_type == 'call' else -norm.cdf(-d1)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - r * K * np.exp(-r*T) * norm.cdf(d2)) / 365
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    
    return {'Delta': delta, 'Gamma': gamma, 'Theta': theta, 'Vega': vega}

# Area principale
if ticker and selected_expiry:
    try:
        # Scarica dati
        with st.spinner('Caricamento dati...'):
            stock = yf.Ticker(ticker)
            chain = stock.option_chain(selected_expiry)
            spot = stock.history(period='1d')['Close'].iloc[-1]
            
            # Prepara dati
            if option_type == 'CALL':
                df = chain.calls.copy()
            else:
                df = chain.puts.copy()
            
            # Calcola prezzi teorici e greci
            df['TheoreticalPrice'] = df.apply(
                lambda row: black_scholes(
                    spot, row['strike'], 30/365, 0.05, 
                    row['impliedVolatility'] if pd.notna(row['impliedVolatility']) else 0.3,
                    option_type.lower()
                ), axis=1
            )
            
            # Calcola Greci per ogni strike
            greeks_data = []
            for _, row in df.iterrows():
                greeks = calculate_greeks(
                    spot, row['strike'], 30/365, 0.05,
                    row['impliedVolatility'] if pd.notna(row['impliedVolatility']) else 0.3,
                    option_type.lower()
                )
                greeks_data.append(greeks)
            
            greeks_df = pd.DataFrame(greeks_data)
            df = pd.concat([df, greeks_df], axis=1)
        
        # Metriche principali
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Prezzo Spot", f"${spot:.2f}")
        with col2:
            st.metric("Volatilità Media", f"{df['impliedVolatility'].mean()*100:.1f}%")
        with col3:
            st.metric("Numero Opzioni", len(df))
        with col4:
            max_oi = df.loc[df['openInterest'].idxmax()] if 'openInterest' in df else None
            if max_oi is not None:
                st.metric("Max Open Interest", f"${max_oi['strike']:.0f}")
        
        # Tabella Option Chain
        st.subheader("📋 Option Chain")
        
        # Colonne da mostrare
        display_cols = ['strike', 'bid', 'ask', 'impliedVolatility', 
                       'TheoreticalPrice', 'Delta', 'Gamma', 'Theta', 'Vega']
        display_cols = [c for c in display_cols if c in df.columns]
        
        st.dataframe(
            df[display_cols].style.format({
                'strike': '${:.2f}',
                'bid': '${:.2f}',
                'ask': '${:.2f}',
                'impliedVolatility': '{:.1%}',
                'TheoreticalPrice': '${:.2f}',
                'Delta': '{:.3f}',
                'Gamma': '{:.3f}',
                'Theta': '${:.3f}',
                'Vega': '${:.3f}'
            }),
            use_container_width=True,
            height=400
        )
        
        # Grafici
        st.subheader("📊 Visualizzazioni")
        
        tab1, tab2, tab3 = st.tabs(["Volatility Smile", "Greeks Profile", "Payoff Diagram"])
        
        with tab1:
            # Volatility Smile
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['strike'],
                y=df['impliedVolatility'] * 100,
                mode='lines+markers',
                name='IV Smile',
                line=dict(color='blue', width=2)
            ))
            fig.add_vline(x=spot, line_dash="dash", line_color="red", 
                         annotation_text=f"Spot: ${spot}")
            fig.update_layout(
                title="Volatility Smile",
                xaxis_title="Strike Price",
                yaxis_title="Implied Volatility (%)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Greci
            selected_greek = st.selectbox("Scegli Greek", ['Delta', 'Gamma', 'Theta', 'Vega'])
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['strike'],
                y=df[selected_greek],
                mode='lines+markers',
                name=selected_greek,
                line=dict(width=2)
            ))
            fig.add_vline(x=spot, line_dash="dash", line_color="red")
            fig.update_layout(
                title=f"{selected_greek} vs Strike",
                xaxis_title="Strike Price",
                yaxis_title=selected_greek,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            # Payoff Diagram (simulazione)
            st.write("Simulazione Payoff a Scadenza")
            selected_strike = st.slider("Seleziona Strike", 
                                       float(df['strike'].min()), 
                                       float(df['strike'].max()), 
                                       float(spot))
            
            # Calcola payoff per range di prezzi
            prices = np.linspace(spot * 0.7, spot * 1.3, 100)
            if option_type == 'CALL':
                payoffs = np.maximum(prices - selected_strike, 0)
            else:
                payoffs = np.maximum(selected_strike - prices, 0)
            
            # Costo opzione (bid medio)
            option_cost = df[df['strike'] == selected_strike]['bid'].mean() if selected_strike in df['strike'].values else 1
            net_payoffs = payoffs - option_cost
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=prices,
                y=net_payoffs,
                mode='lines',
                name='Payoff Netto',
                fill='tozeroy',
                line=dict(color='green', width=2)
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.add_vline(x=selected_strike, line_dash="dash", line_color="red")
            fig.update_layout(
                title=f"Payoff {option_type} Strike ${selected_strike:.0f}",
                xaxis_title="Prezzo Sottostante a Scadenza",
                yaxis_title="Profit/Loss ($)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Break-even point
            breakeven = selected_strike + option_cost if option_type == 'CALL' else selected_strike - option_cost
            st.info(f"💡 Break-even point: ${breakeven:.2f}")
        
        # Download dati
        st.subheader("💾 Esporta Dati")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Scarica CSV",
            data=csv,
            file_name=f"{ticker}_{selected_expiry}_{option_type}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Errore nel caricamento: {e}")

else:
    st.info("👈 Inserisci un ticker valido nella barra laterale per iniziare")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <sub>🚀 Built with Streamlit | Dati da Yahoo Finance | Calcoli Black-Scholes</sub>
</div>
""", unsafe_allow_html=True)
