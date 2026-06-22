"""
indicators.py — Teknik Gösterge Hesaplamaları
Tüm göstergeler sıfırdan pandas/numpy ile hesaplanır (harici TA kütüphanesi yok).
"""
from __future__ import annotations
import pandas as pd
import numpy as np


# ─────────────────────────────────────────────
# HAREKETLI ORTALAMALAR
# ─────────────────────────────────────────────

def compute_ma(series: pd.Series, period: int) -> pd.Series:
    """Basit hareketli ortalama (SMA)."""
    return series.rolling(window=period, min_periods=period).mean()


def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Üstel hareketli ortalama (EMA)."""
    return series.ewm(span=period, adjust=False).mean()


# ─────────────────────────────────────────────
# RSI (Wilder Yöntemi)
# ─────────────────────────────────────────────

def compute_wilder_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI hesaplar."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    eps = np.finfo(float).eps
    rs = avg_gain / (avg_loss + eps)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi[avg_loss < eps] = 100.0
    return rsi


# ─────────────────────────────────────────────
# MACD
# ─────────────────────────────────────────────

def compute_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD satırı, sinyal satırı ve histogram döndürür."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ─────────────────────────────────────────────
# ATR (Wilder Yöntemi)
# ─────────────────────────────────────────────

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — Wilder yumuşatması."""
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


# ─────────────────────────────────────────────
# BOLLINGER BANTLARI
# ─────────────────────────────────────────────

def compute_bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bantları: üst, orta (SMA), alt."""
    mid = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


# ─────────────────────────────────────────────
# GÖRECELİ HACİM
# ─────────────────────────────────────────────

def compute_relative_volume(volume: pd.Series, period: int = 20) -> pd.Series:
    """Göreceli Hacim = bugünkü hacim / son N günlük ortalama hacim."""
    avg = volume.rolling(window=period, min_periods=5).mean()
    return volume / (avg.replace(0, np.nan))


# ─────────────────────────────────────────────
# ADX + DI± (Wilder Yöntemi)
# ─────────────────────────────────────────────

def compute_wilder_adx(
    df: pd.DataFrame, period: int = 14
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Wilder ADX, +DI ve -DI döndürür."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    # True Range
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    # Yönsel Hareket
    dm_plus = (high - prev_high).clip(lower=0)
    dm_minus = (prev_low - low).clip(lower=0)

    # Çakışmaları sıfırla
    mask = dm_plus >= dm_minus
    dm_plus = dm_plus.where(mask, 0.0)
    dm_minus = dm_minus.where(~mask, 0.0)

    eps = np.finfo(float).eps
    atr_w = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    sm_plus = dm_plus.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    sm_minus = dm_minus.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    di_plus = 100.0 * sm_plus / (atr_w + eps)
    di_minus = 100.0 * sm_minus / (atr_w + eps)

    di_sum = (di_plus + di_minus).replace(0, np.nan)
    dx = 100.0 * (di_plus - di_minus).abs() / di_sum
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    return adx, di_plus, di_minus


# ─────────────────────────────────────────────
# DESTEK / DİRENÇ
# ─────────────────────────────────────────────

def find_support_resistance(
    df: pd.DataFrame,
    lookback: int = 60,
    n_levels: int = 4,
    tolerance: float = 0.018,
) -> tuple[list[float], list[float]]:
    """Yakın dönem yerel dip/tepe noktalarından destek & direnç bulur."""
    if df is None or len(df) < max(lookback, 20):
        return [], []

    recent = df.tail(lookback)
    highs = recent["High"].values
    lows = recent["Low"].values
    current_price = float(df["Close"].iloc[-1])

    def cluster(raw: list[float]) -> list[float]:
        if not raw:
            return []
        srt = sorted(raw)
        clusters: list[float] = []
        group = [srt[0]]
        for v in srt[1:]:
            if (v - group[-1]) / (group[-1] + 1e-9) < tolerance:
                group.append(v)
            else:
                clusters.append(float(np.mean(group)))
                group = [v]
        clusters.append(float(np.mean(group)))
        return clusters

    res_raw, sup_raw = [], []
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
            res_raw.append(highs[i])
    for i in range(2, len(lows) - 2):
        if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
            sup_raw.append(lows[i])

    resistance = sorted([r for r in cluster(res_raw) if r > current_price * 0.99])[:n_levels]
    support = sorted([s for s in cluster(sup_raw) if s < current_price * 1.01], reverse=True)[:n_levels]

    return support, resistance


# ─────────────────────────────────────────────
# TÜM GÖSTERGELERİ EKLE
# ─────────────────────────────────────────────

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tüm teknik göstergeleri DataFrame'e ekler ve döndürür."""
    if df is None or df.empty or len(df) < 30:
        return df

    df = df.copy()
    close = df["Close"]

    # Hareketli Ortalamalar
    df["MA20"] = compute_ma(close, 20)
    df["MA50"] = compute_ma(close, 50)
    df["MA200"] = compute_ma(close, 200)

    # RSI
    df["RSI"] = compute_wilder_rsi(close, 14)

    # MACD
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = compute_macd(close)

    # ATR
    df["ATR"] = compute_atr(df, 14)
    df["ATR_Pct"] = df["ATR"] / close * 100

    # Bollinger Bantları
    df["BB_Upper"], df["BB_Mid"], df["BB_Lower"] = compute_bollinger_bands(close)

    # Göreceli Hacim
    df["RelVol"] = compute_relative_volume(df["Volume"])

    # ADX
    df["ADX"], df["DI_Plus"], df["DI_Minus"] = compute_wilder_adx(df, 14)

    # Yardımcı Sütunlar
    df["Price_Chg_Pct"] = close.pct_change() * 100
    df["MA20_Pct"] = (close - df["MA20"]) / df["MA20"] * 100
    df["MA50_Pct"] = (close - df["MA50"]) / df["MA50"] * 100

    return df
