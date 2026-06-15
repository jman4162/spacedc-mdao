# ruff: noqa: RUF001  (intentionally maps ambiguous Unicode glyphs to LaTeX)
"""Build the white-paper PDF from docs/whitepaper.md with Tectonic.

Run:

    python scripts/build_whitepaper_pdf.py

Converts the Markdown to LaTeX (a focused, stdlib-only converter for the
constructs this document uses) and compiles it with Tectonic, the self-contained
XeTeX engine (`brew install tectonic`). No pandoc/LaTeX distribution or Python
dependencies needed. Output: docs/assets/orbital-data-centers-primer.pdf.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

SRC = Path("docs/whitepaper.md")
OUT = Path("docs/assets/orbital-data-centers-primer.pdf")
IMG_ROOT = Path("docs").resolve()

PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[margin=2.2cm]{geometry}
\usepackage{graphicx}
\usepackage{array}
\usepackage[colorlinks=true,urlcolor=blue,linkcolor=blue]{hyperref}
\usepackage{parskip}
\setlength{\emergencystretch}{3em}
\begin{document}
"""

# Map non-ASCII characters to robust LaTeX (the document is otherwise ASCII).
# Keys use \u escapes so the source stays ASCII (no ambiguous-glyph lint noise).
_UNICODE = {
    "²": r"\textsuperscript{2}",  # superscript two
    "ü": r"\"{u}",  # u-umlaut
    "≈": r"$\approx$",
    "×": r"$\times$",
    "·": r"$\cdot$",  # middle dot
    "≤": r"$\le$",
    "≥": r"$\ge$",
    "–": "--",  # en dash
    "—": "---",  # em dash
    "“": "``",  # left double quote
    "”": "''",  # right double quote
    "‘": "`",  # left single quote
    "’": "'",  # right single quote
    "…": r"\ldots{}",
}

# Verbatim can't hold LaTeX commands, so non-ASCII there is replaced with ASCII.
_VERBATIM_ASCII = {
    "²": "2",
    "·": "*",
    "≤": "<=",
    "≈": "~",
    "—": "--",
    "ü": "u",
    "×": "x",
}


def _verbatim_ascii(text: str) -> str:
    for ch, rep in _VERBATIM_ASCII.items():
        text = text.replace(ch, rep)
    return text


def esc(text: str) -> str:
    """Escape LaTeX specials in prose (run before inserting any LaTeX commands)."""
    text = text.replace("\\", r"\textbackslash{}")
    for ch, rep in {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }.items():
        text = text.replace(ch, rep)
    for ch, rep in _UNICODE.items():
        text = text.replace(ch, rep)
    return text


def inline(text: str) -> str:
    """Convert inline Markdown (code, links, bold, italic) with escaping."""
    codes: list[str] = []
    links: list[tuple[str, str]] = []

    def stash_code(m: re.Match[str]) -> str:
        codes.append(m.group(1))
        return f"XCODE{len(codes) - 1}X"

    def stash_link(m: re.Match[str]) -> str:
        links.append((m.group(1), m.group(2)))
        return f"XLINK{len(links) - 1}X"

    text = re.sub(r"`([^`]+)`", stash_code, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", stash_link, text)
    text = esc(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", text)
    for i, (label, url) in enumerate(links):
        text = text.replace(f"XLINK{i}X", rf"\href{{{url}}}{{{esc(label)}}}")
    for i, code in enumerate(codes):
        text = text.replace(f"XCODE{i}X", rf"\texttt{{{esc(code)}}}")
    return text


def _is_block_start(line: str) -> bool:
    return (
        line.startswith(("```", "# ", "## ", "- "))
        or line.lstrip().startswith("|")
        or bool(re.match(r"!\[[^\]]*\]\(", line))
    )


def md_to_latex(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i, n = 0, len(lines)
    first_h1 = True
    while i < n:
        line = lines[i]
        if line.startswith("```"):  # fenced code -> verbatim
            i += 1
            block = []
            while i < n and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            code = _verbatim_ascii("\n".join(block))
            out.append("\\begin{verbatim}\n" + code + "\n\\end{verbatim}")
        elif line.startswith("# "):
            if first_h1:
                out.append(
                    r"\begin{center}{\LARGE\bfseries " + inline(line[2:]) + r"}\end{center}\medskip"
                )
                first_h1 = False
            else:
                out.append(r"\section*{" + inline(line[2:]) + "}")
            i += 1
        elif line.startswith("## "):
            out.append(r"\section*{" + inline(line[3:]) + "}")
            i += 1
        elif line.lstrip().startswith("|") and i + 1 < n and set(lines[i + 1]) <= set("|-: "):
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(_table(rows))
        elif re.match(r"!\[[^\]]*\]\(([^)]+)\)", line):
            m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", line)
            assert m
            path = (IMG_ROOT / m.group(1)).as_posix()
            out.append(
                r"\begin{center}\includegraphics[width=0.82\textwidth]{" + path + "}\\end{center}"
            )
            i += 1
        elif line.startswith("- "):
            items = []
            while i < n and lines[i].startswith("- "):
                items.append(r"\item " + inline(lines[i][2:]))
                i += 1
            out.append("\\begin{itemize}\n" + "\n".join(items) + "\n\\end{itemize}")
        elif line.strip() == "":
            i += 1
        else:
            # Join consecutive wrapped lines into one paragraph so inline markup
            # (e.g. a *caption* split across two source lines) pairs correctly.
            para = []
            while i < n and lines[i].strip() != "" and not _is_block_start(lines[i]):
                para.append(lines[i])
                i += 1
            out.append(inline(" ".join(para)))
    return "\n\n".join(out)


def _table(rows: list[str]) -> str:
    def cells(r: str) -> list[str]:
        return [c.strip() for c in r.strip().strip("|").split("|")]

    header = cells(rows[0])
    align_row = cells(rows[1])
    body = [cells(r) for r in rows[2:]]
    align = "".join("r" if a.endswith(":") else "l" for a in align_row)
    spec = "|" + "|".join(align) + "|"
    lines = [r"\begin{center}\begin{tabular}{" + spec + "}", r"\hline"]
    lines.append(" & ".join(rf"\textbf{{{inline(h)}}}" for h in header) + r" \\ \hline")
    for row in body:
        lines.append(" & ".join(inline(c) for c in row) + r" \\ \hline")
    lines.append(r"\end{tabular}\end{center}")
    return "\n".join(lines)


def main() -> None:
    if not shutil.which("tectonic"):
        raise SystemExit("tectonic not found; install it (e.g. `brew install tectonic`)")
    body = md_to_latex(SRC.read_text(encoding="utf-8"))
    tex = PREAMBLE + body + "\n\\end{document}\n"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "paper.tex").write_text(tex, encoding="utf-8")
        proc = subprocess.run(
            ["tectonic", "--outdir", str(tmp), str(tmp / "paper.tex")],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise SystemExit(f"tectonic failed:\n{proc.stderr[-2000:]}")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp / "paper.pdf", OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
