import sys, os, traceback

LOG_PATH = "/sdcard/btc_debug.log"

def write_log(msg):
    with open(LOG_PATH, "a") as f:
        f.write(msg + "\n")

write_log("=== App starting ===")

try:
    write_log("Import kivy...")
    from kivy.app import App
    write_log("Kivy OK")
    
    write_log("Import engine...")
    import engine
    write_log("Engine OK")
    
    write_log("Import db...")
    import db
    write_log("DB OK")
    
    write_log("Import main...")
    from main import BTCEngineApp
    write_log("Main OK")
    
    write_log("Starting app...")
    BTCEngineApp().run()
    write_log("App closed normally")

except Exception as e:
    write_log("ERROR: " + str(e))
    write_log(traceback.format_exc())
