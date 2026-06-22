# 📈 BIST Portföy Asistanı

Borsa İstanbul (BIST) hisseleri için teknik analiz, sinyal motoru ve karar destek sistemi.
Streamlit Cloud üzerinde **ücretsiz** olarak çalışır.

---

## 🖥️ Özellikler

| Modül | Açıklama |
|-------|----------|
| 📊 Portföy | Hisse ekleme/çıkarma, maliyet takibi, P&L özeti |
| 🔍 Analiz | MA20/50/200, RSI, MACD, ADX, ATR, BB – gösterge tablosu |
| 📡 Sinyaller | 10 puanlık skorlama; Güçlü Al → Riskli/Çık |
| 💰 Kâr Alma | Kademeli seviyelere göre "tam çık / kısmi sat / bekle" önerisi |
| ➕ Ekleme | MA & ATR bazlı geri çekilme seviyeleri, ortalama düşürme hesabı |
| 📈 Grafik | Mum + hacim + RSI + MACD – interaktif Plotly grafik |
| ⚙️ Ayarlar | CSV dışa/içe aktarım, hisse güncelleme |

---

## 🚀 Streamlit Cloud Kurulumu (5 Dakika)

### 1 — Repoyu Fork'layın veya Oluşturun

```
GitHub → New Repository → "bist-portfolio"
```

Tüm dosyaları bu yapıyla yükleyin:

```
bist-portfolio/
├── app.py
├── data_loader.py
├── indicators.py
├── signals.py
├── portfolio.py
├── requirements.txt
├── README.md
└── .streamlit/
    └── config.toml
```

### 2 — Streamlit Cloud'a Bağlayın

1. [share.streamlit.io](https://share.streamlit.io) → **New app**
2. GitHub reponuzu seçin
3. **Main file path:** `app.py`
4. **Deploy!** → birkaç dakika içinde hazır

> Gizli API anahtarı veya ek konfigürasyon gerekmez.

### 3 — Yerel Çalıştırma

```bash
git clone https://github.com/<kullanici>/bist-portfolio.git
cd bist-portfolio
pip install -r requirements.txt
streamlit run app.py
```

---

## 📐 Sinyal Puanlama Sistemi

| Bileşen | Maks Puan | Kural |
|---------|-----------|-------|
| Uzun Vadeli Trend | 1 | Fiyat > MA200 |
| Orta Vadeli Trend | 1 | Fiyat > MA50 |
| MA Hizalaması | 1 | MA20 > MA50 > MA200 |
| RSI Momentumu | 2 | 50–65 ideal, <30 / >75 risk |
| MACD Sinyali | 1 | MACD > Signal satırı |
| MACD Histogramı | 1 | Histogram pozitif & artıyor |
| Hacim Gücü | 2 | RelVol ≥ 1.5x = güçlü ilgi |
| Giriş Kalitesi | 1 | Fiyat MA20'nin 0–6% üstünde |
| **TOPLAM** | **10** | |

### Sinyal Etiketleri

| Skor | Etiket | Renk |
|------|--------|------|
| 8.0 – 10 | Güçlü Al | 🟢 |
| 6.5 – 8.0 | Al / Ekle | 🟢 |
| 5.0 – 6.5 | Tut / İzle | 🟡 |
| 3.5 – 5.0 | Dikkatli Ol | 🟠 |
| 0 – 3.5 | Riskli / Çık | 🔴 |

---

## 💰 Kâr Alma Mantığı

Uygulama şu faktörleri birlikte değerlendirerek öneri üretir:

- **Getiri yüzdesi** (alış fiyatına göre)
- **RSI** (aşırı alım bölgesinde → kâr al)
- **Hedef fiyat** (kullanıcı tarafından tanımlanmış)
- **Stop-loss seviyesi** (fiyat ≤ stop → acil çıkış)
- **Sinyal skoru** (trend güçlüyse tutma önerisi)

Kâr alma seviyeleri: **+%5 → 1/4 sat, +%10 → 1/3 sat, +%20 → 1/2 sat, +%30 → tümünü sat**

---

## ➕ Ekleme / Ortalama Düşürme Mantığı

| Seviye | Açıklama |
|--------|----------|
| MA20 Desteği | Kısa vadeli geri çekilme desteği |
| MA50 Desteği | Swing trading ana destek noktası |
| −1×ATR | Normal volatilite geri çekilmesi |
| −2×ATR | Derin geri çekilme, agresif ekleme |
| Maliyet −%10 | Ortalama maliyet düşürme fırsatı |

---

## 📊 Teknik Göstergeler

| Gösterge | Parametre | Yöntem |
|----------|-----------|--------|
| MA | 20 / 50 / 200 | Basit hareketli ortalama |
| RSI | 14 dönem | Wilder yumuşatması |
| MACD | 12 / 26 / 9 | EMA tabanlı |
| ATR | 14 dönem | Wilder yumuşatması |
| Bollinger | 20 dönem, 2σ | Standart sapma |
| ADX | 14 dönem | Wilder yöntemi |
| RelVol | 20 günlük ortalama | Göreceli hacim |

> Tüm göstergeler sıfırdan `pandas` / `numpy` ile hesaplanmaktadır.
> Harici TA kütüphanesi kullanılmamaktadır.

---

## 🗂️ Proje Yapısı

```
app.py           — Ana Streamlit uygulaması, UI, sekmeler
data_loader.py   — yfinance veri çekme, önbellekleme
indicators.py    — Teknik gösterge hesaplamaları
signals.py       — 10 puanlık sinyal motoru, kâr/ekleme önerileri
portfolio.py     — Portföy yönetimi, CSV export/import
requirements.txt — Python bağımlılıkları
.streamlit/
  config.toml    — Koyu tema konfigürasyonu
```

---

## ⚠️ Önemli Notlar

1. **Veri Kaynağı:** Yahoo Finance (`yfinance`) — ücretsiz, ücretli API gerekmez
2. **Veri Gecikmesi:** Kapanış fiyatları gerçek zamanlı değil; gün içinde 15–20 dk gecikmeli olabilir
3. **Portföy Kalıcılığı:** Veriler oturum içinde saklanır. Kalıcı kullanım için **CSV dışa aktarın**
4. **Hata Toleransı:** Geçersiz ticker veya veri eksikliğinde uygulama çökmez, uyarı verir

---

## ⚖️ Yasal Uyarı

Bu uygulama yalnızca **analiz ve karar destek** amacıyla hazırlanmıştır.
**Yatırım tavsiyesi niteliği taşımaz.**
Piyasalarda işlem yapmak risk içerir; tüm yatırım kararları kullanıcının sorumluluğundadır.

---

*Geliştirici notu: Uygulama açık kaynak ve kişisel kullanım içindir.*
