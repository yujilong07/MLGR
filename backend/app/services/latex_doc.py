"""LaTeX mode: the report content as LaTeX source and back.

    to_latex_body(report, images)  -> the editable part (no preamble / title page)
    parse_latex_body(source, kind) -> sections, goal / introduction, conclusion,
                                      bibliography, figure placement, warnings
    export_tex_zip(report, images) -> main.tex (preamble + title page + body) and images/

There is no TeX on the server: the source is parsed into the same structure the form
edits, and the .docx / PDF are built from that. Only a practical subset is understood
(sections, paragraphs, $...$, equation-like environments, lstlisting / verbatim / minted,
figure + \\includegraphics, itemize / enumerate, thebibliography); anything else is
simplified to its text and reported in `warnings`."""
import io
import os
import re
import zipfile

from app.services.content import item_blocks, split_inline
from app.services.report_outline import essay_people, is_essay, signature_rows

# ── text escaping ────────────────────────────────────────────────────────────

_ESCAPES = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "$": r"\$",
}


def escape_text(text: str) -> str:
    return "".join(_ESCAPES.get(ch, ch) for ch in text)


def inline_to_latex(line: str) -> str:
    """Plain line with $...$ formulas -> LaTeX (text escaped, formulas kept)."""
    return "".join(f"${v}$" if kind == "math" else escape_text(v) for kind, v in split_inline(line))


# lstlisting names; javascript / typescript / css are defined in the exported preamble
_LST_LANG = {"python": "Python", "javascript": "JavaScript", "typescript": "TypeScript", "java": "Java",
             "cpp": "C++", "c": "C", "sql": "SQL", "bash": "bash", "html": "HTML", "css": "CSS"}
_LANG_FROM_LST = {v.lower(): k for k, v in _LST_LANG.items()} | {"sh": "bash", "shell": "bash", "c++": "cpp", "js": "javascript"}


def _image_name(img) -> str:
    return f"img-{img.id}"


# ── structure -> LaTeX ───────────────────────────────────────────────────────

def _blocks_to_latex(item, figures) -> list[str]:
    out = []
    for block in item_blocks(item):
        kind = block["type"]
        if kind == "text":
            out += [inline_to_latex(line.strip()) for line in (block.get("text") or "").split("\n") if line.strip()]
        elif kind == "code" and (block.get("code") or "").strip():
            lang = _LST_LANG.get(block.get("language") or "python", "Python")
            code = block["code"].replace("\r\n", "\n").rstrip("\n")
            out.append(f"\\begin{{lstlisting}}[language={lang}]\n{code}\n\\end{{lstlisting}}")
        elif kind == "formula" and (block.get("latex") or "").strip():
            out.append(f"\\begin{{equation}}\n  {block['latex'].strip()}\n\\end{{equation}}")
    for img in figures:
        out.append(
            "\\begin{figure}[h]\n  \\centering\n"
            f"  \\includegraphics[width=0.8\\textwidth]{{{_image_name(img)}}}\n"
            f"  \\caption{{{inline_to_latex(img.caption or '')}}}\n\\end{{figure}}"
        )
    return out


def _paragraphs(text) -> list[str]:
    return [inline_to_latex(line.strip()) for line in (text or "").split("\n") if line.strip()]


def to_latex_body(report, images=None) -> str:
    by_path = {}
    for img in sorted(images or [], key=lambda i: (i.position or 0, i.id or 0)):
        by_path.setdefault(img.section_path, []).append(img)

    parts = []
    if is_essay(report):
        parts += ["\\section*{Вступ}", *_paragraphs(getattr(report, "introduction", ""))]
    else:
        parts += ["\\section*{Мета роботи}", *_paragraphs(report.goal)]

    for i, section in enumerate(report.sections or []):
        parts.append(f"\\section{{{inline_to_latex((section.get('title') or '').strip())}}}")
        parts += _blocks_to_latex(section, by_path.get(str(i), []))
        for j, sub in enumerate(section.get("subsections") or []):
            parts.append(f"\\subsection{{{inline_to_latex((sub.get('title') or '').strip())}}}")
            parts += _blocks_to_latex(sub, by_path.get(f"{i}.{j}", []))

    parts += ["\\section*{Висновки}", *_paragraphs(report.conclusion)]

    refs = [r for r in (getattr(report, "bibliography", None) or []) if (r or "").strip()]
    if refs or is_essay(report):
        items = "\n".join(f"  \\bibitem{{{n}}} {escape_text(r.strip())}" for n, r in enumerate(refs, start=1))
        parts.append(f"\\begin{{thebibliography}}{{99}}\n{items}\n\\end{{thebibliography}}")
    return "\n\n".join(parts) + "\n"


# ── LaTeX -> structure ───────────────────────────────────────────────────────

_MATH_ENVS = {"equation", "equation*", "align", "align*", "gather", "gather*", "multline", "multline*",
              "displaymath", "eqnarray", "eqnarray*"}
_CODE_ENVS = ("lstlisting", "verbatim", "minted", "Verbatim")
_DROP_ENVS = {"titlepage", "abstract"}
_SPECIAL_TITLES = {
    "мета роботи": "goal", "мета": "goal",
    "вступ": "introduction",
    "висновки": "conclusion", "висновок": "conclusion",
    "перелік посилань": "references", "список літератури": "references", "література": "references",
    "список використаних джерел": "references", "список використаної літератури": "references",
}
_NOISE = re.compile(
    r"\\(maketitle|tableofcontents|newpage|clearpage|pagebreak|noindent|centering|"
    r"bigskip|medskip|smallskip|hfill|vfill|indent|par(?![a-z]))\b\s*"
    r"|\\(label|vspace\*?|hspace\*?|addcontentsline|setcounter|thispagestyle|pagestyle)\s*(\{[^{}]*\}\s*)+"
)
_FORMAT_CMDS = ("textbf", "textit", "emph", "underline", "texttt", "textrm", "textsc", "textsf", "mbox", "text")


def _match_brace(s: str, start: int) -> int:
    """Index just after the "}" closing the "{" at s[start]; -1 when unbalanced."""
    depth, i = 0, start
    while i < len(s):
        ch = s[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _braced_arg(s: str, pos: int) -> tuple[str, int]:
    """(content, end) of the {...} argument starting at or after pos (skipping spaces / [opts])."""
    while pos < len(s) and s[pos] in " \t\n":
        pos += 1
    if pos < len(s) and s[pos] == "[":
        close = s.find("]", pos)
        pos = close + 1 if close != -1 else pos
        while pos < len(s) and s[pos] in " \t\n":
            pos += 1
    if pos >= len(s) or s[pos] != "{":
        return "", pos
    end = _match_brace(s, pos)
    if end == -1:
        return s[pos + 1:], len(s)
    return s[pos + 1:end - 1], end


def _flatten_env(body: str) -> str:
    """Text of an unsupported environment (tables: one line per row, cells joined by " | ")."""
    body = re.sub(r"^\s*\[[^\]]*\]", "", body)                               # [h] placement
    body = re.sub(r"\\(begin|end)\{[^{}]*\}(\[[^\]]*\])?(\{[^{}]*\})?", " ", body)
    body = re.sub(r"\\(hline|toprule|midrule|bottomrule|centering)|\\cline\{[^{}]*\}", " ", body)
    body = re.sub(r"\\caption\s*\{([^{}]*)\}", r"\n\n\1\n\n", body)
    rows = [" | ".join(c.strip() for c in row.split("&")) for row in body.split("\\\\")]
    return "\n\n".join(r for r in rows if r.strip())


def _strip_comments(s: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", s)


class _Parser:
    def __init__(self, kind: str, image_ids: set[int]):
        self.kind = kind
        self.image_ids = image_ids
        self.warnings: list[str] = []
        self.front: list[str] = []          # goal (lab) / introduction (essay)
        self.conclusion: list[str] = []
        self.references: list[str] = []
        self.sections: list[dict] = []
        self.figures: list[dict] = []        # {image_id, section_path, position, caption}
        self.target = "front"                # front | conclusion | references | section
        self.code_blocks: list[tuple[str, str]] = []

    # warnings are shown to the user; keep each one once
    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)

    # ── inline text ──
    def text_to_plain(self, s: str) -> str:
        """LaTeX paragraph -> our plain line (inline math kept as $...$)."""
        s = re.sub(r"\\\((.+?)\\\)", lambda m: f"${m.group(1)}$", s, flags=re.S)
        out = []
        for kind, value in split_inline(s.replace("\\$", "\x01")):
            if kind == "math":
                out.append(f"${' '.join(value.split())}$")
            else:
                out.append(self._unlatex(value.replace("\x01", "\\$")))
        return " ".join("".join(out).split())

    def _unlatex(self, s: str) -> str:
        if re.search(r"\\(textbf|textit|emph|underline|textsc)\b", s):
            self.warn("Жирний, курсив і підкреслення (\\textbf, \\emph, ...) у документі не зберігаються — лишається звичайний текст")
        for _ in range(5):  # nested \textbf{\emph{..}}
            new = re.sub(r"\\(" + "|".join(_FORMAT_CMDS) + r")\s*\{([^{}]*)\}", r"\2", s)
            if new == s:
                break
            s = new
        s = re.sub(r"\\cite\s*(\[[^\]]*\])?\{([^{}]*)\}", lambda m: f"[{m.group(2)}]", s)
        s = re.sub(r"\\(ref|eqref|pageref)\{([^{}]*)\}", r"\2", s)
        s = re.sub(r"\\url\{([^{}]*)\}", r"\1", s)
        s = re.sub(r"\\href\{([^{}]*)\}\{([^{}]*)\}", r"\2 (\1)", s)
        for latex, plain in ((r"\textbackslash{}", "\\"), (r"\textasciitilde{}", "~"), (r"\textasciicircum{}", "^"),
                             ("---", "—"), ("--", "–"), (r"\ldots", "…"), (r"\dots", "…"),
                             ("``", "«"), ("''", "»"), (r"\,", " "), (r"\;", " "), (r"\ ", " ")):
            s = s.replace(latex, plain)
        s = re.sub(r"(?<!\\)~", " ", s)
        s = re.sub(r"\\([&%#_{}$])", r"\1", s)
        unknown = re.findall(r"\\([a-zA-Z]+)", s)
        if unknown:
            self.warn("Команди " + ", ".join(sorted({f"\\{u}" for u in unknown})) + " не підтримуються — залишено лише їхній текст")
            s = re.sub(r"\\[a-zA-Z]+\*?\s*(\[[^\]]*\])?", "", s)
            s = s.replace("{", "").replace("}", "")
        return s

    def paragraphs(self, chunk: str) -> list[str]:
        chunk = chunk.replace("\\\\", "\n\n")
        return [p for p in (self.text_to_plain(para) for para in re.split(r"\n\s*\n", chunk)) if p]

    # ── targets ──
    def current_item(self):
        if self.target != "section" or not self.sections:
            return None
        sec = self.sections[-1]
        return sec["subsections"][-1] if sec["subsections"] else sec

    def current_path(self):
        if self.target != "section" or not self.sections:
            return None
        i = len(self.sections) - 1
        subs = self.sections[-1]["subsections"]
        return f"{i}.{len(subs) - 1}" if subs else str(i)

    def add_block(self, block):
        item = self.current_item()
        if item is not None:
            if block["type"] == "text" and item["blocks"] and item["blocks"][-1]["type"] == "text":
                item["blocks"][-1]["text"] += "\n" + block["text"]
            else:
                item["blocks"].append(block)
            return
        # goal / introduction / conclusion are plain text fields
        dest = {"front": self.front, "conclusion": self.conclusion, "references": self.references}[self.target]
        if block["type"] == "text":
            if self.target == "references":
                dest += [re.sub(r"^\s*\d+[.)]\s*", "", l) for l in block["text"].split("\n") if l.strip()]
            else:
                dest += block["text"].split("\n")
        elif block["type"] == "formula":
            dest.append(f"${block['latex']}$")
        else:
            self.warn("Код поза розділами (у меті, вступі чи висновках) не підтримується — його пропущено")

    def add_text(self, chunk):
        paras = self.paragraphs(chunk)
        if paras:
            self.add_block({"type": "text", "text": "\n".join(paras)})

    def heading(self, level, starred, title_src):
        title = self.text_to_plain(title_src)
        special = _SPECIAL_TITLES.get(title.strip().lower().rstrip("."))
        if level == 1 and special:
            if special in ("goal", "introduction"):
                self.target = "front"
            else:
                self.target = special
            return
        if level == 1:
            if starred:
                self.warn(f"\\section*{{{title}}} у документі буде пронумеровано як звичайний розділ")
            self.sections.append({"title": title, "blocks": [], "subsections": []})
            self.target = "section"
        elif level == 2:
            if not self.sections or self.target != "section":
                self.warn("\\subsection до першого \\section — створено розділ без назви")
                self.sections.append({"title": "", "blocks": [], "subsections": []})
                self.target = "section"
            self.sections[-1]["subsections"].append({"title": title, "blocks": []})
        else:
            # \subsubsection / \paragraph: our document has two heading levels
            self.warn("\\subsubsection і \\paragraph стають звичайним абзацом")
            self.add_block({"type": "text", "text": title})

    def figure(self, body):
        names = re.findall(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^{}]*)\}", body)
        cap_pos = body.find("\\caption")
        caption = None
        if cap_pos != -1:
            caption_src, _ = _braced_arg(body, cap_pos + len("\\caption"))
            caption = self.text_to_plain(caption_src)
        for name in names:
            self.place_image(name, caption)

    def place_image(self, name, caption):
        m = re.search(r"img-(\d+)", name)
        if not m or int(m.group(1)) not in self.image_ids:
            self.warn(f"Зображення «{name}» не знайдено серед завантажених — додайте його кнопкою «Рисунок»")
            return
        path = self.current_path()
        if path is None:
            self.warn("Рисунок поза розділом не підтримується — перенесіть його в розділ")
            return
        position = sum(1 for f in self.figures if f["section_path"] == path)
        self.figures.append({"image_id": int(m.group(1)), "section_path": path, "position": position,
                             "caption": caption})

    def list_env(self, env, body):
        items = [i.strip() for i in re.split(r"\\item\b", body)[1:]]
        lines = []
        for n, item in enumerate(items, start=1):
            text = " ".join(self.paragraphs(item))
            if text:
                lines.append(f"{n}. {text}" if env == "enumerate" else f"– {text}")
        if self.target == "references":
            self.references += [" ".join(self.paragraphs(i)) for i in items if i.strip()]
        elif lines:
            self.add_block({"type": "text", "text": "\n".join(lines)})

    def bibliography(self, body):
        body = re.sub(r"^\s*\{[^{}]*\}", "", body)  # {99}
        for item in re.split(r"\\bibitem\s*(?:\[[^\]]*\])?\s*\{[^{}]*\}", body)[1:]:
            text = " ".join(self.paragraphs(item))
            if text:
                self.references.append(text)

    # ── main loop ──
    _TOKEN = re.compile(
        r"\\(section|subsection|subsubsection|paragraph)(\*?)\s*(?=[\[{])"
        r"|\\begin\{([a-zA-Z]+\*?)\}"
        r"|\\\[|\$\$"
        r"|\x00CODE(\d+)\x00"
        r"|\\includegraphics"
    )

    def run(self, source: str):
        source = source.replace("\r\n", "\n")
        if "\\begin{document}" in source:
            source = source.split("\\begin{document}", 1)[1]
            source = source.split("\\end{document}", 1)[0]

        # code first: % and \ inside code are literal
        def keep_code(m):
            env, opts, body = m.group(1), m.group(2) or "", m.group(4)
            lang = "python"
            lm = re.search(r"language\s*=\s*\{?([\w+#]+)", opts)
            if env == "minted" and m.group(3):
                lang = m.group(3)
            elif lm:
                lang = lm.group(1)
            self.code_blocks.append((_LANG_FROM_LST.get(lang.lower(), "python"), body.strip("\n")))
            return f"\x00CODE{len(self.code_blocks) - 1}\x00"

        source = re.sub(
            r"\\begin\{(lstlisting|verbatim|minted|Verbatim)\}(\[[^\]]*\])?(?:\{([^{}]*)\})?(.*?)\\end\{\1\}",
            keep_code, source, flags=re.S)
        source = _strip_comments(source)
        source = _NOISE.sub("", source)

        pos = 0
        while True:
            m = self._TOKEN.search(source, pos)
            end_text = m.start() if m else len(source)
            if end_text > pos:
                self.add_text(source[pos:end_text])
            if not m:
                break
            pos = m.end()

            if m.group(1):  # heading
                level = {"section": 1, "subsection": 2}.get(m.group(1), 3)
                title, pos = _braced_arg(source, pos)
                self.heading(level, bool(m.group(2)), title)
            elif m.group(3):  # environment
                env = m.group(3)
                close = source.find(f"\\end{{{env}}}", pos)
                body = source[pos:close] if close != -1 else source[pos:]
                pos = close + len(f"\\end{{{env}}}") if close != -1 else len(source)
                if env in _MATH_ENVS:
                    latex = re.sub(r"\\(label|nonumber|notag)(\{[^{}]*\})?", "", body).strip()
                    if env.startswith(("align", "eqnarray")) or "\\\\" in latex and env.startswith(("gather", "multline")):
                        latex = f"\\begin{{aligned}}{latex}\\end{{aligned}}"
                    if latex:
                        self.add_block({"type": "formula", "latex": " ".join(latex.split())})
                elif env == "figure" or env == "figure*":
                    self.figure(body)
                elif env in ("itemize", "enumerate"):
                    self.list_env(env, body)
                elif env == "thebibliography":
                    self.bibliography(body)
                elif env in _DROP_ENVS:
                    continue
                elif env in ("center", "flushleft", "flushright", "quote", "quotation"):
                    self.add_text(body)
                else:
                    if env in ("table", "tabular", "table*", "longtable", "tabularx"):
                        self.warn("Таблиці поки не підтримуються — рядки таблиці збережено як текст «a | b»")
                    else:
                        self.warn(f"Оточення {env} не підтримується — збережено лише його текст")
                    self.add_text(_flatten_env(body))
            elif m.group(0) in ("\\[", "$$"):
                closer = "\\]" if m.group(0) == "\\[" else "$$"
                close = source.find(closer, pos)
                latex = source[pos:close] if close != -1 else source[pos:]
                pos = close + len(closer) if close != -1 else len(source)
                if latex.strip():
                    self.add_block({"type": "formula", "latex": " ".join(latex.split())})
            elif m.group(4) is not None:  # code
                lang, code = self.code_blocks[int(m.group(4))]
                self.add_block({"type": "code", "code": code, "language": lang})
            else:  # bare \includegraphics in the text
                name, pos = _braced_arg(source, pos)
                self.place_image(name, None)

    def result(self):
        def clean(item):
            item["blocks"] = [b for b in item["blocks"] if not (b["type"] == "text" and not b["text"].strip())]
            return item
        sections = [{**clean(s), "subsections": [clean(sub) for sub in s["subsections"]]} for s in self.sections]
        front = "\n".join(l for l in self.front if l.strip())
        return {
            "sections": sections,
            "goal" if self.kind != "essay" else "introduction": front,
            "conclusion": "\n".join(l for l in self.conclusion if l.strip()),
            "bibliography": self.references,
            "figures": self.figures,
            "warnings": self.warnings,
        }


def parse_latex_body(source: str, kind: str = "lab", image_ids=()) -> dict:
    parser = _Parser(kind, set(image_ids))
    parser.run(source or "")
    return parser.result()


# ── full document for Overleaf ───────────────────────────────────────────────

_PREAMBLE = r"""% Згенеровано MLGR. Компілювати XeLaTeX або LuaLaTeX
% (Overleaf: Menu -> Compiler -> XeLaTeX).
\documentclass[14pt,a4paper]{extarticle}
\usepackage{fontspec}
\IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{%
  \IfFontExistsTF{Liberation Serif}{\setmainfont{Liberation Serif}}{\setmainfont{CMU Serif}}}
\IfFontExistsTF{Courier New}{\setmonofont{Courier New}}{%
  \IfFontExistsTF{Liberation Mono}{\setmonofont{Liberation Mono}}{\setmonofont{CMU Typewriter Text}}}
\usepackage{polyglossia}
\setdefaultlanguage{ukrainian}
\usepackage[left=30mm,right=20mm,top=20mm,bottom=20mm,headsep=5mm]{geometry}
\usepackage{setspace}
\onehalfspacing
\usepackage{indentfirst}
\setlength{\parindent}{1.25cm}
\setlength{\parskip}{0pt}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\graphicspath{{images/}}
\usepackage{listings}
\lstset{basicstyle=\fontsize{12}{13.5}\selectfont\ttfamily, breaklines=true, columns=fullflexible,
  keepspaces=true, showstringspaces=false, frame=none, xleftmargin=0pt}
\lstdefinelanguage{JavaScript}{morekeywords={function,return,var,let,const,if,else,for,while,class,new,import,export},
  sensitive=true, morecomment=[l]{//}, morecomment=[s]{/*}{*/}, morestring=[b]", morestring=[b]'}
\lstdefinelanguage{TypeScript}[]{JavaScript}{morekeywords={interface,type,implements}}
\lstdefinelanguage{CSS}{sensitive=false, morecomment=[s]{/*}{*/}}
\renewcommand{\lstlistingname}{Лістинг}
\usepackage[labelsep=endash]{caption}
\captionsetup[figure]{name=Рисунок}
\captionsetup[lstlisting]{singlelinecheck=false, justification=raggedright}
\usepackage{titlesec}
\titleformat{\section}{\normalfont\bfseries\filcenter}{\thesection}{0.5em}{\MakeUppercase}
\titleformat{\subsection}{\normalfont\bfseries}{\hspace{1.25cm}\thesubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{0pt}{@@heading_after@@}
\titlespacing*{\subsection}{0pt}{0pt}{@@heading_after@@}
@@section_break@@
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[R]{\thepage}
\renewcommand{\headrulewidth}{0pt}
\usepackage{tocloft}
\renewcommand{\cfttoctitlefont}{\hfill\bfseries}
\renewcommand{\cftaftertoctitle}{\hfill}
\renewcommand{\cftsecfont}{\normalfont}
\renewcommand{\cftsecpagefont}{\normalfont}
\renewcommand{\cftsecleader}{\cftdotfill{\cftdotsep}}
\renewcommand{\contentsname}{ЗМІСТ}
\renewcommand{\refname}{ПЕРЕЛІК ПОСИЛАНЬ}
@@numbering@@
% Unnumbered sections (\section*) still go to the table of contents
\makeatletter
\let\mlgr@section\section
\renewcommand{\section}{\@ifstar{\mlgr@starsection}{\mlgr@section}}
\newcommand{\mlgr@starsection}[1]{\mlgr@section*{\MakeUppercase{#1}}\addcontentsline{toc}{section}{\MakeUppercase{#1}}}
\renewenvironment{thebibliography}[1]{\section*{Перелік посилань}\begin{enumerate}\setlength{\itemsep}{0pt}}{\end{enumerate}}
\renewcommand{\bibitem}[1]{\item}
\makeatother
"""


def _tex_line(text):
    return escape_text(text or "")


def _lab_title(report) -> str:
    rows = signature_rows(report)
    table = "\\\\\n".join(f"{_tex_line(a)} & {_tex_line(b)}" for a, b in rows)
    dept = (getattr(report, "department", "") or "штучного інтелекту").strip()
    return (
        "\\begin{titlepage}\n\\begin{center}\n"
        "Міністерство освіти і науки України\\\\\nХарківський національний університет радіоелектроніки\\\\[1em]\n"
        f"Кафедра {_tex_line(dept)}\n\\vspace{{6em}}\n\n"
        f"Дисципліна «{_tex_line(report.discipline)}»\\\\\n{_tex_line(report.title)}\n\\vspace{{6em}}\n\n"
        "\\begin{tabular}{p{0.45\\textwidth}p{0.45\\textwidth}}\n" + table + "\n\\end{tabular}\n\\vfill\n"
        "Харків -- \\the\\year\n\\end{center}\n\\end{titlepage}\n"
    )


def _essay_title(report) -> str:
    did, lines, checked, teacher = essay_people(report)
    field = lambda label, value: f"{label} \\underline{{\\makebox[0.75\\textwidth]{{{_tex_line(value)}}}}}\\\\"

    def hint(text, newline=True):
        small = f"{{\\fontsize{{10}}{{11}}\\selectfont {text}}}"
        return small + "\\\\[0.6em]" if newline else small

    people = "\n".join(field(did if k == 0 else "\\phantom{" + did + "}", l) + "\n" + hint("(дата, група, прізвище, ініціали)")
                       for k, l in enumerate(lines))
    year = (getattr(report, "work_date", "") or "")[-4:]
    year = year if year.isdigit() else "\\the\\year"
    return (
        "\\begin{titlepage}\n\\begin{center}\n"
        "Міністерство освіти і науки України\\\\\nХарківський національний університет радіоелектроніки\\\\[3em]\n"
        "\\end{center}\n\\noindent\n"
        + field("Факультет", getattr(report, "faculty", "")) + "\n"
        + field("Кафедра", getattr(report, "department", "")) + "\n"
        "\\vspace{4em}\n\\begin{center}{\\fontsize{16}{20}\\selectfont\\bfseries РЕФЕРАТ}\\end{center}\n\\noindent\n"
        + field("на тему:", report.title) + "\n\\centerline{" + hint("(тема реферату)", False) + "}\n\\noindent\n"
        + field("", report.discipline) + "\n\\centerline{" + hint("(дисципліна)", False) + "}\n"
        "\\vspace{3em}\n\\noindent\n" + people + "\n\\vspace{1em}\n\\noindent\n"
        + field(checked, teacher) + "\n" + hint("(посада, прізвище, ініціали)") + "\n"
        f"\\vfill\n\\begin{{center}}Харків {year} р.\\end{{center}}\n\\end{{titlepage}}\n"
    )


def build_tex_document(report, body: str) -> str:
    essay = is_essay(report)
    preamble = _PREAMBLE
    for key, value in {
        "heading_after": "\\baselineskip" if essay else "0pt",
        "section_break": "\\newcommand{\\sectionbreak}{\\clearpage}" if essay else "",
        "numbering": ("\\counterwithin{figure}{section}\n"
                                  # the lstlisting counter only exists from \begin{document}
                                  "\\AtBeginDocument{\\counterwithin{lstlisting}{section}}\n" if essay else "")
                     + "\\numberwithin{equation}{section}",
    }.items():
        preamble = preamble.replace(f"@@{key}@@", value)
    title = _essay_title(report) if essay else _lab_title(report)
    return (
        preamble + "\n\\begin{document}\n" + title
        + "\\setcounter{page}{2}\n\\thispagestyle{empty}\n\\tableofcontents\n\\clearpage\n\n"
        + body + "\n\\end{document}\n"
    )


def export_tex_zip(report, images, uploads_dir=None) -> bytes:
    """main.tex + images/img-<id>.<ext>; ready to upload to Overleaf."""
    uploads_dir = uploads_dir or os.getenv("UPLOADS_DIR", "/app/uploads")
    if getattr(report, "editor_mode", "form") == "latex" and (getattr(report, "latex_source", None) or "").strip():
        body = report.latex_source
    else:
        body = to_latex_body(report, images)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("main.tex", build_tex_document(report, body))
        for img in images or []:
            path = os.path.join(uploads_dir, img.filename)
            if os.path.exists(path):
                ext = os.path.splitext(img.filename)[1] or ".png"
                zf.write(path, f"images/{_image_name(img)}{ext}")
    return buf.getvalue()
