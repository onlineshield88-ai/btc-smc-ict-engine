"""
main.py
================================================================================
UI utama aplikasi Kivy. Tiga tab:
  1. Dashboard - tampilkan hasil analisa terkini (live, refresh otomatis 30s)
  2. History   - daftar history sinyal dari SQLite (entry/SL/TP/score/status)
  3. Engine    - kontrol Start/Stop background service, info & peringatan

ARSITEKTUR:
Loop analisa kontinu berjalan di service.py (foreground service Android),
terpisah dari siklus hidup UI ini. UI hanya memanggil engine.run_analysis()
untuk refresh tampilan dashboard, dan membaca db.py untuk history.
================================================================================
"""


import os

try:
    with open("/storage/emulated/0/main_loaded.txt", "w") as fp:
        fp.write("main.py imported\n")
except Exception:
    pass

import threading


from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import (
    StringProperty, ListProperty, BooleanProperty
)

import engine
import db
from notify import send_notify

# -----------------------------------------------------------------------
# KV Language UI definition
# -----------------------------------------------------------------------
KV = """
<HistoryRow>:
    orientation: "vertical"
    size_hint_y: None
    height: "140dp"
    padding: "8dp", "4dp"
    spacing: "3dp"
    canvas.before:
        Color:
            rgba: 0.12, 0.13, 0.16, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8]

    BoxLayout:
        size_hint_y: None
        height: "28dp"
        Label:
            text: root.signal_text
            color: root.signal_color
            font_size: "16sp"
            halign: "left"
            valign: "middle"
            text_size: self.size
        Label:
            text: root.status_text
            font_size: "12sp"
            color: 0.7, 0.7, 0.7, 1
            halign: "right"
            valign: "middle"
            text_size: self.size

    Label:
        text: root.time_text + "    Score: " + root.score_text + "/80"
        font_size: "11sp"
        color: 0.55, 0.55, 0.55, 1
        halign: "left"
        valign: "middle"
        text_size: self.size
        size_hint_y: None
        height: "20dp"

    BoxLayout:
        size_hint_y: None
        height: "52dp"
        spacing: "6dp"
        BoxLayout:
            orientation: "vertical"
            spacing: "2dp"
            canvas.before:
                Color:
                    rgba: 0.18, 0.18, 0.22, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [6]
            Label:
                text: "Entry"
                font_size: "10sp"
                color: 0.55, 0.55, 0.55, 1
            Label:
                text: root.entry_text
                font_size: "13sp"
        BoxLayout:
            orientation: "vertical"
            spacing: "2dp"
            canvas.before:
                Color:
                    rgba: 0.18, 0.18, 0.22, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [6]
            Label:
                text: "Stop Loss"
                font_size: "10sp"
                color: 0.55, 0.55, 0.55, 1
            Label:
                text: root.sl_text
                font_size: "13sp"
                color: 0.92, 0.38, 0.38, 1
        BoxLayout:
            orientation: "vertical"
            spacing: "2dp"
            canvas.before:
                Color:
                    rgba: 0.18, 0.18, 0.22, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [6]
            Label:
                text: "TP1"
                font_size: "10sp"
                color: 0.55, 0.55, 0.55, 1
            Label:
                text: root.tp_text
                font_size: "13sp"
                color: 0.35, 0.85, 0.5, 1

    Label:
        text: "TP2 " + root.tp2_text + "   TP3 " + root.tp3_text
        font_size: "11sp"
        color: 0.45, 0.75, 0.55, 1
        halign: "left"
        valign: "middle"
        text_size: self.size
        size_hint_y: None
        height: "16dp"

    Label:
        text: "RR 1:" + root.rr_text + "    ATR: " + root.atr_text + "    " + root.regime_text
        font_size: "11sp"
        color: 0.5, 0.7, 0.9, 1
        halign: "left"
        valign: "middle"
        text_size: self.size
        size_hint_y: None
        height: "18dp"

<RootLayout>:
    orientation: "vertical"
    canvas.before:
        Color:
            rgba: 0.08, 0.09, 0.11, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: "48dp"
        padding: "12dp", "8dp"
        canvas.before:
            Color:
                rgba: 0.1, 0.11, 0.14, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "BTC SMC ICT Engine"
            font_size: "17sp"
            color: 0.95, 0.78, 0.25, 1
            halign: "left"
            text_size: self.size
            valign: "middle"
        Label:
            id: header_status
            text: "- - -"
            font_size: "11sp"
            color: 0.5, 0.5, 0.5, 1
            halign: "right"
            text_size: self.size
            valign: "middle"

    TabbedPanel:
        do_default_tab: False
        tab_height: "42dp"

        # ============================================================
        # TAB 1: DASHBOARD
        # ============================================================
        TabbedPanelItem:
            text: "Dashboard"
            ScrollView:
                BoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    padding: "12dp"
                    spacing: "10dp"

                    # Signal badge
                    BoxLayout:
                        size_hint_y: None
                        height: "58dp"
                        padding: "0dp"
                        spacing: "8dp"
                        canvas.before:
                            Color:
                                rgba: 0.12, 0.13, 0.16, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [10]
                        Label:
                            id: dash_signal
                            text: "Memuat..."
                            font_size: "24sp"
                            color: 0.85, 0.85, 0.85, 1
                        Label:
                            id: dash_score
                            text: ""
                            font_size: "13sp"
                            color: 0.6, 0.6, 0.6, 1
                            halign: "right"
                            text_size: self.size
                            valign: "middle"

                    # Entry / SL / TP
                    BoxLayout:
                        size_hint_y: None
                        height: "70dp"
                        spacing: "6dp"
                        BoxLayout:
                            orientation: "vertical"
                            spacing: "3dp"
                            canvas.before:
                                Color:
                                    rgba: 0.14, 0.16, 0.20, 1
                                RoundedRectangle:
                                    pos: self.pos
                                    size: self.size
                                    radius: [8]
                            Label:
                                text: "Entry"
                                font_size: "11sp"
                                color: 0.55, 0.55, 0.55, 1
                            Label:
                                id: dash_entry
                                text: "-"
                                font_size: "15sp"
                        BoxLayout:
                            orientation: "vertical"
                            spacing: "3dp"
                            canvas.before:
                                Color:
                                    rgba: 0.14, 0.16, 0.20, 1
                                RoundedRectangle:
                                    pos: self.pos
                                    size: self.size
                                    radius: [8]
                            Label:
                                text: "Stop Loss"
                                font_size: "11sp"
                                color: 0.55, 0.55, 0.55, 1
                            Label:
                                id: dash_sl
                                text: "-"
                                font_size: "15sp"
                                color: 0.92, 0.38, 0.38, 1
                        BoxLayout:
                            orientation: "vertical"
                            spacing: "3dp"
                            canvas.before:
                                Color:
                                    rgba: 0.14, 0.16, 0.20, 1
                                RoundedRectangle:
                                    pos: self.pos
                                    size: self.size
                                    radius: [8]
                            Label:
                                text: "Take Profit 1"
                                font_size: "11sp"
                                color: 0.55, 0.55, 0.55, 1
                            Label:
                                id: dash_tp
                                text: "-"
                                font_size: "15sp"
                                color: 0.35, 0.85, 0.5, 1

                    # RR + ATR row
                    Label:
                        id: dash_rr
                        text: "Belum ada sinyal aktif"
                        font_size: "13sp"
                        color: 0.5, 0.7, 0.9, 1
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: "22dp"

                    # Separator
                    Widget:
                        size_hint_y: None
                        height: "1dp"
                        canvas:
                            Color:
                                rgba: 0.22, 0.22, 0.25, 1
                            Rectangle:
                                pos: self.pos
                                size: self.size

                    # Indikator
                    Label:
                        text: "Indikator"
                        font_size: "13sp"
                        color: 0.75, 0.75, 0.75, 1
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: "24dp"

                    Label:
                        id: dash_indicators
                        text: "-"
                        font_size: "12sp"
                        color: 0.75, 0.75, 0.75, 1
                        size_hint_y: None
                        height: self.texture_size[1]
                        text_size: self.width, None
                        halign: "left"

                    # Separator
                    Widget:
                        size_hint_y: None
                        height: "1dp"
                        canvas:
                            Color:
                                rgba: 0.22, 0.22, 0.25, 1
                            Rectangle:
                                pos: self.pos
                                size: self.size

                    # Confluence
                    Label:
                        text: "Confluence"
                        font_size: "13sp"
                        color: 0.75, 0.75, 0.75, 1
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: "24dp"

                    Label:
                        id: dash_reasons
                        text: "-"
                        font_size: "12sp"
                        color: 0.65, 0.75, 0.65, 1
                        size_hint_y: None
                        height: self.texture_size[1]
                        text_size: self.width, None
                        halign: "left"

                    Label:
                        id: dash_last_update
                        text: ""
                        font_size: "10sp"
                        color: 0.4, 0.4, 0.4, 1
                        halign: "right"
                        text_size: self.size
                        size_hint_y: None
                        height: "18dp"

                    Button:
                        text: "Refresh sekarang"
                        size_hint_y: None
                        height: "44dp"
                        background_color: 0.18, 0.22, 0.32, 1
                        on_release: app.refresh_dashboard()

        # ============================================================
        # TAB 2: HISTORY
        # ============================================================
        TabbedPanelItem:
            text: "History"
            BoxLayout:
                orientation: "vertical"
                padding: "8dp"
                spacing: "6dp"

                BoxLayout:
                    size_hint_y: None
                    height: "42dp"
                    spacing: "8dp"
                    Label:
                        id: history_stats
                        text: "Memuat..."
                        font_size: "11sp"
                        color: 0.6, 0.6, 0.6, 1
                        halign: "left"
                        text_size: self.size
                        valign: "middle"
                    Button:
                        text: "Refresh"
                        size_hint_x: None
                        width: "80dp"
                        height: "36dp"
                        size_hint_y: None
                        background_color: 0.18, 0.22, 0.32, 1
                        on_release: app.refresh_history()

                RecycleView:
                    id: history_rv
                    viewclass: "HistoryRow"
                    bar_width: "4dp"
                    RecycleBoxLayout:
                        default_size: None, 140
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        orientation: "vertical"
                        spacing: "5dp"

        # ============================================================
        # TAB 3: ENGINE
        # ============================================================
        TabbedPanelItem:
            text: "Engine"
            ScrollView:
                BoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    padding: "16dp"
                    spacing: "14dp"

                    Label:
                        text: "Kontrol Background Engine"
                        font_size: "16sp"
                        color: 0.9, 0.9, 0.9, 1
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: "30dp"

                    Label:
                        id: engine_status_label
                        text: "Status: belum dimulai"
                        font_size: "13sp"
                        color: 0.6, 0.6, 0.6, 1
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: "26dp"

                    Button:
                        id: btn_toggle_engine
                        text: "Start Engine (Background)"
                        size_hint_y: None
                        height: "52dp"
                        background_color: 0.15, 0.45, 0.25, 1
                        on_release: app.toggle_engine()

                    Widget:
                        size_hint_y: None
                        height: "1dp"
                        canvas:
                            Color:
                                rgba: 0.22, 0.22, 0.25, 1
                            Rectangle:
                                pos: self.pos
                                size: self.size

                    Label:
                        text: "PENTING - Agar engine stabil di background:"
                        font_size: "13sp"
                        color: 0.9, 0.75, 0.3, 1
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: "24dp"

                    Label:
                        text: "Buka Setting > Apps > BTC SMC ICT Engine > Battery > pilih Unrestricted / Tanpa batas."
                        font_size: "12sp"
                        color: 0.65, 0.65, 0.65, 1
                        size_hint_y: None
                        height: self.texture_size[1]
                        text_size: self.width, None
                        halign: "left"

                    Label:
                        text: "Peringatan: Android tetap bisa menghentikan service paksa saat RAM sangat rendah atau battery saver agresif aktif (terutama Xiaomi / Oppo / Vivo). Alarm restart otomatis terjadwal tiap 15 menit sebagai jaring pengaman."
                        font_size: "12sp"
                        color: 0.6, 0.6, 0.6, 1
                        size_hint_y: None
                        height: self.texture_size[1]
                        text_size: self.width, None
                        halign: "left"

                    Widget:
                        size_hint_y: None
                        height: "8dp"
"""


# -----------------------------------------------------------------------
# HistoryRow: class Python dengan StringProperty/ListProperty
# WAJIB untuk RecycleView agar update data rows terdeteksi oleh Kivy
# -----------------------------------------------------------------------
class HistoryRow(BoxLayout):
    signal_text  = StringProperty("")
    score_text   = StringProperty("")
    entry_text   = StringProperty("-")
    sl_text      = StringProperty("-")
    tp_text      = StringProperty("-")
    tp2_text     = StringProperty("-")
    tp3_text     = StringProperty("-")
    rr_text      = StringProperty("-")
    atr_text     = StringProperty("-")
    regime_text  = StringProperty("")
    time_text    = StringProperty("")
    status_text  = StringProperty("OPEN")
    signal_color = ListProperty([1, 1, 1, 1])


class RootLayout(BoxLayout):
    pass


# -----------------------------------------------------------------------
# Main App
# -----------------------------------------------------------------------
class BTCEngineApp(App):
    engine_running = BooleanProperty(False)

    def build(self):
        db.init_db()
        return Builder.load_string(KV)

    def on_start(self):
        Clock.schedule_once(lambda dt: self.refresh_dashboard(), 0.8)
        Clock.schedule_once(lambda dt: self.refresh_history(),   1.0)
        # Auto-refresh dashboard setiap 30 detik saat app dibuka
        Clock.schedule_interval(lambda dt: self.refresh_dashboard(), 30)

    # ------------------------------------------------------------------
    # DASHBOARD
    # ------------------------------------------------------------------
    def refresh_dashboard(self):
        self.root.ids.dash_last_update.text = "Mengambil data..."
        threading.Thread(target=self._analysis_thread, daemon=True).start()

    def _analysis_thread(self):
        try:
            result = engine.run_analysis()
        except Exception as e:
            result = {"error": str(e)}
        Clock.schedule_once(lambda dt: self._apply_dashboard(result))

    def _apply_dashboard(self, result):
        ids = self.root.ids

        if result.get("error"):
            ids.dash_signal.text  = "Error"
            ids.dash_signal.color = (0.9, 0.45, 0.2, 1)
            ids.dash_score.text   = str(result["error"])
            ids.dash_last_update.text = "Gagal mengambil data"
            return

        signal = result["signal"]
        ids.dash_signal.text  = signal
        ids.dash_signal.color = (
            (0.35, 0.85, 0.5,  1) if "BUY"  in signal else
            (0.92, 0.38, 0.38, 1) if "SELL" in signal else
            (0.75, 0.75, 0.75, 1)
        )

        ids.dash_score.text = f"Score {result['score']}/80"

        plan = result.get("plan")
        if plan:
            ids.dash_entry.text = f"${plan['entry']:,.2f}"
            ids.dash_sl.text    = f"${plan['stop_loss']:,.2f}"
            ids.dash_tp.text    = f"${plan.get('tp1', plan['take_profit']):,.2f}"
            tp2_str = f"  TP2 ${plan['tp2']:,.0f}" if plan.get("tp2") else ""
            tp3_str = f"  TP3 ${plan['tp3']:,.0f}" if plan.get("tp3") else ""
            ids.dash_rr.text    = (
                f"RR 1:{plan['risk_reward']}  |  Risk ${plan['risk_usd_per_btc']:.0f}  |  "
                f"ATR {plan['atr_used']:.1f}{tp2_str}{tp3_str}"
            )
        else:
            ids.dash_entry.text = "-"
            ids.dash_sl.text    = "-"
            ids.dash_tp.text    = "-"
            ids.dash_rr.text    = "Belum ada sinyal aktif"

        fibo_str = ""
        if result.get("fibo_zone"):
            in_ote = result.get("fibo_in_ote")
            in_ote_str = "YA" if str(in_ote) == "True" else "tidak"
            fibo_str = (
                f"\nFibo: {result['fibo_zone']} (leg {result.get('fibo_direction','-')})  "
                f"in OTE: {in_ote_str}"
            )

        regime = result.get("volatility_regime", "-")
        regime_label = {
            "HIGH_VOLATILITY": "Volatilitas Tinggi",
            "CHOPPY": "Choppy / Sideways",
            "TRENDING": "Trending Normal",
        }.get(regime, regime)

        ids.dash_indicators.text = (
            f"Close: ${result['close']:,.2f}   ATR(14): {result.get('atr','-')}\n"
            f"RSI(14): {result['rsi']}   RSI(2): {result.get('rsi2','-')}\n"
            f"WMA9: {result.get('wma_fast','-')}  WMA119: {result.get('wma_slow','-')}\n"
            f"Regime: {regime_label}\n"
            f"Bias 1H: {result['bias_1h']}   Bias 4H: {result['bias_4h']}"
            f"{fibo_str}"
        )

        reasons = result.get("reasons") or []
        ids.dash_reasons.text = (
            "\n".join(f"• {r}" for r in reasons)
            if reasons else "Belum ada confluence signifikan saat ini"
        )

        from datetime import datetime
        ids.dash_last_update.text = f"Update: {datetime.now().strftime('%H:%M:%S')}"
        ids.header_status.text    = f"${result['close']:,.0f}"

    # ------------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------------
    def refresh_history(self):
        threading.Thread(target=self._history_thread, daemon=True).start()

    def _history_thread(self):
        try:
            rows  = db.get_history(limit=100)
            stats = db.get_stats()
        except Exception as e:
            rows, stats = [], {"error": str(e)}
        Clock.schedule_once(lambda dt: self._apply_history(rows, stats))

    def _apply_history(self, rows, stats):
        ids = self.root.ids

        data = []
        for h in rows:
            signal = h["signal"]
            color  = (
                (0.35, 0.85, 0.5,  1) if "BUY"  in signal else
                (0.92, 0.38, 0.38, 1) if "SELL" in signal else
                (0.75, 0.75, 0.75, 1)
            )
            entry  = h["entry_price"]
            sl     = h["stop_loss"]
            tp     = h["take_profit"]
            tp2    = h.get("tp2")
            tp3    = h.get("tp3")
            rr     = h.get("risk_reward")
            atr    = h.get("atr_used")
            regime = h.get("volatility_regime")
            data.append({
                "signal_text":  signal,
                "score_text":   str(h["score"]),
                "entry_text":   f"${entry:,.2f}"  if entry is not None else "-",
                "sl_text":      f"${sl:,.2f}"     if sl    is not None else "-",
                "tp_text":      f"${tp:,.2f}"     if tp    is not None else "-",
                "tp2_text":     f"${tp2:,.0f}"    if tp2   is not None else "-",
                "tp3_text":     f"${tp3:,.0f}"    if tp3   is not None else "-",
                "rr_text":      f"{rr:.2f}"       if rr    is not None else "-",
                "atr_text":     f"{atr:.1f}"      if atr   is not None else "-",
                "regime_text":  regime or "",
                "time_text":    h["candle_time"],
                "status_text":  h["status"],
                "signal_color": list(color),
            })
        ids.history_rv.data = data

        if stats.get("error"):
            ids.history_stats.text = f"DB error: {stats['error']}"
        else:
            wr = f"{stats['win_rate']:.1f}%" if stats["win_rate"] is not None else "N/A"
            ids.history_stats.text = (
                f"Total: {stats['total']}  Open: {stats['open']}  "
                f"TP: {stats['tp_hit']}  SL: {stats['sl_hit']}  WR: {wr}"
            )

    # ------------------------------------------------------------------
    # ENGINE START / STOP
    # ------------------------------------------------------------------
    def toggle_engine(self):
        ids = self.root.ids
        if not self.engine_running:
            ok = self._start_service()
            self.engine_running = True
            ids.btn_toggle_engine.text        = "Stop Engine"
            ids.btn_toggle_engine.background_color = (0.45, 0.15, 0.15, 1)
            ids.engine_status_label.text      = "Status: berjalan di background" if ok \
                else "Status: berjalan di thread (mode desktop)"
            send_notify("Engine SMC ICT dimulai", title_suffix="Started")
        else:
            self._stop_service()
            self.engine_running = False
            ids.btn_toggle_engine.text        = "Start Engine (Background)"
            ids.btn_toggle_engine.background_color = (0.15, 0.45, 0.25, 1)
            ids.engine_status_label.text      = "Status: dihentikan"

    def _start_service(self):
        """Coba start foreground service Android. Fallback thread di desktop."""
        try:
            from jnius import autoclass
            mActivity   = autoclass("org.kivy.android.PythonActivity").mActivity
            pkg         = mActivity.getPackageName()
            ServiceCls  = autoclass(f"{pkg}.ServiceEngine")
            ServiceCls.start(mActivity, "")
            self._svc_cls      = ServiceCls
            self._svc_activity = mActivity
            import restart_alarm
            restart_alarm.schedule_restart_check(interval_minutes=15)
            return True
        except Exception as e:
            print(f"[main] Android service tidak tersedia ({e}), pakai thread fallback")
            import service as svc
            self._stop_flag = False
            def _loop():
                import time
                while not self._stop_flag:
                    try:
                        svc.run_cycle()
                    except Exception as ex:
                        print(f"[desktop_loop] {ex}")
                    time.sleep(svc.REFRESH_SECONDS)
            threading.Thread(target=_loop, daemon=True).start()
            return False

    def _stop_service(self):
        try:
            if hasattr(self, "_svc_cls"):
                self._svc_cls.stop(self._svc_activity)
            import restart_alarm
            restart_alarm.cancel_restart_check()
        except Exception as e:
            print(f"[main] stop service: {e}")
        self._stop_flag = True


if __name__ == "__main__":
    BTCEngineApp().run()
