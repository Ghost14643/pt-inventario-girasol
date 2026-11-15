from __future__ import annotations

import unittest

from backend.logica.factura_ocr import parsear_dte_xml, parsear_texto_ocr


class InvoiceExtractionTests(unittest.TestCase):
    def test_reads_dte_xml_lines_and_unit_costs(self) -> None:
        xml = b"""<?xml version="1.0" encoding="ISO-8859-1"?>
        <DTE xmlns="http://www.sii.cl/SiiDte">
          <Documento>
            <Detalle>
              <NroLinDet>1</NroLinDet>
              <CdgItem><TpoCodigo>INT1</TpoCodigo><VlrCodigo>8653</VlrCodigo></CdgItem>
              <NmbItem>ENTERITO RECTO HALTER</NmbItem>
              <QtyItem>1.00</QtyItem><PrcItem>35892.00</PrcItem><MontoItem>35892</MontoItem>
            </Detalle>
            <Detalle>
              <NroLinDet>2</NroLinDet>
              <CdgItem><TpoCodigo>INT1</TpoCodigo><VlrCodigo>8670</VlrCodigo></CdgItem>
              <NmbItem>JEANS STRAIGHT</NmbItem>
              <QtyItem>4</QtyItem><PrcItem>27687</PrcItem><MontoItem>110748</MontoItem>
            </Detalle>
          </Documento>
        </DTE>"""

        items = parsear_dte_xml(xml)

        self.assertEqual([item["sku"] for item in items], ["8653", "8670"])
        self.assertEqual([item["cantidad"] for item in items], [1, 4])
        self.assertEqual([item["precio_costo"] for item in items], [35892.0, 27687.0])
        self.assertEqual(items[0]["nombre"], "ENTERITO RECTO HALTER")
        self.assertIsNone(items[0]["precio_venta"])

    def test_reads_product_lines_from_tesseract_text(self) -> None:
        text = """\
8653 1,00 35.892 35.892
ENTERITO RECTO HALTER
CALIFORNIA AZULINO
8670 4,00 27.687 110.748
JEANS STRAIGHT 5 BOLSILLO
VINTAGE AZUL
"""

        items = parsear_texto_ocr(text)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["sku"], "8653")
        self.assertEqual(items[0]["nombre"], "ENTERITO RECTO HALTER CALIFORNIA AZULINO")
        self.assertEqual(items[1]["cantidad"], 4)
        self.assertEqual(items[1]["precio_costo"], 27687.0)

    def test_rejects_fractional_inventory_quantities(self) -> None:
        with self.assertRaisesRegex(ValueError, "número entero"):
            parsear_dte_xml(
                b"<DTE><Detalle><NmbItem>Tela</NmbItem><QtyItem>1.5</QtyItem></Detalle></DTE>"
            )

    def test_rejects_xml_with_no_invoice_lines(self) -> None:
        with self.assertRaisesRegex(ValueError, "No se encontraron"):
            parsear_dte_xml(b"<DTE><Documento><Encabezado /></Documento></DTE>")


if __name__ == "__main__":
    unittest.main()
