"""
signals.py — Sinyal Motoru
10 puanlık skorlama sistemi; kâr alma ve ekleme önerileri üretir.
Tüm kararlar açıklamalı ve şeffaftır — yatırım tavsiyesi değildir.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from indicators import add_all_indicators


# ─────────────────────────────────────────────
# VERİ YAPILARI
# ─────────────────────────────────────────────

@dataclass
class ScoreComponent:
    name: str
    score: float
    max_score: float
    description: str
    emoji: str

    @property
    def score_str(self) -> str:
        return f"{self.score:.1f}/{self.max_score:.0f}"


@dataclass
class PriceLevel:
    label: str
    price: float
    action: str
    note: str
    triggered: bool = False


@dataclass
class SignalResult:
    ticker: str = ""
    score: float = 0.0
    max_score: float = 10.0
    label: str = "Bilinmiyor"
    color: str = "#808080"
    emoji: str = "⚫"

    # Puan bileşenleri
    components: list[ScoreComponent] = field(default_factory=list)

    # Anlık gösterge değerleri
    current_price: float = 0.0
    rsi: float = 0.0
    adx: float = 0.0
    rel_vol: float = 0.0
    atr_pct: float = 0.0
    macd_hist: float = 0.0
    ma20: float = 0.0
    ma50: float = 0.0
    ma200: float = 0.0

    # Portföy bağlamı
    pct_return: float = 0.0
    profit_action: str = ""
    profit_detail: str = ""
    add_action: str = ""

    # Kâr alma seviyeleri
    profit_levels: list[PriceLevel] = field(default_factory=list)
    # Ekleme seviyeleri
    add_levels: list[PriceLevel] = field(default_factory=list)

    error: str = ""

    @property
    def is_valid(self) -> bool:
        return not self.error and self.current_price > 0

    @property
    def score_pct(self) -> float:
        return (self.score / self.max_score * 100) if self.max_score else 0


# ─────────────────────────────────────────────
# YARDIMCI ARAÇLAR
# ─────────────────────────────────────────────

def _f(val, default: float = np.nan) -> float:
    """Değeri güvenli şekilde float'a çevirir; geçersizse default döner."""
    try:
        v = float(val)
        return v if (not np.isnan(v) and not np.isinf(v)) else default
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────
# ANA SİNYAL FONKSİYONU
# ─────────────────────────────────────────────

def generate_signal(
    df: pd.DataFrame,
    ticker: str,
    buy_price: Optional[float] = None,
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    quantity: float = 0.0,
    price_override: Optional[float] = None,
) -> SignalResult:
    """Hisse için kapsamlı teknik sinyal üretir.

    price_override: Gerçek anlık fiyat (fast_info kaynağı).
    Verilirse gösterge hesaplamalarında değil, yalnızca
    kâr/ekleme analizinde ve ekran gösteriminde kullanılır.
    """

    result = SignalResult(ticker=ticker.upper())

    # ── Veri Kontrolü ──
    if df is None or df.empty:
        result.error = "Veri çekilemedi"
        result.label = "Veri Yok"
        return result

    if len(df) < 60:
        result.error = f"Yetersiz veri ({len(df)} bar)"
        result.label = "Yetersiz Veri"
        return result

    df_i = add_all_indicators(df)
    if df_i is None or df_i.empty:
        result.error = "Gösterge hesaplanamadı"
        result.label = "Hata"
        return result

    last = df_i.iloc[-1]
    prev = df_i.iloc[-2] if len(df_i) >= 2 else last

    # price_override varsa onu kullan (auto_adjust farkını gider)
    price   = price_override if (price_override and price_override > 0) else _f(last.get("Close"))
    ma20    = _f(last.get("MA20"))
    ma50    = _f(last.get("MA50"))
    ma200   = _f(last.get("MA200"))
    rsi     = _f(last.get("RSI"))
    macd    = _f(last.get("MACD"))
    macd_s  = _f(last.get("MACD_Signal"))
    macd_h  = _f(last.get("MACD_Hist"))
    p_macd_h= _f(prev.get("MACD_Hist"))
    rel_vol = _f(last.get("RelVol"))
    atr     = _f(last.get("ATR"))
    atr_pct = _f(last.get("ATR_Pct"))
    adx     = _f(last.get("ADX"))

    result.current_price = price
    result.rsi     = rsi     if not np.isnan(rsi)     else 0.0
    result.adx     = adx     if not np.isnan(adx)     else 0.0
    result.rel_vol = rel_vol if not np.isnan(rel_vol) else 0.0
    result.atr_pct = atr_pct if not np.isnan(atr_pct) else 0.0
    result.macd_hist = macd_h if not np.isnan(macd_h) else 0.0
    result.ma20    = ma20    if not np.isnan(ma20)    else 0.0
    result.ma50    = ma50    if not np.isnan(ma50)    else 0.0
    result.ma200   = ma200   if not np.isnan(ma200)   else 0.0

    # ════════════════════════════════════════
    # PUANLAMA SİSTEMİ (10 puan üzerinden)
    # ════════════════════════════════════════
    components: list[ScoreComponent] = []
    total = 0.0

    # ── 1. TREND — MA Yapısı (maks 3 puan) ──────────────────────
    t_score = 0.0

    if not np.isnan(ma200):
        if price > ma200:
            t_score += 1.0
            components.append(ScoreComponent(
                "Uzun Vadeli Trend", 1.0, 1.0,
                f"Fiyat ({price:.2f}) > MA200 ({ma200:.2f}) — Bullish yapı", "✅",
            ))
        else:
            pct = (ma200 - price) / ma200 * 100
            components.append(ScoreComponent(
                "Uzun Vadeli Trend", 0.0, 1.0,
                f"Fiyat MA200'ün %{pct:.1f} altında — Bearish yapı", "❌",
            ))

    if not np.isnan(ma50):
        if price > ma50:
            t_score += 1.0
            components.append(ScoreComponent(
                "Orta Vadeli Trend", 1.0, 1.0,
                f"Fiyat ({price:.2f}) > MA50 ({ma50:.2f}) — Orta vade pozitif", "✅",
            ))
        else:
            pct = (ma50 - price) / ma50 * 100
            components.append(ScoreComponent(
                "Orta Vadeli Trend", 0.0, 1.0,
                f"Fiyat MA50'nin %{pct:.1f} altında — Orta vade negatif", "❌",
            ))

    if not np.isnan(ma20) and not np.isnan(ma50) and not np.isnan(ma200):
        if ma20 > ma50 > ma200:
            t_score += 1.0
            components.append(ScoreComponent(
                "MA Hizalaması", 1.0, 1.0,
                "MA20 > MA50 > MA200 — TAM BULLISH HİZALAMA", "✅",
            ))
        elif ma20 > ma50:
            t_score += 0.5
            components.append(ScoreComponent(
                "MA Hizalaması", 0.5, 1.0,
                "MA20 > MA50 — Kısa vadeli yükseliş, MA200 gecikmeli", "🟡",
            ))
        else:
            components.append(ScoreComponent(
                "MA Hizalaması", 0.0, 1.0,
                "MA'lar hizalı değil — Zayıf trend yapısı", "❌",
            ))

    total += t_score

    # ── 2. MOMENTUM — RSI (maks 2 puan) ─────────────────────────
    m_score = 0.0

    if not np.isnan(rsi):
        prev_rsi = _f(prev.get("RSI"))
        dir_arrow = "↑" if (not np.isnan(prev_rsi) and rsi > prev_rsi) else "↓"

        if 50 <= rsi <= 65:
            m_score = 2.0
            components.append(ScoreComponent(
                "RSI Momentumu", 2.0, 2.0,
                f"RSI {rsi:.1f} {dir_arrow} — Sağlıklı momentum bölgesi (50–65)", "✅",
            ))
        elif 65 < rsi <= 72:
            m_score = 1.5
            components.append(ScoreComponent(
                "RSI Momentumu", 1.5, 2.0,
                f"RSI {rsi:.1f} {dir_arrow} — Güçlü, aşırı alım sınırına yakın", "🟡",
            ))
        elif 72 < rsi <= 80:
            m_score = 0.5
            components.append(ScoreComponent(
                "RSI Aşırı Alım", 0.5, 2.0,
                f"RSI {rsi:.1f} {dir_arrow} — Aşırı alım bölgesi, dikkat!", "⚠️",
            ))
        elif rsi > 80:
            m_score = 0.0
            components.append(ScoreComponent(
                "RSI Kritik Alım", 0.0, 2.0,
                f"RSI {rsi:.1f} {dir_arrow} — Kritik aşırı alım, düzeltme riski!", "🔴",
            ))
        elif 40 <= rsi < 50:
            m_score = 1.0
            components.append(ScoreComponent(
                "RSI Zayıf", 1.0, 2.0,
                f"RSI {rsi:.1f} {dir_arrow} — Nötr bölge, yön arayışında", "🟡",
            ))
        elif 30 <= rsi < 40:
            m_score = 0.7
            components.append(ScoreComponent(
                "RSI Toparlanıyor", 0.7, 2.0,
                f"RSI {rsi:.1f} {dir_arrow} — Aşırı satım sınırı yakın, sıçrama olabilir", "⚠️",
            ))
        elif 20 <= rsi < 30:
            m_score = 0.5
            components.append(ScoreComponent(
                "RSI Aşırı Satım", 0.5, 2.0,
                f"RSI {rsi:.1f} {dir_arrow} — Aşırı satım, teknik sıçrama potansiyeli", "⚠️",
            ))
        else:
            m_score = 0.0
            components.append(ScoreComponent(
                "RSI Kritik Satım", 0.0, 2.0,
                f"RSI {rsi:.1f} {dir_arrow} — Kritik satış baskısı", "🔴",
            ))

    total += m_score

    # ── 3. MACD (maks 2 puan) ────────────────────────────────────
    c_score = 0.0

    if not np.isnan(macd) and not np.isnan(macd_s):
        if macd > macd_s:
            c_score += 1.0
            components.append(ScoreComponent(
                "MACD Sinyali", 1.0, 1.0,
                f"MACD ({macd:.3f}) > Sinyal ({macd_s:.3f}) — Yükseliş sinyali aktif", "✅",
            ))
        else:
            components.append(ScoreComponent(
                "MACD Sinyali", 0.0, 1.0,
                f"MACD ({macd:.3f}) < Sinyal ({macd_s:.3f}) — Düşüş baskısı", "❌",
            ))

    if not np.isnan(macd_h) and not np.isnan(p_macd_h):
        improving = macd_h > p_macd_h
        if improving and macd_h > 0:
            c_score += 1.0
            components.append(ScoreComponent(
                "MACD Histogramı", 1.0, 1.0,
                "Histogram pozitif ve artıyor — Güçlü momentum ivmesi", "✅",
            ))
        elif improving and macd_h <= 0:
            c_score += 0.5
            components.append(ScoreComponent(
                "MACD Histogramı", 0.5, 1.0,
                "Histogram negatiften pozitife dönüyor — İyileşiyor", "🟡",
            ))
        elif not improving and macd_h > 0:
            c_score += 0.5
            components.append(ScoreComponent(
                "MACD Histogramı", 0.5, 1.0,
                "Histogram pozitif ama azalıyor — Momentum zayıflıyor", "🟡",
            ))
        else:
            components.append(ScoreComponent(
                "MACD Histogramı", 0.0, 1.0,
                "Histogram negatif ve düşüyor — Satış baskısı sürüyor", "❌",
            ))

    total += c_score

    # ── 4. HACİM (maks 2 puan) ────────────────────────────────────
    v_score = 0.0

    if not np.isnan(rel_vol):
        if rel_vol >= 2.0:
            v_score = 2.0
            components.append(ScoreComponent(
                "Hacim Gücü", 2.0, 2.0,
                f"Göreceli Hacim {rel_vol:.2f}x — Kurumsal ilgi işareti", "✅",
            ))
        elif rel_vol >= 1.5:
            v_score = 1.5
            components.append(ScoreComponent(
                "Hacim Gücü", 1.5, 2.0,
                f"Göreceli Hacim {rel_vol:.2f}x — Ortalamanın belirgin üstünde", "✅",
            ))
        elif rel_vol >= 1.0:
            v_score = 1.0
            components.append(ScoreComponent(
                "Hacim Gücü", 1.0, 2.0,
                f"Göreceli Hacim {rel_vol:.2f}x — Normal düzeyde", "🟡",
            ))
        elif rel_vol >= 0.5:
            v_score = 0.5
            components.append(ScoreComponent(
                "Hacim Gücü", 0.5, 2.0,
                f"Göreceli Hacim {rel_vol:.2f}x — Düşük ilgi, dikkatli olun", "⚠️",
            ))
        else:
            components.append(ScoreComponent(
                "Hacim Gücü", 0.0, 2.0,
                f"Göreceli Hacim {rel_vol:.2f}x — Çok düşük hacim, kırılgan hareket", "❌",
            ))

    total += v_score

    # ── 5. GİRİŞ KALİTESİ — MA20 Mesafesi (maks 1 puan) ─────────
    p_score = 0.0

    if not np.isnan(ma20) and price > 0:
        pct_ma20 = (price - ma20) / ma20 * 100
        if 0 <= pct_ma20 <= 6:
            p_score = 1.0
            components.append(ScoreComponent(
                "Giriş Kalitesi", 1.0, 1.0,
                f"MA20'nin %{pct_ma20:.1f} üzerinde — İdeal swing giriş bölgesi", "✅",
            ))
        elif 6 < pct_ma20 <= 15:
            p_score = 0.5
            components.append(ScoreComponent(
                "Giriş Kalitesi", 0.5, 1.0,
                f"MA20'nin %{pct_ma20:.1f} üzerinde — Kabul edilebilir, biraz uzak", "🟡",
            ))
        elif pct_ma20 > 15:
            p_score = 0.0
            components.append(ScoreComponent(
                "Aşırı Uzaklaşma", 0.0, 1.0,
                f"MA20'nin %{pct_ma20:.1f} üzerinde — Aşırı uzaklaşma, giriş riskli", "🔴",
            ))
        else:
            pct_below = abs(pct_ma20)
            components.append(ScoreComponent(
                "MA20 Altında", 0.0, 1.0,
                f"MA20'nin %{pct_below:.1f} altında — Kısa vade kırık", "❌",
            ))

    total += p_score

    # ════════════════════════════════════════
    # SONUÇ ETİKETİ
    # ════════════════════════════════════════
    total = round(min(total, 10.0), 1)
    result.score = total
    result.components = components

    if total >= 8.0:
        result.label, result.color, result.emoji = "Güçlü Al",   "#00C851", "🟢"
    elif total >= 6.5:
        result.label, result.color, result.emoji = "Al / Ekle",  "#4CAF50", "🟢"
    elif total >= 5.0:
        result.label, result.color, result.emoji = "Tut / İzle", "#FF8C00", "🟡"
    elif total >= 3.5:
        result.label, result.color, result.emoji = "Dikkatli Ol","#FF5722", "🟠"
    else:
        result.label, result.color, result.emoji = "Riskli / Çık","#F44336","🔴"

    # ════════════════════════════════════════
    # KÂR ALMA ANALİZİ
    # ════════════════════════════════════════
    if buy_price and buy_price > 0 and price > 0:
        pct_ret = (price - buy_price) / buy_price * 100
        result.pct_return = pct_ret
        result.profit_action, result.profit_detail = _profit_logic(
            price, buy_price, pct_ret, rsi, target_price, stop_loss, atr_pct, total
        )
        result.profit_levels = _profit_levels(price, buy_price, target_price, stop_loss, atr)

    # ════════════════════════════════════════
    # POZİSYON EKLEME ANALİZİ
    # ════════════════════════════════════════
    result.add_action = _add_logic(total, price, ma20, ma50, rsi, rel_vol)
    result.add_levels = _add_levels(price, ma20, ma50, atr, buy_price)

    return result


# ─────────────────────────────────────────────
# KÂR ALMA KARAR LOJİĞİ
# ─────────────────────────────────────────────

def _profit_logic(
    price: float,
    buy_price: float,
    pct: float,
    rsi: float,
    target: Optional[float],
    stop: Optional[float],
    atr_pct: float,
    score: float,
) -> tuple[str, str]:

    # Stop-Loss vuruldu
    if stop and price <= stop:
        return ("🔴 STOP-LOSS HİTLENDİ",
                f"Fiyat ({price:.2f} ₺) stop seviyenize ({stop:.2f} ₺) ulaştı. "
                "Kayıpları sınırlandırmak için pozisyondan çıkmanızı değerlendirin.")

    # Stop'a çok yakın (<%5 mesafede)
    if stop and price <= stop * 1.05:
        return ("🟠 STOP'A YAKLIŞIYOR",
                f"Stop seviyenize ({stop:.2f} ₺) %{((price/stop-1)*100):.1f} mesafede. "
                "Stop'u gözden geçirin veya pozisyonu daraltın.")

    # Hedefe ulaşıldı
    if target and price >= target:
        return ("🎯 HEDEF ULAŞILDI — TAM ÇIK",
                f"Belirlediğiniz hedefe ({target:.2f} ₺) ulaşıldı! "
                f"Getiri: %{pct:.1f}. Tüm pozisyonu kapatmayı veya "
                "trailing stop ile takip etmeyi düşünebilirsiniz.")

    if pct >= 30:
        if not np.isnan(rsi) and rsi > 70:
            return ("🔴 KÂR AL — 1/2 POZİSYON SAT",
                    f"Getiri %{pct:.1f} ve RSI aşırı alım ({rsi:.0f}). "
                    "Pozisyonun yarısını satarak kârı güvenceye alın.")
        return ("🟡 KÂR ALMA ZAMANI",
                f"Güçlü getiri (%{pct:.1f}). Hedef fiyatınızı gözden geçirin; "
                "kısmi kâr alarak trailing stop belirleyin.")

    if pct >= 20:
        if not np.isnan(rsi) and rsi > 70:
            return ("🟡 KISMİ KÂR AL",
                    f"Getiri %{pct:.1f}, RSI aşırı alım ({rsi:.0f}). "
                    "1/3 – 1/2 satışla kâr güvenceye alınabilir.")
        if score >= 6.5:
            return ("🟢 TUT — HEDEF YUKARI ÇEK",
                    f"Getiri %{pct:.1f}, sinyal hâlâ güçlü ({score:.1f}/10). "
                    "Stop seviyenizi maliyet üzerine çekip trend sürsün.")
        return ("🟡 GÖZLEMLE",
                f"Getiri %{pct:.1f}. Sinyal orta düzey ({score:.1f}/10). "
                "Kısmi kâr alın, geri kalanı stop ile koruyun.")

    if pct >= 10:
        if not np.isnan(rsi) and rsi > 70:
            return ("🟡 KISMİ KÂR AL",
                    f"Getiri %{pct:.1f}, RSI aşırı alım ({rsi:.0f}). "
                    "1/4 satış yaparak riski azaltabilirsiniz.")
        if score >= 6.5:
            return ("🟢 TUT — Pozitif Sinyaller",
                    f"Getiri %{pct:.1f}, sinyal güçlü ({score:.1f}/10). "
                    "Trende devam edin, stop seviyesini yukarı taşıyın.")
        return ("🟡 İZLE",
                f"Getiri %{pct:.1f}. Sinyal nötr ({score:.1f}/10). "
                "Trend bozulursa kısmi çıkış planlayın.")

    if pct >= 5:
        return ("🟢 TUT",
                f"Pozitif bölgede (%{pct:.1f}). Devam eden trend var. "
                "Stop seviyenizi en azından başa başa çekin.")

    if pct > 0:
        return ("🟢 BEKLE",
                f"Küçük kâr (%{pct:.1f}). Yeterli hareket yok, pozisyona devam. "
                "Stop seviyenizi koruyun.")

    if pct > -5:
        return ("🟡 DİKKAT",
                f"Küçük zarar (%{pct:.1f}). Stop seviyenizi kontrol edin. "
                "Sinyal skoru: {:.1f}/10.".format(score))

    if pct > -10:
        return ("🟠 ZARAR YÖNETİMİ",
                f"Zarar: %{pct:.1f}. Stop-loss seviyenizi belirleyin veya gözden geçirin. "
                "Daha fazla zarar etmeden pozisyonu kısaltabilirsiniz.")

    return ("🔴 ACİL KARAR",
            f"Ciddi zarar: %{pct:.1f}. Stop-loss disiplini kritik. "
            "Pozisyondan çıkmayı veya büyük ölçüde küçültmeyi değerlendirin.")


# ─────────────────────────────────────────────
# KÂR ALMA SEVİYELERİ
# ─────────────────────────────────────────────

def _profit_levels(
    price: float,
    buy_price: float,
    target: Optional[float],
    stop: Optional[float],
    atr: float,
) -> list[PriceLevel]:
    levels: list[PriceLevel] = []

    if stop:
        pct = (stop - buy_price) / buy_price * 100
        levels.append(PriceLevel(
            "🛑 Stop-Loss", round(stop, 2), "Tümünü Sat",
            f"Zarar sınırı (maliyet üzeri %{pct:.1f})",
            price <= stop,
        ))

    for p, act in [(5, "1/4 Sat"), (10, "1/3 Sat"), (15, "1/3 Sat"), (20, "1/2 Sat"), (30, "Tümünü Sat")]:
        lp = buy_price * (1 + p / 100)
        levels.append(PriceLevel(
            f"🎯 +%{p} Hedef", round(lp, 2), act,
            f"Maliyet üzeri %{p} kâr",
            price >= lp,
        ))

    if target:
        pct_t = (target - buy_price) / buy_price * 100
        levels.append(PriceLevel(
            "⭐ Benim Hedefim", round(target, 2), "Tümünü Sat",
            f"Kişisel hedef fiyatı (maliyet üzeri %{pct_t:.1f})",
            price >= target,
        ))

    if atr and not np.isnan(atr):
        atr_tgt = price + 2 * atr
        levels.append(PriceLevel(
            "📊 2×ATR Projeksiyon", round(atr_tgt, 2), "1/3 Sat",
            "Volatilite tabanlı kâr hedefi",
            False,
        ))

    levels.sort(key=lambda x: x.price)
    return levels


# ─────────────────────────────────────────────
# EKLEME KARAR LOJİĞİ
# ─────────────────────────────────────────────

def _add_logic(
    score: float,
    price: float,
    ma20: float,
    ma50: float,
    rsi: float,
    rel_vol: float,
) -> str:
    near_ma20 = not np.isnan(ma20) and abs(price - ma20) / ma20 < 0.03
    near_ma50 = not np.isnan(ma50) and abs(price - ma50) / ma50 < 0.03

    if score >= 7.5:
        if near_ma20 or near_ma50:
            return "🟢 GÜÇLÜ EKLE — MA destek seviyesinde güçlü sinyal"
        return "🟢 EKLE — Sinyaller güçlü, pozisyon artırılabilir"

    if score >= 6.0:
        if not np.isnan(rsi) and rsi < 45:
            return "🟢 EKLE — Geri çekilme + pozitif sinyal kombinasyonu"
        if near_ma20 or near_ma50:
            return "🟢 EKLE — MA desteğinde duruyor"
        return "🟡 DİKKATLİ EKLE — Sinyal orta düzey, küçük ekleme yapılabilir"

    if score >= 4.5:
        if near_ma50:
            return "🟡 KÜÇÜK EKLE — MA50 desteğinde, ölçülü ekle"
        return "🟡 BEKLE — Daha güçlü sinyal bekleyin"

    return "🔴 EKLEME YAPMA — Sinyaller henüz yeterince güçlü değil"


# ─────────────────────────────────────────────
# EKLEME SEVİYELERİ
# ─────────────────────────────────────────────

def _add_levels(
    price: float,
    ma20: float,
    ma50: float,
    atr: float,
    buy_price: Optional[float],
) -> list[PriceLevel]:
    levels: list[PriceLevel] = []

    if not np.isnan(ma20):
        pct = (price - ma20) / price * 100
        levels.append(PriceLevel(
            "📊 MA20 Desteği", round(ma20, 2), "Küçük Ekle",
            f"Güncel fiyatın %{pct:.1f} altında — Kısa vadeli destek",
            abs(price - ma20) / ma20 < 0.02,
        ))

    if not np.isnan(ma50):
        pct = (price - ma50) / price * 100
        levels.append(PriceLevel(
            "📊 MA50 Desteği", round(ma50, 2), "Orta Ekle",
            f"Güncel fiyatın %{pct:.1f} altında — Swing trading ana desteği",
            abs(price - ma50) / ma50 < 0.02,
        ))

    if not np.isnan(atr):
        levels.append(PriceLevel(
            "📉 −1×ATR", round(price - atr, 2), "Küçük Ekle",
            "Normal volatilite geri çekilmesi",
            False,
        ))
        levels.append(PriceLevel(
            "📉 −2×ATR", round(price - 2 * atr, 2), "Büyük Ekle",
            "Derin geri çekilme — Agresif ekleme için",
            False,
        ))

    if buy_price and buy_price > 0:
        avg10 = buy_price * 0.90
        if avg10 < price:
            levels.append(PriceLevel(
                "💰 Maliyet −%10", round(avg10, 2), "Ortalama Düşür",
                "Maliyet fiyatınızın %10 altı",
                abs(price - avg10) / avg10 < 0.02,
            ))

    levels.sort(key=lambda x: x.price)
    return levels
