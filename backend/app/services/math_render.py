"""Formulas: LaTeX -> Word OMML (real, editable Word equations in the .docx) and
LaTeX -> SVG (WeasyPrint has no MathML support, so the PDF gets vector images).

Both go through MathML (latex2mathml), so the same LaTeX subset works in both.
A formula that cannot be converted falls back to its LaTeX source in the document
instead of failing the whole build."""
import re
from functools import lru_cache

import structlog
from lxml import etree

logger = structlog.get_logger().bind(service="math")

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# 14 pt in CSS px — the body font size, so inline formulas match the text
BODY_PX = 14 * 96 / 72


class FormulaError(ValueError):
    pass


def normalize(latex: str) -> str:
    """Spacing hints that latexify emits and the converters do not understand."""
    latex = re.sub(r"\\math(open|close)\{\}", "", latex or "")
    return latex.strip()


@lru_cache(maxsize=512)
def latex_to_mathml(latex: str, display: bool = False) -> str:
    import latex2mathml.converter
    try:
        return latex2mathml.converter.convert(normalize(latex), display="block" if display else "inline")
    except Exception as exc:  # the library raises many exception types for bad input
        raise FormulaError(str(exc) or "Некоректна формула") from exc


def latex_to_omml(latex: str):
    """<m:oMath> element ready to be appended to a w:p (inline) or wrapped in m:oMathPara."""
    import mathml2omml
    try:
        xml = mathml2omml.convert(latex_to_mathml(latex))
        root = etree.fromstring(f'<root xmlns:m="{M_NS}" xmlns:w="{W_NS}">{xml}</root>')
    except FormulaError:
        raise
    except Exception as exc:
        raise FormulaError(str(exc) or "Некоректна формула") from exc
    math = root.find(f"{{{M_NS}}}oMath")
    if math is None:
        raise FormulaError("Порожня формула")
    return math


@lru_cache(maxsize=512)
def latex_to_svg(latex: str, inline: bool = False, size: float = BODY_PX) -> tuple[str, float, float, float]:
    """(svg, width_px, height_px, depth_px); depth is how far the formula goes below the
    text baseline — used to align inline formulas with the surrounding text."""
    import ziamath
    try:
        math = ziamath.Latex(normalize(latex), size=size, inline=inline, margin=0)
        svg = math.svg()
    except Exception as exc:
        raise FormulaError(str(exc) or "Некоректна формула") from exc
    width, height = (float(v) for v in re.search(r'width="([\d.]+)" height="([\d.]+)"', svg).groups())
    view_y = float(re.search(r'viewBox="[-\d.]+ ([-\d.]+)', svg).group(1))
    return svg, width, height, max(0.0, height + view_y)


def check_latex(latex: str) -> str | None:
    """Error message for a formula that would not render, or None."""
    try:
        latex_to_omml(latex)
        latex_to_svg(latex)
    except FormulaError as exc:
        return str(exc)
    return None
