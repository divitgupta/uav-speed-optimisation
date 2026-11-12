"""Small helper layer over python-pptx for the RVCE SDG templates."""
import copy

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

RED = RGBColor(0xC0, 0x00, 0x00)
NAVY = RGBColor(0x00, 0x20, 0x60)
INK = RGBColor(0x1F, 0x1F, 0x1F)
GREY = RGBColor(0x59, 0x59, 0x59)
TINT = RGBColor(0xEA, 0xF0, 0xF7)
TINT2 = RGBColor(0xFB, 0xEA, 0xEA)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
AMBER = RGBColor(0xB2, 0x6A, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Bookman Old Style"
BODY = "Calibri"


class Deck:
    def __init__(self, template):
        self.prs = Presentation(template)
        self.layout = self.prs.slide_layouts[0]  # "Title and Content": RVCE logo + footer
        self.n = 2

    # ---------- template slides ----------
    def fill_title(self, title, team_no, team_name, members):
        tb = [s for s in self.prs.slides[0].shapes if s.name == "TextBox 1"][0]
        tf = tb.text_frame
        lines = [("TITLE: ", title), ("TEAM No: ", f"{team_no}\t\tTEAM NAME: {team_name}")] + [(u, "\t\t\t" + n) for u, n in members]
        for p, (lab, val) in zip(tf.paragraphs, lines):
            for r in list(p.runs)[1:]:
                r._r.getparent().remove(r._r)
            r0 = p.runs[0] if p.runs else p.add_run()
            r0.text = lab; r0.font.bold = True; r0.font.size = Pt(16 if lab == "TITLE: " else 14); r0.font.color.rgb = NAVY
            r1 = p.add_run(); r1.text = val; r1.font.size = Pt(16 if lab == "TITLE: " else 14)
            r1.font.color.rgb = RED if lab == "TITLE: " else INK; r1.font.bold = lab == "TITLE: "

    def fill_outline(self, phase_label, items):
        s = self.prs.slides[1]
        for sh in s.shapes:
            if sh.has_text_frame and sh.text_frame.text.startswith("EL Phase"):
                sh.text_frame.paragraphs[0].runs[0].text = phase_label
            if sh.is_placeholder and sh.placeholder_format.type == 2:
                tf = sh.text_frame
                ps = tf.paragraphs
                tmpl_pPr = copy.deepcopy(ps[1]._p.pPr)
                for p in ps[1:]:
                    p._p.getparent().remove(p._p)
                first = ps[0]
                for r in list(first.runs)[1:]:
                    r._r.getparent().remove(r._r)
                for i, (head, sub) in enumerate(items):
                    p = first if i == 0 else tf.add_paragraph()
                    if i == 0:
                        first.runs[0].text = ""
                    r = p.add_run() if i else first.runs[0]
                    r.text = head; r.font.size = Pt(24); r.font.bold = True; r.font.color.rgb = RED; r.font.name = FONT
                    old = p._p.pPr
                    if old is not None: p._p.remove(old)
                    p._p.insert(0, copy.deepcopy(tmpl_pPr))
                    if sub:
                        r2 = p.add_run(); r2.text = ":  " + sub; r2.font.size = Pt(16); r2.font.color.rgb = NAVY; r2.font.name = FONT
                    p.space_after = Pt(10)

    def finalize_template(self):
        """Move the template's 'Thank you' slide to the end and drop its empty TITLE-layout slides."""
        lst = self.prs.slides._sldIdLst
        ids = list(lst)
        slides = list(self.prs.slides)
        for sid, sl in zip(ids, slides):
            if sl.slide_layout.name == "TITLE":
                self.prs.part.drop_rel(sid.rId); lst.remove(sid)
            elif any(sh.has_text_frame and sh.text_frame.text.strip() == "Thank you" for sh in sl.shapes):
                lst.remove(sid); lst.append(sid)

    def renumber(self):
        for i, s in enumerate(self.prs.slides, 1):
            for sh in s.shapes:
                if sh.name in ("SlideNo",):
                    sh.text_frame.paragraphs[0].runs[0].text = str(i)

    # ---------- content slides ----------
    def slide(self, title, section=None):
        s = self.prs.slides.add_slide(self.layout)
        for ph in list(s.placeholders):
            ph._element.getparent().remove(ph._element)
        self.n += 1
        t = self.text(s, Emu(1386895), Emu(145670), Emu(9834426), Emu(839401), title, size=32 if len(title) <= 38 else 28, color=RED, bold=True,
                      align=PP_ALIGN.CENTER, font=FONT, anchor=MSO_ANCHOR.MIDDLE)
        t.name = "Title"
        if section:
            self.text(s, Emu(9900000), Emu(150000), Emu(2150000), Emu(330000), section, size=11, color=GREY,
                      align=PP_ALIGN.RIGHT, italic=True, font=BODY)
        num = self.text(s, Emu(9273988), Emu(6347205), Emu(2743200), Emu(365125), str(self.n), size=11, color=GREY,
                        align=PP_ALIGN.RIGHT, font=BODY)
        num.name = "SlideNo"
        return s

    def text(self, s, x, y, w, h, text, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, italic=False,
             font=BODY, anchor=MSO_ANCHOR.TOP, wrap=True):
        tb = s.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame; tf.word_wrap = wrap; tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.03)
        p = tf.paragraphs[0]; p.alignment = align
        r = p.add_run(); r.text = text
        f = r.font; f.size = Pt(size); f.bold = bold; f.italic = italic; f.color.rgb = color; f.name = font
        return tb

    def rich(self, s, x, y, w, h, paras, size=16, font=BODY, space=6, bullet=True):
        """paras: list of items; each item is a str, or list of (text, {'bold':..,'color':..}) runs,
        or ('sub', ...) for an indented sub-bullet."""
        tb = s.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0.05)
        for i, item in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            lvl = 0
            if isinstance(item, tuple) and item[0] == "sub":
                lvl, item = 1, item[1]
            runs = [(item, {})] if isinstance(item, str) else item
            if bullet:
                self._bullet(p, lvl, size)
            p.space_after = Pt(space)
            for txt, st in runs:
                r = p.add_run(); r.text = txt
                r.font.size = Pt(st.get("size", size - 2 * lvl)); r.font.name = st.get("font", font)
                r.font.bold = st.get("bold", False); r.font.italic = st.get("italic", False)
                r.font.color.rgb = st.get("color", INK)
        return tb

    def _bullet(self, p, lvl, size):
        from pptx.oxml.ns import qn
        pPr = p._p.get_or_add_pPr()
        indent = 228600 if lvl == 0 else 457200
        pPr.set("marL", str(indent + (0 if lvl == 0 else 0))); pPr.set("indent", str(-228600))
        for tag in ("a:buClr", "a:buSzPct", "a:buFont", "a:buChar", "a:buNone"):
            for e in pPr.findall(qn(tag)): pPr.remove(e)
        buClr = pPr.makeelement(qn("a:buClr"), {}); c = buClr.makeelement(qn("a:srgbClr"), {"val": "C00000" if lvl == 0 else "002060"}); buClr.append(c)
        buFont = pPr.makeelement(qn("a:buFont"), {"typeface": "Arial"})
        buChar = pPr.makeelement(qn("a:buChar"), {"char": "•" if lvl == 0 else "–"})
        pPr.append(buClr); pPr.append(buFont); pPr.append(buChar)

    def box(self, s, x, y, w, h, fill=TINT, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08):
        b = s.shapes.add_shape(shape, x, y, w, h)
        b.fill.solid(); b.fill.fore_color.rgb = fill
        if line is None:
            b.line.fill.background()
        else:
            b.line.color.rgb = line; b.line.width = Pt(1.25)
        b.shadow.inherit = False
        if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            b.adjustments[0] = radius
        b.text_frame.text = ""
        return b

    def card(self, s, x, y, w, h, head, body_lines, fill=TINT, head_color=NAVY, size=14, head_size=17):
        self.box(s, x, y, w, h, fill)
        self.text(s, x + Inches(0.15), y + Inches(0.1), w - Inches(0.3), Inches(0.45), head, size=head_size, bold=True,
                  color=head_color, font=FONT)
        return self.rich(s, x + Inches(0.15), y + Inches(0.6), w - Inches(0.3), h - Inches(0.7), body_lines, size=size, space=4)

    def stat(self, s, x, y, w, value, label, color=RED, vsize=36, lsize=12):
        self.text(s, x, y, w, Inches(0.7), value, size=vsize, bold=True, color=color, align=PP_ALIGN.CENTER, font=FONT)
        self.text(s, x, y + Inches(0.72), w, Inches(0.6), label, size=lsize, color=GREY, align=PP_ALIGN.CENTER)

    def chip(self, s, x, y, w, text, fill=GREEN, size=11):
        b = self.box(s, x, y, w, Inches(0.3), fill, radius=0.5)
        tf = b.text_frame; tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = text; r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = BODY
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        return b

    def node(self, s, x, y, w, h, head, sub, fill=NAVY, color=WHITE, size=14):
        b = self.box(s, x, y, w, h, fill, radius=0.12)
        tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = Inches(0.08)
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = head; r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = color; r.font.name = FONT
        if sub:
            p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run(); r2.text = sub; r2.font.size = Pt(size - 3); r2.font.color.rgb = color; r2.font.name = BODY
        return b

    def arrow(self, s, x1, y1, x2, y2, color=GREY):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
        c.line.color.rgb = color; c.line.width = Pt(2)
        from pptx.oxml.ns import qn
        ln = c.line._get_or_add_ln()
        tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}); ln.append(tail)
        return c

    def table(self, s, x, y, w, rows, col_w=None, size=12, head_size=12, row_h=0.36, head_fill=NAVY, zebra=True, bold_first=False):
        nr, nc = len(rows), len(rows[0])
        gt = s.shapes.add_table(nr, nc, x, y, w, Inches(row_h * nr))
        tbl = gt.table
        tblPr = tbl._tbl.tblPr
        tblPr.set("bandRow", "0"); tblPr.set("firstRow", "1")
        style = tblPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}tableStyleId")
        if col_w:
            tot = sum(col_w)
            for i, cw in enumerate(col_w):
                tbl.columns[i].width = int(w * cw / tot)
        for r in range(nr):
            tbl.rows[r].height = Inches(row_h)
            for c in range(nc):
                cell = tbl.cell(r, c); v = rows[r][c]
                cell.margin_left = cell.margin_right = Inches(0.06); cell.margin_top = cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                tf = cell.text_frame; tf.word_wrap = True
                p = tf.paragraphs[0]
                color, bold = INK, False
                if isinstance(v, tuple):
                    v, opts = v; color = opts.get("color", INK); bold = opts.get("bold", False)
                run = p.add_run(); run.text = str(v)
                run.font.size = Pt(head_size if r == 0 else size); run.font.name = BODY
                cell.fill.solid()
                if r == 0:
                    cell.fill.fore_color.rgb = head_fill; run.font.color.rgb = WHITE; run.font.bold = True
                else:
                    cell.fill.fore_color.rgb = TINT if (zebra and r % 2 == 0) else WHITE
                    run.font.color.rgb = color; run.font.bold = bold or (bold_first and c == 0)
        return gt

    def image(self, s, path, x, y, w=None, h=None):
        """Place a picture inside the box (x, y, w, h), keeping aspect ratio, centred horizontally."""
        if w is None or h is None:
            return s.shapes.add_picture(str(path), x, y, w, h)
        from PIL import Image
        iw, ih = Image.open(path).size
        scale = min(w / iw, h / ih)
        pw, ph = int(iw * scale), int(ih * scale)
        return s.shapes.add_picture(str(path), x + (w - pw) // 2, y, pw, ph)

    def notes(self, s, text):
        s.notes_slide.notes_text_frame.text = text

    def save(self, path, author="Divit Gupta", title=""):
        cp = self.prs.core_properties
        cp.author = author; cp.last_modified_by = author; cp.title = title; cp.comments = ""
        for sh in self.prs.slides[0].shapes:
            el = sh._element.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr")
            if el is not None and "automatically generated" in (el.get("descr") or ""):
                el.set("descr", "RV College of Engineering campus")
        self.renumber()
        self.prs.save(path)
