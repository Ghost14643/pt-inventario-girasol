from __future__ import annotations

import io
import re
import shutil
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree.ElementTree import Element

import pymupdf
import pytesseract
from defusedxml.common import DefusedXmlException
from defusedxml import ElementTree
from PIL import Image

MONEY_PATTERN = r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?"
DETAIL_ROW = re.compile(
    rf"^\s*(\d{{3,20}})\s+(\d+(?:[.,]\d+)?)\s+({MONEY_PATTERN})(?:\s+({MONEY_PATTERN}))?\s*$"
)
MAX_PDF_PAGES_FOR_OCR = 20
MAX_INVOICE_LINES = 100
MIN_OCR_DPI = 250


class OCREngineUnavailable(RuntimeError):
    pass


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _child_text(element: Element, name: str) -> str | None:
    for child in element.iter():
        if _local_name(child.tag) == name and child.text:
            value = child.text.strip()
            if value:
                return value
    return None


def _parse_amount(value: str) -> Decimal:
    normalized = value.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"El monto {value!r} de la factura no es válido") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"El monto {value!r} de la factura no es válido")
    return amount


def _parse_xml_amount(value: str) -> Decimal:
    try:
        amount = Decimal(value.strip())
    except InvalidOperation as exc:
        raise ValueError(f"El monto {value!r} del DTE no es válido") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"El monto {value!r} del DTE no es válido")
    return amount


def _parse_quantity(value: str) -> int:
    try:
        quantity = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"La cantidad {value!r} de la factura no es válida") from exc
    if not quantity.is_finite() or quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError(
            f"La cantidad {value!r} no es un número entero de unidades; "
            "revisa esta línea antes de ingresarla al inventario"
        )
    return int(quantity)


def _public_amount(amount: Decimal | None) -> float | None:
    return float(amount) if amount is not None else None


def parsear_dte_xml(content: bytes) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(content)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise ValueError("El archivo XML no tiene una estructura válida") from exc

    items: list[dict[str, Any]] = []
    for detail in (node for node in root.iter() if _local_name(node.tag) == "Detalle"):
        name = _child_text(detail, "NmbItem") or ""
        quantity_text = _child_text(detail, "QtyItem")
        if not quantity_text:
            continue
        quantity = _parse_quantity(quantity_text)
        provider_code = _child_text(detail, "VlrCodigo") or ""
        price_text = _child_text(detail, "PrcItem")
        amount_text = _child_text(detail, "MontoItem")
        cost = _parse_xml_amount(price_text) if price_text else None
        if cost is None and amount_text:
            cost = _parse_xml_amount(amount_text) / quantity
        items.append(
            {
                "sku": provider_code,
                "codigo_proveedor": provider_code,
                "nombre": name[:100],
                "cantidad": quantity,
                "precio_costo": _public_amount(cost),
                "precio_venta": None,
            }
        )

    if not items:
        raise ValueError(
            "No se encontraron líneas de productos en el XML. "
            "Verifica que sea un DTE de factura electrónica del SII"
        )
    if len(items) > MAX_INVOICE_LINES:
        raise ValueError(
            f"La factura contiene más de {MAX_INVOICE_LINES} productos; "
            "divide el documento para revisarlo"
        )
    return items


def parsear_texto_ocr(text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines()]
    rows: list[tuple[int, str, int, Decimal]] = []
    for index, line in enumerate(lines):
        match = DETAIL_ROW.match(line)
        if not match:
            continue
        provider_code, quantity_text, unit_price_text, _ = match.groups()
        quantity = _parse_quantity(quantity_text)
        unit_price = _parse_amount(unit_price_text)
        rows.append((index, provider_code, quantity, unit_price))

    items: list[dict[str, Any]] = []
    for position, (line_index, code, quantity, cost) in enumerate(rows):
        next_line = rows[position + 1][0] if position + 1 < len(rows) else len(lines)
        name_parts = [
            lines[index]
            for index in range(line_index + 1, next_line)
            if lines[index] and not lines[index].startswith(("|", "TOTAL", "NETO", "IVA"))
        ]
        items.append(
            {
                "sku": code,
                "codigo_proveedor": code,
                "nombre": " ".join(name_parts)[:100],
                "cantidad": quantity,
                "precio_costo": _public_amount(cost),
                "precio_venta": None,
            }
        )
    if len(items) > MAX_INVOICE_LINES:
        raise ValueError(
            f"La factura contiene más de {MAX_INVOICE_LINES} productos; "
            "divide el documento para revisarlo"
        )
    return items


def _extract_pdf_text(content: bytes) -> str:
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if len(document) > MAX_PDF_PAGES_FOR_OCR:
                raise ValueError(
                    f"El PDF tiene {len(document)} páginas; el máximo para procesarlo es "
                    f"{MAX_PDF_PAGES_FOR_OCR}"
                )
            return "\n".join(page.get_text(sort=True) for page in document)
    except pymupdf.FileDataError as exc:
        raise ValueError("No se pudo abrir el PDF de la factura") from exc


def _run_image_ocr(image: Image.Image) -> str:
    if shutil.which("tesseract") is None:
        raise OCREngineUnavailable(
            "Tesseract no está instalado en el backend. Reconstruye el servicio Docker "
            "con `docker compose up -d --build dev`"
        )
    try:
        languages = pytesseract.get_languages(config="")
    except pytesseract.TesseractNotFoundError as exc:
        raise OCREngineUnavailable(
            "No se pudo iniciar Tesseract en el backend"
        ) from exc
    if "spa" not in languages:
        raise OCREngineUnavailable(
            "Falta el idioma español de Tesseract en el backend"
        )
    try:
        return pytesseract.image_to_string(image, lang="spa", config="--psm 6")
    except pytesseract.TesseractError as exc:
        raise OCREngineUnavailable("Tesseract no pudo procesar el documento") from exc


def _parse_image(content: bytes) -> str:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            return _run_image_ocr(image.convert("RGB"))
    except OCREngineUnavailable:
        raise
    except OSError as exc:
        raise ValueError("No se pudo abrir la imagen de la factura") from exc


def _parse_pdf_with_ocr(content: bytes) -> str:
    pages_text: list[str] = []
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if len(document) > MAX_PDF_PAGES_FOR_OCR:
                raise ValueError(
                    f"El PDF tiene {len(document)} páginas; el máximo para procesarlo es "
                    f"{MAX_PDF_PAGES_FOR_OCR}"
                )
            for page in document:
                pixmap = page.get_pixmap(dpi=MIN_OCR_DPI, alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                pages_text.append(_run_image_ocr(image))
    except pymupdf.FileDataError as exc:
        raise ValueError("No se pudo abrir el PDF de la factura") from exc
    return "\n".join(pages_text)


def extraer_items(
    content: bytes,
    extension: str,
) -> tuple[list[dict[str, Any]], str]:
    suffix = extension.lower()
    if suffix == ".xml":
        return parsear_dte_xml(content), "XML_DTE"

    if suffix == ".pdf":
        text = _extract_pdf_text(content)
        items = parsear_texto_ocr(text)
        if items:
            return items, "PDF_TEXTO"
        text = _parse_pdf_with_ocr(content)
    else:
        text = _parse_image(content)

    items = parsear_texto_ocr(text)
    return items, "TESSERACT" if items else "REVISION_MANUAL"
