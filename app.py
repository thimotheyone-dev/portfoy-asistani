"""
app.py — BIST Portföy Asistanı · Ana Uygulama
Streamlit Cloud'da çalışacak şekilde tasarlanmıştır.
⚠️  Bu uygulama yatırım tavsiyesi vermez; yalnızca analiz ve karar destek aracıdır.
"""
from __future__ import annotations
import time
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from data_loader import (
    fetch_current_price,
    fetch_current_prices,
    fetch_stock_data,
    fetch_stock_info,
    get_daily_change,
)
from indicators import add_all_indicators, find_support_resistance
from portfolio import (
    add_stock,
    csv_to_portfolio,
    get_portfolio_summary,
    load_portfolio,
    portfolio_to_csv,
    remove_stock,
    save_portfolio,
    update_stock,
)
from signals import SignalResult, generate_signal

# ══════════════════════════════════════════════════════════════════
# SAYFA KONFİGÜRASYONU  (ilk Streamlit çağrısı olmalı)
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="BIST Portföy Asistanı",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════
_CSS = """
<style>
/* ── Genel ─────────────────────────────────── */
.main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
h1,h2,h3 { color: #e2e8f0; }

/* ── Uygulama Başlığı ───────────────────────── */
.app-banner {
    background: linear-gradient(135deg, #0f3460 0%, #16213e 60%, #1a1a2e 100%);
    border-radius: 14px;
    padding: 1.4rem 2rem;
    margin-bottom: 1.5rem;
    border: 1px solid #1E3A5F;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
.app-banner h1 { font-size: 1.8rem; font-weight: 900; margin: 0; letter-spacing: -.5px; color: #e2e8f0; }
.app-banner p  { color: #8b9dc3; margin: 0.2rem 0 0; font-size: 0.85rem; }

/* ── KPI Kartları ───────────────────────────── */
.kpi-card {
    background: linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 1rem 1.3rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    margin-bottom: 0.5rem;
}
.kpi-card::after {
    content:'';
    position:absolute;
    top:0;left:0;right:0;
    height:3px;
    border-radius:12px 12px 0 0;
}
.kpi-card.blue::after  { background: linear-gradient(90deg,#1E88E5,#42A5F5); }
.kpi-card.green::after { background: linear-gradient(90deg,#00C851,#4CAF50); }
.kpi-card.red::after   { background: linear-gradient(90deg,#F44336,#FF5252); }
.kpi-card.amber::after { background: linear-gradient(90deg,#FF8C00,#FFA726); }
.kpi-label { color:#8b9dc3; font-size:.68rem; text-transform:uppercase; letter-spacing:1.3px; margin-bottom:.35rem; }
.kpi-value { font-size:1.55rem; font-weight:800; color:#e2e8f0; line-height:1.1; }
.kpi-delta { font-size:.8rem; margin-top:.3rem; font-weight:600; }

/* ── Rozet ──────────────────────────────────── */
.badge {
    display:inline-block;
    padding:.25rem .75rem;
    border-radius:20px;
    font-size:.75rem;
    font-weight:700;
    letter-spacing:.3px;
    white-space:nowrap;
}

/* ── Skor Çubuğu ────────────────────────────── */
.sb-wrap { display:flex; align-items:center; gap:.6rem; }
.sb-bg   { flex:1; background:#2d2d44; border-radius:6px; height:7px; overflow:hidden; }
.sb-fill { height:100%; border-radius:6px; }

/* ── Bileşen Satırı ─────────────────────────── */
.comp-row {
    display:grid;
    grid-template-columns:1.4rem 9rem 1fr 3.5rem;
    gap:.4rem;
    align-items:start;
    padding:.38rem .2rem;
    border-bottom:1px solid rgba(50,50,80,.35);
    font-size:.82rem;
    line-height:1.4;
}
.comp-name  { color:#8b9dc3; }
.comp-desc  { color:#cbd5e1; }
.comp-score { color:#60a5fa; font-weight:700; text-align:right; }

/* ── Aksiyon Kutusu ─────────────────────────── */
.action-box {
    border-radius:10px;
    padding:.9rem 1.1rem;
    margin:.5rem 0;
    font-size:.86rem;
    line-height:1.6;
}
.a-green  { background:rgba(0,200,81,.09);  border-left:4px solid #00C851; }
.a-yellow { background:rgba(255,140,0,.09); border-left:4px solid #FF8C00; }
.a-orange { background:rgba(255,87,34,.09); border-left:4px solid #FF5722; }
.a-red    { background:rgba(244,67,54,.09); border-left:4px solid #F44336; }

/* ── Hisse Kartı (Portföy Listesi) ─────────── */
.stock-row {
    background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
    border:1px solid #1e3a5f;
    border-left:4px solid;
    border-radius:10px;
    padding:.8rem 1rem;
    margin-bottom:.5rem;
}

/* ── Seviye Tablosu ─────────────────────────── */
.level-row {
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:.32rem .6rem;
    border-radius:5px;
    font-size:.8rem;
    margin-bottom:.2rem;
    gap:.5rem;
}
.lv-sup  { background:rgba(0,200,81,.07);  border-left:3px solid rgba(0,200,81,.5);  }
.lv-res  { background:rgba(244,67,54,.07); border-left:3px solid rgba(244,67,54,.5); }
.lv-trig { background:rgba(30,136,229,.12); border-left:3px solid #1E88E5; }
.lv-price { font-weight:700; color:#e2e8f0; white-space:nowrap; }

/* ── Sidebar Başlık ─────────────────────────── */
.sb-brand { text-align:center; padding:.6rem 0 1rem; }
.sb-brand span { font-size:1.05rem; font-weight:900; color:#1E88E5; letter-spacing:.5px; }

/* ── Yasal Uyarı ────────────────────────────── */
.disclaimer {
    color:#4b5563;
    font-size:.68rem;
    text-align:center;
    padding:.8rem .5rem;
    border-top:1px solid #1f2937;
    margin-top:1.5rem;
    line-height:1.6;
}

/* ── Responsive ─────────────────────────────── */
@media(max-width:768px){
    .app-banner h1 { font-size:1.3rem; }
    .comp-row { grid-template-columns:1.2rem 1fr; }
}
</style>
"""


def _load_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# GRAFİK FONKSİYONU
# ══════════════════════════════════════════════════════════════════

def _make_chart(
    df: pd.DataFrame,
    ticker: str,
    show_bb: bool = True,
    show_ma: bool = True,
    bars: int = 120,
) -> go.Figure:
    """Çok panelli Plotly teknik analiz grafiği oluşturur."""
    df_i = add_all_indicators(df)
    recent = df_i.tail(bars)

    support, resistance = find_support_resistance(df, lookback=min(80, len(df)))

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[0.52, 0.14, 0.17, 0.17],
        subplot_titles=("", "Hacim", "RSI (14)", "MACD (12·26·9)"),
    )

    # ── Mum Grafiği ──────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=recent.index,
        open=recent["Open"], high=recent["High"],
        low=recent["Low"],   close=recent["Close"],
        name="OHLC",
        increasing_line_color="#26a69a", increasing_fillcolor="#26a69a",
        decreasing_line_color="#ef5350", decreasing_fillcolor="#ef5350",
        line=dict(width=1),
    ), row=1, col=1)

    # ── Hareketli Ortalamalar ─────────────────────────────────────
    if show_ma:
        ma_cfg = [("MA20", "#FFA726", 1.2), ("MA50", "#42A5F5", 1.5), ("MA200", "#EF5350", 1.8)]
        for col_name, color, width in ma_cfg:
            if col_name in recent.columns:
                fig.add_trace(go.Scatter(
                    x=recent.index, y=recent[col_name],
                    mode="lines", name=col_name,
                    line=dict(color=color, width=width),
                    opacity=0.85,
                ), row=1, col=1)

    # ── Bollinger Bantları ────────────────────────────────────────
    if show_bb and "BB_Upper" in recent.columns:
        fig.add_trace(go.Scatter(
            x=recent.index, y=recent["BB_Upper"],
            mode="lines", name="BB Üst",
            line=dict(color="rgba(120,120,220,.4)", width=1, dash="dot"),
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=recent.index, y=recent["BB_Lower"],
            mode="lines", name="BB Alt",
            line=dict(color="rgba(120,120,220,.4)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(100,100,200,.04)",
            showlegend=False,
        ), row=1, col=1)

    # ── Destek / Direnç ───────────────────────────────────────────
    x0, x1 = recent.index[0], recent.index[-1]
    for lvl in resistance[:3]:
        fig.add_shape(type="line", x0=x0, x1=x1, y0=lvl, y1=lvl,
                      line=dict(color="rgba(244,67,54,.5)", width=1, dash="dot"),
                      row=1, col=1)
        fig.add_annotation(x=x1, y=lvl, text=f"  D {lvl:.2f}",
                           showarrow=False, font=dict(size=9, color="rgba(244,67,54,.8)"),
                           xanchor="left", row=1, col=1)
    for lvl in support[:3]:
        fig.add_shape(type="line", x0=x0, x1=x1, y0=lvl, y1=lvl,
                      line=dict(color="rgba(0,200,81,.5)", width=1, dash="dot"),
                      row=1, col=1)
        fig.add_annotation(x=x1, y=lvl, text=f"  S {lvl:.2f}",
                           showarrow=False, font=dict(size=9, color="rgba(0,200,81,.8)"),
                           xanchor="left", row=1, col=1)

    # ── Hacim ─────────────────────────────────────────────────────
    vol_colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(recent["Close"], recent["Open"])
    ]
    fig.add_trace(go.Bar(
        x=recent.index, y=recent["Volume"],
        name="Hacim", marker_color=vol_colors, opacity=0.65, showlegend=False,
    ), row=2, col=1)
    vol_ma20 = recent["Volume"].rolling(20).mean()
    fig.add_trace(go.Scatter(
        x=recent.index, y=vol_ma20, mode="lines",
        line=dict(color="#FFA726", width=1.2), showlegend=False, name="Hacim MA20",
    ), row=2, col=1)

    # ── RSI ───────────────────────────────────────────────────────
    if "RSI" in recent.columns:
        rsi_colors = []
        for v in recent["RSI"].fillna(50):
            if v >= 70:
                rsi_colors.append("#ef5350")
            elif v <= 30:
                rsi_colors.append("#26a69a")
            else:
                rsi_colors.append("#CE93D8")
        fig.add_trace(go.Scatter(
            x=recent.index, y=recent["RSI"],
            mode="lines", name="RSI(14)",
            line=dict(color="#CE93D8", width=1.5), showlegend=False,
        ), row=3, col=1)
        for level, color in [(70, "rgba(244,67,54,.4)"), (30, "rgba(0,200,81,.4)"), (50, "rgba(200,200,200,.2)")]:
            fig.add_hline(y=level, line_dash="dot", line_color=color, line_width=1, row=3, col=1)

    # ── MACD ──────────────────────────────────────────────────────
    if "MACD" in recent.columns:
        fig.add_trace(go.Scatter(
            x=recent.index, y=recent["MACD"],
            mode="lines", name="MACD",
            line=dict(color="#4FC3F7", width=1.5), showlegend=False,
        ), row=4, col=1)
        fig.add_trace(go.Scatter(
            x=recent.index, y=recent["MACD_Signal"],
            mode="lines", name="Sinyal",
            line=dict(color="#FF8A65", width=1.2), showlegend=False,
        ), row=4, col=1)
        hist_vals = recent["MACD_Hist"].fillna(0)
        h_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in hist_vals]
        fig.add_trace(go.Bar(
            x=recent.index, y=hist_vals,
            marker_color=h_colors, opacity=0.65, showlegend=False, name="Histogram",
        ), row=4, col=1)
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(200,200,200,.2)", line_width=1, row=4, col=1)

    # ── Layout ───────────────────────────────────────────────────
    ax = dict(gridcolor="rgba(40,40,65,.7)", zerolinecolor="rgba(40,40,65,.7)",
              tickfont=dict(size=10, color="#8b9dc3"))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        height=680,
        margin=dict(l=60, r=80, t=35, b=20),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="top", y=1.015,
            xanchor="left", x=0,
            font=dict(size=10), bgcolor="rgba(0,0,0,0)",
        ),
        title=dict(text=f"<b>{ticker}</b>  —  Teknik Analiz", font=dict(size=13, color="#8b9dc3")),
    )
    fig.update_xaxes(**ax)
    fig.update_yaxes(**ax)
    fig.update_yaxes(row=3, range=[0, 100])
    return fig


# ══════════════════════════════════════════════════════════════════
# YARDIMCI UI FONKSİYONLARI
# ══════════════════════════════════════════════════════════════════

def _kpi(label: str, value: str, delta: str = "", color: str = "blue") -> None:
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    st.markdown(
        f'<div class="kpi-card {color}">'
        f'  <div class="kpi-label">{label}</div>'
        f'  <div class="kpi-value">{value}</div>'
        f'  {delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _badge(label: str, color: str) -> str:
    return (
        f'<span class="badge" '
        f'style="background:{color}22;color:{color};border:1px solid {color}66">'
        f'{label}</span>'
    )


def _score_bar(score: float, color: str, max_score: float = 10.0) -> str:
    pct = min(score / max_score * 100, 100)
    return (
        f'<div class="sb-wrap">'
        f'  <span style="color:{color};font-weight:700;font-size:1rem">{score}</span>'
        f'  <div class="sb-bg"><div class="sb-fill" style="width:{pct:.0f}%;background:{color}"></div></div>'
        f'  <span style="color:#8b9dc3;font-size:.8rem">/ 10</span>'
        f'</div>'
    )


def _action_box(text: str) -> None:
    if text.startswith("🟢"):
        cls = "a-green"
    elif text.startswith("🟡"):
        cls = "a-yellow"
    elif text.startswith("🟠"):
        cls = "a-orange"
    else:
        cls = "a-red"
    st.markdown(f'<div class="action-box {cls}">{text}</div>', unsafe_allow_html=True)


def _fmt_tl(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"₺{v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"₺{v/1_000:.1f}K"
    return f"₺{v:.2f}"


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════

def _render_sidebar(portfolio: list[dict]) -> None:
    st.sidebar.markdown(
        '<div class="sb-brand"><span>📈 BIST Portföy</span></div>',
        unsafe_allow_html=True,
    )

    # ── Hisse Ekle ────────────────────────────────────────────────
    with st.sidebar.expander("➕  Hisse Ekle", expanded=len(portfolio) == 0):
        ticker_in = st.text_input("Ticker (örn: THYAO)", key="add_ticker",
                                  placeholder="THYAO").strip().upper()
        qty_in    = st.number_input("Miktar (adet)", min_value=0.01, value=100.0,
                                    step=1.0, key="add_qty")
        buy_in    = st.number_input("Alış Fiyatı (₺)", min_value=0.01, value=100.0,
                                    step=0.01, key="add_buy", format="%.2f")

        use_tgt = st.checkbox("Hedef Fiyat belirle", key="use_tgt")
        tgt_in  = None
        if use_tgt:
            tgt_in = st.number_input("Hedef Fiyat (₺)", min_value=0.01,
                                     value=float(buy_in * 1.20),
                                     step=0.01, key="add_tgt", format="%.2f")

        use_stop = st.checkbox("Stop-Loss belirle", key="use_stop")
        stop_in  = None
        if use_stop:
            stop_in = st.number_input("Stop-Loss (₺)", min_value=0.01,
                                      value=float(buy_in * 0.90),
                                      step=0.01, key="add_stop", format="%.2f")

        notes_in = st.text_input("Notlar (opsiyonel)", key="add_notes", placeholder="")

        if st.button("✅  Portföye Ekle", type="primary", use_container_width=True):
            if ticker_in:
                ok, msg = add_stock(ticker_in, qty_in, buy_in, tgt_in, stop_in, notes_in)
                if ok:
                    st.success(msg)
                    # sinyal önbelleğini sıfırla
                    if "signals_data" in st.session_state:
                        del st.session_state["signals_data"]
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Lütfen ticker girin.")

    # ── Portföy Listesi (Sidebar) ─────────────────────────────────
    if portfolio:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Portföydeki Hisseler**")
        for s in portfolio:
            c1, c2 = st.sidebar.columns([4, 1])
            c1.markdown(f"**{s['ticker']}** — {s['quantity']:.0f} adet")
            if c2.button("🗑️", key=f"del_{s['ticker']}", help=f"{s['ticker']} sil"):
                remove_stock(s["ticker"])
                if "signals_data" in st.session_state:
                    del st.session_state["signals_data"]
                st.rerun()

    st.sidebar.markdown(
        '<div class="disclaimer">'
        "⚠️ Bu uygulama yatırım tavsiyesi vermez.<br>"
        "Tüm yatırım kararları kullanıcıya aittir."
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════
# TAB 1 — PORTFÖY ÖZETİ
# ══════════════════════════════════════════════════════════════════

def _render_portfolio_tab(
    portfolio: list[dict],
    current_prices: dict,
    summary: dict,
) -> None:
    if not portfolio:
        st.info("📭 Portföyde henüz hisse yok. Sol panelden ekleyebilirsiniz.")
        return

    # ── KPI Kartları ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _kpi("Toplam Değer", _fmt_tl(summary.get("total_value", 0)),
             f"Maliyet: {_fmt_tl(summary.get('total_cost', 0))}", "blue")
    with c2:
        pnl = summary.get("total_pnl", 0)
        pnl_pct = summary.get("total_pnl_pct", 0)
        sign = "+" if pnl >= 0 else ""
        col = "green" if pnl >= 0 else "red"
        _kpi("Toplam Kâr / Zarar",
             f"{sign}{_fmt_tl(pnl)}",
             f"{sign}{pnl_pct:.2f}%",
             col)
    with c3:
        _kpi("Kârlı Hisse", str(summary.get("winners", 0)), "", "green")
    with c4:
        _kpi("Zararda Hisse", str(summary.get("losers", 0)), "", "red")

    st.markdown("---")
    st.markdown("### 📋 Portföy Detayı")

    # ── Tablo ─────────────────────────────────────────────────────
    details = summary.get("details", [])
    if not details:
        st.warning("Anlık fiyat verisi alınamadı. Birkaç dakika sonra tekrar deneyin.")
        return

    rows = []
    for d in details:
        sign = "+" if d["pnl_pct"] >= 0 else ""
        rows.append({
            "Ticker":       d["ticker"],
            "Adet":         int(d["qty"]),
            "Alış (₺)":     d["buy_price"],
            "Anlık (₺)":    d["current_price"],
            "Getiri %":     d["pnl_pct"],
            "Kâr/Zarar (₺)":d["pnl"],
            "Değer (₺)":    d["value"],
            "Ağırlık %":    d["weight"],
        })

    df_tbl = pd.DataFrame(rows)

    def _clr_pct(v: float) -> str:
        return "color: #26a69a; font-weight:700" if v >= 0 else "color: #ef5350; font-weight:700"

    styled = (
        df_tbl.style
        .applymap(_clr_pct, subset=["Getiri %", "Kâr/Zarar (₺)"])
        .format({
            "Alış (₺)": "₺{:.2f}", "Anlık (₺)": "₺{:.2f}",
            "Getiri %": "{:+.2f}%", "Kâr/Zarar (₺)": "₺{:+,.0f}",
            "Değer (₺)": "₺{:,.0f}", "Ağırlık %": "{:.1f}%",
        })
        .hide(axis="index")
    )
    st.dataframe(styled, use_container_width=True, height=min(400, 55 + len(rows) * 38))

    # ── Ağırlık Pasta Grafiği ─────────────────────────────────────
    if len(details) > 1:
        with st.expander("📊 Portföy Ağırlık Dağılımı"):
            pie = go.Figure(go.Pie(
                labels=[d["ticker"] for d in details],
                values=[d["value"] for d in details],
                hole=0.45,
                textinfo="label+percent",
                textfont=dict(size=12),
                marker=dict(line=dict(color="#0E1117", width=2)),
            ))
            pie.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0E1117",
                margin=dict(t=20, b=20),
                height=340,
                showlegend=False,
            )
            st.plotly_chart(pie, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# TAB 2 — HİSSE ANALİZİ
# ══════════════════════════════════════════════════════════════════

def _render_analysis_tab(
    portfolio: list[dict],
    current_prices: dict,
) -> None:
    if not portfolio:
        st.info("Portföyde henüz hisse yok.")
        return

    tickers = [s["ticker"] for s in portfolio]

    # Manuel ticker de eklenebilsin
    all_opts = ["— Manuel Gir —"] + tickers
    sel = st.selectbox("Analiz edilecek hisse", all_opts, key="analysis_sel")

    if sel == "— Manuel Gir —":
        manual = st.text_input("Ticker girin (örn: GARAN)", key="manual_ticker").strip().upper()
        if not manual:
            st.info("Yukarıdan bir hisse seçin veya ticker girin.")
            return
        ticker = manual
        stock_meta = {"ticker": ticker, "quantity": 0, "buy_price": 0}
    else:
        ticker = sel
        stock_meta = next((s for s in portfolio if s["ticker"] == ticker), {})

    # ── Veri Yükleme ──────────────────────────────────────────────
    with st.spinner(f"{ticker} verileri yükleniyor…"):
        df = fetch_stock_data(ticker)
        info = fetch_stock_info(ticker)

    if df is None or df.empty:
        st.error(f"❌ {ticker} için veri alınamadı. Ticker'ı kontrol edin.")
        return

    df_i   = add_all_indicators(df)
    last   = df_i.iloc[-1]
    price  = float(last["Close"])
    chg, chg_pct = get_daily_change(df)

    # ── Fiyat Başlığı ─────────────────────────────────────────────
    col_h1, col_h2, col_h3 = st.columns([3, 2, 2])
    with col_h1:
        st.markdown(f"## {ticker}")
        st.caption(info.get("longName", ticker))
    with col_h2:
        sign = "+" if chg >= 0 else ""
        color = "#26a69a" if chg >= 0 else "#ef5350"
        st.markdown(
            f'<div style="font-size:1.9rem;font-weight:800;color:{color}">₺{price:.2f}</div>'
            f'<div style="color:{color};font-size:.9rem">{sign}₺{chg:.2f}  ({sign}{chg_pct:.2f}%)</div>',
            unsafe_allow_html=True,
        )
    with col_h3:
        if stock_meta.get("buy_price", 0) > 0:
            buy = stock_meta["buy_price"]
            ret = (price - buy) / buy * 100
            rc = "#26a69a" if ret >= 0 else "#ef5350"
            sign2 = "+" if ret >= 0 else ""
            st.markdown(
                f'<div style="font-size:.8rem;color:#8b9dc3">Alış: ₺{buy:.2f}</div>'
                f'<div style="font-size:1.2rem;font-weight:700;color:{rc}">{sign2}{ret:.2f}%</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Gösterge Değerleri ────────────────────────────────────────
    def _safe(col: str) -> str:
        v = last.get(col)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "—"
        return f"{float(v):.2f}"

    st.markdown("#### 📐 Teknik Göstergeler")
    gc = st.columns(7)
    labels = ["MA20", "MA50", "MA200", "RSI(14)", "ADX(14)", "Göreceli Hacim", "ATR %"]
    cols   = ["MA20", "MA50", "MA200", "RSI",     "ADX",    "RelVol",          "ATR_Pct"]
    suffixes = ["", "", "", "", "", "x", "%"]
    for i, (lbl, col_name, suf) in enumerate(zip(labels, cols, suffixes)):
        v = last.get(col_name)
        val_str = "—"
        if v is not None and not (isinstance(v, float) and np.isnan(float(v))):
            val_str = f"{float(v):.2f}{suf}"
        gc[i].metric(lbl, val_str)

    st.markdown("---")

    # ── Sinyal ────────────────────────────────────────────────────
    buy_p   = stock_meta.get("buy_price")   or None
    tgt_p   = stock_meta.get("target_price") or None
    stop_p  = stock_meta.get("stop_loss")    or None
    qty     = stock_meta.get("quantity", 0)

    with st.spinner("Sinyal hesaplanıyor…"):
        sig = generate_signal(df, ticker, buy_p, tgt_p, stop_p, qty)

    if sig.error:
        st.warning(f"⚠️ Sinyal hesaplanamadı: {sig.error}")
        return

    st.markdown("#### 🎯 Sinyal Skoru")
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.markdown(
            f'<div style="font-size:3rem;font-weight:900;color:{sig.color};line-height:1">{sig.score}</div>'
            f'<div style="color:#8b9dc3;font-size:.85rem">/ 10 puan</div>'
            f'<br>{_badge(f"{sig.emoji}  {sig.label}", sig.color)}',
            unsafe_allow_html=True,
        )

    with right_col:
        # Bileşen tablosu
        rows_comp = []
        for c in sig.components:
            rows_comp.append(
                f'<div class="comp-row">'
                f'  <span>{c.emoji}</span>'
                f'  <span class="comp-name">{c.name}</span>'
                f'  <span class="comp-desc">{c.description}</span>'
                f'  <span class="comp-score">{c.score_str}</span>'
                f'</div>'
            )
        st.markdown("".join(rows_comp), unsafe_allow_html=True)

    st.markdown("---")

    # ── Kâr Alma & Ekleme ─────────────────────────────────────────
    col_p, col_a = st.columns(2)

    with col_p:
        st.markdown("#### 💰 Kâr Alma Analizi")
        if sig.profit_action:
            _action_box(sig.profit_action)
            st.caption(sig.profit_detail)
        else:
            st.info("Alış fiyatı girildiğinde kâr alma analizi görünür.")

        if sig.profit_levels:
            st.markdown("**Kâr Alma Seviyeleri**")
            for pl in sig.profit_levels:
                cls = "lv-trig" if pl.triggered else ("lv-res" if "Stop" in pl.label else "lv-sup")
                status = "✅ Geçildi" if pl.triggered else "⏳ Bekliyor"
                st.markdown(
                    f'<div class="level-row {cls}">'
                    f'  <span>{pl.label}</span>'
                    f'  <span class="lv-price">₺{pl.price:.2f}</span>'
                    f'  <span style="color:#8b9dc3">{pl.action}</span>'
                    f'  <span style="color:#60a5fa;font-size:.75rem">{status}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with col_a:
        st.markdown("#### ➕ Pozisyon Ekleme Analizi")
        _action_box(sig.add_action)

        if sig.add_levels:
            st.markdown("**Ekleme Seviyeleri**")
            for al in sig.add_levels:
                cls = "lv-trig" if al.triggered else "lv-sup"
                near = "📍 Yakın!" if al.triggered else ""
                st.markdown(
                    f'<div class="level-row {cls}">'
                    f'  <span>{al.label}  {near}</span>'
                    f'  <span class="lv-price">₺{al.price:.2f}</span>'
                    f'  <span style="color:#8b9dc3">{al.action}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.caption("Not: Seviyelere yaklaşıldığında 📍 işareti çıkar.")

    # ── Destek / Direnç ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🧱 Destek / Direnç Seviyeleri")
    sup, res = find_support_resistance(df)
    col_s, col_r = st.columns(2)
    with col_s:
        st.markdown("**Destek**")
        if sup:
            for s in sup:
                pct = (price - s) / price * 100
                st.markdown(
                    f'<div class="level-row lv-sup">'
                    f'  <span>₺{s:.2f}</span>'
                    f'  <span style="color:#26a69a">−%{pct:.1f}</span>'
                    f'</div>', unsafe_allow_html=True)
        else:
            st.caption("Tespit edilemedi")
    with col_r:
        st.markdown("**Direnç**")
        if res:
            for r in res:
                pct = (r - price) / price * 100
                st.markdown(
                    f'<div class="level-row lv-res">'
                    f'  <span>₺{r:.2f}</span>'
                    f'  <span style="color:#ef5350">+%{pct:.1f}</span>'
                    f'</div>', unsafe_allow_html=True)
        else:
            st.caption("Tespit edilemedi")


# ══════════════════════════════════════════════════════════════════
# TAB 3 — SİNYALLER
# ══════════════════════════════════════════════════════════════════

def _render_signals_tab(portfolio: list[dict], current_prices: dict) -> None:
    if not portfolio:
        st.info("Portföyde henüz hisse yok.")
        return

    hdr_c1, hdr_c2 = st.columns([4, 1])
    with hdr_c1:
        st.markdown("### 📡 Portföy Sinyal Tablosu")
    with hdr_c2:
        refresh = st.button("🔄 Yenile", key="sig_refresh", use_container_width=True)

    # Filtreleme / Sıralama
    fc1, fc2 = st.columns([2, 2])
    with fc1:
        sort_opt = st.selectbox("Sırala",
            ["Puana Göre (↓)", "Getiriye Göre (↓)", "Ticker Alfabetik"], key="sig_sort")
    with fc2:
        filter_opts = st.multiselect("Sinyal Filtresi",
            ["Güçlü Al", "Al / Ekle", "Tut / İzle", "Dikkatli Ol", "Riskli / Çık"],
            default=[], key="sig_filter")

    # Hesapla veya önbellekten al
    needs_run = refresh or "signals_data" not in st.session_state
    if needs_run:
        signals_list: list[dict] = []
        prog = st.progress(0, text="Sinyaller hesaplanıyor…")
        total_n = len(portfolio)
        for i, s in enumerate(portfolio):
            tk = s["ticker"]
            prog.progress((i + 1) / total_n, text=f"⏳ {tk} analiz ediliyor…")
            df_s = fetch_stock_data(tk)
            sg   = generate_signal(df_s, tk,
                                   s.get("buy_price"),
                                   s.get("target_price"),
                                   s.get("stop_loss"),
                                   s.get("quantity", 0))
            signals_list.append({"ticker": tk, "signal": sg, "stock": s})
            if i < total_n - 1:
                time.sleep(0.25)
        prog.empty()
        st.session_state["signals_data"] = signals_list

    signals_list = st.session_state.get("signals_data", [])

    # Filtre
    if filter_opts:
        signals_list = [x for x in signals_list if x["signal"].label in filter_opts]

    # Sıralama
    if sort_opt == "Puana Göre (↓)":
        signals_list = sorted(signals_list, key=lambda x: x["signal"].score, reverse=True)
    elif sort_opt == "Getiriye Göre (↓)":
        signals_list = sorted(signals_list, key=lambda x: x["signal"].pct_return, reverse=True)
    else:
        signals_list = sorted(signals_list, key=lambda x: x["ticker"])

    if not signals_list:
        st.warning("Filtre kriterlerine uyan sinyal bulunamadı.")
        return

    # ── Özet Tablo ────────────────────────────────────────────────
    tbl_rows = []
    for item in signals_list:
        sg = item["signal"]
        s  = item["stock"]
        if not sg.is_valid:
            tbl_rows.append({
                "Ticker": sg.ticker, "Fiyat (₺)": None,
                "Getiri %": None, "Puan": None,
                "Sinyal": sg.label if sg.label else "Hata",
                "RSI": None, "RelVol": None,
            })
            continue
        tbl_rows.append({
            "Ticker":     sg.ticker,
            "Fiyat (₺)": sg.current_price,
            "Getiri %":  sg.pct_return if s.get("buy_price") else None,
            "Puan":      sg.score,
            "Sinyal":    f"{sg.emoji}  {sg.label}",
            "RSI":       round(sg.rsi, 1) if sg.rsi else None,
            "RelVol":    round(sg.rel_vol, 2) if sg.rel_vol else None,
        })

    df_tbl = pd.DataFrame(tbl_rows)

    SIGNAL_COLORS_MAP = {
        "🟢  Güçlü Al":   "#00C851", "🟢  Al / Ekle":  "#4CAF50",
        "🟡  Tut / İzle": "#FF8C00", "🟠  Dikkatli Ol":"#FF5722",
        "🔴  Riskli / Çık":"#F44336",
    }

    def _clr_sig(v):
        return f"color:{SIGNAL_COLORS_MAP.get(v, '#808080')};font-weight:700"

    def _clr_ret(v):
        if pd.isna(v):
            return ""
        return "color:#26a69a;font-weight:600" if v >= 0 else "color:#ef5350;font-weight:600"

    def _clr_score(v):
        if pd.isna(v):
            return ""
        if v >= 7.5:
            return "color:#00C851;font-weight:700"
        if v >= 5.0:
            return "color:#FF8C00;font-weight:700"
        return "color:#F44336;font-weight:700"

    fmt = {"Fiyat (₺)": "₺{:.2f}", "Getiri %": "{:+.2f}%", "Puan": "{:.1f}", "RelVol": "{:.2f}x"}
    styled_tbl = (
        df_tbl.style
        .applymap(_clr_sig,   subset=["Sinyal"])
        .applymap(_clr_ret,   subset=["Getiri %"])
        .applymap(_clr_score, subset=["Puan"])
        .format(fmt, na_rep="—")
        .hide(axis="index")
    )
    st.dataframe(styled_tbl, use_container_width=True,
                 height=min(500, 55 + len(tbl_rows) * 38))

    # ── Detay Kartlar ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🗂️ Detaylı Aksiyon Önerileri")
    for item in signals_list:
        sg = item["signal"]
        if not sg.is_valid:
            continue
        with st.expander(f"{sg.emoji}  **{sg.ticker}**  —  {sg.label}  |  Puan: {sg.score}/10"):
            ec1, ec2 = st.columns(2)
            with ec1:
                st.markdown("**💰 Kâr Alma**")
                if sg.profit_action:
                    _action_box(sg.profit_action)
                    st.caption(sg.profit_detail)
                else:
                    st.caption("Alış fiyatı girilmedi.")
            with ec2:
                st.markdown("**➕ Pozisyon Ekleme**")
                _action_box(sg.add_action)


# ══════════════════════════════════════════════════════════════════
# TAB 4 — GRAFİK
# ══════════════════════════════════════════════════════════════════

def _render_chart_tab(portfolio: list[dict], current_prices: dict) -> None:
    if not portfolio:
        st.info("Portföyde henüz hisse yok.")
        return

    tickers  = [s["ticker"] for s in portfolio]
    all_opts = ["— Manuel Gir —"] + tickers
    sel = st.selectbox("Hisse seç", all_opts, key="chart_sel")

    if sel == "— Manuel Gir —":
        manual = st.text_input("Ticker girin", key="chart_manual").strip().upper()
        if not manual:
            st.info("Yukarıdan bir hisse seçin veya ticker girin.")
            return
        ticker = manual
    else:
        ticker = sel

    # Ayarlar
    ca1, ca2, ca3, ca4 = st.columns(4)
    with ca1:
        period = st.selectbox("Periyot", ["3 Ay", "6 Ay", "1 Yıl", "Tümü"], index=1, key="chart_period")
    with ca2:
        show_ma = st.toggle("MA Çizgileri", value=True, key="chart_ma")
    with ca3:
        show_bb = st.toggle("Bollinger Bantları", value=True, key="chart_bb")
    with ca4:
        pass

    period_days = {"3 Ay": 90, "6 Ay": 180, "1 Yıl": 365, "Tümü": 420}
    bars = period_days.get(period, 180)

    with st.spinner(f"{ticker} grafiği hazırlanıyor…"):
        df = fetch_stock_data(ticker)

    if df is None or df.empty:
        st.error(f"❌ {ticker} için veri alınamadı.")
        return

    fig = _make_chart(df, ticker, show_bb=show_bb, show_ma=show_ma, bars=bars)
    st.plotly_chart(fig, use_container_width=True)

    # İndikatör Özeti
    with st.expander("📊 Son Gösterge Değerleri"):
        df_i = add_all_indicators(df)
        last = df_i.iloc[-1]
        cols_show = ["Close", "MA20", "MA50", "MA200", "RSI", "MACD",
                     "MACD_Signal", "ADX", "RelVol", "ATR_Pct"]
        labels_show = ["Kapanış", "MA20", "MA50", "MA200", "RSI",
                       "MACD", "Sinyal", "ADX", "RelVol", "ATR %"]
        vals = {}
        for k, lbl in zip(cols_show, labels_show):
            v = last.get(k)
            if v is not None and not (isinstance(v, float) and np.isnan(float(v))):
                vals[lbl] = f"{float(v):.2f}"
            else:
                vals[lbl] = "—"

        ind_cols = st.columns(5)
        for i, (k, v) in enumerate(vals.items()):
            ind_cols[i % 5].metric(k, v)


# ══════════════════════════════════════════════════════════════════
# TAB 5 — AYARLAR
# ══════════════════════════════════════════════════════════════════

def _render_settings_tab(portfolio: list[dict], current_prices: dict) -> None:
    st.markdown("### ⚙️ Ayarlar & Veri Yönetimi")
    st.caption("Portföy veriniz yalnızca mevcut oturum içinde saklanır. "
               "Kalıcı kullanım için CSV dışa aktarımı yapın.")

    st.markdown("---")

    # ── Export ────────────────────────────────────────────────────
    st.markdown("#### 📥 Portföyü Dışa Aktar (CSV)")
    if portfolio:
        csv_bytes = portfolio_to_csv(portfolio, current_prices)
        st.download_button(
            label="⬇️  CSV İndir",
            data=csv_bytes,
            file_name="bist_portfoy.csv",
            mime="text/csv",
            type="primary",
        )
    else:
        st.info("Dışa aktarmak için önce hisse ekleyin.")

    st.markdown("---")

    # ── Import ────────────────────────────────────────────────────
    st.markdown("#### 📤 CSV'den Portföy Yükle")
    st.caption("Daha önce indirdiğiniz CSV dosyasını yükleyerek portföyü geri yükleyebilirsiniz.")
    uploaded = st.file_uploader("CSV Dosyası", type=["csv"], key="csv_upload")
    if uploaded:
        new_portfolio, msg = csv_to_portfolio(uploaded.read())
        if new_portfolio:
            if st.button(f"✅ {len(new_portfolio)} Hisseyi Yükle", type="primary"):
                save_portfolio(new_portfolio)
                if "signals_data" in st.session_state:
                    del st.session_state["signals_data"]
                st.success(msg)
                st.rerun()
        else:
            st.error(msg)

    st.markdown("---")

    # ── Portföy Düzenle ───────────────────────────────────────────
    if portfolio:
        st.markdown("#### ✏️ Hisse Güncelle")
        upd_ticker = st.selectbox("Güncellenecek hisse",
            [s["ticker"] for s in portfolio], key="upd_sel")
        upd_stock = next((s for s in portfolio if s["ticker"] == upd_ticker), None)

        if upd_stock:
            uc1, uc2 = st.columns(2)
            with uc1:
                new_qty = st.number_input("Miktar", min_value=0.01,
                    value=float(upd_stock.get("quantity", 1)), key="upd_qty")
                new_buy = st.number_input("Alış Fiyatı (₺)", min_value=0.01,
                    value=float(upd_stock.get("buy_price", 1)), key="upd_buy", format="%.2f")
            with uc2:
                _tgt = upd_stock.get("target_price") or 0.0
                new_tgt = st.number_input("Hedef Fiyat (₺, 0=yok)", min_value=0.0,
                    value=float(_tgt), key="upd_tgt", format="%.2f")
                _stp = upd_stock.get("stop_loss") or 0.0
                new_stp = st.number_input("Stop-Loss (₺, 0=yok)", min_value=0.0,
                    value=float(_stp), key="upd_stop", format="%.2f")
            new_notes = st.text_input("Notlar", value=upd_stock.get("notes", ""), key="upd_notes")

            if st.button("💾 Güncelle", type="primary"):
                update_stock(upd_ticker, {
                    "quantity": new_qty,
                    "buy_price": new_buy,
                    "target_price": new_tgt if new_tgt > 0 else None,
                    "stop_loss":    new_stp if new_stp > 0 else None,
                    "notes":        new_notes,
                })
                if "signals_data" in st.session_state:
                    del st.session_state["signals_data"]
                st.success(f"✅ {upd_ticker} güncellendi.")
                st.rerun()

    st.markdown("---")

    # ── Portföyü Temizle ──────────────────────────────────────────
    st.markdown("#### 🗑️ Portföyü Temizle")
    st.warning("Bu işlem portföydeki tüm hisseleri siler ve geri alınamaz.")
    if st.button("🗑️ Tüm Portföyü Sil", type="secondary"):
        save_portfolio([])
        if "signals_data" in st.session_state:
            del st.session_state["signals_data"]
        st.success("Portföy temizlendi.")
        st.rerun()


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main() -> None:
    _load_css()

    # ── Başlık ────────────────────────────────────────────────────
    st.markdown(
        '<div class="app-banner">'
        '  <h1>📈 BIST Portföy Asistanı</h1>'
        '  <p>Teknik Analiz  ·  Sinyal Motoru  ·  Karar Destek Sistemi  —  '
        'BIST Hisseleri için Swing Trading Paneli</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Portföy & Fiyatlar ────────────────────────────────────────
    portfolio = load_portfolio()
    tickers   = [s["ticker"] for s in portfolio]

    with st.spinner("Anlık fiyatlar alınıyor…") if tickers else st.empty() if not tickers else st.empty():
        current_prices = fetch_current_prices(tickers) if tickers else {}

    summary = get_portfolio_summary(portfolio, current_prices)

    # ── Sidebar ───────────────────────────────────────────────────
    _render_sidebar(portfolio)

    # ── Sekmeler ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊  Portföy", "🔍  Analiz", "📡  Sinyaller", "📈  Grafik", "⚙️  Ayarlar",
    ])

    with tab1:
        _render_portfolio_tab(portfolio, current_prices, summary)

    with tab2:
        _render_analysis_tab(portfolio, current_prices)

    with tab3:
        _render_signals_tab(portfolio, current_prices)

    with tab4:
        _render_chart_tab(portfolio, current_prices)

    with tab5:
        _render_settings_tab(portfolio, current_prices)

    # ── Yasal Uyarı ───────────────────────────────────────────────
    st.markdown(
        '<div class="disclaimer">'
        "⚠️ <b>Yasal Uyarı:</b> Bu uygulama yalnızca analiz ve karar destek amacıyla hazırlanmıştır. "
        "Yatırım tavsiyesi niteliği taşımaz. Piyasalar yüksek risk içerir; "
        "tüm yatırım kararları kullanıcının sorumluluğundadır."
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
