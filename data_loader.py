"""
data_loader.py — BIST Veri Yükleme Modülü
yfinance üzerinden BIST hisselerine .IS uzantısıyla erişir.
Tüm fonksiyonlar @st.cache_data ile önbelleğe alınır.
"""
from __future__ import annotations
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

BIST_SUFFIX = ".IS"
DEFAULT_DAYS = 420   # MA200 için yeterli veri


def _normalize(ticker: str) -> str:
    """Ticker'ı büyük harfe çevirir, gerekirse .IS ekler."""
    t = ticker.strip().upper()
    if not t.endswith(BIST_SUFFIX):
        t = t + BIST_SUFFIX
    return t


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance'ın MultiIndex sütunlarını düzleştirir."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(col[0]) for col in df.columns]
    return df


# ─────────────────────────────────────────────
# OHLCV VERİSİ
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_data(ticker: str, days: int = DEFAULT_DAYS) -> pd.DataFrame:
    """
    BIST hissesi için OHLCV verisi çeker.
    Başarısız olursa boş DataFrame döndürür — uygulama çökmez.
    """
    symbol = _normalize(ticker)
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)

    try:
        df = yf.download(
            symbol,
            start=start_dt.strftime("%Y-%m-%d"),
            end=end_dt.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True,
        )
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    df = _flatten_columns(df)

    required = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df.columns for c in required):
        return pd.DataFrame()

    df = df[required].copy()
    df.index = pd.to_datetime(df.index)
    df = df.dropna(subset=["Close", "High", "Low"])
    df = df[df["Close"] > 0]

    if len(df) < 50:
        return pd.DataFrame()

    return df


# ─────────────────────────────────────────────
# ANLAK FİYAT
# ─────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)   # 10 dk önbellek
def fetch_current_price(ticker: str) -> float | None:
    """
    Anlık (veya son kapanış) fiyatını döndürür.
    Başarısız olursa None döner.
    """
    symbol = _normalize(ticker)
    # 1) fast_info (anlık)
    try:
        fi = yf.Ticker(symbol).fast_info
        price = getattr(fi, "last_price", None)
        if price and float(price) > 0:
            return float(price)
    except Exception:
        pass

    # 2) Yedek: son 5 günlük kapanış
    try:
        df = yf.download(symbol, period="5d", progress=False, auto_adjust=True)
        if not df.empty:
            df = _flatten_columns(df)
            if "Close" in df.columns:
                return float(df["Close"].iloc[-1])
    except Exception:
        pass

    return None


def fetch_current_prices(tickers: list[str]) -> dict[str, float | None]:
    """Birden fazla hisse için anlık fiyatları toplu çeker."""
    prices: dict[str, float | None] = {}
    for i, t in enumerate(tickers):
        if i > 0:
            time.sleep(0.3)   # rate-limit dostu
        prices[t.upper()] = fetch_current_price(t)
    return prices


# ─────────────────────────────────────────────
# HİSSE BİLGİSİ
# ─────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)  # 24 saat
def fetch_stock_info(ticker: str) -> dict:
    """
    Şirket adı, sektör, piyasa değeri gibi meta verileri döndürür.
    Hata durumunda varsayılan sözlük döner.
    """
    symbol = _normalize(ticker)
    result = {
        "shortName": ticker.upper(),
        "longName": ticker.upper(),
        "sector": "—",
        "industry": "—",
        "marketCap": None,
        "currency": "TRY",
    }
    try:
        info = yf.Ticker(symbol).info or {}
        result["shortName"] = info.get("shortName", ticker.upper())
        result["longName"] = info.get("longName", ticker.upper())
        result["sector"] = info.get("sector", "—")
        result["industry"] = info.get("industry", "—")
        result["marketCap"] = info.get("marketCap")
    except Exception:
        pass
    return result


# ─────────────────────────────────────────────
# DOĞRULAMA
# ─────────────────────────────────────────────

def validate_ticker(ticker: str) -> bool:
    """Ticker'ın BIST'te geçerli olup olmadığını kontrol eder."""
    df = fetch_stock_data(ticker, days=60)
    return not df.empty


# ─────────────────────────────────────────────
# GÜNLÜK DEĞİŞİM
# ─────────────────────────────────────────────

def get_daily_change(df: pd.DataFrame) -> tuple[float, float]:
    """
    Son bar kapanışı ile bir önceki kapanışı karşılaştırır.
    (değişim_tl, değişim_yüzde) döndürür.
    """
    if df is None or len(df) < 2:
        return 0.0, 0.0
    prev_close = float(df["Close"].iloc[-2])
    last_close = float(df["Close"].iloc[-1])
    chg = last_close - prev_close
    chg_pct = (chg / prev_close * 100) if prev_close > 0 else 0.0
    return chg, chg_pct
