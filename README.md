# 👠 Is Nancy A Good Girl? (Trinity Quant Auditor)

> *"We are a free market economy. They should be able to participate in that."*  
> — Nancy, definitely not trading on inside info (probably)

An auditable, zero-BS quantitative surveillance dashboard designed to answer the multi-million-dollar question: **Is Nancy actually an omniscient Capitol Hill trading deity, or is Paul just buying calls at the top like the rest of r/wallstreetbets?**

---

## 🧐 What Is This?

Everyone on Twitter/X screams that Congress beats the market with god-tier insider alpha. But being skeptical PMs, we don't buy vibes, Twitter memes, or AI hallucinations. We want raw receipts, unadjusted prices, and cold, hard timestamps.

This dashboard cross-examines:
1. **Official STOCK Act PTR Filings** (Clerk of the House PDFs — no fabricated execution dates).
2. **Point-in-Time Corporate Reality** (10-Q/10-K filings using `FinBERT` to detect corporate hedging and sweaty executive safe-harbor talk).
3. **Unadjusted As-Traded Price Realities** (via `yfinance` with split adjustments intact).

All wrapped in an interactive, auditable Streamlit workbench.

---

## 🚨 Spoiler Alert: The 2024 NVDA Verdict

Did Nancy (sorry, Paul) execute the trade of the century on June 26, 2024 (10,000 NVDA shares)?

* **The Timing**: Bought right into the local cyclical peak (~$125).
* **The Immediate Reward**: A brutal ~20% drawdown through early August 2024.
* **The Residual Alpha**: After netting out the S&P 500 (SPY) beta, the cumulative abnormal return (CAR) over the statutory disclosure lag was... practically **zero** ($p > 0.05$).

**Conclusion**: *In the matter of NVDA (Summer 2024), we fail to reject the null hypothesis ($H_0$). Turns out, even Congress can hold bags.* 🛍️

---

## 🛡️ Anti-BS Compliance Rules (Because We Have Standards)

* ⏰ **Three-Clock Isolation**: We strictly decouple Trade Date ($T_{\text{trade}}$), Filing Date ($T_{\text{filing}}$), and Verified Public Date ($T_{\text{public}}$). If you're backtesting using the filing date as the trade date, you're not doing quant — you're doing time travel.
* 🛑 **No Option Shenanigans**: Options are not spot shares. Missing strike/expiry/premium? We display discrete event markers rather than hallucinating synthetic equity curves.
* 🤖 **No Hallucinated "Insider Scores"**: FinBERT evaluates sentiment and hedging language from actual managerial call transcripts using non-overlapping token chunking. No "magic insider probabilities."
* 🔗 **Receipts Included**: Every transaction and filing maps directly back to official SEC EDGAR dossiers and House Clerk scanned PDFs.

---

## 🚀 Quick Start (For Skeptics & Degens)

### 1. Clone the receipts
git clone https://github.com/YOUR_USERNAME/is-nancy-a-good-girl.git
cd is-nancy-a-good-girl
pip install -r requirements.txt

### 2. Summon the Auditor
streamlit run app.py

---

## 🛠️ Tech Stack

* **Front-End / UI**: Streamlit & Plotly (Dark mode by default, because bright screens are for accountants).
* **Data Pipelines**: `yfinance` (pure unadjusted close prices), Beautiful Soup 4, SEC EDGAR CIK Routing.
* **Deep Learning Engine**: PyTorch + HuggingFace Transformers (`ProsusAI/finbert`).
* **Snark**: 100% organic, locally sourced.

---

*Disclaimer: Not financial advice. Not legal advice. If the SEC or Capitol Ethics Committee is reading this, this is pure academic satire backed by your own public PDFs.*
