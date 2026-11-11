\# 🏛️ Trinity Monitor: Congressional Trade \& Alternative Sentiment Auditor



An auditable quantitative surveillance dashboard cross-examining congressional trade disclosures (STOCK Act PTR) against Point-in-Time fundamental filings, alternative text sentiment (FinBERT), and unadjusted market price actions.



\## 📌 Executive Summary

\* \*\*Point-in-Time (PIT) Surveillance\*\*: Decouples execution dates, filing signatures, and official public access to eliminate look-ahead bias.

\* \*\*Alternative Text-as-Signal\*\*: Applies ProsusAI/finbert token chunking across corporate disclosures to extract managerial tone alongside empirical market movements.

\* \*\*Compliance \& Asset Fidelity\*\*: Distinguishes cash equity positions from derivative structures; requires explicit buy/sell matching rather than heuristic assumptions.



\---



\## 🚀 Quick Start



\### 1. Installation

git clone https://github.com/YOUR\_USERNAME/congress-quant-trinity.git

cd congress-quant-trinity

pip install -r requirements.txt



\### 2. Run Application

streamlit run app.py



\---



\## 🛠️ Tech Stack

\* \*\*Framework\*\*: Streamlit, Plotly

\* \*\*Data Sources\*\*: yfinance, SEC EDGAR, Official PTR Filings

\* \*\*Modeling\*\*: PyTorch, HuggingFace Transformers (ProsusAI/finbert)

