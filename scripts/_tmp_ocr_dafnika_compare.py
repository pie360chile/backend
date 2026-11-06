"""Prueba OCR Dafnika: Tesseract / EasyOCR / PaddleOCR (+ RapidOCR baseline).

Descarga el PDF desde Drive, OCR por motor, mapea campos anamnesis y reporta conteos.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DATABASE_URL"] = (
    os.environ.get("IMPORT_DATABASE_URL")
    or "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
)

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.import_drive_anamnesis import (
    _access_token,
    _download_drive_file,
    map_pdf_to_anamnesis_payload,
)

DRIVE_FILE_ID = "1KVUTB9W91Z3IfB7G_24RTTnc3V5X3miR"
STUDENT_ID = 1851
OUT_DIR = ROOT / "scripts" / "output" / "ocr_dafnika"
MAX_PAGES = 8
ZOOM = 2.0


def _find_tesseract() -> str | None:
    candidates = [
        os.environ.get("TESSERACT_CMD"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def _pdf_to_images(content: bytes) -> list[np.ndarray]:
    import fitz
    import cv2

    images: list[np.ndarray] = []
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        mat = fitz.Matrix(ZOOM, ZOOM)
        for i, page in enumerate(doc):
            if i >= MAX_PAGES:
                break
            pix = page.get_pixmap(matrix=mat, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            # fitz RGB → BGR for OpenCV consumers
            images.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    finally:
        doc.close()
    return images


def ocr_tesseract(images: list[np.ndarray]) -> str:
    import pytesseract
    from PIL import Image

    cmd = _find_tesseract()
    if not cmd:
        raise RuntimeError("tesseract.exe no encontrado")
    pytesseract.pytesseract.tesseract_cmd = cmd
    parts = []
    for img in images:
        rgb = img[:, :, ::-1]
        pil = Image.fromarray(rgb)
        # spa+eng si disponible, sino spa, sino default
        for lang in ("spa+eng", "spa", "eng"):
            try:
                txt = pytesseract.image_to_string(pil, lang=lang, config="--psm 6")
                break
            except Exception:
                txt = ""
        if txt.strip():
            parts.append(txt.strip())
    return "\n\n".join(parts)


def ocr_easyocr(images: list[np.ndarray]) -> str:
    import easyocr

    reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
    parts = []
    for img in images:
        result = reader.readtext(img, detail=0, paragraph=True)
        page = "\n".join(str(x).strip() for x in result if str(x).strip())
        if page:
            parts.append(page)
    return "\n\n".join(parts)


def ocr_paddle(images: list[np.ndarray]) -> str:
    from paddleocr import PaddleOCR

    # PaddleOCR 2.x / 3.x APIs varían
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="es", show_log=False)
    except TypeError:
        ocr = PaddleOCR(lang="es")
    parts = []
    for img in images:
        try:
            result = ocr.ocr(img, cls=True)
        except TypeError:
            result = ocr.ocr(img)
        lines = []
        if not result:
            continue
        # result puede ser list[list] o dict-like en v3
        pages = result if isinstance(result, list) else [result]
        for page in pages:
            if page is None:
                continue
            if isinstance(page, dict):
                texts = page.get("rec_texts") or page.get("texts") or []
                lines.extend(str(t).strip() for t in texts if str(t).strip())
                continue
            for item in page:
                if not item:
                    continue
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    txt = item[1][0] if isinstance(item[1], (list, tuple)) else item[1]
                    if txt:
                        lines.append(str(txt).strip())
        if lines:
            parts.append("\n".join(lines))
    return "\n\n".join(parts)


def ocr_rapid(images: list[np.ndarray]) -> str:
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    parts = []
    for img in images:
        result, _ = engine(img)
        if not result:
            continue
        lines = [str(item[1]).strip() for item in result if item and len(item) > 1]
        page = "\n".join(ln for ln in lines if ln)
        if page:
            parts.append(page)
    return "\n\n".join(parts)


def count_mapped(text: str) -> tuple[int, list[str], dict]:
    payload = map_pdf_to_anamnesis_payload(
        student_id=STUDENT_ID,
        text=text,
        fields={},
        student_name_fallback="DAFNIKA SAINT FORT ALBERT",
    )
    keys = payload.pop("_mapped_keys", []) or []
    # quitar meta
    filled = {
        k: v
        for k, v in payload.items()
        if k != "student_id" and v is not None and str(v).strip() != ""
    }
    return len(keys), sorted(keys), filled


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUT_DIR / "dafnika.pdf"

    if pdf_path.exists() and pdf_path.stat().st_size > 1000:
        print(f"Usando PDF local: {pdf_path} ({pdf_path.stat().st_size} bytes)", flush=True)
        content = pdf_path.read_bytes()
    else:
        print("Descargando PDF Dafnika desde Drive...", flush=True)
        engine = create_engine(os.environ["DATABASE_URL"])
        Session = sessionmaker(bind=engine)
        with Session() as db:
            token = _access_token(db)
        content = _download_drive_file(token, DRIVE_FILE_ID)
        pdf_path.write_bytes(content)
        print(f"Guardado {pdf_path} ({len(content)} bytes)", flush=True)

    print("Renderizando páginas a imagen...", flush=True)
    images = _pdf_to_images(content)
    print(f"Páginas renderizadas: {len(images)}", flush=True)

    engines = [
        ("tesseract", ocr_tesseract),
        ("easyocr", ocr_easyocr),
        ("paddleocr", ocr_paddle),
        ("rapidocr", ocr_rapid),
    ]

    summary = []
    for name, fn in engines:
        print(f"\n=== {name} ===", flush=True)
        t0 = time.time()
        err = None
        text = ""
        try:
            text = fn(images)
        except Exception as exc:
            err = str(exc)
            print(f"ERROR: {exc}", flush=True)
        elapsed = round(time.time() - t0, 1)
        (OUT_DIR / f"{name}_text.txt").write_text(text or "", encoding="utf-8")
        n_keys, keys, filled = count_mapped(text or "")
        preview = (text or "")[:400].replace("\n", " | ")
        print(f"chars={len(text or '')} mapped_keys={n_keys} filled={len(filled)} sec={elapsed}", flush=True)
        print(f"keys: {keys}", flush=True)
        print(f"preview: {preview}", flush=True)
        row = {
            "engine": name,
            "error": err,
            "chars": len(text or ""),
            "mapped_keys": n_keys,
            "filled_fields": len(filled),
            "keys": keys,
            "sample_fields": {k: filled[k] for k in list(filled)[:25]},
            "seconds": elapsed,
        }
        summary.append(row)
        (OUT_DIR / f"{name}_fields.json").write_text(
            json.dumps({"keys": keys, "filled": filled}, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print("\n===== RESUMEN =====", flush=True)
    for row in summary:
        print(
            f"{row['engine']}: campos_mapeados={row['mapped_keys']} "
            f"rellenos={row['filled_fields']} chars={row['chars']} "
            f"sec={row['seconds']} err={row['error']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
