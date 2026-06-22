"""
portfolio.py — Portföy Yönetim Modülü
Session state tabanlı portföy saklama; CSV export/import desteği.
"""
from __future__ import annotations
from typing import Optional
import io

import pandas as pd
import streamlit as st


# ─────────────────────────────────────────────
# TEMEL CRUD
# ─────────────────────────────────────────────

def load_portfolio() -> list[dict]:
    """Portföyü session state'den yükler."""
    if "portfolio" not in st.session_state:
        st.session_state["portfolio"] = []
    return st.session_state["portfolio"]


def save_portfolio(portfolio: list[dict]) -> None:
    """Portföyü session state'e kaydeder."""
    st.session_state["portfolio"] = portfolio


def add_stock(
    ticker: str,
    quantity: float,
    buy_price: float,
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    notes: str = "",
) -> tuple[bool, str]:
    """Portföye yeni hisse ekler."""
    portfolio = load_portfolio()
    ticker = ticker.strip().upper()

    if not ticker:
        return False, "Geçersiz ticker!"
    if quantity <= 0:
        return False, "Miktar 0'dan büyük olmalıdır."
    if buy_price <= 0:
        return False, "Alış fiyatı 0'dan büyük olmalıdır."

    for s in portfolio:
        if s["ticker"].upper() == ticker:
            return False, f"{ticker} portföyde zaten mevcut. Güncelleme için önce silin."

    entry: dict = {
        "ticker": ticker,
        "quantity": float(quantity),
        "buy_price": float(buy_price),
        "target_price": float(target_price) if target_price else None,
        "stop_loss": float(stop_loss) if stop_loss else None,
        "notes": notes.strip(),
        "add_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
    }
    portfolio.append(entry)
    save_portfolio(portfolio)
    return True, f"✅ {ticker} portföye eklendi!"


def remove_stock(ticker: str) -> bool:
    """Portföyden hisse çıkarır."""
    portfolio = load_portfolio()
    ticker = ticker.upper()
    before = len(portfolio)
    portfolio = [s for s in portfolio if s["ticker"].upper() != ticker]
    save_portfolio(portfolio)
    # Sinyalleri temizle
    if "signals_data" in st.session_state:
        st.session_state["signals_data"] = [
            x for x in st.session_state["signals_data"]
            if x["ticker"].upper() != ticker
        ]
    return len(portfolio) < before


def update_stock(ticker: str, updates: dict) -> bool:
    """Hisse bilgilerini günceller."""
    portfolio = load_portfolio()
    ticker = ticker.upper()
    for s in portfolio:
        if s["ticker"].upper() == ticker:
            s.update(updates)
            save_portfolio(portfolio)
            return True
    return False


# ─────────────────────────────────────────────
# PORTFÖY ÖZETİ
# ─────────────────────────────────────────────

def get_portfolio_summary(
    portfolio: list[dict],
    current_prices: dict[str, float | None],
) -> dict:
    """Portföy bazlı KPI'ları hesaplar."""
    if not portfolio:
        return {}

    total_cost = 0.0
    total_value = 0.0
    details: list[dict] = []

    for s in portfolio:
        ticker = s["ticker"].upper()
        qty = s.get("quantity", 0)
        buy = s.get("buy_price", 0)
        current = current_prices.get(ticker)

        if not current or current <= 0:
            continue

        cost = qty * buy
        value = qty * current
        pnl = value - cost
        pnl_pct = pnl / cost * 100 if cost > 0 else 0.0

        total_cost += cost
        total_value += value
        details.append({
            "ticker": ticker,
            "qty": qty,
            "buy_price": buy,
            "current_price": current,
            "cost": cost,
            "value": value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "target": s.get("target_price"),
            "stop": s.get("stop_loss"),
            "weight": 0.0,
        })

    for d in details:
        d["weight"] = d["value"] / total_value * 100 if total_value > 0 else 0.0

    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost > 0 else 0.0
    winners = sum(1 for d in details if d["pnl"] > 0)
    losers = sum(1 for d in details if d["pnl"] <= 0)

    return {
        "total_cost": total_cost,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "num_stocks": len(portfolio),
        "num_priced": len(details),
        "winners": winners,
        "losers": losers,
        "details": details,
    }


# ─────────────────────────────────────────────
# CSV EXPORT / IMPORT
# ─────────────────────────────────────────────

def portfolio_to_csv(
    portfolio: list[dict],
    current_prices: dict[str, float | None],
) -> bytes:
    """Portföyü UTF-8 BOM CSV olarak döndürür (Excel uyumlu)."""
    rows = []
    for s in portfolio:
        ticker = s["ticker"].upper()
        current = current_prices.get(ticker)
        buy = s.get("buy_price", 0)
        qty = s.get("quantity", 0)
        pnl_pct = (current - buy) / buy * 100 if (current and buy) else None

        rows.append({
            "Ticker": ticker,
            "Miktar": qty,
            "Alış Fiyatı (₺)": buy,
            "Anlık Fiyat (₺)": round(current, 2) if current else "",
            "Hedef Fiyat (₺)": s.get("target_price", ""),
            "Stop-Loss (₺)": s.get("stop_loss", ""),
            "Getiri (%)": f"{pnl_pct:+.2f}" if pnl_pct is not None else "",
            "Notlar": s.get("notes", ""),
            "Ekleme Tarihi": s.get("add_date", ""),
        })

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


def csv_to_portfolio(content: bytes) -> tuple[list[dict], str]:
    """CSV içeriğini okuyarak portföy listesi döndürür."""
    try:
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    except Exception:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
        except Exception as e:
            return [], f"CSV okunamadı: {e}"

    required = ["Ticker", "Miktar", "Alış Fiyatı (₺)"]
    for col in required:
        if col not in df.columns:
            return [], f"Gerekli sütun eksik: '{col}'"

    portfolio: list[dict] = []
    errors = 0
    for _, row in df.iterrows():
        try:
            ticker = str(row["Ticker"]).strip().upper()
            qty = float(row["Miktar"])
            buy = float(row["Alış Fiyatı (₺)"])
            if not ticker or qty <= 0 or buy <= 0:
                errors += 1
                continue

            def _opt(key: str) -> Optional[float]:
                v = row.get(key, "")
                if pd.isna(v) or str(v).strip() in ("", "—", "nan"):
                    return None
                try:
                    return float(str(v).replace("%", "").replace("+", ""))
                except ValueError:
                    return None

            portfolio.append({
                "ticker": ticker,
                "quantity": qty,
                "buy_price": buy,
                "target_price": _opt("Hedef Fiyat (₺)"),
                "stop_loss": _opt("Stop-Loss (₺)"),
                "notes": str(row.get("Notlar", "") or ""),
                "add_date": str(row.get("Ekleme Tarihi", pd.Timestamp.now().strftime("%Y-%m-%d"))),
            })
        except Exception:
            errors += 1

    msg = f"✅ {len(portfolio)} hisse yüklendi"
    if errors:
        msg += f" ({errors} satır atlandı)"
    return portfolio, msg
