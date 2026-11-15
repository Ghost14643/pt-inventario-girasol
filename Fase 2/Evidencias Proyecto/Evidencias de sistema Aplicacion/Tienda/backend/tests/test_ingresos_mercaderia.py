from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import patch

from mysql.connector import IntegrityError

from backend.repositorios.ingresos_mercaderia import aplicar_factura_aprobada


class FakeConnection:
    def __init__(self) -> None:
        self.applied: set[str] = set()
        self.products = {
            "CAM-001": {
                "id_variante": 7,
                "id_producto": 3,
                "nombre": "Camiseta básica",
                "activo": True,
            }
        }
        self.stock = {7: 10}
        self.prices = {3: {"precio_venta": Decimal("100"), "precio_costo": None}}
        self.movements: list[tuple[int, int, str, int]] = []
        self.pending_invoices: set[str] = set()
        self.pending_stock: dict[int, int] = {}
        self.pending_prices: dict[int, tuple[Decimal, Decimal | None]] = {}
        self.pending_movements: list[tuple[int, int, str, int]] = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, **kwargs: object) -> FakeCursor:
        if kwargs.get("dictionary") is not True:
            raise AssertionError("Expected dictionary cursor")
        return FakeCursor(self)

    def commit(self) -> None:
        self.applied.update(self.pending_invoices)
        for id_variante, cantidad in self.pending_stock.items():
            self.stock[id_variante] += cantidad
        for id_producto, (precio_venta, precio_costo) in self.pending_prices.items():
            self.prices[id_producto]["precio_venta"] = precio_venta
            if precio_costo is not None:
                self.prices[id_producto]["precio_costo"] = precio_costo
        self.movements.extend(self.pending_movements)
        self._clear_pending()
        self.commits += 1

    def rollback(self) -> None:
        self._clear_pending()
        self.rollbacks += 1

    def start_transaction(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _clear_pending(self) -> None:
        self.pending_invoices.clear()
        self.pending_stock.clear()
        self.pending_prices.clear()
        self.pending_movements.clear()


class FakeCursor:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.row: dict[str, object] | None = None

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        sql = " ".join(statement.split())
        self.row = None
        if sql.startswith("INSERT INTO ingreso_factura_aprobada"):
            factura_id = str(params[0])
            if factura_id in self.connection.applied:
                raise IntegrityError("Duplicate invoice")
            self.connection.pending_invoices.add(factura_id)
        elif sql.startswith("SELECT factura_id FROM ingreso_factura_aprobada"):
            factura_id = str(params[0])
            if factura_id in self.connection.applied:
                self.row = {"factura_id": factura_id}
        elif sql.startswith("SELECT vp.id_variante, p.id_producto, p.nombre"):
            product = self.connection.products.get(str(params[0]))
            self.row = product if product and product["activo"] else None
        elif sql.startswith("UPDATE variante_producto"):
            cantidad, id_variante = int(params[0]), int(params[1])
            self.connection.pending_stock[id_variante] = (
                self.connection.pending_stock.get(id_variante, 0) + cantidad
            )
        elif sql.startswith("INSERT INTO movimiento_stock"):
            id_variante, cantidad, referencia, id_usuario = params
            self.connection.pending_movements.append(
                (int(id_variante), int(cantidad), str(referencia), int(id_usuario))
            )
        elif sql.startswith("UPDATE producto"):
            precio_venta, precio_costo, id_producto = params
            self.connection.pending_prices[int(id_producto)] = (
                precio_venta,
                precio_costo,
            )

    def fetchone(self) -> dict[str, object] | None:
        return self.row

    def close(self) -> None:
        pass


class ApplyApprovedInvoiceTests(unittest.TestCase):
    def test_combines_duplicate_skus_and_records_stock_movement(self) -> None:
        connection = FakeConnection()
        with patch(
            "backend.repositorios.ingresos_mercaderia.conectar_mariadb",
            return_value=connection,
        ):
            result = aplicar_factura_aprobada(
                "a" * 24,
                [
                    {"sku": "CAM-001", "cantidad": 2, "precio_venta": 1200, "precio_costo": 600},
                    {"sku": "CAM-001", "cantidad": 3, "precio_venta": 1200, "precio_costo": 600},
                ],
                5,
            )

        self.assertEqual(connection.stock[7], 15)
        self.assertEqual(connection.movements, [(7, 5, f"Factura {'a' * 24}", 5)])
        self.assertEqual(connection.prices[3]["precio_venta"], Decimal("1200"))
        self.assertEqual(connection.prices[3]["precio_costo"], Decimal("600"))
        self.assertEqual(result["items"][0]["cantidad"], 5)
        self.assertEqual(connection.commits, 2)

    def test_repeated_approval_does_not_add_stock_twice(self) -> None:
        connection = FakeConnection()
        with patch(
            "backend.repositorios.ingresos_mercaderia.conectar_mariadb",
            return_value=connection,
        ):
            aplicar_factura_aprobada(
                "b" * 24,
                [{"sku": "CAM-001", "cantidad": 4, "precio_venta": 1200}],
                5,
            )
            result = aplicar_factura_aprobada(
                "b" * 24,
                [{"sku": "CAM-001", "cantidad": 4, "precio_venta": 1200}],
                5,
            )

        self.assertEqual(connection.stock[7], 14)
        self.assertEqual(len(connection.movements), 1)
        self.assertTrue(result["ya_aplicada"])

    def test_unknown_sku_rolls_back_the_entire_invoice(self) -> None:
        connection = FakeConnection()
        with patch(
            "backend.repositorios.ingresos_mercaderia.conectar_mariadb",
            return_value=connection,
        ):
            with self.assertRaisesRegex(LookupError, "NO-EXISTE"):
                aplicar_factura_aprobada(
                    "c" * 24,
                    [{"sku": "NO-EXISTE", "cantidad": 4, "precio_venta": 1200}],
                    5,
                )

        self.assertEqual(connection.stock[7], 10)
        self.assertFalse(connection.applied)
        self.assertEqual(connection.rollbacks, 1)

    def test_inactive_product_cannot_receive_invoice_stock(self) -> None:
        connection = FakeConnection()
        connection.products["CAM-001"]["activo"] = False
        with patch(
            "backend.repositorios.ingresos_mercaderia.conectar_mariadb",
            return_value=connection,
        ):
            with self.assertRaisesRegex(LookupError, "producto activo"):
                aplicar_factura_aprobada(
                    "d" * 24,
                    [{"sku": "CAM-001", "cantidad": 4, "precio_venta": 1200}],
                    5,
                )

        self.assertEqual(connection.stock[7], 10)
        self.assertFalse(connection.applied)
        self.assertEqual(connection.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()
