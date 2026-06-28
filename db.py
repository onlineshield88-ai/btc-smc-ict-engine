"""
db.py
================================================================================
Modul SQLite untuk menyimpan history sinyal trading (entry/SL/TP/score) secara
permanen dan offline di perangkat. Dipakai oleh main.py (tampilkan history)
dan service.py (simpan sinyal baru saat terdeteksi).
================================================================================
"""

import sqlite3
import os
import threading
from config import DATABASE

# Development mode
DEBUG_SAVE_ALL_SIGNALS = True

_lock = threading.Lock()


def get_db_path():
    """
    Path database. Di Android, app punya folder data privat sendiri.
    os.environ['ANDROID_PRIVATE'] di-set otomatis oleh python-for-android
    saat app berjalan sebagai APK. Fallback ke folder lokal untuk testing
    di desktop/non-Android.
    """
    android_private = os.environ.get("ANDROID_PRIVATE")
    if android_private:
        base_dir = android_private
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DATABASE)


def get_connection():
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Buat tabel jika belum ada. Aman dipanggil berkali-kali."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candle_time TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    tp1 REAL,
                    tp2 REAL,
                    tp3 REAL,
                    risk_reward REAL,
                    atr_used REAL,
                    volatility_regime TEXT,
                    reasons TEXT,
                    bias_1h TEXT,
                    bias_4h TEXT,
                    fibo_zone TEXT,
                    status TEXT DEFAULT 'OPEN',
                    closed_price REAL,
                    closed_at TEXT,
                    pnl_percent REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_candle_time
                ON signal_history (candle_time)
            """)
            # Migrasi aman untuk DB lama (v1) yang belum punya kolom baru -
            # ALTER TABLE ADD COLUMN akan gagal jika kolom sudah ada, jadi
            # dibungkus try/except per kolom agar idempotent.
            new_columns = [
                ("tp1", "REAL"), ("tp2", "REAL"), ("tp3", "REAL"),
                ("volatility_regime", "TEXT"),
            ]
            for col_name, col_type in new_columns:
                try:
                    conn.execute(f"ALTER TABLE signal_history ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass  # kolom sudah ada
            conn.commit()
        finally:
            conn.close()


def insert_signal(data):
    """
    Simpan sinyal baru ke history. `data` adalah dict hasil dari
    engine.run_analysis() yang sudah punya signal != 'NO SIGNAL / WAIT'.
    Mengembalikan True jika berhasil disimpan, False jika sudah ada
    (duplikat candle_time + signal, mencegah double entry tiap cycle).
    """
    if (
        data.get("signal", "NO SIGNAL / WAIT") == "NO SIGNAL / WAIT"
        and not DEBUG_SAVE_ALL_SIGNALS
    ):
        return False

    plan = data.get("plan") or {}
    reasons_str = " | ".join(data.get("reasons", []))

    with _lock:
        conn = get_connection()
        try:
            existing = conn.execute(
                "SELECT id FROM signal_history WHERE candle_time = ? AND signal = ?",
                (data["time"], data["signal"])
            ).fetchone()
            if existing:
                return False

            from datetime import datetime
            conn.execute("""
                INSERT INTO signal_history
                (candle_time, created_at, symbol, signal, score, entry_price,
                 stop_loss, take_profit, tp1, tp2, tp3, risk_reward, atr_used,
                 volatility_regime, reasons, bias_1h, bias_4h, fibo_zone, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, (
                data["time"], datetime.now().isoformat(), "BTCUSDT",
                data["signal"], data["score"],
                plan.get("entry"), plan.get("stop_loss"), plan.get("take_profit"),
                plan.get("tp1"), plan.get("tp2"), plan.get("tp3"),
                plan.get("risk_reward"), plan.get("atr_used"),
                data.get("volatility_regime"), reasons_str,
                data.get("bias_1h"), data.get("bias_4h"), data.get("fibo_zone")
            ))
            conn.commit()
            return True
        finally:
            conn.close()


def get_history(limit=50):
    """Ambil history terbaru, urut dari yang paling baru."""
    with _lock:
        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM signal_history
                ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()


def update_status(signal_id, status, closed_price=None, pnl_percent=None):
    """
    Update status sinyal lama (mis. saat user manual tandai TP_HIT / SL_HIT / CANCELLED).
    Auto-tracking TP/SL hit secara live membutuhkan price monitoring berkelanjutan,
    untuk versi ini status diupdate manual oleh user dari UI History.
    """
    with _lock:
        conn = get_connection()
        try:
            from datetime import datetime
            conn.execute("""
                UPDATE signal_history
                SET status = ?, closed_price = ?, pnl_percent = ?, closed_at = ?
                WHERE id = ?
            """, (status, closed_price, pnl_percent, datetime.now().isoformat(), signal_id))
            conn.commit()
        finally:
            conn.close()


def get_stats():
    """Statistik ringkas: total sinyal, win rate dari yang sudah ditandai closed."""
    with _lock:
        conn = get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) c FROM signal_history").fetchone()["c"]
            tp_hit = conn.execute(
                "SELECT COUNT(*) c FROM signal_history WHERE status = 'TP_HIT'"
            ).fetchone()["c"]
            sl_hit = conn.execute(
                "SELECT COUNT(*) c FROM signal_history WHERE status = 'SL_HIT'"
            ).fetchone()["c"]
            open_count = conn.execute(
                "SELECT COUNT(*) c FROM signal_history WHERE status = 'OPEN'"
            ).fetchone()["c"]

            closed = tp_hit + sl_hit
            win_rate = (tp_hit / closed * 100) if closed > 0 else None

            return {
                "total": total, "tp_hit": tp_hit, "sl_hit": sl_hit,
                "open": open_count, "win_rate": win_rate
            }
        finally:
            conn.close()


def export_to_csv(filepath=None):
    """
    Export seluruh history ke file CSV (diadopsi dari fitur CSV logger
    smclite v7.6.8 - di sini SQLite tetap menjadi source-of-truth tunggal,
    CSV hanya format export untuk dibuka di Excel/Google Sheets atau
    diolah lebih lanjut untuk backtest statistik eksternal).

    Jika filepath tidak diberikan, otomatis pakai folder data privat app
    (sama seperti get_db_path) dengan nama signals_export_<timestamp>.csv.
    Mengembalikan path file yang berhasil ditulis, atau None jika gagal.
    """
    import csv
    from datetime import datetime

    if filepath is None:
        android_private = os.environ.get("ANDROID_PRIVATE")
        base_dir = android_private if android_private else os.path.dirname(os.path.abspath(__file__))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(base_dir, f"signals_export_{ts}.csv")

    with _lock:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM signal_history ORDER BY id ASC").fetchall()
            if not rows:
                return None

            fieldnames = rows[0].keys()
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))

            return filepath
        except Exception as e:
            print(f"[db] export_to_csv gagal: {e}")
            return None
        finally:
            conn.close()
