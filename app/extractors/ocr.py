"""OCR opcional con Tesseract (Apache-2.0) para PDFs escaneados. Si no está instalado se avisa con claridad."""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from app.errors import UserError

LANG_CODES = {"es": "spa", "en": "eng"}
DPI = 250


def tesseract_path() -> str | None:
    return shutil.which("tesseract")


def installed_languages() -> set[str]:
    exe = tesseract_path()
    if not exe:
        return set()
    out = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, check=False).stdout
    return {ln.strip() for ln in out.splitlines()[1:] if ln.strip()}


def require(language: str) -> str:
    """Comprueba Tesseract y el idioma; devuelve el código de idioma de Tesseract."""
    if not tesseract_path():
        raise UserError("ocr_missing")
    code = LANG_CODES.get(language, "spa")
    if code not in installed_languages():
        raise UserError("ocr_lang_missing", lang=code)
    return code


def ocr_pages(path: Path, page_indexes: list[int], language: str,
              progress: Callable[[int, int], None] | None = None) -> dict[int, str]:
    """Reconoce el texto de las páginas indicadas (índices desde 0). Devuelve {página: texto}."""
    code = require(language)
    import pypdfium2 as pdfium
    import pytesseract

    result: dict[int, str] = {}
    pdf = pdfium.PdfDocument(str(path))
    try:
        for n, idx in enumerate(page_indexes):
            if progress:
                progress(n, len(page_indexes))
            page = pdf[idx]
            image = page.render(scale=DPI / 72).to_pil().convert("L")
            try:
                result[idx] = pytesseract.image_to_string(image, lang=code)
            except pytesseract.TesseractError as exc:
                raise UserError("ocr_failed", str(exc)[:200]) from exc
            finally:
                page.close()
    finally:
        pdf.close()
    if progress:
        progress(len(page_indexes), len(page_indexes))
    return result
