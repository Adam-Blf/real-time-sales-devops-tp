"""Génère le rapport PDF des deux TP.

Usage : python docs/rapport/build.py
Les captures se refont avec capture.py, plateforme Jenkins et SonarQube démarrée.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from content import SPEC  # noqa: E402
from report_engine import build  # noqa: E402

OUT = HERE.parent / "Rapport TP DevOps et Kubernetes - Adam Beloucif.pdf"

if __name__ == "__main__":
    pages = build(SPEC, OUT)
    print(f"{pages} pages -> {OUT.name} ({OUT.stat().st_size / 1_000_000:.2f} Mo)")
