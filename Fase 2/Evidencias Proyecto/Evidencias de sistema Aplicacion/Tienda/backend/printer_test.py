from datetime import datetime


def imprimir_boleta_abono(
    cliente,
    direccion,
    ciudad,
    telefono,
    monto_total,
    monto_abono,
    saldo_anterior,
    saldo_actual,
    num_cuota,
    total_cuotas,
    hoja_credito,
    num_boleta
):
    from escpos.printer import Usb
    p = Usb(0x0483, 0x5743)
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    p.set(align="center", bold=True, width=2, height=2)
    p.text("GIRASOL\n")
    p.set(align="center", bold=False, width=1, height=1)
    p.text("Tienda de Ropa\n")
    p.text("================================\n")

    p.set(align="left")
    p.text(f"Dirección : {direccion}\n")
    p.text(f"Ciudad    : {ciudad}\n")
    p.text(f"Teléfono  : {telefono}\n")
    p.text("--------------------------------\n")

    p.text(f"Fecha     : {fecha}\n")
    p.text(f"N° Boleta : {num_boleta}\n")
    p.text(f"Hoja Créd.: {hoja_credito}\n")
    p.text("--------------------------------\n")

    p.set(bold=True)
    p.text("DATOS DEL CLIENTE\n")
    p.set(bold=False)
    p.text(f"Nombre    : {cliente}\n")
    p.text("--------------------------------\n")

    p.set(bold=True)
    p.text("DETALLE DEL ABONO\n")
    p.set(bold=False)
    p.text(f"Monto total crédito : ${monto_total:,}\n")
    p.text(f"Saldo anterior      : ${saldo_anterior:,}\n")
    p.text(f"Abono realizado     : ${monto_abono:,}\n")
    p.text(f"Saldo actual        : ${saldo_actual:,}\n")
    p.text(f"Cuota               : {num_cuota} de {total_cuotas}\n")
    p.text("--------------------------------\n")

    p.set(align="center", bold=True)
    p.text("COMPROBANTE DE PAGO\n")
    p.text("--------------------------------\n")

    p.set(align="center", bold=False)
    p.text("Este documento acredita\n")
    p.text("el pago de un abono\n")
    p.text("sobre crédito vigente.\n\n")

    p.set(bold=True)
    p.text("¡GRACIAS POR SU PREFERENCIA!\n")
    p.set(bold=False)
    p.text("Girasol 🌻\n")

    p.text("\n\n")
    p.cut()
