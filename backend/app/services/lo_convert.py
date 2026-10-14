"""Render a .docx with LibreOffice: refresh the table of contents, export PDF and report
the page of every TOC bookmark.

Must run under a Python that has LibreOffice's `uno` module (Debian: /usr/bin/python3 with
python3-uno), so the app calls it as a subprocess — see pdf_service.py.

Usage: lo_convert.py IN.docx OUT.pdf
Prints JSON to stdout: {"pages": {"_Toc00000001": 3, ...}}
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import uno
from com.sun.star.beans import PropertyValue


def _prop(name, value):
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def _connect(pipe, proc, timeout=90):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"soffice exited with code {proc.returncode}")
        try:
            return resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("LibreOffice did not start in time")


def convert(src, pdf):
    soffice = os.environ.get("SOFFICE", "soffice")
    profile = tempfile.mkdtemp(prefix="mlgr-lo-")
    pipe = f"mlgr_{os.getpid()}"
    proc = subprocess.Popen(
        [soffice, "--headless", "--invisible", "--norestore", "--nologo", "--nodefault",
         f"-env:UserInstallation={uno.systemPathToFileUrl(profile)}",
         f"--accept=pipe,name={pipe};urp;"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    desktop = None
    try:
        ctx = _connect(pipe, proc)
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.loadComponentFromURL(
            uno.systemPathToFileUrl(os.path.abspath(src)), "_blank", 0, (_prop("Hidden", True),)
        )

        # The .docx carries estimated page numbers; let the layout engine compute real ones
        indexes = doc.getDocumentIndexes()
        for i in range(indexes.getCount()):
            indexes.getByIndex(i).update()
        doc.getTextFields().refresh()

        pages = {}
        cursor = doc.getCurrentController().getViewCursor()
        bookmarks = doc.getBookmarks()
        for name in bookmarks.getElementNames():
            if name.startswith("_Toc"):
                cursor.gotoRange(bookmarks.getByName(name).getAnchor(), False)
                pages[name] = cursor.getPage()

        doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(pdf)), (_prop("FilterName", "writer_pdf_Export"),))
        doc.close(True)
        return pages
    finally:
        try:
            if desktop is not None:
                desktop.terminate()
        except Exception:
            pass  # the bridge drops when soffice exits
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    print(json.dumps({"pages": convert(sys.argv[1], sys.argv[2])}))
