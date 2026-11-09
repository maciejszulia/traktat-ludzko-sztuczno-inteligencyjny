#!/usr/bin/env python3
"""Build traktat.md -> traktat.tex -> traktat.pdf (xelatex-free: pdflatex + babel)."""
import re, subprocess, sys, pathlib

SRC = pathlib.Path(__file__).with_name("traktat.md")
TEX = SRC.with_suffix(".tex")

PROP = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")

blocks, cur = [], []
for line in SRC.read_text(encoding="utf-8").splitlines():
    if line.strip():
        cur.append(line.rstrip())
    elif cur:
        blocks.append(cur)
        cur = []
if cur:
    blocks.append(cur)

title = []
epigraph, sections = [], []          # sections: (name, [items])
for b in blocks:
    if b[0].startswith("# "):
        title.append(b[0][2:].strip())
    elif b[0].startswith("## "):
        sections.append((b[0][3:].strip(), []))
    elif not sections:
        epigraph.append(b)
    else:
        sections[-1][1].append(b)

def esc(s):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("#", r"\#"), ("_", r"\_"), ("$", r"\$")):
        s = s.replace(a, b)
    return s

out = []
w = out.append
w(r"""\documentclass[11pt,a5paper]{book}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[polish]{babel}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage[a5paper,inner=2.3cm,outer=2.0cm,top=2.1cm,bottom=2.3cm]{geometry}
\usepackage[hidelinks]{hyperref}
\hypersetup{pdftitle={Traktat ludzko-sztuczno-inteligencyjny},pdfauthor={maszyna, na zamowienie czlowieka}}
\pagestyle{plain}
\setlength{\parindent}{1.2em}
\setlength{\parskip}{0pt}
\newcommand{\prop}[2]{\par\addvspace{0.6em}\parindent=0pt\noindent
  \hangindent=2.7em\hangafter=1\makebox[2.7em][l]{\mbox{\small #1}}#2\par}
\begin{document}
\begin{titlepage}\centering
\vspace*{3.2cm}
{\Large\scshape Traktat\\[0.35em] ludzko-sztuczno-\\ inteligencyjny\par}
\vspace{2.8cm}
{\small spisała maszyna\\ zlecił człowiek\par}
\vfill
{\small Olsztyn, listopad 2026\par}
\end{titlepage}
""")

if epigraph:
    w(r"\thispagestyle{empty}\vspace*{7cm}")
    w(r"\begin{flushright}\begin{minipage}{0.85\textwidth}\itshape")
    for blk in epigraph:
        for ln in blk:
            w(esc(ln) + r"\\" if blk is epigraph[-1] else esc(ln) + r"\\")
        w(r"\par\vspace{0.4em}")
    w(r"\end{minipage}\end{flushright}" if False else r"\end{minipage}\end{flushright}")
    w(r"\clearpage")

for name, items in sections:
    note = name.lower().startswith("przypis")
    w(r"\par\addvspace{2.4em}{\centering\scshape %s\par}\addvspace{1.6em}" % esc(name))
    for blk in items:
        m = PROP.match(blk[0])
        if m and len(blk) == 1:
            w(r"\prop{%s}{%s}" % (m.group(1), esc(m.group(2))))
        else:
            body = esc(" ".join(blk)) + r"\par\addvspace{0.4em}"
            w(r"{\small\itshape %s}" % body if note else body)

w(r"\end{document}")
TEX.write_text("\n".join(out) + "\n", encoding="utf-8")

for run in (1, 2):
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                        TEX.name], cwd=SRC.parent, capture_output=True)
    if r.returncode:
        print(r.stdout.decode("utf-8", "replace")[-3000:]); sys.exit(1)

log = (SRC.parent / "traktat.log").read_text(errors="ignore")
pages = re.search(r"Output written on .*\((\d+) pages", log)
props = sum(1 for _, items in sections for blk in items if len(blk) == 1 and PROP.match(blk[0]))
print("OK pages=%s props=%d" % (pages.group(1) if pages else "?", props))
