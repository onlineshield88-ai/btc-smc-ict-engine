"""
Bootstrap untuk seluruh test.

Menambahkan root project ke sys.path sehingga semua modul
(engine.py, core/, backend/, dll.) dapat di-import.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
