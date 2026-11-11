"""Auditable Congress transactions dashboard. Run: streamlit run line_segment.py.

Historical samples are incomplete. Blank prices, quantities and public dates
mean unknown; they must never be filled with invented execution data.
"""
from __future__ import annotations
import hashlib
import json
import re
import threading
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import version
from urllib.parse import urlparse
import numpy as np
import pandas as pd
import streamlit as st

MODEL_ID = "ProsusAI/finbert"
MODEL_REVISION = "0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031"
HOUSE = "https://disclosures-clerk.house.gov"
IR = "https://investor.nvidia.com/news/press-release-details/2024/"
TRADE_COLUMNS = ["trade_id", "member", "ticker", "owner", "account", "asset_type", "side",
    "trade_date", "notification_date", "filing_date", "public_date", "amount_min", "amount_max",
    "quantity", "execution_price", "fees", "source_url", "source_page", "notes"]
EXIT_COLUMNS = ["exit_id", "buy_id", "date", "quantity", "execution_price", "fees", "source_url"]
SNAPSHOT_COLUMNS = ["member", "ticker", "owner", "account", "date", "shares", "source_url"]
DOC_COLUMNS = ["doc_id", "ticker", "title", "published_date", "source_url", "locator", "text",
    "quarter_eps", "eps_basis_date", "score_override", "notes"]
PRICE_COLUMNS = ["date", "close", "split", "source_url"]
NUMERIC = {"amount_min", "amount_max", "quantity", "execution_price", "fees", "source_page",
    "shares", "quarter_eps", "score_override", "close", "split"}


def typed_frame(rows, columns):
    df = pd.DataFrame(rows).reindex(columns=columns)
    for c in columns:
        if c in NUMERIC:
            # Preserve malformed numeric text for validation rather than silently replacing it.
            converted = pd.to_numeric(df[c].replace("", np.nan), errors="coerce")
            bad = df[c].notna() & (df[c].astype(str).str.strip() != "") & converted.isna()
            if bad.any():
                raise ValueError(f"{c} 包含非数字内容")
            df[c] = converted.astype(float)
        else:
            df[c] = df[c].fillna("").astype(str)
    return df


def seed_trades():
    """Official PTR rows; filing dates checked against the House annual index.
    IDs are LOCAL row IDs. public_date is intentionally unknown for every seed.
    """
    rows = []
    def add(member, doc, filing, ticker, day, side, lo, hi, owner="SP", qty=None,
            page=1, account="", kind="STOCK", note="", notified=None, year=2024):
        rows.append(dict(zip(TRADE_COLUMNS, [f"{doc}-{len(rows)+1:02d}", member, ticker,
            owner, account, kind, side, day, notified or day, filing, "", lo, hi, qty, None, 0.0,
            f"{HOUSE}/public_disc/ptr-pdfs/{year}/{doc}.pdf", page, note])))
    add("Nancy Pelosi", "20025368", "2024-07-02", "AVGO", "2024-06-24", "BUY", 1000001, 5000000,
        qty=20, kind="OPTION", note="20 calls; strike USD 800; expiry 2025-06-20")
    add("Nancy Pelosi", "20025368", "2024-07-02", "NVDA", "2024-06-26", "BUY", 1000001, 5000000, qty=10000)
    add("Nancy Pelosi", "20025368", "2024-07-02", "TSLA", "2024-06-24", "SELL", 250001, 500000, qty=2500)
    add("Nancy Pelosi", "20025368", "2024-07-02", "V", "2024-07-01", "SELL", 500001, 1000000, qty=2000, note="Partial sale")
    add("Nancy Pelosi", "20025535", "2024-07-30", "MSFT", "2024-07-26", "SELL", 1000001, 5000000, qty=5000, note="Partial sale")
    add("Nancy Pelosi", "20025535", "2024-07-30", "NVDA", "2024-07-26", "BUY", 1000001, 5000000, qty=10000)
    for symbol, pg in [("AEIS", 1), ("AAPL", 2), ("AVGO", 3), ("NVDA", 10)]:
        add("Josh Gottheimer", "20025419", "2024-07-09", symbol,
            "2024-06-27" if symbol == "AEIS" else "2024-06-28", "BUY", 1001, 15000,
            owner="JT", page=pg, account="Morgan Stanley - Select UMA Account # 1", notified="2024-07-08")
    for symbol in ["GOOG", "AMZN", "FDX", "INTC", "KMI", "NVDA"]:
        add("Marjorie Taylor Greene", "20025722", "2024-08-22", symbol, "2024-08-21", "BUY", 1001, 15000,
            owner="SELF", notified="2024-08-22")
    for symbol, day, side, lo, hi in [("AMZN", "2024-11-27", "BUY", 15001, 50000),
            ("AMAT", "2024-11-27", "SELL", 15001, 50000), ("CHD", "2024-11-13", "BUY", 15001, 50000),
            ("REGN", "2024-11-13", "SELL", 15001, 50000), ("REGN", "2024-11-01", "SELL", 1001, 15000)]:
        add("Jonathan Jackson", "20026313", "2024-12-12", symbol, day, side, lo, hi,
            owner="JT", account="Morgan Stanley Trust Account", notified="2024-12-03")
    for symbol in ["BA", "GLW", "CVS", "NVDA"]:
        add("Thomas Suozzi", "20026202", "2024-11-12", symbol, "2024-10-24", "BUY" if symbol == "NVDA" else "SELL",
            15001 if symbol == "NVDA" else 1001, 50000 if symbol == "NVDA" else 15000, owner="SELF",
            account="Merrill Lynch - Advisor Discretion Account - IRA", notified="2024-10-25")
    for day, lo, hi in [("2024-08-07", 250001, 500000), ("2024-10-01", 500001, 1000000)]:
        add("Daniel Meuser", "20030884", "2025-08-13", "NVDA", day, "SELL", lo, hi,
            account="Schwab Brokerage Account", note="Partial sale; 2024 trade filed in 2025", year=2025)
    add("Ro Khanna", "8220252", "2024-05-06", "NVDA", "2024-04-23", "SELL", 1001, 15000,
        page=20, account="SP trust - page 20", notified="2024-05-01", note="Partial sale")
    for symbol, day in [("SYY", "2024-04-04"), ("TXN", "2024-04-15"), ("SBAC", "2024-04-16"),
            ("SBUX", "2024-04-19"), ("SBUX", "2024-04-24"), ("SBUX", "2024-04-25")]:
        add("Ro Khanna", "8220252", "2024-05-06", symbol, day, "BUY", 1001, 15000,
            page=21, account="SURA Ahuja 1995 Trust", notified="2024-05-02")
    for symbol, day, side, lo, hi in [("NVDA", "2024-11-19", "SELL", 250001, 500000),
            ("GPN", "2024-11-06", "BUY", 100001, 250000), ("GPC", "2024-11-19", "BUY", 100001, 250000),
            ("C", "2024-11-19", "BUY", 50001, 100000)]:
        add("Michael McCaul", "8220706", "2024-12-16", symbol, day, side, lo, hi,
            page=5, notified="2024-12-05", note="Scanned p.5; filing date from official 2024 index")
    return typed_frame(rows, TRADE_COLUMNS)


def seed_docs():
    specs = [
        ("NVDA-FY24-Q4", "Fourth-Quarter-and-Fiscal-2024", "2024-02-21", 4.93,
         "Demand is surging worldwide across companies, industries and nations."),
        ("NVDA-FY25-Q1", "First-Quarter-Fiscal-2025", "2024-05-22", 5.98,
         "Our data center growth was fueled by strong and accelerating demand for generative AI training and inference on the Hopper platform."),
        ("NVDA-FY25-Q2", "Second-Quarter-Fiscal-2025", "2024-08-28", .67,
         "Hopper demand remains strong, and the anticipation for Blackwell is incredible,"),
        ("NVDA-FY25-Q3", "Third-Quarter-Fiscal-2025", "2024-11-20", .78,
         "The age of AI is in full steam, propelling a global shift to NVIDIA computing,"),
    ]
    return typed_frame([dict(zip(DOC_COLUMNS, [ident, "NVDA", f"NVIDIA earnings: {slug}", day,
        IR+f"NVIDIA-Announces-Financial-Results-for-{slug}/default.aspx", "CEO remarks; short exact excerpt", text,
        eps, day, None, "仅为简短原文样本，非完整财报；季度 GAAP diluted EPS 来自同一公告。次日才可使用。"
        ])) for ident, slug, day, eps, text in specs], DOC_COLUMNS)


def clean_text(value):
    return "" if pd.isna(value) else str(value).strip()


def valid_url(value):
    try:
        u = urlparse(clean_text(value))
        return u.scheme in {"https", "http"} and bool(u.hostname) and not u.username
    except ValueError:
        return False


def day(value):
    s = clean_text(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise ValueError(f"日期须为 YYYY-MM-DD：{s!r}")
    return pd.Timestamp(date.fromisoformat(s))


def number(value):
    try:
        x = float(value)
        return x if np.isfinite(x) else np.nan
    except (ValueError, TypeError):
        return np.nan


def validate_trades(df):
    errors, seen = [], set()
    for idx, r in df.iterrows():
        try:
            for c in ["trade_id", "member", "ticker", "owner", "asset_type", "side"]:
                if not clean_text(r[c]):
                    raise ValueError(f"{c} 不能为空")
            if r.trade_id in seen:
                raise ValueError("trade_id 重复；请核对重复导入或修订申报")
            seen.add(r.trade_id)
            if not re.fullmatch(r"[A-Z0-9.^=-]{1,20}", r.ticker):
                raise ValueError("ticker 格式错误")
            if r.side not in {"BUY", "SELL"} or r.asset_type not in {"STOCK", "OPTION"}:
                raise ValueError("side 只能 BUY/SELL；asset_type 只能 STOCK/OPTION")
            td = day(r.trade_date)
            for c in ["notification_date", "filing_date", "public_date"]:
                if clean_text(r[c]) and day(r[c]) < td:
                    raise ValueError(f"{c} 早于交易日")
            for c in ["amount_min", "amount_max", "quantity", "execution_price", "fees"]:
                if pd.notna(r[c]) and (not np.isfinite(number(r[c])) or r[c] < 0 or
                        (c in {"quantity", "execution_price"} and r[c] == 0)):
                    raise ValueError(f"{c} 必须为正数（费用可为零）")
            if r.amount_min > r.amount_max:
                raise ValueError("金额上下界倒置")
            if not valid_url(r.source_url):
                raise ValueError("须填写证据 http(s) URL")
        except (ValueError, TypeError) as exc:
            errors.append(f"交易第 {idx+1} 行：{exc}")
    return errors


def validate_docs(df):
    errors, seen = [], set()
    if df.duplicated(["ticker", "published_date"]).any():
        errors.append("同一股票同一发布日期只接受一行财报；请将该报告多个片段合并到 text，避免任意选择估值来源。")
    for idx, r in df.iterrows():
        try:
            if not r.doc_id.strip() or r.doc_id in seen:
                raise ValueError("doc_id 为空或重复")
            seen.add(r.doc_id)
            day(r.published_date)
            day(r.eps_basis_date)
            if day(r.eps_basis_date) > day(r.published_date):
                raise ValueError("EPS 股本日期不能晚于资料发布日期")
            if not valid_url(r.source_url) or not r.ticker.strip() or not r.text.strip():
                raise ValueError("ticker、来源 URL、原文不能为空")
            if len(r.text) > 200000:
                raise ValueError("每份文本最多 200,000 字符，请拆分")
            if pd.notna(r.score_override) and not -1 <= number(r.score_override) <= 1:
                raise ValueError("人工情绪分须介于 -1 和 1")
            if pd.notna(r.quarter_eps) and not np.isfinite(number(r.quarter_eps)):
                raise ValueError("EPS 必须为有限数字")
        except (ValueError, TypeError) as exc:
            errors.append(f"财报第 {idx+1} 行：{exc}")
    return errors


def normalize_prices(df):
    """Canonical close is UNADJUSTED as-traded. split is the ex-date ratio (none=1)."""
    if df.empty:
        return pd.DataFrame(columns=["close", "split", "source_url"], index=pd.DatetimeIndex([], name="date"))
    out = df.copy()
    if not set(PRICE_COLUMNS).issubset(out.columns):
        raise ValueError("行情需 date, close, split, source_url；close 为当日未复权收盘价")
    out["date"] = out.date.map(day)
    if out.date.duplicated().any():
        raise ValueError("行情日期重复")
    for c in ["close", "split"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if not np.isfinite(out[["close", "split"]]).all().all() or (out.close <= 0).any() or (out.split <= 0).any():
        raise ValueError("close 与 split 必须为正数；无拆股日 split=1")
    if not out.source_url.map(valid_url).all():
        raise ValueError("每行行情须填写来源 URL")
    return out.sort_values("date").set_index("date")[["close", "split", "source_url"]]


def yahoo_to_raw(h, symbol):
    h = h.copy().sort_index()
    h.index = pd.DatetimeIndex(h.index).tz_localize(None).normalize()
    splits = h.get("Stock Splits", pd.Series(0., index=h.index)).fillna(0).replace(0, 1).astype(float)
    future = splits.iloc[::-1].cumprod().iloc[::-1] / splits
    return pd.DataFrame({"date": h.index.strftime("%Y-%m-%d"), "close": (h.Close*future).to_numpy(),
        "split": splits.to_numpy(), "source_url": f"https://finance.yahoo.com/quote/{symbol}/history/"})


@st.cache_data(ttl=3600, max_entries=24, show_spinner=False)
def fetch_prices(symbol, start, through):
    import yfinance as yf
    # Fetch to today, not the historical cutoff: Yahoo Close is already adjusted
    # for subsequent splits. Undo all subsequent splits before truncating history.
    end = max(date.fromisoformat(through), datetime.now(timezone.utc).date()) + timedelta(days=1)
    h = yf.Ticker(symbol).history(start=start, end=end.isoformat(), auto_adjust=False,
        actions=True, timeout=20, raise_errors=True)
    if h.empty or "Close" not in h:
        raise ValueError(f"{symbol} 未返回行情；请检查代码/日期或上传 CSV")
    out = yahoo_to_raw(h, symbol)
    return out[out.date <= through].reset_index(drop=True)


def split_factor(prices, start, end):
    return float(prices.loc[(prices.index > pd.Timestamp(start)) & (prices.index <= pd.Timestamp(end)), "split"].prod())


def quote_on(prices, when, direction="exact", max_gap=7):
    target = pd.Timestamp(when)
    candidates = prices.loc[prices.index <= target] if direction == "backward" else prices.loc[prices.index == target]
    if candidates.empty:
        return None
    dt = candidates.index[-1]
    return None if abs((target-dt).days) > max_gap else (dt, float(candidates.loc[dt, "close"]))


def purchase_returns(trades, exits, prices, benchmark, asof, max_gap=7):
    """One row per purchase; explicit buy/sell matching, never inferred FIFO."""
    output, asof = [], pd.Timestamp(asof)
    mark = quote_on(prices, asof, "backward", max_gap)
    for _, b in trades[(trades.side == "BUY") & (trades.trade_date <= asof.date().isoformat())].iterrows():
        td = day(b.trade_date)
        result = {"trade_id": b.trade_id, "议员": b.member, "所有人": b.owner, "交易日": b.trade_date,
            "本金范围下限$": b.amount_min, "本金范围上限$": b.amount_max, "买入参考价$": np.nan,
            "截止参考价$": np.nan, "估值日": "", "参考持有收益%": np.nan, "基准收益%": np.nan,
            "超额收益百分点": np.nan, "已实现净盈利$": np.nan, "已售部分成本收益%": np.nan,
            "已实现盈利占总本金%": np.nan, "出售比例%": np.nan, "状态": "", "source_url": b.source_url}
        if b.asset_type != "STOCK":
            result["状态"] = "期权资料不足：需权利金/合约调整/平仓记录；不以正股收益替代"
            output.append(result)
            continue
        entry = quote_on(prices, td)
        if entry and mark and mark[0] >= td:
            ret = mark[1]*split_factor(prices, td, mark[0])/entry[1]-1
            result.update({"买入参考价$": entry[1], "截止参考价$": mark[1], "估值日": mark[0].date().isoformat(),
                "参考持有收益%": ret*100, "状态": "收盘价假设持续持有；非议员实际回报，不含股息/税费"})
            bm0, bm1 = quote_on(benchmark, td), quote_on(benchmark, mark[0])
            if bm0 and bm1:
                br = bm1[1]*split_factor(benchmark, td, mark[0])/bm0[1]-1
                result.update({"基准收益%": br*100, "超额收益百分点": (ret-br)*100})
        else:
            result["状态"] = "缺交易当日/截止日附近行情；不以未来/陈旧价格补齐"
        linked = exits[exits.buy_id == b.trade_id]
        if not linked.empty:
            try:
                q, p, fee = number(b.quantity), number(b.execution_price), number(b.fees)
                if not all(np.isfinite(x) for x in [q, p, fee]) or min(q, p) <= 0:
                    raise ValueError("缺精确买入数量/成交价/费用")
                sold = profit = sold_cost = 0.
                for _, x in linked.iterrows():
                    xd = day(x.date)
                    if xd > asof:
                        continue
                    if xd < td or not clean_text(x.exit_id) or (exits.exit_id == x.exit_id).sum() > 1:
                        raise ValueError("平仓日期/流水号错误或重复")
                    if not valid_url(x.source_url):
                        raise ValueError("平仓缺证据 URL")
                    eq, ep, ef = number(x.quantity), number(x.execution_price), number(x.fees)
                    if not all(np.isfinite(v) for v in [eq, ep, ef]) or min(eq, ep) <= 0 or ef < 0:
                        raise ValueError("平仓数量/成交价/费用无效")
                    if prices.empty or prices.index.min() > td or prices.index.max() < xd:
                        raise ValueError("拆股记录覆盖不足")
                    units = eq/split_factor(prices, td, xd)
                    sold += units
                    cost = units*(p+fee/q)
                    sold_cost += cost
                    profit += eq*ep-ef-cost
                if sold > q+1e-7:
                    raise ValueError("配对平仓数量超过该笔买入数量（已考虑拆股）")
                if sold > 0:
                    result.update({"已实现净盈利$": profit, "已售部分成本收益%": 100*profit/sold_cost,
                        "已实现盈利占总本金%": 100*profit/(q*p+fee), "出售比例%": 100*sold/q,
                        "状态": "按用户提供成交及明确平仓配对计算，不含股息/税；参考持有列仍为假设"})
            except (ValueError, TypeError) as exc:
                result["状态"] += f"；已实现收益不可算：{exc}"
        output.append(result)
    return pd.DataFrame(output)


def net_holdings(trades, prices, max_date, clock="trade_date"):
    result, warnings = {}, []
    for member, rows in trades.groupby("member"):
        lo = pd.Series(0., index=prices.index)
        hi = lo.copy()
        for _, r in rows.iterrows():
            td = day(r.trade_date)
            if td > pd.Timestamp(max_date) or r.asset_type != "STOCK":
                continue
            q, quote = number(r.quantity), quote_on(prices, td)
            if np.isfinite(q):
                a = b = q
            elif quote and np.isfinite(r.amount_min) and np.isfinite(r.amount_max):
                a, b = r.amount_min/quote[1], r.amount_max/quote[1]
            else:
                warnings.append(f"{r.trade_id} 缺数量/行情/区间，不绘制 {member} 净股数曲线")
                lo[:], hi[:] = np.nan, np.nan
                break
            factor = split_factor(prices, td, max_date)
            a, b = a*factor, b*factor
            if r.side == "SELL":
                a, b = -b, -a
            effective = day(r[clock])
            lo.loc[lo.index >= effective] += a
            hi.loc[hi.index >= effective] += b
        result[member] = pd.DataFrame({"low": lo, "high": hi})
    return result, warnings


@st.cache_resource(show_spinner=False)
def load_finbert(revision):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=revision, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=revision, trust_remote_code=False)
    model.eval()
    return tokenizer, model, threading.Lock()


def infer_chunks(texts, tokenizer, model, batch_size=8):
    """Non-overlapping windows; expose every actual token window; no truncation."""
    import torch
    capacity = min(int(tokenizer.model_max_length), int(model.config.max_position_embeddings))
    
    chunks_records = []
    
    for doc_idx, text in enumerate(texts):
        # 官方原生滑动窗口切片：自动添加 [CLS] [SEP]，步长等于容量实现无重叠切块
        enc = tokenizer(
            text,
            max_length=capacity,
            stride=0,
            truncation=True,
            return_overflowing_tokens=True,
            return_offsets_mapping=False,
            padding=False
        )
        
        for chunk_idx, input_ids in enumerate(enc["input_ids"]):
            chunks_records.append({
                "doc_index": doc_idx,
                "input_ids": input_ids,
                "token_start": chunk_idx * capacity,
                "token_end": chunk_idx * capacity + len(input_ids),
                "token_count": len(input_ids),
                "model_input": tokenizer.decode(input_ids, skip_special_tokens=True)
            })

    labels = {int(i): str(v).lower() for i, v in model.config.id2label.items()}
    if set(labels.values()) != {"positive", "negative", "neutral"}:
        raise ValueError(f"未知模型标签：{labels}")

    with torch.inference_mode():
        for i in range(0, len(chunks_records), batch_size):
            batch_slice = chunks_records[i:i+batch_size]
            batch_input = [{"input_ids": r["input_ids"]} for r in batch_slice]
            batch = tokenizer.pad(batch_input, padding=True, return_tensors="pt")
            probs = torch.softmax(model(**batch).logits, dim=-1).cpu().numpy()
            
            for j, p in enumerate(probs):
                r = batch_slice[j]
                for k, label in labels.items():
                    r[label] = float(p[k])
                r["sentiment"] = r["positive"] - r["negative"]
                r["label"] = labels[int(np.argmax(p))]
                r.pop("input_ids", None)  # 移除张量载荷，保留整洁报表数据
                
    return chunks_records


@st.cache_data(max_entries=24, show_spinner=False)
def score_texts(texts, revision):
    tokenizer, model, lock = load_finbert(revision)
    with lock:
        chunks = infer_chunks(texts, tokenizer, model)
    return {"chunks": chunks, "model": MODEL_ID, "revision": getattr(model.config, "_commit_hash", None) or revision,
        "transformers": version("transformers"), "torch": version("torch"),
        "scored_at": datetime.now(timezone.utc).isoformat()}


def score_key(docs, revision):
    data = docs[["doc_id", "text"]].to_json(orient="records", force_ascii=False)
    return hashlib.sha256((revision+data).encode()).hexdigest()


@st.cache_data(ttl=3600, max_entries=16, show_spinner=False)
def fetch_report_text(url, sec_user_agent=""):
    """Explicit user action only; exact official hosts, no redirects/private URLs.
    Other issuers remain supported via text/CSV upload (no arbitrary server fetch).
    """
    import requests
    from bs4 import BeautifulSoup
    u = urlparse(url)
    if u.scheme != "https" or u.hostname not in {"www.sec.gov", "investor.nvidia.com", "nvidianews.nvidia.com"} or u.port not in {None, 443} or u.username:
        raise ValueError("自动抓取只接受 SEC 或 NVIDIA 官方 HTTPS 页面；其他来源请上传 TXT/CSV。")
    if u.hostname == "www.sec.gov" and "@" not in sec_user_agent:
        raise ValueError("SEC 请求须填写含真实联系邮箱的 User-Agent。")
    headers = {"User-Agent": sec_user_agent if u.hostname == "www.sec.gov" else "CongressDisclosureResearch/1.0"}
    with requests.get(url, headers=headers, timeout=(5, 30), stream=True, allow_redirects=False) as response:
        if 300 <= response.status_code < 400:
            raise ValueError("来源发生重定向，请先核对并填入最终官方页面地址。")
        response.raise_for_status()
        if "html" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("仅支持 HTML 正文；PDF 请提取文本后上传 TXT。")
        data = bytearray()
        for chunk in response.iter_content(16384):
            data.extend(chunk)
            if len(data) > 8*1024*1024:
                raise ValueError("来源超过 8 MB，请自行筛选财报正文后上传。")
    soup = BeautifulSoup(bytes(data), "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    if u.hostname == "investor.nvidia.com":
        body = soup.select_one(".module_body")
    else:
        body = soup.find("article") or soup.find("main") or soup.body
    if body is None:
        raise ValueError("未识别到正文；请核对页面或上传 TXT。")
    text = body.get_text("\n", strip=True)
    if not 100 <= len(text) <= 200000:
        raise ValueError("正文长度异常；请核对并筛选后上传。")
    return {"text": text, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(bytes(data)).hexdigest()}


def attach_scores(docs, stored, revision):
    result = docs.copy()
    result["sentiment"], result["score_origin"] = np.nan, "未评分"
    if stored and stored.get("key") == score_key(docs, revision):
        chunks = pd.DataFrame(stored["result"]["chunks"])
        for i, group in chunks.groupby("doc_index"):
            result.loc[result.index[int(i)], "sentiment"] = np.average(group.sentiment, weights=group.token_count)
            result.loc[result.index[int(i)], "score_origin"] = "FinBERT 实际推理"
    override = result.score_override.notna()
    result.loc[override, "sentiment"] = result.loc[override, "score_override"]
    result.loc[override, "score_origin"] = "人工情景覆盖（非 FinBERT）"
    result["text_sha256"] = result.text.map(lambda s: hashlib.sha256(s.encode()).hexdigest())
    original = {r["doc_id"]: r for r in records(seed_docs())}
    result["source_status"] = ["已核对原始短摘录" if r == original.get(r["doc_id"])
        else "用户新增/修改/抓取，需核对原文及日期" for r in records(docs)]
    return result


def valuation_series(prices, docs, pe, beta, stale_days=180):
    rows = []
    for dt in prices.index:
        eligible = docs[docs.published_date < dt.date().isoformat()].sort_values(["published_date", "doc_id"])
        row = {"date": dt, "value": np.nan, "base_value": np.nan, "doc_id": "", "sentiment": np.nan}
        if not eligible.empty:
            d = eligible.iloc[-1]
            if (dt-day(d.published_date)).days <= stale_days and number(d.quarter_eps) > 0:
                if prices.index.min() <= day(d.eps_basis_date) <= dt:
                    eps = d.quarter_eps/split_factor(prices, day(d.eps_basis_date), dt)
                    row.update({"doc_id": d.doc_id, "base_value": eps*4*pe, "sentiment": d.sentiment})
                    if np.isfinite(d.sentiment):
                        row["value"] = row["base_value"]*(1+beta*d.sentiment)
        rows.append(row)
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(columns=["value", "base_value", "doc_id", "sentiment"])


def records(df):
    return json.loads(df.to_json(orient="records", force_ascii=False))


def make_payload(trades, docs, exits, snapshots, prices, config):
    return {"schema_version": 1, "config": config, "trades": records(trades), "docs": records(docs),
        "exits": records(exits), "snapshots": records(snapshots), "prices": {k: records(v) for k, v in prices.items()}}


def parse_payload(raw):
    if len(raw) > 20*1024*1024:
        raise ValueError("项目文件超过 20 MB")
    obj = json.loads(raw)
    if not isinstance(obj, dict) or obj.get("schema_version") != 1:
        raise ValueError("项目版本不支持")
    out = {}
    for key, cols in [("trades", TRADE_COLUMNS), ("docs", DOC_COLUMNS), ("exits", EXIT_COLUMNS), ("snapshots", SNAPSHOT_COLUMNS)]:
        values = obj.get(key, [])
        if not isinstance(values, list) or len(values) > 10000 or not all(isinstance(v, dict) for v in values):
            raise ValueError(f"{key} 数据格式/行数错误")
        out[key] = typed_frame(values, cols)
    out["prices"] = {}
    if not isinstance(obj.get("prices", {}), dict):
        raise ValueError("prices 必须是按股票代码组织的对象")
    for symbol, values in obj.get("prices", {}).items():
        if not isinstance(values, list) or len(values) > 50000:
            raise ValueError("单只股票行情须为最多 50,000 行的数组")
        p = typed_frame(values, PRICE_COLUMNS)
        normalize_prices(p)
        out["prices"][symbol] = p
    out["config"] = obj.get("config", {})
    if not isinstance(out["config"], dict):
        raise ValueError("config 必须为对象")
    cfg = out["config"]
    for key in ["ticker", "benchmark", "start", "asof", "model_revision", "title", "subtitle", "chart_title", "research_note", "price_color", "value_color", "mode"]:
        if key in cfg and not isinstance(cfg[key], str):
            raise ValueError(f"配置 {key} 必须为文本")
    for key in ["start", "asof"]:
        if key in cfg:
            day(cfg[key])
    for key, low, high in [("pe", 1, 200), ("beta", 0, .5), ("stale_days", 1, 730), ("max_gap", 0, 30)]:
        if key in cfg and not low <= number(cfg[key]) <= high:
            raise ValueError(f"配置 {key} 超出范围")
    for key in ["price_color", "value_color"]:
        if key in cfg and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(cfg[key])):
            raise ValueError(f"{key} 颜色格式错误")
    if "mode" in cfg and cfg["mode"] not in ["事后复盘（收录全部申报）", "按申报日近似公众当时可知", "严格：仅已核实公开日"]:
        raise ValueError("交易可见性模式错误")
    if "selected" in cfg and (not isinstance(cfg["selected"], list) or not all(isinstance(x, str) for x in cfg["selected"])):
        raise ValueError("selected 必须为数组")
    if "show_holdings" in cfg and not isinstance(cfg["show_holdings"], bool):
        raise ValueError("show_holdings 必须为布尔值")
    return out


LABELS = {
    "trade_id": "交易 ID（本地）", "member": "议员", "ticker": "股票代码", "owner": "所有人",
    "account": "账户/信托", "asset_type": "STOCK/OPTION", "side": "BUY/SELL", "trade_date": "交易日",
    "notification_date": "获知交易日", "filing_date": "申报日（非公开日）", "public_date": "核实公开日（可空）",
    "amount_min": "申报金额下限 $", "amount_max": "申报金额上限 $", "quantity": "股数/合约数（可空）",
    "execution_price": "实际成交单价 $（可空）", "fees": "费用 $", "source_url": "证据原件 URL",
    "source_page": "原件页码", "notes": "备注", "exit_id": "平仓 ID", "buy_id": "配对买入 ID",
    "date": "日期 YYYY-MM-DD", "shares": "核实持仓股数", "doc_id": "文档 ID", "title": "标题",
    "published_date": "发布日期", "locator": "原文定位", "text": "实际评分原文（双击编辑）",
    "quarter_eps": "季度 GAAP EPS $", "eps_basis_date": "EPS 对应股本日期",
    "score_override": "人工情绪覆盖 [-1,1]", "close": "当日未复权收盘 $", "split": "当日拆股倍数（无=1）"}


def editor(df, key):
    config = {c: st.column_config.NumberColumn(LABELS.get(c, c), format="%.6f") if c in NUMERIC
        else st.column_config.TextColumn(LABELS.get(c, c)) for c in df.columns}
    for c, options in {"side": ["BUY", "SELL"], "asset_type": ["STOCK", "OPTION"]}.items():
        if c in config:
            config[c] = st.column_config.SelectboxColumn(LABELS[c], options=options)
    return st.data_editor(df, key=key, num_rows="dynamic", hide_index=True, column_config=config, width="stretch")


def csv_download(df, name, label):
    st.download_button(label, df.to_csv(index=False).encode("utf-8-sig"), name, "text/csv", key="dl_"+name)


def table_form(name, columns, label):
    with st.form(name+"_form"):
        edited = editor(st.session_state[name], f"ed_{name}_{st.session_state.data_revision}")
        if st.form_submit_button(label):
            try:
                st.session_state[name] = typed_frame(edited, columns)
                st.session_state.data_revision += 1
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def filter_trades(trades, ticker, members, asof, mode):
    f = trades[(trades.ticker == ticker) & trades.member.isin(members) & (trades.trade_date <= str(asof))].copy()
    if mode == "按申报日近似公众当时可知":
        f = f[(f.filing_date != "") & (f.filing_date <= str(asof))]
    elif mode == "严格：仅已核实公开日":
        f = f[(f.public_date != "") & (f.public_date <= str(asof))]
    return f


METHODS = """
**数据与计算口径**

- 交易、平仓配对、持仓快照、原文、EPS、行情、参数、标题、说明、颜色和笔记均可编辑并导出；派生收益与图表随输入重算。各表先点“应用”再切换。
- 内置为历史选样，不自动更新议员交易。可导入更多议员/股票/披露；同一披露的修订应替换原记录，不能叠加当作新交易。
- 获知交易日、签署日、申报日、公开日不同。浅橙色区间只代表交易至申报/已核实公开日的时间差，不证明存在秘密信息。严格模式只接受填有核实公开日的记录。
- 净股数曲线由已收录的交易累加，初始基点为零，**并非实际完整持仓**。未披露数量时用金额上下界/当日收盘价近似，卖出上下界反向处理；负数不表示做空。快照是单独的有据观测点。
- 参考持有收益 = (截止日收盘价 × 区间拆股倍数 / 买入日收盘价 − 1) × 100%。这是价格代理的假设回报，不证明议员实际持续持有、平仓或盈利。
- 已实现净盈利 = 配对卖出收入 − 卖出费用 − 所售部分买入成本（含按比例分配的买入费用）。同时显示占已售部分成本及整笔买入本金的百分比；多次部分卖出汇总。配对必须由用户依据同一账户的证据确认；不会猜测 FIFO。
- 期权缺少历史权利金、合约调整和完整平仓信息时不计算收益，绝不拿正股涨幅替代。
- 财报情景价 = 最近已发布季度 GAAP EPS × 4 × 假设 P/E × (1 + β × 情绪分)。EPS 按拆股换算；季度年化不是 TTM；P/E 和 β 是情景假设，**此线不是实际公允价值**。
- FinBERT 情绪分=P(positive)−P(negative)。仅使用输入文本，不自动理解整份财报。长文按 token 完整切块，token 数加权，输出每块实际输入及三类概率；不生成“避险概率”。人工覆盖单独标记。
- 日期级资料在发布日期之后才可使用，不将财报期末日当公开日。更改原文会使旧评分失效；模型版本、文本哈希均可查。未评分时只显示 EPS 基础情景线。
- 基准回报用相同日期收盘价。参考收益不含股息、税、汇率、实际成交滑点；超额回报、申报滞后或财报前交易是调查线索，不能据此认定内幕交易。
- Yahoo 口径为美元计价的美股样本。切换其他币种市场前，应自行统一币种、拆股和交易日；无行情时不模拟价格。来源 URL 不代表用户修改内容已经得到独立验证。
"""


def main():
    import plotly.graph_objects as go
    st.set_page_config(page_title="国会交易与公开信息审计", layout="wide")
    if "data_revision" not in st.session_state:
        st.session_state.update(data_revision=0, settings_generation=0, trades=seed_trades(), docs=seed_docs(),
            exits=typed_frame([], EXIT_COLUMNS), snapshots=typed_frame([], SNAPSHOT_COLUMNS), prices={},
            price_origin={}, import_config={}, score_result=None)
    state, cfg = st.session_state, st.session_state.import_config
    def key(name):
        return f"cfg_{name}_{state.settings_generation}"
    modes = ["事后复盘（收录全部申报）", "按申报日近似公众当时可知", "严格：仅已核实公开日"]
    with st.sidebar:
        st.header("分析设置")
        ticker = st.text_input("股票代码", cfg.get("ticker", "NVDA"), key=key("ticker")).strip().upper()
        benchmark_symbol = st.text_input("比较基准", cfg.get("benchmark", "SPY"), key=key("benchmark")).strip().upper()
        start = st.date_input("图表开始日", date.fromisoformat(cfg.get("start", "2024-01-01")), key=key("start"))
        asof = st.date_input("分析截止日", date.fromisoformat(cfg.get("asof", "2024-12-31")), key=key("asof"))
        mode = st.selectbox("交易可见性", modes, index=modes.index(cfg.get("mode", modes[0])), key=key("mode"))
        pe = st.number_input("假设市盈率 P/E", 1., 200., float(cfg.get("pe", 40.)), key=key("pe"))
        beta = st.slider("情绪修正系数 β", 0., .5, float(cfg.get("beta", .15)), .01, key=key("beta"))
        stale_days = st.number_input("财报最多沿用天数", 1, 730, int(cfg.get("stale_days", 180)), key=key("stale"))
        max_gap = st.number_input("截止行情容许落后天数", 0, 30, int(cfg.get("max_gap", 7)), key=key("gap"))
        revision = st.text_input("FinBERT 模型版本/commit", cfg.get("model_revision", MODEL_REVISION), key=key("model"))
        show_holdings = st.checkbox("叠加样本净股数区间", cfg.get("show_holdings", True), key=key("holdings"))
        if st.button("刷新行情缓存"):
            fetch_prices.clear()
        st.caption("首次使用：在「行情编辑」获取价格，再到「财报原文」运行真实评分。")
    with st.expander("编辑页面标题、说明、图表和研究笔记"):
        title = st.text_input("页面标题", cfg.get("title", "国会交易 × 市场走势 × 公开财报"), key=key("title"))
        subtitle = st.text_area("页面说明", cfg.get("subtitle", "逐笔核对申报、公开信息与收益，寻找值得进一步调查的异常。"), key=key("subtitle"))
        chart_title = st.text_input("图表标题", cfg.get("chart_title", "市场价格、财报情景估值与交易时间线"), key=key("chart"))
        research_note = st.text_area("研究笔记", cfg.get("research_note", ""), key=key("note"))
        price_color = st.color_picker("市场线颜色", cfg.get("price_color", "#28A9E0"), key=key("pc"))
        value_color = st.color_picker("情景线颜色", cfg.get("value_color", "#17B890"), key=key("vc"))
    st.title(title)
    st.caption(subtitle)
    st.info(f"内置 {seed_trades().member.nunique()} 位议员、{len(seed_trades())} 笔经原件核对的历史样本；并非完整持仓或实时议员数据库。记录所有人可能为配偶、联名或子女。")
    if start > asof or asof > datetime.now(timezone.utc).date():
        st.error("开始日须不晚于截止日；截止日不能在未来。")
        return
    if not all(re.fullmatch(r"[A-Z0-9.^=-]{1,20}", s) for s in [ticker, benchmark_symbol]):
        st.error("股票或基准代码格式不正确。")
        return
    with st.expander("项目恢复 / 保存与 CSV 导入"):
        st.caption("编辑保存在当前会话；下载项目 JSON 可在下次恢复。CSV 导入只替换所选表。")
        project = st.file_uploader("恢复项目 JSON", type=["json"])
        if st.button("应用项目文件", disabled=project is None):
            try:
                restored = parse_payload(project.getvalue())
                for k in ["trades", "docs", "exits", "snapshots", "prices"]:
                    state[k] = restored[k]
                state.import_config = restored["config"]
                state.score_result = None
                state.price_origin = {s: "用户导入项目（需核对）" for s in state.prices}
                state.data_revision += 1
                state.settings_generation += 1
                st.rerun()
            except (ValueError, TypeError, KeyError) as exc:
                st.error(f"无法导入：{exc}")
        table_name = st.selectbox("CSV 导入目标", ["trades", "docs", "exits", "snapshots"])
        uploaded = st.file_uploader("CSV（字段名见各表下载文件）", type=["csv"])
        if st.button("替换所选表", disabled=uploaded is None):
            try:
                imported = pd.read_csv(uploaded, keep_default_na=False)
                cols = {"trades": TRADE_COLUMNS, "docs": DOC_COLUMNS, "exits": EXIT_COLUMNS, "snapshots": SNAPSHOT_COLUMNS}[table_name]
                if not set(cols).issubset(imported.columns):
                    raise ValueError("字段不完整，请使用导出 CSV 模板")
                state[table_name] = typed_frame(imported, cols)
                state.data_revision += 1
                st.rerun()
            except (ValueError, TypeError) as exc:
                st.error(f"CSV 导入失败：{exc}")
        download_slot = st.empty()
    tabs = st.tabs(["交易与持仓编辑", "财报原文与 FinBERT", "行情编辑", "分析结果", "方法与来源"])
    with tabs[0]:
        st.caption("新增议员：在交易表加入姓名即可进入筛选器。SELF 本人 / SP 配偶 / JT 联名 / DC 子女。日期用 YYYY-MM-DD。")
        table_form("trades", TRADE_COLUMNS, "应用交易编辑")
        csv_download(state.trades, "trades.csv", "下载交易 CSV / 导入模板")
        with st.expander("填写真实成交与逐笔平仓配对（用于已实现收益）"):
            st.caption("先在买入行填实际单价、数量与费用，再用 buy_id 配对每次卖出。数量为卖出日股数，拆股自动换算。须核实同一所有人、账户、币种与批次。")
            table_form("exits", EXIT_COLUMNS, "应用平仓配对")
            csv_download(state.exits, "exits.csv", "下载平仓配对 CSV")
        with st.expander("补充多个日期的有据持仓快照"):
            st.caption("没有期初持仓不能恢复完整余额。快照单独展示，不自动连接/插值为真实持仓。")
            table_form("snapshots", SNAPSHOT_COLUMNS, "应用持仓快照")
            csv_download(state.snapshots, "snapshots.csv", "下载持仓快照 CSV")
        errors = validate_trades(state.trades)
        for error in errors:
            st.error(error)
        if not state.trades.empty:
            audit = state.trades[["trade_id", "member", "ticker", "source_url", "source_page"]].copy()
            originals = {r["trade_id"]: r for r in records(seed_trades())}
            audit["校验状态"] = ["已核对原始样本" if r == originals.get(r["trade_id"]) else "用户新增/修改，需核对" for r in records(state.trades)]
            st.dataframe(audit, hide_index=True, width="stretch", column_config={"source_url": st.column_config.LinkColumn("原件")})
        orphan = state.exits[~state.exits.buy_id.isin(state.trades.loc[state.trades.side == "BUY", "trade_id"])]
        if not orphan.empty:
            st.error("部分平仓 buy_id 找不到买入记录：" + ", ".join(orphan.buy_id))
    with st.sidebar:
        members = sorted(set(state.trades.member)-{""})
        default_members = cfg.get("selected", ["Nancy Pelosi", "Josh Gottheimer", "Marjorie Taylor Greene"])
        selected = st.multiselect("监控议员（可多选）", members, default=[m for m in default_members if m in members], key=key("selected"))
    filtered = filter_trades(state.trades, ticker, selected, asof, mode)
    with tabs[1]:
        st.caption("原文可直接编辑或由 CSV 导入。内置为短摘录，不代表全文。FinBERT 只识别正面/负面/中性，不输出内幕交易或避险概率。")
        table_form("docs", DOC_COLUMNS, "应用财报与原文编辑")
        csv_download(state.docs, "documents.csv", "下载财报原文 CSV")
        with st.expander("用官方财报正文 / TXT 替换短摘录"):
            st.caption("覆盖后请核对清洗出的原文，再运行 FinBERT。HTML 可能包含表格和免责声明，不会自动当作高管发言。")
            doc_ids = state.docs.doc_id.tolist()
            chosen = st.selectbox("替换哪份文档正文", doc_ids) if doc_ids else None
            sec_ua = st.text_input("SEC 联系标识（仅抓取 SEC 时需要，含真实邮箱）")
            text_file = st.file_uploader("上传 UTF-8 TXT / Markdown 正文", type=["txt", "md"])
            if st.button("应用上传正文", disabled=text_file is None or chosen is None):
                try:
                    text = text_file.getvalue().decode("utf-8-sig")
                    if not text.strip() or len(text) > 200000:
                        raise ValueError("正文须为 1 至 200,000 字符")
                    state.docs.loc[state.docs.doc_id == chosen, "text"] = text
                    state.docs.loc[state.docs.doc_id == chosen, "notes"] = "用户上传正文；请核对原文来源、定位与发布日期。"
                    state.data_revision += 1
                    st.rerun()
                except (ValueError, UnicodeError) as exc:
                    st.error(str(exc))
            if st.button("抓取所选官方页面正文", disabled=chosen is None):
                try:
                    url = state.docs.loc[state.docs.doc_id == chosen, "source_url"].iloc[0]
                    with st.spinner("读取官方 HTML 正文…"):
                        fetched = fetch_report_text(url, sec_ua)
                    state.docs.loc[state.docs.doc_id == chosen, "text"] = fetched["text"]
                    state.docs.loc[state.docs.doc_id == chosen, "notes"] = f"HTML 正文（含表格/免责声明）；需核对清洗文本。抓取 {fetched['retrieved_at']}；原文件 SHA256 {fetched['source_sha256']}"
                    state.data_revision += 1
                    st.rerun()
                except Exception as exc:
                    st.error(f"未替换正文：{exc}")
        doc_errors = validate_docs(state.docs)
        for error in doc_errors:
            st.error(error)
        relevant = state.docs[state.docs.ticker == ticker].reset_index(drop=True)
        if mode != modes[0]:
            relevant = relevant[relevant.published_date <= asof.isoformat()].reset_index(drop=True)
        if st.button("运行 / 更新 FinBERT 真实评分", disabled=relevant.empty or bool(doc_errors)):
            try:
                with st.spinner("加载金融文本模型并完整分块推理；首次需要下载模型…"):
                    result = score_texts(tuple(relevant.text), revision)
                state.score_result = {"key": score_key(relevant, revision), "result": result}
            except Exception as exc:
                st.error(f"评分未完成，未生成替代分数。请检查 torch、transformers 与模型网络：{exc}")
        scored = attach_scores(relevant, state.score_result, revision)
        if not scored.empty:
            st.dataframe(scored[["doc_id", "published_date", "title", "sentiment", "score_origin", "source_status", "source_url", "text_sha256"]],
                hide_index=True, width="stretch", column_config={"source_url": st.column_config.LinkColumn("原文来源")})
            for _, d in scored.iterrows():
                with st.expander(f"{d.doc_id} · {d.title}"):
                    st.write("原文定位：", d.locator)
                    st.text(d.text)
                    st.caption(d.notes)
                    st.link_button("打开原始财报", d.source_url)
        if state.score_result and state.score_result["key"] == score_key(relevant, revision):
            mr = state.score_result["result"]
            chunks = pd.DataFrame(mr["chunks"])
            chunks["doc_id"] = chunks.doc_index.map(relevant.doc_id.to_dict())
            st.dataframe(chunks, hide_index=True, width="stretch")
            st.json({k: v for k, v in mr.items() if k != "chunks"})
            csv_download(chunks, "finbert_chunks.csv", "下载真实输入切块与三类概率")
        else:
            st.info("当前文本尚未评分或已更改；人工覆盖会单独标记。")
    # Input dates are validated before they can drive any network request.
    needed_start = min([start.isoformat()] + filtered.trade_date.tolist() + relevant.eps_basis_date.tolist()) if not errors and not doc_errors else start.isoformat()
    with tabs[2]:
        st.caption("行情须为当日未复权收盘价，拆股日填新股/旧股倍数，其余填 1。Yahoo Close 会被还原到当日股本。数据源无价时不会生成随机价格。")
        if st.button("获取 / 更新股票与基准行情", type="primary", disabled=bool(errors or doc_errors)):
            for symbol in dict.fromkeys([ticker, benchmark_symbol]):
                try:
                    with st.spinner(f"获取 {symbol}…"):
                        state.prices[symbol] = fetch_prices(symbol, needed_start, asof.isoformat())
                    state.price_origin[symbol] = "Yahoo Finance，经拆股口径还原；" + datetime.now(timezone.utc).isoformat()
                    state.data_revision += 1
                except Exception as exc:
                    st.error(f"{symbol} 获取失败：{exc}")
        price_symbol = st.selectbox("编辑哪只标的", list(dict.fromkeys([ticker, benchmark_symbol])))
        price_upload = st.file_uploader("上传未复权行情 CSV", type=["csv"], key="price_file")
        if st.button("应用行情 CSV", disabled=price_upload is None):
            try:
                p = typed_frame(pd.read_csv(price_upload), PRICE_COLUMNS)
                normalize_prices(p)
                state.prices[price_symbol] = p
                state.price_origin[price_symbol] = "用户上传行情（需核对）"
                state.data_revision += 1
                st.rerun()
            except (ValueError, TypeError) as exc:
                st.error(str(exc))
        market_input = state.prices.get(price_symbol, typed_frame([], PRICE_COLUMNS))
        with st.form("price_form"):
            edited = editor(market_input, f"ed_prices_{price_symbol}_{state.data_revision}")
            if st.form_submit_button("应用行情编辑"):
                try:
                    normalize_prices(edited)
                    state.prices[price_symbol] = edited
                    state.price_origin[price_symbol] = "用户编辑行情（需核对）"
                    state.data_revision += 1
                    st.rerun()
                except (ValueError, TypeError) as exc:
                    st.error(str(exc))
        st.caption(state.price_origin.get(price_symbol, "尚无数据"))
        csv_download(market_input, f"{price_symbol}_prices.csv", "下载行情 CSV")
    config = dict(ticker=ticker, benchmark=benchmark_symbol, start=start.isoformat(), asof=asof.isoformat(),
        pe=pe, beta=beta, stale_days=int(stale_days), max_gap=int(max_gap), model_revision=revision,
        title=title, subtitle=subtitle, chart_title=chart_title, research_note=research_note,
        price_color=price_color, value_color=value_color, selected=selected, mode=mode, show_holdings=show_holdings)
    payload = make_payload(state.trades, state.docs, state.exits, state.snapshots, state.prices, config)
    payload["price_origin"] = state.price_origin
    with download_slot:
        st.download_button("保存全部编辑为项目 JSON", json.dumps(payload, ensure_ascii=False, indent=2),
            "congress_audit_project.json", "application/json")
    with tabs[4]:
        st.markdown(METHODS)
        for text, url in [("众议院原件检索", HOUSE+"/FinancialDisclosure"),
                ("2024 官方年度索引 ZIP", HOUSE+"/public_disc/financial-pdfs/2024FD.zip"),
                ("众议院财务申报说明", "https://ethics.house.gov/financial-disclosure/"),
                ("参议院 eFD（检索后可导入）", "https://efdsearch.senate.gov/search/"),
                ("SEC EDGAR", "https://www.sec.gov/edgar/search/"),
                ("FinBERT 模型与许可", "https://huggingface.co/ProsusAI/finbert"),
                ("Yahoo 行情", f"https://finance.yahoo.com/quote/{ticker}/history/")]:
            st.link_button(text, url)
    with tabs[3]:
        if errors or doc_errors or not orphan.empty:
            st.error("请先修正交易、财报或平仓输入错误。")
            return
        if filtered.empty:
            st.info("当前股票/议员/可见性筛选没有交易；不会套用其他记录。")
        try:
            prices = normalize_prices(state.prices.get(ticker, typed_frame([], PRICE_COLUMNS)))
            benchmark = normalize_prices(state.prices.get(benchmark_symbol, typed_frame([], PRICE_COLUMNS)))
        except ValueError as exc:
            st.error(str(exc))
            return
        prices = prices.loc[prices.index <= pd.Timestamp(asof)]
        benchmark = benchmark.loc[benchmark.index <= pd.Timestamp(asof)]
        if prices.empty:
            st.info("请在「行情编辑」获取行情或上传 CSV。")
            return
        display = prices.loc[prices.index >= pd.Timestamp(start)]
        if display.empty:
            st.warning("显示区间没有行情。")
            return
        st.caption("行情状态：" + state.price_origin.get(ticker, "用户导入（需核对）"))
        val = valuation_series(prices, scored, pe, beta, int(stale_days))
        factors = prices.split.iloc[::-1].cumprod().iloc[::-1]/prices.split
        factors = factors.reindex(display.index)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=display.index, y=display.close/factors, name=f"{ticker} 市场价格（截止日股本）", line=dict(color=price_color, width=2)))
        fig.add_trace(go.Scatter(x=display.index, y=val.reindex(display.index).base_value/factors,
            name="EPS × 假设 P/E 基础情景", line=dict(dash="dot", color="#999999")))
        fig.add_trace(go.Scatter(x=display.index, y=val.reindex(display.index).value/factors,
            name="FinBERT / 人工情景（非公允价值）", line=dict(dash="dash", color=value_color)))
        for side, color, symbol in [("BUY", "#16A085", "triangle-up"), ("SELL", "#E74C3C", "triangle-down")]:
            xs, ys, texts = [], [], []
            for _, r in filtered[filtered.side == side].iterrows():
                td, q = day(r.trade_date), quote_on(prices, day(r.trade_date))
                if q and td >= pd.Timestamp(start):
                    xs.append(td)
                    ys.append(q[1]/split_factor(prices, td, asof))
                    texts.append(f"{r.member} · {r.owner} · {r.asset_type}<br>{r.trade_id}")
            fig.add_trace(go.Scatter(x=xs, y=ys, text=texts, mode="markers", name=side,
                marker=dict(color=color, symbol=symbol, size=10), hovertemplate="%{text}<br>%{x}<extra></extra>"))
        for _, r in filtered.iterrows():
            stop = r.public_date or r.filing_date
            if stop and day(stop) >= pd.Timestamp(start):
                left, right = max(day(r.trade_date), pd.Timestamp(start)), min(day(stop), pd.Timestamp(asof))
                if right >= left:
                    fig.add_vrect(x0=left.isoformat(), x1=right.isoformat(), fillcolor="#E67E22", opacity=.06, line_width=0, layer="below")
        if show_holdings:
            clock = "trade_date" if mode == modes[0] else ("filing_date" if mode == modes[1] else "public_date")
            holdings, warnings = net_holdings(filtered, prices, asof, clock)
            for member, h in holdings.items():
                h = h.reindex(display.index)
                if h.low.isna().all():
                    continue
                fig.add_trace(go.Scatter(x=h.index, y=h.low, name=f"{member} 净变化下限", yaxis="y2", line=dict(shape="hv", width=1), legendgroup=member))
                fig.add_trace(go.Scatter(x=h.index, y=h.high, name=f"{member} 净变化上限", yaxis="y2", line=dict(shape="hv", width=1), fill="tonexty", legendgroup=member))
            for warning in warnings:
                st.warning(warning)
        fig.update_layout(title=chart_title, xaxis_title="日期", yaxis_title="美元 / 截止日股本单位",
            yaxis2=dict(title="样本净股数变化（非绝对持仓）", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", y=-.25), height=660, margin=dict(b=130), hovermode="x unified")
        st.plotly_chart(fig, width="stretch")
        st.caption("浅橙色为交易至申报/核实公开日区间，不代表已证实的信息优势。持仓轴只显示已收录交易的净变化。")
        if mode != modes[0]:
            st.caption("此模式中，净股数阶梯在申报/核实公开日才更新；买卖标记仍定位原交易日，供核对当时已披露的交易历史。")
        returns = purchase_returns(filtered, state.exits, prices, benchmark, asof, int(max_gap))
        st.subheader("每笔买入相对本金的收益")
        if returns.empty:
            st.info("当前筛选没有买入记录。")
        else:
            st.dataframe(returns, hide_index=True, width="stretch", column_config={
                c: st.column_config.NumberColumn(c, format="%.2f") for c in returns.select_dtypes("number").columns})
            csv_download(returns, "purchase_returns.csv", "下载逐笔收益明细")
        audit = filtered[["trade_id", "member", "owner", "trade_date", "filing_date", "public_date", "source_url"]].copy()
        audit["申报滞后天数"] = [((day(r.filing_date)-day(r.trade_date)).days if r.filing_date else np.nan) for _, r in filtered.iterrows()]
        audit["下一份已收录财报相隔天数"] = [min([(day(d)-day(r.trade_date)).days for d in relevant.published_date
            if day(d) >= day(r.trade_date)], default=np.nan) for _, r in filtered.iterrows()]
        st.subheader("时间线核查线索")
        st.dataframe(audit, hide_index=True, width="stretch", column_config={"source_url": st.column_config.LinkColumn("原件")})
        snapshots = state.snapshots[(state.snapshots.ticker == ticker) & state.snapshots.member.isin(selected)]
        valid_snapshots = []
        for i, r in snapshots.iterrows():
            try:
                dt = day(r.date)
                if not np.isfinite(number(r.shares)) or r.shares < 0 or not valid_url(r.source_url):
                    raise ValueError("持仓数量/证据无效")
                if pd.Timestamp(start) <= dt <= pd.Timestamp(asof):
                    valid_snapshots.append(r)
            except ValueError as exc:
                st.error(f"持仓快照第 {i+1} 行：{exc}")
        if valid_snapshots:
            st.subheader("用户核实的持仓快照（当日股数）")
            st.dataframe(pd.DataFrame(valid_snapshots), hide_index=True, width="stretch")
        if research_note:
            st.subheader("研究笔记")
            st.write(research_note)


if __name__ == "__main__":
    main()
