import json
import os
import shutil
import subprocess


# lo_convert.py needs LibreOffice's `uno` module, which lives in the system Python
# (Debian: python3-uno), not in the app's interpreter
UNO_PYTHON = os.getenv("UNO_PYTHON", "/usr/bin/python3")
SOFFICE = os.getenv("SOFFICE", "soffice")
CONVERT_SCRIPT = os.path.join(os.path.dirname(__file__), "lo_convert.py")
TIMEOUT_S = int(os.getenv("PDF_TIMEOUT_S", "180"))


def pdf_available() -> bool:
    return os.path.exists(UNO_PYTHON) and shutil.which(SOFFICE) is not None


def render_pdf(docx_path: str) -> tuple[str, dict[str, int]]:
    """Convert docx -> pdf next to it. Returns (pdf_path, {toc_bookmark: page})."""
    pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
    result = subprocess.run(
        [UNO_PYTHON, CONVERT_SCRIPT, docx_path, pdf_path],
        capture_output=True, text=True, timeout=TIMEOUT_S,
        env={**os.environ, "SOFFICE": SOFFICE},
    )
    if result.returncode != 0 or not os.path.exists(pdf_path):
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr.strip()[-500:]}")
    pages = json.loads(result.stdout.strip().splitlines()[-1])["pages"]
    return pdf_path, pages
