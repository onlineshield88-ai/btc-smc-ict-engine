import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import core.indicators

    print("=" * 60)
    print("CORE IMPORT")
    print("=" * 60)

    print("SUCCESS")

except Exception as e:
    print(type(e).__name__)
    print(e)
