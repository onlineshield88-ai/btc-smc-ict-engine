import subprocess
import time

BACKEND = None
SERVICE = None


def start_backend():
    print("[START] Backend")
    return subprocess.Popen(
        ["python", "backend/app.py"]
    )


def start_service():
    print("[START] Service")
    return subprocess.Popen(
        ["python", "service.py"]
    )


BACKEND = start_backend()

time.sleep(2)

SERVICE = start_service()

print("[MANAGER] Running")

while True:

    if BACKEND.poll() is not None:
        print("[MANAGER] Backend stopped. Restarting...")
        BACKEND = start_backend()

    if SERVICE.poll() is not None:
        print("[MANAGER] Service stopped. Restarting...")
        SERVICE = start_service()

    time.sleep(5)
