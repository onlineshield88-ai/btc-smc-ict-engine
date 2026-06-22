# BTC SMC ICT Engine v2

Aplikasi Android analisa sinyal trading BTC/USDT Futures berbasis Smart Money Concept (SMC) + ICT + WMA + RSI + Fibonacci.

## Cara Build APK via GitHub Actions

### 1. Upload ke GitHub
- Buat repository baru di [github.com](https://github.com) → klik **New repository**
- Nama repo bebas, misal: `btc-smc-ict-engine`
- Pilih **Private** (disarankan)
- Klik **Create repository**

### 2. Upload semua file
Di halaman repo yang baru dibuat, klik **uploading an existing file**, lalu drag & drop semua file dari folder ini termasuk folder `.github/`.

### 3. Jalankan build
- Buka tab **Actions** di repo
- Klik workflow **Build APK Android**
- Klik tombol **Run workflow** → **Run workflow**
- Tunggu ±30-45 menit

### 4. Download APK
- Setelah workflow selesai (centang hijau ✅)
- Klik nama workflow → scroll ke bawah bagian **Artifacts**
- Klik **BTC-SMC-ICT-Engine-APK** untuk download

---

## Fitur Engine

- **SMC**: Order Block, FVG, Inverse FVG, BOS, CHoCH, Liquidity Sweep
- **ICT**: OTE Fibonacci 0.618–0.79, Premium/Discount Zone
- **WMA**: Cross WMA9 vs WMA119
- **RSI**: RSI(14) dan RSI(2) untuk momentum
- **Multi-Timeframe**: Bias 1H + 4H sebagai filter
- **Score System**: 0–80 poin, sinyal muncul jika ≥40
- **History**: Tersimpan di SQLite lokal di HP
- **Background Service**: Engine tetap jalan meski app diminimize
