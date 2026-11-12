"""Build the 2-page project synopsis (.docx) in the RVCE EL synopsis format."""
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

import team

EL = Path(__file__).resolve().parents[1]
LOGO = Path(__file__).parent / "assets" / "rvce_logo.png"
OUT = sys.argv[1] if len(sys.argv) > 1 else str(EL / "SDG9_Synopsis_UAV.docx")
FONT = "Times New Roman"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)          # US Letter, same as the reference synopsis
sec.left_margin = sec.right_margin = Cm(2.54)
sec.top_margin, sec.bottom_margin = Cm(2.6), Cm(2.0)
sec.header_distance = Cm(0.6)
st = doc.styles["Normal"]
st.font.name = FONT; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(0); st.paragraph_format.line_spacing = 1.15

# header: RVCE logo on every page
sec.header.paragraphs[0].add_run().add_picture(str(LOGO), width=Cm(4.4))


def para(text="", bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=0, size=11):
    p = doc.add_paragraph(); p.alignment = align
    p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after)
    if text:
        r = p.add_run(text); r.bold = bold; r.font.size = Pt(size)
    return p


def heading(text):
    para(text + ":", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=12, after=8)


def body(text, after=4):
    return para(text, after=after)


def numbered(items):
    for i, t in enumerate(items, 1):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format; pf.left_indent = Cm(1.27); pf.first_line_indent = Cm(-0.63); pf.space_after = Pt(1)
        pf.tab_stops.add_tab_stop(Cm(1.27))
        p.add_run(f"{i}.\t{t}")


def cell_text(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]; p.alignment = align
    r = p.add_run(text); r.bold = bold; r.font.size = Pt(10.5)


# ---------------- details table (same layout as the reference) ----------------
members = team.MEMBERS
t = doc.add_table(rows=2 + len(members) + 2, cols=5); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
for row in t.rows:
    for c, w in zip(row.cells, [Cm(3.3), Cm(3.8), Cm(3.6), Cm(2.6), Cm(3.2)]):
        c.width = w


def span(r, c0, c1, text, bold=True):
    cell = t.cell(r, c0).merge(t.cell(r, c1)) if c1 > c0 else t.cell(r, c0)
    cell_text(cell, text, bold=bold)


cell_text(t.cell(0, 0), "College", True); span(0, 1, 4, "RV COLLEGE OF ENGINEERING®")
cell_text(t.cell(1, 0), "SDG9 EL", True); span(1, 1, 4, "CS Cluster")
for i, (usn, name) in enumerate(members):
    r = 2 + i
    cell_text(t.cell(r, 0), f"Student Name{i+1}", True); span(r, 1, 2, name)
    cell_text(t.cell(r, 3), "USN", True, WD_ALIGN_PARAGRAPH.RIGHT); cell_text(t.cell(r, 4), usn, True)
r = 2 + len(members)
cell_text(t.cell(r, 0), "Project Title", True); span(r, 1, 4, team.TITLE)
cell_text(t.cell(r + 1, 0), "Under taken at", True); span(r + 1, 1, 4, "RV College of Engineering")

para("SYNOPSIS", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=16, after=4, size=12)

# ---------------- sections ----------------
heading("Introduction")
body("Drones are now used to deliver parcels and medicines, support search and rescue, spray crops, inspect industrial assets and "
     "watch over large sites. On every one of these missions the operator has to balance three things: how much battery the trip uses, "
     "how long it takes, and how likely it is to finish without a failure. Small multirotors fly for only tens of minutes on a charge, so "
     "this balance matters. Flight speed is the one setting that affects all three. Flying too slowly wastes energy because the drone is "
     "close to hovering, and flying too fast increases drag and stress. Today the speed is usually picked by rule of thumb. In this project "
     "we treat the choice of speed as a computational problem: we model the drone mathematically, simulate missions, and use optimisation "
     "algorithms to find the best speed that still meets the battery and reliability limits. The project supports SDG 9 (Industry, "
     "Innovation and Infrastructure) by making drone-based delivery and emergency response more efficient and dependable.")

heading("Objectives")
numbered([
    "Model the energy, delivery time and reliability of a UAV mission as functions of flight speed, payload, distance and wind.",
    "Formulate the choice of speed as a constrained multi-objective problem with battery, reliability and speed limits.",
    "Implement and compare grid search, a weighted-sum method and NSGA-II for finding the optimal feasible speed.",
    "Build an industry benchmark of commercial drones so the model is set up with real published specifications.",
    "Develop a web application where a planner can change the mission and see the recommended speed and trade-offs.",
])

heading("Methodology")
body("For energy we use the rotary-wing power model of Zeng, Xu and Zhang (2019) and scale it to the mass of each drone category. "
     "Delivery time is the distance divided by the ground speed, which includes headwind. Mission reliability is modelled as "
     "R = exp(-λ(V)·T), where the failure rate λ(V) grows with speed; since no drone company publishes failure rates, its parameters "
     "are clearly marked as assumptions. The problem is: minimise energy and time, subject to reliability ≥ 0.995, energy within the "
     "usable battery, and speed below the drone's maximum. We solve it with grid search as an exact baseline, a SciPy weighted-sum "
     "method, and NSGA-II (pymoo), which returns the whole energy-time Pareto front.")
body("Inputs for six categories (delivery, disaster relief, agriculture, surveillance, mapping and inspection) come from our benchmark. "
     "We first checked our code against the Phase-1 reference curve, where the largest error is 0.05 kJ, and all 19 automated tests "
     "pass. We then compare the three optimisers, study how payload, headwind and distance change the optimal speed, and compare the "
     "result with flying at a fixed 10 m/s. In our current results the optimal speeds save 18-47% energy and 16-60% time compared "
     "with 10 m/s. The model and optimisers are served through a Flask web application with an interactive front end.")

heading("Data set used")
body("A UAV Industry Benchmark that we compiled from official specification sheets of 50 commercial drones in six categories, with a "
     "source link for every entry. Blank cells mean a specification is not published. Power-model coefficients are taken from Zeng et al. "
     "(2019). For validation in Phase-3 we plan to use a public multirotor flight-energy dataset; the exact dataset may change once we "
     "check that it matches our model inputs.")

heading("Software Requirements")
body("Python with NumPy and SciPy for the model, pymoo for NSGA-II, Matplotlib for result figures, and pytest for testing. Flask for "
     "the web server, with HTML, CSS, JavaScript and Plotly.js for the interface. Microsoft Excel and openpyxl for the benchmark. "
     "These choices can be refined during implementation.")

heading("Hardware Requirements")
body("A laptop or desktop is enough to run the simulations, the optimisers and the web application. The study is simulation-based, "
     "so no drone hardware or GPU is needed.")

heading("Contribution to the field")
body("The project optimises energy, delivery time and reliability together, where most earlier work looks at energy or time alone. "
     "It grounds the model in a sourced benchmark of real commercial drones instead of one assumed aircraft, and it compares an exact "
     "method, a weighted-sum method and NSGA-II on the same problem. The web application turns the results into a tool that a delivery "
     "or disaster-response planner can actually use to choose a speed.")

cp = doc.core_properties
cp.author = "Divit Gupta"; cp.last_modified_by = "Divit Gupta"; cp.comments = ""; cp.title = "Synopsis: " + team.TITLE
doc.save(OUT)
print("saved", OUT)
