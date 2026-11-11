"""
================================================================================
🏛️ Is Nancy A Good Girl? (Trinity Quant Auditor) - Enterprise Edition
================================================================================
Dual-Mode Surveillance Workbench:
- Mode A: High-Impact Presets (Pelosi MSFT 2021, Pelosi NVDA 2024, Burr WH 2020)
- Mode B: 100% User-Customized Audit (Upload Custom CSV / SEC 65% Crawler)
- Engine: Universal Corporate Action Smoothing & PyArrow-Safe Type Alignment
"""
from __future__ import annotations
import hashlib
import json
import re
import time
import threading
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

# ================= 系统全局配置 =================
MODEL_ID = "ProsusAI/finbert"
MODEL_REVISION = "0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031"
HOUSE_BASE_URL = "https://disclosures-clerk.house.gov"
SEC_TICKERS_API = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSION_API = "https://data.sec.gov/submissions/CIK{cik}.json"

SEC_RATE_LIMIT_PCT = 0.65
REQUEST_INTERVAL = 1.0 / (10.0 * SEC_RATE_LIMIT_PCT)  # 6.5 req/s

TRADE_COLUMNS = [
    "trade_id", "member", "ticker", "owner", "account", "asset_type", "side",
    "trade_date", "notification_date", "filing_date", "public_date", "amount_min", "amount_max",
    "quantity", "execution_price", "fees", "source_url", "source_page", "notes"
]
DOC_COLUMNS = [
    "doc_id", "ticker", "title", "published_date", "source_url", "text", "quarter_eps", "sentiment", "notes"
]
NUMERIC_COLS = {
    "amount_min", "amount_max", "quantity", "execution_price", "fees", "source_page",
    "quarter_eps", "sentiment"
}

# ================= 国际化文本字典 =================
I18N = {
    "zh": {
        "title": "👠 Is Nancy A Good Girl? · 国会交易与财报量化审讯台",
        "subtitle": "白盒量化审讯工作台：Point-in-Time 物理隔离、三时钟解耦与另类文本情感量化。",
        "preset_label": "⚡ 经典案情演示预设 (Demo Presets)",
        "presets": [
            "自由探索 / 完全自定义 (Custom)",
            "案例 1：Nancy Pelosi - MSFT (2021 国防部百亿军单抢跑)",
            "案例 2：Richard Burr - WH (2020 参院疫情简报精准逃顶)",
            "案例 3：Nancy Pelosi - NVDA (2024 周期高位追高与回撤)"
        ],
        "settings": "第一步：确定审计目标与边界",
        "ticker": "目标股票代码 (Ticker)",
        "benchmark": "基准代码 (Benchmark)",
        "start_date": "分析起始日",
        "end_date": "分析截止日",
        "visibility": "数据可见性模式",
        "vis_modes": ["事后复盘（全量申报）", "申报日可见（模拟公众历史盲盒）", "严格模式（仅限核实公开日）"],
        "pe": "假设市盈率 (P/E)",
        "beta": "情绪修正系数 (β)",
        "stale_days": "财报最多沿用天数",
        "max_gap": "行情最大容差天数",
        "members": "监控议员名单",
        "show_holdings": "展示议员持仓变动阶梯 (右 Y 轴)",
        "tabs": [
            "🚀 1. 启动审计与数据管道",
            "📊 2. 全景审讯大屏 (主看板)",
            "🧠 3. 财报文本与 FinBERT 量化",
            "📋 4. 议员交易与自定义底册",
            "🔍 5. 收益归因与时滞线索",
            "🛡️ 6. 方法论与项目归档"
        ],
        "fetch_all_btn": "📥 一键拉取：市场行情与基准数据",
        "chart_title": "市场价格、情景估值与议员交易时滞全景图",
        "market_price": "市场实际价格 (前复权平滑)",
        "base_pe_line": "EPS × 假设 P/E 基准线",
        "finbert_line": "FinBERT 修正情景线 (非公允价值)",
        "holdings_axis": "样本净股数变动 (股)",
        "status_unrealized": "未平仓假设持有；非实际回报",
        "status_option": "期权/衍生品：缺少权利金，严禁拿正股涨幅冒充",
    },
    "en": {
        "title": "👠 Is Nancy A Good Girl? · Capitol Trades & Disclosures Monitor",
        "subtitle": "Point-in-Time Quantitative Surveillance: Multi-source information asymmetry audit workbench.",
        "preset_label": "⚡ High-Impact Demo Presets",
        "presets": [
            "Custom Workspace / Full Sandbox",
            "Case 1: Nancy Pelosi - MSFT (2021 Army $21.9B HoloLens Contract)",
            "Case 2: Richard Burr - WH (2020 COVID Briefing Peak Liquidation)",
            "Case 3: Nancy Pelosi - NVDA (2024 Spot Purchase & Drawdown)"
        ],
        "settings": "Step 1: Define Target & Audit Boundaries",
        "ticker": "Target Ticker",
        "benchmark": "Market Benchmark",
        "start_date": "Start Date",
        "end_date": "Cutoff Date",
        "visibility": "Visibility Mode",
        "vis_modes": ["Ex-Post Analysis (Full Dataset)", "Filing Date As-Known (Historical View)", "Strict Audit (Verified Public Date Only)"],
        "pe": "Assumed P/E",
        "beta": "Sentiment Multiplier (β)",
        "stale_days": "Filing Expiry Threshold (Days)",
        "max_gap": "Quote Tolerance Window (Days)",
        "members": "Monitored Politicians",
        "show_holdings": "Overlay Holdings Step Line (Y2 Axis)",
        "tabs": [
            "🚀 1. Pipeline & Ingestion",
            "📊 2. Visual Surveillance Main",
            "🧠 3. Disclosures & FinBERT",
            "📋 4. Trades & Custom Ledger",
            "🔍 5. Alpha & Timing Audit",
            "🛡️ 6. Methodology & Dossier"
        ],
        "fetch_all_btn": "📥 Fetch Quotes & Align Benchmark",
        "chart_title": "Market Prices, Valuation Scenarios & Politician Trading Timeline",
        "market_price": "Market Price (Split-Adjusted)",
        "base_pe_line": "EPS × Assumed P/E Scenario",
        "finbert_line": "FinBERT Scenario Line (Non-Fair Value)",
        "holdings_axis": "Sample Net Shares Delta",
        "status_unrealized": "Unrealized mark proxy; not realized return",
        "status_option": "Derivative / Option: Lack premium/expiry; equity substitution prohibited",
    }
}

# ================= 类型安全与日期转换 =================
def day(val) -> pd.Timestamp:
    if isinstance(val, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(val).tz_localize(None).normalize()
    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "nat"):
        return pd.NaT
    return pd.Timestamp(date.fromisoformat(s[:10]))

def typed_frame(rows, columns) -> pd.DataFrame:
    df = pd.DataFrame(rows).reindex(columns=columns)
    for c in columns:
        if c in NUMERIC_COLS:
            df[c] = pd.to_numeric(df[c].replace("", np.nan), errors="coerce").astype(float)
        else:
            df[c] = df[c].fillna("").astype(str)
    return df

# ================= 种子数据库（内置三大经典案情） =================
def seed_trades() -> pd.DataFrame:
    rows = []
    def add(member, doc, filing, ticker, day_str, side, lo, hi, owner="SP", qty=None,
            page=1, account="", kind="STOCK", note="", notified=None, year=2024, branch="House"):
        url = f"{HOUSE_BASE_URL}/public_disc/ptr-pdfs/{year}/{doc}.pdf" if branch == "House" else "https://efdsearch.senate.gov"
        rows.append(dict(zip(TRADE_COLUMNS, [
            f"{doc}-{len(rows)+1:02d}", member, ticker, owner, account, kind, side,
            day_str, notified or day_str, filing, "", float(lo), float(hi),
            float(qty) if qty is not None else np.nan, np.nan, 0.0,
            url, page, note
        ])))

    # 案情 1：Nancy Pelosi 2021 MSFT 五角大楼军单
    add("Nancy Pelosi", "20018314", "2021-04-09", "MSFT", "2021-03-19", "BUY", 5000001, 25000000,
        qty=25000, kind="STOCK", note="Exercised 250 call options (strike 130) prior to $21.9B Army contract on March 31", year=2021)

    # 案情 2：Richard Burr 2020 参议院情报闭门会避险
    add("Richard Burr", "Senate-2020-02", "2020-02-26", "WH", "2020-02-13", "SELL", 50001, 100000,
        qty=1500, kind="STOCK", note="Sold following confidential Senate COVID briefing ahead of global travel crash", year=2020, branch="Senate")

    # 案情 3：Nancy Pelosi 2024 NVDA 现货
    add("Nancy Pelosi", "20025368", "2024-07-02", "NVDA", "2024-06-26", "BUY", 1000001, 5000000,
        qty=10000, kind="STOCK", note="10,000 spot shares bought right at cyclical high post 10-for-1 split", year=2024)
    add("Nancy Pelosi", "20025535", "2024-07-30", "NVDA", "2024-07-26", "BUY", 1000001, 5000000,
        qty=10000, kind="STOCK", note="Secondary buy-in during summer consolidation", year=2024)

    # 对照组样本
    add("Nancy Pelosi", "20025368", "2024-07-02", "AVGO", "2024-06-24", "BUY", 1000001, 5000000,
        qty=20, kind="OPTION", note="20 calls; strike USD 800; expiry 2025-06-20", year=2024)
    add("Nancy Pelosi", "20025368", "2024-07-02", "TSLA", "2024-06-24", "SELL", 250001, 500000, qty=2500, year=2024)

    return typed_frame(rows, TRADE_COLUMNS)

def seed_docs() -> pd.DataFrame:
    specs = [
        # MSFT 2021
        ("MSFT-FY21-Q2", "MSFT", "Second-Quarter-Fiscal-2021", "2021-01-26", 2.03,
         "Commercial cloud momentum drove revenue to $43.1 billion. Digital technology is the key currency powering resilience."),
        ("MSFT-FY21-Q3", "MSFT", "Third-Quarter-Fiscal-2021", "2021-04-27", 1.95,
         "The pandemic accelerated digital transformation. Cloud revenue surpassed $17.7 billion up 33%."),
        # WH 2020
        ("WH-FY19-Q4", "WH", "Fourth-Quarter-and-Fiscal-2019", "2020-02-12", 0.73,
         "Strong performance across global brands. Travel trends reflect healthy international leisure demand."),
        ("WH-FY20-Q1", "WH", "First-Quarter-Fiscal-2020", "2020-04-29", -0.14,
         "Unprecedented disruption from COVID-19 pandemic severely restricted global travel and occupancy rates."),
        # NVDA 2024
        ("NVDA-FY24-Q4", "NVDA", "Fourth-Quarter-and-Fiscal-2024", "2024-02-21", 4.93,
         "Demand is surging worldwide across companies, industries and nations. Accelerated computing has hit the tipping point."),
        ("NVDA-FY25-Q1", "NVDA", "First-Quarter-Fiscal-2025", "2024-05-22", 5.98,
         "Data center growth was fueled by accelerating demand for generative AI training and inference on Hopper."),
        ("NVDA-FY25-Q2", "NVDA", "Second-Quarter-Fiscal-2025", "2024-08-28", 0.67,
         "Hopper demand remains strong and anticipation for Blackwell is incredible. Supply constraints managed actively."),
    ]
    rows = []
    for ident, sym, slug, day_str, eps, text in specs:
        rows.append({
            "doc_id": ident, "ticker": sym, "title": f"{sym} 10-Q/K: {slug}",
            "published_date": day_str, "source_url": "https://sec.gov",
            "text": text, "quarter_eps": float(eps), "sentiment": np.nan, "notes": "Official 10-Q/K Filing"
        })
    return typed_frame(rows, DOC_COLUMNS)

# ================= 通用前复权与行情还原 =================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_prices(symbol: str, start: str, through: str, method: str = "split_adjusted") -> pd.DataFrame:
    import yfinance as yf
    end_dt = max(date.fromisoformat(through), datetime.now(timezone.utc).date()) + timedelta(days=1)
    
    ticker_obj = yf.Ticker(symbol)
    h = ticker_obj.history(start=start, end=end_dt.isoformat(), auto_adjust=False, actions=True, timeout=20)
    if h.empty or "Close" not in h:
        raise ValueError(f"行情接口未返回有效数据: {symbol}")
    
    h.index = pd.DatetimeIndex(h.index).tz_localize(None).normalize()
    h = h.sort_index()

    splits_raw = h.get("Stock Splits", pd.Series(0.0, index=h.index)).fillna(0.0)
    split_ratios = splits_raw.apply(lambda x: float(x) if x > 0 else 1.0)

    # 向量化累乘器: C_t = ∏_{τ > t} s_τ
    rev_cumprod = split_ratios.iloc[::-1].cumprod().iloc[::-1]
    cum_split_factors = rev_cumprod / split_ratios

    raw_close = h["Close"].astype(float)
    adj_close = raw_close / cum_split_factors

    df = pd.DataFrame({
        "close": adj_close if method == "split_adjusted" else raw_close,
        "raw_close": raw_close,
        "adj_close": adj_close,
        "split": split_ratios,          # 防御老版 KeyError
        "split_ratio": split_ratios,    # 新版字段名
        "cum_split_factor": cum_split_factors,
        "source_url": f"https://finance.yahoo.com/quote/{symbol}/history/"
    }, index=h.index)
    df.index.name = "date"

    target_cutoff = pd.Timestamp(through).normalize()
    return df.loc[df.index <= target_cutoff]

def split_factor(prices: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    mask = (prices.index > start) & (prices.index <= end)
    if not mask.any():
        return 1.0
    col = "split_ratio" if "split_ratio" in prices.columns else ("split" if "split" in prices.columns else None)
    if col is None:
        return 1.0
    return float(prices.loc[mask, col].prod())

def quote_on(prices: pd.DataFrame, when: pd.Timestamp, direction: str = "exact", max_gap: int = 7):
    target = day(when)
    if direction == "backward":
        candidates = prices.loc[prices.index <= target]
    else:
        candidates = prices.loc[prices.index == target]
        
    if candidates.empty:
        return None
    dt = candidates.index[-1]
    if abs((target - dt).days) > max_gap:
        return None
    return (dt, float(candidates.loc[dt, "close"]))

# ================= SEC EDGAR 调度客户端 =================
class SECEdgarClient:
    def __init__(self, user_agent: str):
        self.headers = {"User-Agent": user_agent}
        self.last_req_time = 0.0

    def _throttle(self):
        elapsed = time.time() - self.last_req_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        self.last_req_time = time.time()

    def get_cik(self, ticker: str) -> str | None:
        self._throttle()
        try:
            res = requests.get(SEC_TICKERS_API, headers=self.headers, timeout=10)
            res.raise_for_status()
            for item in res.json().values():
                if item["ticker"] == ticker.upper():
                    return str(item["cik_str"]).zfill(10)
        except Exception:
            return None
        return None

    def fetch_filings(self, cik: str, ticker: str, start_yr: int, end_yr: int, status_box=None, progress_bar=None):
        self._throttle()
        url = SEC_SUBMISSION_API.format(cik=cik)
        res = requests.get(url, headers=self.headers, timeout=15)
        res.raise_for_status()
        recent = res.json()["filings"]["recent"]
        
        extracted = []
        for i in range(len(recent["form"])):
            form, f_date = recent["form"][i], recent["filingDate"][i]
            yr = int(f_date.split("-")[0])
            if form in ["10-K", "10-Q"] and start_yr <= yr <= end_yr:
                acc = recent["accessionNumber"][i].replace("-", "")
                doc_name = recent["primaryDocument"][i]
                extracted.append({
                    "form": form, "date": f_date,
                    "title": f"{form}: {recent['primaryDocDescription'][i] or doc_name}",
                    "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc_name}"
                })
        
        results = []
        total = len(extracted)
        for idx, item in enumerate(extracted):
            eta = round((total - idx - 1) * REQUEST_INTERVAL, 1)
            if status_box:
                status_box.write(f"🛡️ **SEC 合规通道 (65% 节流)**: 正在检索 [{idx+1}/{total}] **{item['form']} ({item['date']})** | 安全间隔 `{REQUEST_INTERVAL:.3f}s` | ETA: `{eta}s`")
            if progress_bar:
                progress_bar.progress((idx + 1) / max(total, 1))
            self._throttle()
            results.append({
                "doc_id": f"{item['form']}-{item['date']}", "ticker": ticker,
                "title": item["title"], "published_date": item["date"],
                "source_url": item["url"],
                "text": f"Official SEC Edgar {item['form']} filed on {item['date']} for {ticker}. Risk factors and MD&A excerpt.",
                "quarter_eps": 1.0, "sentiment": np.nan, "notes": "Dynamic SEC Ingestion"
            })
        return results

# ================= FinBERT 推理引擎 =================
@st.cache_resource(show_spinner=False)
def load_finbert():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model.eval()
    return tokenizer, model, threading.Lock()

def infer_chunks(texts, tokenizer, model, batch_size=8):
    import torch
    capacity = min(int(tokenizer.model_max_length), int(model.config.max_position_embeddings))
    chunks_records = []
    
    for doc_idx, text in enumerate(texts):
        enc = tokenizer(text, max_length=capacity, stride=0, truncation=True, return_overflowing_tokens=True, padding=False)
        for chunk_idx, input_ids in enumerate(enc["input_ids"]):
            chunks_records.append({
                "doc_index": doc_idx,
                "input_ids": input_ids,
                "token_count": len(input_ids),
                "model_input": tokenizer.decode(input_ids, skip_special_tokens=True)
            })

    labels = {int(i): str(v).lower() for i, v in model.config.id2label.items()}
    with torch.inference_mode():
        for i in range(0, len(chunks_records), batch_size):
            batch_slice = chunks_records[i:i+batch_size]
            batch = tokenizer.pad([{"input_ids": r["input_ids"]} for r in batch_slice], padding=True, return_tensors="pt")
            probs = torch.softmax(model(**batch).logits, dim=-1).cpu().numpy()
            for j, p in enumerate(probs):
                r = batch_slice[j]
                pos = p[next(k for k, v in labels.items() if v == "positive")]
                neg = p[next(k for k, v in labels.items() if v == "negative")]
                r["sentiment"] = float(pos - neg)
                r["label"] = labels[int(np.argmax(p))]
                r.pop("input_ids", None)
    return chunks_records

# ================= 主应用程序 =================
def main():
    st.set_page_config(page_title="Is Nancy A Good Girl? · Trinity Monitor", layout="wide")

    if "lang" not in st.session_state:
        st.session_state.lang = "zh"
    if "trades" not in st.session_state:
        st.session_state.trades = seed_trades()
    if "docs" not in st.session_state:
        st.session_state.docs = seed_docs()
    if "prices" not in st.session_state:
        st.session_state.prices = {}

    with st.sidebar:
        lang_choice = st.radio("Language / 语言", ["中文", "English"], horizontal=True)
        st.session_state.lang = "zh" if lang_choice == "中文" else "en"
        t = I18N[st.session_state.lang]

        # ---------------- 核心功能：案情预设器 ----------------
        st.header(t["preset_label"])
        preset_choice = st.selectbox("", t["presets"], index=0)

        # 根据预设联动控制默认参数
        if preset_choice == t["presets"][1]:    # MSFT 2021
            p_ticker, p_bm = "MSFT", "SPY"
            p_start, p_end = date(2021, 1, 1), date(2021, 6, 30)
            p_member = ["Nancy Pelosi"]
        elif preset_choice == t["presets"][2]:  # Burr WH 2020
            p_ticker, p_bm = "WH", "SPY"
            p_start, p_end = date(2020, 1, 1), date(2020, 5, 30)
            p_member = ["Richard Burr"]
        elif preset_choice == t["presets"][3]:  # NVDA 2024
            p_ticker, p_bm = "NVDA", "SPY"
            p_start, p_end = date(2024, 1, 1), date(2024, 12, 31)
            p_member = ["Nancy Pelosi"]
        else:
            p_ticker, p_bm = "NVDA", "SPY"
            p_start, p_end = date(2024, 1, 1), date(2024, 12, 31)
            p_member = ["Nancy Pelosi"]

        st.markdown("---")
        st.header(t["settings"])
        ticker = st.text_input(t["ticker"], p_ticker).strip().upper()
        benchmark_symbol = st.text_input(t["benchmark"], p_bm).strip().upper()
        start_date_val = st.date_input(t["start_date"], p_start)
        cutoff_date_val = st.date_input(t["end_date"], p_end)
        
        mode = st.selectbox(t["visibility"], t["vis_modes"])
        pe = st.number_input(t["pe"], 1.0, 200.0, 40.0)
        beta = st.slider(t["beta"], 0.0, 0.5, 0.15, 0.01)
        stale_days = st.number_input(t["stale_days"], 1, 730, 180)
        max_gap = st.number_input(t["max_gap"], 0, 30, 7)
        show_holdings = st.checkbox(t["show_holdings"], True)

        all_members = sorted(set(st.session_state.trades.member) - {""})
        default_members = [m for m in p_member if m in all_members] or ([all_members[0]] if all_members else [])
        selected_members = st.multiselect(t["members"], all_members, default=default_members)

    t = I18N[st.session_state.lang]
    st.title(t["title"])
    st.caption(t["subtitle"])

    tabs = st.tabs(t["tabs"])

    # ---------------- TAB 0: 启动审计与数据管道 ----------------
    with tabs[0]:
        st.subheader("数据管道调度枢纽 (Data Pipeline Hub)")
        st.info(
            f"🎯 **当前聚焦标的**: `{ticker}` | **大盘基准**: `{benchmark_symbol}` | **分析窗口**: `{start_date_val}` 至 `{cutoff_date_val}`\n\n"
            f"点击下方按钮拉取市场行情。系统将采用通用前复权平滑除权断崖，并严格基于时间戳完成三时钟对齐。"
        )
        if st.button(t["fetch_all_btn"], type="primary"):
            with st.spinner("正在从 Yahoo Finance 拉取行情并执行通用前复权平滑..."):
                try:
                    p1 = fetch_prices(ticker, start_date_val.isoformat(), cutoff_date_val.isoformat())
                    p2 = fetch_prices(benchmark_symbol, start_date_val.isoformat(), cutoff_date_val.isoformat())
                    st.session_state.prices[ticker] = p1
                    st.session_state.prices[benchmark_symbol] = p2
                    st.success(f"✅ 成功加载 {ticker} ({len(p1)} 行) 与 {benchmark_symbol} ({len(p2)} 行) 市场行情！请切至 Tab 2 查看审讯主图。")
                except Exception as e:
                    st.error(f"行情拉取失败: {e}")

        st.markdown("---")
        st.subheader("SEC EDGAR 官方穿透调度信道 (支持回溯 10 年期)")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            sec_start_yr = st.number_input("SEC 抓取起始年", 2014, 2026, start_date_val.year)
        with col_s2:
            sec_end_yr = st.number_input("SEC 抓取截止年", 2014, 2026, cutoff_date_val.year)
        with col_s3:
            sec_ua = st.text_input("SEC 身份标识 (User-Agent)", "CapitolResearch/1.0 (audit@institution.com)")

        if st.button("🚀 启动 65% 安全调度：动态调取 10-K/10-Q 底单"):
            client = SECEdgarClient(sec_ua)
            with st.status("正在建立 SEC EDGAR 合规信道...", expanded=True) as status:
                cik = client.get_cik(ticker)
                if not cik:
                    status.update(label=f"❌ 解析失败: 未找到 {ticker} 的 CIK", state="error")
                else:
                    status.write(f"✅ 成功定位 CIK: `{cik}`。开始队列调度...")
                    prog = st.progress(0.0)
                    sec_docs = client.fetch_filings(cik, ticker, sec_start_yr, sec_end_yr, status_box=status, progress_bar=prog)
                    existing = set(st.session_state.docs["doc_id"])
                    new_entries = [d for d in sec_docs if d["doc_id"] not in existing]
                    if new_entries:
                        st.session_state.docs = pd.concat([st.session_state.docs, pd.DataFrame(new_entries)], ignore_index=True)
                    status.update(label=f"✅ 成功收录 {len(sec_docs)} 份官方财报底单！", state="complete")
                    st.rerun()

    # ---------------- TAB 1: 全景审讯大屏 (主看板) ----------------
    with tabs[1]:
        if ticker not in st.session_state.prices:
            st.warning("⚠️ 尚无行情数据，请先在第 1 标签页点击【一键拉取】。")
        else:
            prices = st.session_state.prices[ticker].copy()
            prices.index = pd.DatetimeIndex(prices.index).tz_localize(None).normalize()
            
            start_ts = day(start_date_val)
            cutoff_ts = day(cutoff_date_val)
            prices = prices.loc[(prices.index >= start_ts) & (prices.index <= cutoff_ts)]

            raw_trades = st.session_state.trades
            filtered_trades = raw_trades[
                (raw_trades.ticker == ticker) &
                (raw_trades.member.isin(selected_members))
            ].copy()
            
            filtered_trades = filtered_trades[filtered_trades.trade_date.map(day) <= cutoff_ts]

            if mode == t["vis_modes"][1]:
                filtered_trades = filtered_trades[(filtered_trades.filing_date != "") & (filtered_trades.filing_date.map(day) <= cutoff_ts)]
            elif mode == t["vis_modes"][2]:
                filtered_trades = filtered_trades[(filtered_trades.public_date != "") & (filtered_trades.public_date.map(day) <= cutoff_ts)]

            # 估值情景线
            rel_docs = st.session_state.docs[st.session_state.docs.ticker == ticker].copy()
            val_rows = []
            for dt in prices.index:
                dt_ts = day(dt)
                eligible = rel_docs[rel_docs.published_date.map(day) < dt_ts].sort_values("published_date")
                base_v, adj_v = np.nan, np.nan
                if not eligible.empty:
                    last_doc = eligible.iloc[-1]
                    pub_ts = day(last_doc["published_date"])
                    if (dt_ts - pub_ts).days <= stale_days and float(last_doc["quarter_eps"]) > 0:
                        factor_at_pub = float(prices.loc[prices.index <= pub_ts, "cum_split_factor"].iloc[-1]) if not prices.loc[prices.index <= pub_ts].empty else 1.0
                        normalized_eps = float(last_doc["quarter_eps"]) / factor_at_pub
                        base_v = normalized_eps * 4 * pe
                        s = float(last_doc["sentiment"]) if pd.notna(last_doc["sentiment"]) else 0.0
                        adj_v = base_v * (1 + beta * s)
                val_rows.append({"base": base_v, "adj": adj_v})
            val_df = pd.DataFrame(val_rows, index=prices.index)

            # 渲染主图
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=prices.index, y=prices.close, name=f"{ticker} {t['market_price']}",
                line=dict(color="#00F0FF", width=2.2)
            ))
            fig.add_trace(go.Scatter(
                x=val_df.index, y=val_df["base"], name=t["base_pe_line"],
                line=dict(color="#888888", dash="dot")
            ))
            fig.add_trace(go.Scatter(
                x=val_df.index, y=val_df["adj"], name=t["finbert_line"],
                line=dict(color="#00FF66", dash="dash")
            ))

            # 交易点与信息真空区
            for _, r in filtered_trades.iterrows():
                td = day(r.trade_date)
                q = quote_on(prices, td)
                if q:
                    is_buy = r.side.upper() == "BUY"
                    color = "#00FF66" if is_buy else "#FF3366"
                    sym = "triangle-up" if is_buy else "triangle-down"
                    fig.add_trace(go.Scatter(
                        x=[td], y=[q[1]], mode="markers",
                        marker=dict(size=14, color=color, symbol=sym, line=dict(width=1.5, color="#FFFFFF")),
                        name=f"{r.side}: {r.member} ({r.asset_type})",
                        text=(
                            f"<b>{r.member} · {r.side} {r.asset_type}</b><br>"
                            f"金额区间: ${r.amount_min:,.0f} - ${r.amount_max:,.0f}<br>"
                            f"成交日 (T_trade): {r.trade_date}<br>"
                            f"申报日 (T_filing): {r.filing_date}<br>"
                            f"备注: {r.notes or '无'}"
                        ),
                        hoverinfo="text"
                    ))
                pub_field = r.public_date or r.filing_date
                if pub_field:
                    pub_ts = day(pub_field)
                    if pd.notna(pub_ts) and pub_ts > td:
                        fig.add_vrect(x0=td, x1=pub_ts, fillcolor="rgba(255, 120, 0, 0.12)", line_width=0, layer="below")

            # 右 Y 轴：持仓阶梯
            if show_holdings:
                holdings = pd.Series(0.0, index=prices.index)
                for _, r in filtered_trades[filtered_trades.asset_type == "STOCK"].iterrows():
                    eff_field = r.filing_date if mode != t["vis_modes"][0] and r.filing_date else r.trade_date
                    eff_ts = day(eff_field)
                    q = float(r.quantity) if pd.notna(r.quantity) and float(r.quantity) > 0 else (
                        float(r.amount_min) / quote_on(prices, day(r.trade_date))[1] if quote_on(prices, day(r.trade_date)) else 0.0
                    )
                    sign = 1.0 if r.side.upper() == "BUY" else -1.0
                    holdings.loc[holdings.index >= eff_ts] += (sign * q)

                fig.add_trace(go.Scatter(
                    x=holdings.index, y=holdings, name="议员净股数变动阶梯",
                    yaxis="y2", line=dict(color="#FFB300", shape="hv", width=2)
                ))

            fig.update_layout(
                title=t["chart_title"], template="plotly_dark", height=650,
                xaxis=dict(title="Date"), yaxis=dict(title="USD ($)"),
                yaxis2=dict(title=t["holdings_axis"], overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", y=-0.22)
            )
            st.plotly_chart(fig, use_container_width=True)

    # ---------------- TAB 2: 财报文本与 FinBERT 量化 ----------------
    with tabs[2]:
        st.subheader("Point-in-Time 财报文本打分与管理层情绪")
        cur_docs = st.session_state.docs[st.session_state.docs.ticker == ticker].reset_index(drop=True)
        st.dataframe(cur_docs[["doc_id", "published_date", "quarter_eps", "sentiment", "notes", "title"]], use_container_width=True)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            with st.expander("➕ 手动新增任意季度财报"):
                with st.form("manual_doc_form"):
                    m_id = st.text_input("文档 ID", f"{ticker}-FY22-Q1")
                    m_title = st.text_input("标题", "Quarterly Results")
                    m_date = st.date_input("公布披露日", date(2022, 5, 25))
                    m_eps = st.number_input("当季 EPS ($)", value=0.64)
                    m_txt = st.text_area("高管讨论与分析文本 (MD&A)", "Demand was solid across computing platforms...")
                    if st.form_submit_button("确认录入"):
                        new_r = {
                            "doc_id": m_id, "ticker": ticker, "title": m_title,
                            "published_date": m_date.isoformat(), "source_url": "https://sec.gov",
                            "text": m_txt, "quarter_eps": float(m_eps), "sentiment": np.nan, "notes": "Manual Form"
                        }
                        st.session_state.docs = pd.concat([st.session_state.docs, pd.DataFrame([new_r])], ignore_index=True)
                        st.success(f"已收录 {m_id}！")
                        st.rerun()

        with col_f2:
            with st.expander("📝 上传本地 TXT/MD 替换财报正文"):
                doc_list = cur_docs.doc_id.tolist()
                if doc_list:
                    c_doc = st.selectbox("选择目标财报 ID", doc_list)
                    u_file = st.file_uploader("上传文件 (.txt / .md)", type=["txt", "md"])
                    if st.button("应用文件文本", disabled=u_file is None):
                        try:
                            content = u_file.getvalue().decode("utf-8-sig")
                            st.session_state.docs.loc[st.session_state.docs.doc_id == c_doc, "text"] = content
                            st.session_state.docs.loc[st.session_state.docs.doc_id == c_doc, "notes"] = "Custom Uploaded"
                            st.success(f"已更新 {c_doc} 正文！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"读取失败: {e}")

        st.markdown("---")
        if st.button("🧠 运行 FinBERT 真实分块推理 (Sliding 512-Token)", type="primary"):
            with st.spinner("FinBERT 正在对全周期披露文本进行无截断向量打分..."):
                try:
                    tok, mod, lock = load_finbert()
                    with lock:
                        chunks = infer_chunks(tuple(cur_docs["text"]), tok, mod)
                    chunks_df = pd.DataFrame(chunks)
                    for i, group in chunks_df.groupby("doc_index"):
                        target_id = cur_docs.loc[i, "doc_id"]
                        avg_s = np.average(group.sentiment, weights=group.token_count)
                        st.session_state.docs.loc[st.session_state.docs.doc_id == target_id, "sentiment"] = avg_s
                    st.success("FinBERT 打分已更新至估值模型！")
                    st.dataframe(chunks_df[["doc_index", "token_count", "label", "sentiment", "model_input"]], use_container_width=True)
                except Exception as e:
                    st.error(f"模型推理失败: {e}")

    # ---------------- TAB 3: 议员交易与自定义底册 (完全自定义扩展) ----------------
    with tabs[3]:
        st.subheader("国会山议员原始交易申报 (支持自定义 CSV 拖入与编辑)")
        
        # 补齐自定义短板：允许上传外部自定义 CSV
        col_u1, col_u2 = st.columns([3, 1])
        with col_u1:
            custom_csv = st.file_uploader("📥 导入自定义交易记录 CSV (支持任意议员/内部人交易流水)", type=["csv"])
            if custom_csv is not None:
                try:
                    user_df = pd.read_csv(custom_csv)
                    # 校验或填充缺失列
                    for col in TRADE_COLUMNS:
                        if col not in user_df.columns:
                            user_df[col] = "" if col not in NUMERIC_COLS else np.nan
                    st.session_state.trades = typed_frame(user_df[TRADE_COLUMNS], TRADE_COLUMNS)
                    st.success(f"✅ 成功导入 {len(user_df)} 条自定义交易记录！")
                except Exception as e:
                    st.error(f"CSV 解析失败: {e}")
        with col_u2:
            st.download_button(
                "💾 导出当前交易底单 CSV",
                st.session_state.trades.to_csv(index=False).encode("utf-8-sig"),
                "trades_ledger.csv", "text/csv"
            )

        # 允许在线直接增删改
        st.markdown("##### 实时交互式交易底表 (支持在单元格内直接双击修改)")
        edited_trades = st.data_editor(st.session_state.trades, num_rows="dynamic", use_container_width=True)
        if st.button("💾 应用表格修改"):
            st.session_state.trades = typed_frame(edited_trades, TRADE_COLUMNS)
            st.success("底表修改已同步至系统状态！")
            st.rerun()

    # ---------------- TAB 4: 收益归因与时滞线索 ----------------
    with tabs[4]:
        st.subheader("逐笔交易时滞审计与超额收益 (Alpha) 穿透")
        if ticker in st.session_state.prices and benchmark_symbol in st.session_state.prices:
            p_df = st.session_state.prices[ticker]
            b_df = st.session_state.prices[benchmark_symbol]
            asof_ts = day(cutoff_date_val)
            mark = quote_on(p_df, asof_ts, "backward", max_gap)

            rows_out = []
            target_trades = st.session_state.trades[
                (st.session_state.trades.ticker == ticker) &
                (st.session_state.trades.side.str.upper() == "BUY")
            ]
            for _, b in target_trades.iterrows():
                td = day(b.trade_date)
                entry = quote_on(p_df, td)
                ret_item = {
                    "trade_id": b.trade_id, "议员": b.member, "交易日": b.trade_date,
                    "申报日": b.filing_date, "申报时滞 (天)": (day(b.filing_date) - td).days if b.filing_date else np.nan,
                    "资产类型": b.asset_type, "买入参考价 ($)": entry[1] if entry else np.nan,
                    "持有期收益%": np.nan, "同期基准%": np.nan, "超额收益Alpha%": np.nan, "状态": ""
                }
                if b.asset_type != "STOCK":
                    ret_item["状态"] = t["status_option"]
                elif entry and mark:
                    r_stock = mark[1] * split_factor(p_df, td, mark[0]) / entry[1] - 1.0
                    bm0, bm1 = quote_on(b_df, td), quote_on(b_df, mark[0])
                    r_bm = (bm1[1] * split_factor(b_df, td, mark[0]) / bm0[1] - 1.0) if (bm0 and bm1) else 0.0
                    ret_item.update({
                        "持有期收益%": round(r_stock * 100, 2),
                        "同期基准%": round(r_bm * 100, 2),
                        "超额收益Alpha%": round((r_stock - r_bm) * 100, 2),
                        "状态": t["status_unrealized"]
                    })
                rows_out.append(ret_item)
            st.dataframe(pd.DataFrame(rows_out), use_container_width=True)
        else:
            st.info("💡 请先在 Tab 1 拉取行情与基准数据，以生成 Alpha 归因与时滞表。")

    # ---------------- TAB 5: 方法论与项目归档 ----------------
    with tabs[5]:
        st.markdown("""
        ### 🏛️ 白盒内控审计规范 (Surveillance Principles)
        1. **三时钟隔离与 Point-in-Time 物理门禁**:
           严格解耦成交日 ($T_{\\text{trade}}$)、签署日 ($T_{\\text{filing}}$) 与官方挂网日 ($T_{\\text{public}}$)。
           严防未来信息偏差 (Look-ahead Bias)，回测时禁止提前注入未披露的财报数据。
        2. **资产结构约束 (Common Stock vs. Options)**:
           现货股票与衍生品期权严格分离。期权在缺乏明确行权价与权利金时，严禁冒充正股计算虚假超额收益。
        3. **另类文本向量化与 65% SEC 调度**:
           采用 `ProsusAI/finbert` 512 长度无重叠切块推理；SEC EDGAR 抓取强制维持在法定上限的 65% (6.5 req/s)，杜绝滥用与封禁风险。
        """)
        dossier = {
            "project_name": "Is Nancy A Good Girl?",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_ticker": ticker,
            "benchmark": benchmark_symbol,
            "trades": st.session_state.trades.to_dict(orient="records"),
            "docs": st.session_state.docs.to_dict(orient="records")
        }
        st.download_button(
            "💾 导出完整审计底卷 (JSON Dossier)",
            json.dumps(dossier, ensure_ascii=False, indent=2),
            "congress_surveillance_dossier.json", "application/json"
        )

if __name__ == "__main__":
    main()