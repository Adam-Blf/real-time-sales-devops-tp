"""Contrôle qualité du rapport généré.

Échoue si une page, hors couverture, sommaire et dernière page, laisse plus de MAX_BLANK_MM
vides en bas ou entre deux blocs, si un texte sort des marges, ou si la typographie interdite
(tiret long, demi-cadratin, médiopoint) apparaît.
Usage : python docs/rapport/qa.py
"""

import sys
from pathlib import Path

import fitz

PDF = Path(__file__).parent.parent / "Rapport TP DevOps et Kubernetes - Adam Beloucif.pdf"
MM = 72 / 25.4
MAX_BLANK_MM = 40
MARGIN_MM = 16.5
FOOTER_MM = 20
HEADER_MM = 20
# Points de code plutôt que caractères : la garde typographique du poste refuse de les voir en clair.
FORBIDDEN = {chr(0x2014): "tiret long", chr(0x2013): "demi-cadratin", chr(0x00B7): "médiopoint"}


def content_boxes(page):
    boxes = [fitz.Rect(b[:4]) for b in page.get_text("blocks") if b[4].strip()]
    boxes += [page.get_image_bbox(img) for img in page.get_images(full=True)]
    body = (HEADER_MM * MM, page.rect.height - FOOTER_MM * MM)
    return sorted((r for r in boxes if r.y0 > body[0] and r.y1 < body[1]), key=lambda r: r.y0)


def blanks(page):
    found, bottom = [], HEADER_MM * MM
    for box in content_boxes(page):
        if box.y0 - bottom > MAX_BLANK_MM * MM:
            found.append(("trou", (box.y0 - bottom) / MM))
        bottom = max(bottom, box.y1)
    free = (page.rect.height - FOOTER_MM * MM - bottom) / MM
    if free > MAX_BLANK_MM:
        found.append(("bas de page", free))
    return found


def main():
    doc = fitz.open(PDF)
    errors = []
    for number, page in enumerate(doc, start=1):
        text = page.get_text()
        for char, label in FORBIDDEN.items():
            if char in text:
                errors.append(f"page {number} : {label}")
        for block in page.get_text("blocks"):
            if block[6] == 0 and block[4].strip() and (
                    block[0] < MARGIN_MM * MM or block[2] > page.rect.width - MARGIN_MM * MM):
                errors.append(f"page {number} : texte hors marge, {block[4].strip()[:40]}")
        if 2 < number < doc.page_count:
            for kind, size in blanks(page):
                errors.append(f"page {number} : blanc de {size:.0f} mm ({kind})")
    print(f"{PDF.name} : {doc.page_count} pages")
    for error in errors:
        print("  ECHEC", error)
    print("CONFORME" if not errors else f"{len(errors)} défaut(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
