"""Moteur de rapport PDF a la charte EFREI.

FPDF2 uniquement (regle Adam : jamais reportlab ni weasyprint).
Palette efrei.fr : navy #163767, rose #FF43B8, navy fonce #051832, bleu #0C78B4.
Marges 18 mm, superieures au minimum de 15 mm exige, pour garantir qu'aucun
texte ne soit coupe.

Typographie : Gilroy ExtraBold pour les titres si la police se charge, sinon
Segoe UI Bold. Corps en Segoe UI, qui couvre l'integralite des accents francais
et le signe euro.
"""
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import Align, XPos, YPos
try:
    from fpdf import TitleStyle
except ImportError:  # fpdf2 recent
    from fpdf.fonts import TitleStyle

# ---------------------------------------------------------------- charte
NAVY = (22, 55, 103)        # #163767
ROSE = (255, 67, 184)       # #FF43B8
DARK = (5, 24, 50)          # #051832
BLUE = (12, 120, 180)       # #0C78B4
GREY = (108, 117, 125)
LIGHT = (240, 243, 248)
RULE = (214, 221, 232)
WHITE = (255, 255, 255)

MARGIN = 18
MIN_FIGURE_RATIO = 0.62   # reduction maximale acceptee pour eviter un blanc en bas de page
ASSETS = Path(__file__).parent / "assets"


def optimise_image(path, max_w=1800, seuil_octets=150_000):
    """Image allegee pour l'integration dans le PDF.

    fpdf2 embarque les PNG a pleine resolution : une capture 3360 px de 4,4 Mo
    pesait autant dans le rapport, qui depassait alors les 5 Mo acceptes par les
    portails de candidature. On borne la largeur a 1800 px, suffisante pour une
    figure de 174 mm, et on passe en JPEG les images lourdes (captures d'ecran).
    Les graphiques legers restent en PNG, ou le JPEG baverait sur les traits fins.
    Le JPEG est transmis en octets : fpdf2 l'insere alors tel quel (DCT) au lieu
    de le decompresser puis de le recompresser en Flate.
    """
    import io
    from PIL import Image
    path = Path(path)
    with Image.open(path) as im:
        im.load()
        lourd = path.stat().st_size > seuil_octets
        if im.width <= max_w and not lourd:
            return str(path)
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)),
                           Image.LANCZOS)
        buf = io.BytesIO()
        if lourd:
            fond = Image.new("RGB", im.size, (255, 255, 255))
            fond.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
            fond.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
        else:
            im.save(buf, "PNG", optimize=True)
        buf.seek(0)
        return buf


def wrapped_lines(pdf, w, h, txt):
    """Nombre de lignes qu'occupera un texte, sans l'ecrire.

    `split_only` a ete retire de fpdf2 2.8, le remplacant est le couple
    dry_run + output=LINES.
    """
    return pdf.multi_cell(w, h, txt, dry_run=True, output="LINES")

FONTS = ASSETS / "fonts"

# Montserrat, demandee explicitement. Les fichiers sont embarques dans le depot
# (assets/fonts) et non appeles depuis un CDN, conformement a la regle
# d'assets locaux : un livrable doit se regenerer sans acces reseau.
FONT_CANDIDATES = {
    "body": [
        ("Mont", "", str(FONTS / "Montserrat-Regular.ttf")),
        ("Mont", "B", str(FONTS / "Montserrat-Bold.ttf")),
        ("Mont", "I", str(FONTS / "Montserrat-Italic.ttf")),
    ],
    "mono": [("Consola", "", r"C:\Windows\Fonts\consola.ttf"),
             ("Consola", "B", r"C:\Windows\Fonts\consolab.ttf")],
    "display": [("MontBlack", "", str(FONTS / "Montserrat-ExtraBold.ttf"))],
}


class EfreiReport(FPDF):
    """Rapport paginne avec en-tete et pied de page a la charte."""

    def __init__(self, title, subtitle, block_label):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_title = title
        self.doc_subtitle = subtitle
        self.block_label = block_label
        self.cover_done = False
        self.toc_truncated = False
        self.toc_entries = []
        self.chapter = ""
        self.display_ok = False

        self.set_margins(MARGIN, 22, MARGIN)
        self.set_auto_page_break(True, margin=20)
        self._load_fonts()
        # Aucun style de section : avec des styles, start_section redessine le
        # titre a sa propre marge, ce qui produisait un doublon hors marges.
        # Sans styles, start_section n'alimente que le volet de signets.
        self.set_title(title)
        self.set_author("Adam Beloucif")
        self.set_creator("EFREI Paris - Mastère Data Engineering et IA")

    # ------------------------------------------------------------ polices
    def _load_fonts(self):
        for key, items in FONT_CANDIDATES.items():
            for family, style, path in items:
                if not Path(path).exists():
                    continue
                try:
                    self.add_font(family, style, path)
                    if key == "display":
                        self.display_ok = True
                except Exception:
                    if key == "display":
                        self.display_ok = False

    def f_body(self, style="", size=10.5):
        # Aucune reduction. Montserrat a une hauteur d'x importante mais un oeil
        # etroit en petit corps : sous 10 pt le document devient penible a lire
        # sur papier. Les tailles sont donc prises telles quelles.
        self.set_font("Mont", style, size)

    def f_display(self, size=20):
        if self.display_ok:
            self.set_font("MontBlack", "", size)
        else:
            self.set_font("Mont", "B", size)

    def f_mono(self, size=8.2):
        self.set_font("Consola", "", size)

    def _fit(self, txt, width):
        """Tronque un texte pour qu'il tienne dans la largeur donnee.

        `cell` ne coupe pas et ne renvoie pas a la ligne : un texte trop long
        deborde silencieusement sur ce qui suit, d'ou des superpositions.
        """
        txt = (txt or "").strip()
        if not txt or self.get_string_width(txt) <= width:
            return txt
        while txt and self.get_string_width(txt + "...") > width:
            txt = txt[:-1]
        return txt + "..."

    # ------------------------------------------------- en-tete / pied
    def header(self):
        if not self.cover_done or self.page_no() == 1:
            return
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        # Deux demi-colonnes explicites. Avec une largeur nulle, les deux
        # cellules occupaient toute la ligne et les textes se chevauchaient.
        logo = ASSETS / "efrei-logo-noir.png"
        lw = 0
        if logo.exists():
            lw = 17
            self.image(str(logo), x=MARGIN, y=8.5, w=lw)
        half = (self.w - 2 * MARGIN - lw - 4) / 2
        self.f_body("", 8.4)
        self.set_text_color(*NAVY)
        self.set_xy(MARGIN + lw + 4, 10)
        self.cell(half, 4, self._fit(self.block_label, half), align=Align.L)
        self.set_text_color(*GREY)
        self.set_xy(self.w - MARGIN - half, 10)
        self.cell(half, 4, self._fit(self.chapter, half), align=Align.R)
        self.line(MARGIN, 16, self.w - MARGIN, 16)
        # filet rose signature
        self.set_draw_color(*ROSE)
        self.set_line_width(0.7)
        self.line(MARGIN, 16, MARGIN + 24, 16)
        self.set_line_width(0.2)
        # FPDF ne restaure pas le curseur apres header(), il faut le replacer
        # explicitement sous la marge haute sinon le premier titre chevauche le filet
        self.set_y(self.t_margin)

    def footer(self):
        if not self.cover_done or self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_draw_color(*RULE)
        self.line(MARGIN, self.get_y(), self.w - MARGIN, self.get_y())
        self.set_y(-12)
        self.f_body("", 8.2)
        self.set_text_color(*GREY)
        avail = self.w - 2 * MARGIN
        txt = ("EFREI Paris - Mastère Data Engineering et IA - "
               f"{self.block_label}")
        self.cell(avail - 16, 5, self._fit(txt, avail - 18), align=Align.L)
        self.set_text_color(*NAVY)
        self.f_body("B", 8.6)
        self.cell(16, 5, str(self.page_no()), align=Align.R)

    # --------------------------------------------------------- couverture
    def cover(self, meta_rows, tagline, cover_figure=None):
        """Couverture institutionnelle EFREI.

        Reprend la direction artistique des supports officiels de l'ecole
        (presentation-rncp) : aplat navy fonce, aucun degrade, logo blanc
        centre, titre en blanc, accents rose. Le rose reste un accent, il ne
        forme pas de bandeau.
        """
        self.add_page()
        self.set_auto_page_break(False)
        avail = self.w - 2 * MARGIN

        # Aplat plein, pas de degrade
        self.set_fill_color(*DARK)
        self.rect(0, 0, self.w, self.h, style="F")

        # Logo centre, dimensionne par la hauteur pour preserver le ratio 2:1
        logo = ASSETS / "efrei-logo-blanc.png"
        if logo.exists():
            lw = 62
            self.image(str(logo), x=(self.w - lw) / 2, y=34, w=lw)

        # Titre centre
        self.set_xy(MARGIN, 92)
        self.set_text_color(*WHITE)
        self.f_display(26)
        self.multi_cell(avail, 12, self.doc_title, align=Align.C)

        # Filet rose court, centre, sous le titre
        y = self.get_y() + 5
        self.set_fill_color(*ROSE)
        self.rect((self.w - 34) / 2, y, 34, 1.6, style="F")

        # Sous-titre en rose
        self.set_xy(MARGIN, y + 9)
        self.f_body("", 11.5)
        self.set_text_color(*ROSE)
        self.multi_cell(avail, 6.4, self.doc_subtitle, align=Align.C)

        # Accroche, en gris clair pour rester lisible sur le navy
        self.ln(4)
        self.set_x(MARGIN + 14)
        self.f_body("I", 10)
        self.set_text_color(188, 200, 220)
        self.multi_cell(avail - 28, 5.6, tagline, align=Align.C)

        # Pastille rose portant la mention obligatoire, a la maniere des
        # supports officiels de l'ecole
        mention = next((v for k, v in meta_rows if "ention" in k), None)
        if mention:
            self.f_body("B", 8.8)
            w = min(avail - 26, self.get_string_width(mention) + 18)
            lines = wrapped_lines(self, w - 14, 4.9, mention)
            hh = len(lines) * 4.9 + 6.5
            yb = self.get_y() + 8
            x = (self.w - w) / 2
            # Pastille a bords arrondis. `round_corners` n'existe pas dans cette
            # version de fpdf2 : on compose la forme avec un rectangle central et
            # deux demi-disques, ce qui donne un arrondi exact sans dependance.
            self.set_fill_color(*ROSE)
            r = hh / 2
            self.rect(x + r, yb, w - 2 * r, hh, style="F")
            self.ellipse(x, yb, 2 * r, hh, style="F")
            self.ellipse(x + w - 2 * r, yb, 2 * r, hh, style="F")
            self.set_xy(x + 7, yb + 3)
            self.set_text_color(*WHITE)
            self.multi_cell(w - 14, 4.9, mention, align=Align.C)

        # Bloc d'identification reduit a l'essentiel, en bas de page
        garder = ("Auteur", "Auteurs", "Binôme", "Tutrice", "Tuteurs", "Module",
                  "Numéro étudiant", "Promotion", "Date du rapport")
        rows = [(k, v) for k, v in meta_rows if k in garder]
        yb = self.h - 30 - len(rows) * 6
        self.set_draw_color(60, 82, 116)
        self.set_line_width(0.3)
        self.line(MARGIN + 24, yb - 8, self.w - MARGIN - 24, yb - 8)
        for k, v in rows:
            self.set_xy(MARGIN, yb)
            self.f_body("B", 8.6)
            self.set_text_color(*ROSE)
            lw = avail * 0.40
            self.cell(lw, 6, k, align=Align.R)
            self.f_body("", 8.6)
            self.set_text_color(220, 228, 240)
            self.set_xy(MARGIN + lw + 6, yb)
            self.cell(avail - lw - 6, 6, self._fit(v, avail - lw - 8), align=Align.L)
            yb += 6

        self.set_auto_page_break(True, margin=20)
        self.cover_done = True

    # ------------------------------------------------------------ sommaire
    # nom volontairement distinct de `toc_placeholder`, deja utilise comme
    # attribut interne par FPDF et qui ecraserait la methode
    def start_toc(self, n_pages=1):
        """Reserve les pages du sommaire.

        Le sommaire est rempli apres coup, quand la pagination est connue. En
        positionnement manuel, FPDF n'ajoute pas de page quand le contenu
        deborde : il ecrit sur la page existante suivante, donc par-dessus le
        premier chapitre. Il faut donc reserver le bon nombre de pages ici.
        """
        self.add_page()
        self.chapter = "Sommaire"
        self.h1("Sommaire", toc=False)
        self._toc_page = self.page_no()
        self._toc_y = self.get_y()
        self._toc_pages = max(1, n_pages)
        for _ in range(self._toc_pages - 1):
            self.add_page()
        # Le contenu doit imperativement demarrer apres les pages reservees.
        # Depuis que le premier chapitre ne force plus de saut de page, il
        # commencait sur la derniere page du sommaire et s'y superposait.
        # L'en-tete est dessine a l'ajout de la page : sans remise a zero, la
        # premiere page de contenu affichait encore « Sommaire ».
        self.chapter = ""
        self.add_page()

    def render_toc(self):
        """Ecrit le sommaire dans les pages reservees."""
        # Desactivation imperative : en positionnement manuel, un saut automatique
        # n'ajoute pas de page mais ecrit sur la page existante suivante, donc
        # par-dessus le premier chapitre.
        self.set_auto_page_break(False)
        limit = self.h - 30
        page = self._toc_page
        self.page = page
        # Changer de page en affectant `self.page` ne remet pas a zero le drapeau
        # interne de fpdf2 : `set_font` croit la police deja ecrite sur la page et
        # n'emet rien. Les lignes du sommaire etaient alors dessinees avec la
        # derniere police du pied de page (gras), d'ou le texte illisible.
        self.current_font_is_set_on_page = False
        self.set_y(self._toc_y)
        self._toc_last_page = page
        for level, label, num, lk in self.toc_entries:
            if level > 2:
                continue
            need = 8.3 if level == 1 else 6.8
            if self.get_y() + need > limit:
                page += 1
                if page > self._toc_page + self._toc_pages - 1:
                    self.toc_truncated = True
                    break          # place reservee epuisee, on tronque plutot
                self.page = page   # que d'ecrire par-dessus un chapitre
                self.current_font_is_set_on_page = False
                self._toc_last_page = page
                self.set_y(self.t_margin)
            self.set_x(MARGIN + (6 if level == 2 else 0))
            if level == 1:
                self.f_body("B", 11.4)
                self.set_text_color(*NAVY)
                self.ln(1.5)
            else:
                self.f_body("", 10.4)
                self.set_text_color(*DARK)
            w = self.w - 2 * MARGIN - (6 if level == 2 else 0)
            self.cell(w - 14, 6.8, self._fit(label, w - 16), border=0, link=lk)
            self.f_body("", 10.4)
            self.set_text_color(*GREY)
            self.cell(14, 6.8, str(num), align=Align.R, link=lk,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_auto_page_break(True, margin=20)
        self.page = self.pages_count

    def _anchor(self, text, level):
        """Cree une destination interne et un signet pour un titre.

        Le lien retourne est pose sur la ligne correspondante du sommaire, ce
        qui rend celui-ci cliquable. `start_section` alimente en plus le volet
        de signets des lecteurs PDF.
        """
        lk = self.add_link()
        self.set_link(lk, y=max(0, self.get_y() - 12), page=self.page_no())
        try:
            self.start_section(text, level)
        except Exception:
            pass          # signets indisponibles, les liens internes suffisent
        return lk

    # -------------------------------------------------------------- titres
    def h1(self, text, toc=True):
        if self.get_y() > self.h - 58:
            self.add_page()
        self.chapter = text
        self.ln(3)
        self.set_x(MARGIN)
        self.f_display(18)
        self.set_text_color(*DARK)
        self.multi_cell(self.w - 2 * MARGIN, 9.5, text,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        y = self.get_y() + 1.5
        self.set_fill_color(*ROSE)
        self.rect(MARGIN, y, 26, 1.4, style="F")
        self.set_fill_color(*RULE)
        self.rect(MARGIN + 26, y + 0.5, self.w - 2 * MARGIN - 26, 0.4, style="F")
        self.set_y(y + 6)
        if toc:
            self.toc_entries.append((1, text, self.page_no(), self._anchor(text, 0)))

    def h2(self, text):
        if self.get_y() > self.h - 40:
            self.add_page()
        self.ln(2.5)
        self.f_body("B", 13.2)
        self.set_text_color(*DARK)
        self.set_x(MARGIN)
        self.multi_cell(self.w - 2 * MARGIN, 7, text,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.toc_entries.append((2, text, self.page_no(), self._anchor(text, 1)))

    def h3(self, text):
        if self.get_y() > self.h - 34:
            self.add_page()
        self.ln(1.6)
        self.f_body("B", 11.6)
        self.set_text_color(*BLUE)
        self.set_x(MARGIN)
        self.multi_cell(self.w - 2 * MARGIN, 5.6, text,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    # ------------------------------------------------------------ contenus
    def p(self, text, size=11.2, lh=6.3):
        # Alignement a gauche et non justifie : Montserrat justifiee sur une
        # colonne de 174 mm produit des lezardes qui hachent la lecture.
        self.f_body("", size)
        self.set_text_color(*DARK)
        self.set_x(MARGIN)
        self.multi_cell(self.w - 2 * MARGIN, lh, text, align=Align.L,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def bullets(self, items, size=10.8):
        self.f_body("", size)
        self.set_text_color(*DARK)
        for it in items:
            if self.get_y() > self.h - 30:
                self.add_page()
            self.set_x(MARGIN + 1)
            self.set_text_color(*ROSE)
            self.f_body("B", size)
            self.cell(5, 6, "-")
            self.set_text_color(*DARK)
            self.f_body("", size)
            self.multi_cell(self.w - 2 * MARGIN - 6, 6, it, align=Align.L,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1.4)
        self.ln(2.4)

    def table(self, headers, rows, widths=None, caption=None, size=9.6):
        # marge de securite de 2 mm : le remplissage interne des cellules
        # s'ajoute a la largeur calculee et faisait deborder les tableaux larges
        avail = self.w - 2 * MARGIN - 2
        if widths is None:
            widths = [avail / len(headers)] * len(headers)
        else:
            s = sum(widths)
            widths = [w / s * avail for w in widths]

        need = 11 + 7.5 * min(len(rows), 2)
        if self.get_y() + need > self.h - 22:
            self.add_page()

        self._table_head(headers, widths, size)
        self.f_body("", size)
        self.set_draw_color(*RULE)
        for i, row in enumerate(rows):
            # hauteur requise par la cellule la plus haute
            hs = []
            for c, w in zip(row, widths):
                txt = c[0] if isinstance(c, tuple) else c
                hs.append(len(wrapped_lines(self, w - 2.5, 5.4, str(txt))))
            rh = max(hs) * 5.4 + 3.4
            # La derniere ligne emporte la legende avec elle : sans cette marge, la
            # legende pouvait se retrouver seule en haut de la page suivante.
            reserve = 11 if (caption and i == len(rows) - 1) else 0
            if self.get_y() + rh + reserve > self.h - 21:
                self.add_page()
                self._table_head(headers, widths, size)
                self.f_body("", size)

            y0 = self.get_y()
            self.set_fill_color(*(LIGHT if i % 2 == 0 else WHITE))
            self.rect(MARGIN, y0, avail, rh, style="F")
            x = MARGIN
            self.set_text_color(*DARK)
            for c, w in zip(row, widths):
                self.set_xy(x + 1.2, y0 + 1.7)
                if isinstance(c, tuple):
                    # Cellule lien : (texte affiche, adresse). Soulignee en bleu
                    # charte et cliquable dans tout lecteur PDF.
                    texte, url = c
                    self.set_text_color(*BLUE)
                    self.f_body("U", size)
                    self.cell(w - 2.5, 5.4, self._fit(str(texte), w - 3), link=url)
                    self.f_body("", size)
                    self.set_text_color(*DARK)
                else:
                    self.multi_cell(w - 2.5, 5.4, str(c), align=Align.L)
                x += w
            self.set_y(y0 + rh)
            self.line(MARGIN, self.get_y(), self.w - MARGIN, self.get_y())
        self.ln(2)
        if caption:
            self._caption(caption)

    def _table_head(self, headers, widths, size):
        """En-tete de tableau, sur plusieurs lignes si necessaire."""
        self.f_body("B", size)
        n = max(len(wrapped_lines(self, w - 3, 4.8, str(h)))
                for h, w in zip(headers, widths))
        hh = n * 4.8 + 3.4
        y0 = self.get_y()
        self.set_fill_color(*NAVY)
        self.rect(MARGIN, y0, sum(widths), hh, style="F")
        self.set_text_color(*WHITE)
        x = MARGIN
        for h, w in zip(headers, widths):
            self.set_xy(x + 1.5, y0 + 1.7)
            self.multi_cell(w - 3, 4.8, str(h), align=Align.L)
            x += w
        self.set_y(y0 + hh)

    def figure(self, path, caption, max_h=104):
        path = Path(path)
        if not path.exists():
            return
        from PIL import Image
        with Image.open(path) as im:
            iw, ih = im.size
        avail = self.w - 2 * MARGIN
        w = avail
        h = w * ih / iw
        if h > max_h:                      # jamais d'etirement, on borne la hauteur
            h = max_h
            w = h * iw / ih
        if self.get_y() + h + 11 > self.h - 21:
            # Plutot que d'envoyer la figure page suivante en laissant un grand blanc, on la
            # reduit a la place restante, ratio conserve, tant qu'elle garde 62 % de sa taille.
            room = self.h - 21 - 11 - self.get_y()
            if room >= max(MIN_FIGURE_RATIO * h, 40):
                w, h = w * room / h, room
            else:
                self.add_page()
        x = MARGIN + (avail - w) / 2
        y = self.get_y()
        self.set_draw_color(*RULE)
        self.rect(x - 1, y - 1, w + 2, h + 2)
        self.image(optimise_image(path), x=x, y=y, w=w, h=h)
        self.set_y(y + h + 2)
        self._caption(caption)

    def _caption(self, text):
        self.f_body("I", 9.2)
        self.set_text_color(*GREY)
        self.set_x(MARGIN)
        self.multi_cell(self.w - 2 * MARGIN, 5.2, text, align=Align.C,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def code(self, text, caption=None):
        lines = text.strip("\n").split("\n")
        rh = 4.6
        need = len(lines) * rh + 8
        if self.get_y() + need > self.h - 22:
            self.add_page()
        y0 = self.get_y()
        avail = self.w - 2 * MARGIN
        self.set_fill_color(246, 248, 251)
        self.rect(MARGIN, y0, avail, len(lines) * rh + 5, style="F")
        self.set_fill_color(*NAVY)
        self.rect(MARGIN, y0, 1.3, len(lines) * rh + 5, style="F")
        self.f_mono(8.8)
        self.set_text_color(*DARK)
        y = y0 + 2.5
        for ln_ in lines:
            self.set_xy(MARGIN + 5, y)
            self.cell(avail - 7, rh, ln_[:104])
            y += rh
        self.set_y(y0 + len(lines) * rh + 7)
        if caption:
            self._caption(caption)

    def callout(self, title, text, tone="info"):
        color = {"info": BLUE, "warn": (200, 120, 20), "crit": (200, 40, 70),
                 "ok": (16, 150, 110)}.get(tone, BLUE)
        self.f_body("", 10.4)
        body_lines = wrapped_lines(self, self.w - 2 * MARGIN - 14, 5.8, text)
        h = 11 + len(body_lines) * 5.8
        if self.get_y() + h > self.h - 24:
            self.add_page()
        y0 = self.get_y()
        self.set_fill_color(249, 250, 252)
        self.rect(MARGIN, y0, self.w - 2 * MARGIN, h, style="F")
        self.set_fill_color(*color)
        self.rect(MARGIN, y0, 1.3, h, style="F")
        self.set_xy(MARGIN + 7, y0 + 2)
        self.f_body("B", 10.6)
        self.set_text_color(*color)
        self.cell(0, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.f_body("", 10.4)
        self.set_text_color(*DARK)
        self.set_xy(MARGIN + 7, y0 + 8)
        self.multi_cell(self.w - 2 * MARGIN - 14, 5.8, text,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(y0 + h + 4)

    def kpi_row(self, items):
        """Bandeau de chiffres cles, 3 a 4 par ligne."""
        n = len(items)
        avail = self.w - 2 * MARGIN
        gap = 3
        w = (avail - gap * (n - 1)) / n
        if self.get_y() + 22 > self.h - 24:
            self.add_page()
        y0 = self.get_y()
        x = MARGIN
        for value, label in items:
            self.set_fill_color(251, 252, 254)
            self.rect(x, y0, w, 19, style="F")
            self.set_fill_color(*ROSE)
            self.rect(x, y0, w, 0.8, style="F")
            self.set_draw_color(*RULE)
            self.set_line_width(0.2)
            self.rect(x, y0, w, 19)
            self.set_xy(x, y0 + 3.2)
            self.f_display(15.5)
            self.set_text_color(*NAVY)
            self.cell(w, 8, str(value), align=Align.C)
            self.set_xy(x, y0 + 11.4)
            self.f_body("", 8.4)
            self.set_text_color(*GREY)
            self.multi_cell(w, 3.6, label, align=Align.C)
            x += w + gap
        self.set_y(y0 + 23)


def _figure_min_height(pdf, path):
    """Hauteur minimale d'une figure une fois reduite au maximum, legende comprise."""
    path = Path(path)
    if not path.exists():
        return 0
    from PIL import Image
    with Image.open(path) as im:
        iw, ih = im.size
    h = min((pdf.w - 2 * MARGIN) * ih / iw, 104)
    return max(MIN_FIGURE_RATIO * h, 40) + 11


def build(spec, out_path, n_toc=None, _essais=None):
    """Construit un rapport a partir d'une specification declarative.

    Le sommaire occupe un nombre de pages qui depend de la pagination finale,
    laquelle depend du sommaire. Plutot que d'estimer, on construit une premiere
    fois puis on reconstruit avec le nombre exact si la place manquait. Une
    estimation, meme prudente, avait deja provoque deux fois l'ecriture du
    sommaire par-dessus le premier chapitre.
    """
    if n_toc is None:
        n_entries = sum(1 for it in spec["content"] if it[0] in ("h1", "h2"))
        n_h1 = sum(1 for it in spec["content"] if it[0] == "h1")
        # Hauteurs reelles d'une ligne de sommaire (6,8 mm) et du blanc ajoute
        # avant chaque h1 (1,5 mm). L'ancienne estimation, 7,2 et 2,0, reservait
        # une page de trop, restee blanche dans le rapport de maintenance.
        hauteur = n_entries * 6.8 + n_h1 * 1.5
        dispo_1, dispo_n = 297 - 30 - 50, 297 - 30 - 30
        n_toc = 1 if hauteur <= dispo_1 else 2 + int((hauteur - dispo_1) / dispo_n)

    pdf = EfreiReport(spec["title"], spec["subtitle"], spec["block_label"])
    pdf.cover(spec["meta"], spec["tagline"], spec.get("cover_figure"))
    pdf.start_toc(n_toc)

    content = spec["content"]
    floated = set()
    for idx, item in enumerate(content):
        if idx in floated:
            continue
        kind = item[0]

        # Flottement : une figure qui ne tient pas, meme reduite, laisserait un grand blanc.
        # Le bloc de texte ou le tableau qui la suit remonte combler la place, puis la figure.
        if kind == "figure" and idx + 1 < len(content)                 and content[idx + 1][0] in ("p", "table", "callout")                 and pdf.get_y() + _figure_min_height(pdf, item[1]) > pdf.h - 21:
            nxt = content[idx + 1]
            if nxt[0] == "p":
                pdf.p(nxt[1])
            elif nxt[0] == "table":
                pdf.table(nxt[1], nxt[2], nxt[3] if len(nxt) > 3 else None,
                          nxt[4] if len(nxt) > 4 else None)
            else:
                pdf.callout(nxt[1], nxt[2], nxt[3] if len(nxt) > 3 else "info")
            floated.add(idx + 1)

        # Couplage titre-figure : un intertitre ne doit jamais rester seul en bas
        # de page pendant que sa figure bascule sur la suivante.
        if kind in ("h2", "h3") and idx + 1 < len(content)                 and content[idx + 1][0] == "figure":
            fig = Path(content[idx + 1][1])
            if fig.exists():
                from PIL import Image
                with Image.open(fig) as im:
                    iw, ih = im.size
                w = pdf.w - 2 * MARGIN
                h = min(w * ih / iw, 104)
                h = max(MIN_FIGURE_RATIO * h, 40)      # la figure peut se reduire jusque-la
                if pdf.get_y() + h + 22 > pdf.h - 21:
                    pdf.add_page()

        # Meme regle pour un tableau : sans elle, un intertitre restait orphelin en
        # bas de page, son tableau commencant sur la page suivante. On reserve la
        # place du titre, de l'en-tete et de deux lignes.
        if kind in ("h2", "h3") and idx + 1 < len(content) \
                and content[idx + 1][0] == "table":
            if pdf.get_y() + 48 > pdf.h - 21:
                pdf.add_page()

        if kind == "h1":
            if (pdf.h - 20) - pdf.get_y() < 40:   # titre + deux lignes, sinon blanc inutile
                pdf.add_page()
            else:
                pdf.ln(10)
            pdf.h1(item[1])
        elif kind == "h2":
            pdf.h2(item[1])
        elif kind == "h3":
            pdf.h3(item[1])
        elif kind == "p":
            pdf.p(item[1])
        elif kind == "bullets":
            pdf.bullets(item[1])
        elif kind == "table":
            pdf.table(item[1], item[2], item[3] if len(item) > 3 else None,
                      item[4] if len(item) > 4 else None)
        elif kind == "figure":
            pdf.figure(item[1], item[2])
        elif kind == "code":
            pdf.code(item[1], item[2] if len(item) > 2 else None)
        elif kind == "callout":
            pdf.callout(item[1], item[2], item[3] if len(item) > 3 else "info")
        elif kind == "kpi":
            pdf.kpi_row(item[1])
        elif kind == "pagebreak":
            pdf.add_page()

    pdf.render_toc()
    essais = (_essais or set()) | {n_toc}
    if pdf.toc_truncated and n_toc < 8 and (n_toc + 1) not in essais:
        return build(spec, out_path, n_toc + 1, essais)   # place insuffisante
    derniere_reservee = pdf._toc_page + n_toc - 1
    if (not pdf.toc_truncated and n_toc > 1
            and pdf._toc_last_page < derniere_reservee and (n_toc - 1) not in essais):
        # Une page reservee est restee vide : on reconstruit avec une de moins,
        # faute de quoi elle sortirait blanche dans le document.
        return build(spec, out_path, n_toc - 1, essais)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return pdf.pages_count
