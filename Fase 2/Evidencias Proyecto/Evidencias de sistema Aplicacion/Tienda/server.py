"""API local para exponer la lógica Python existente a React/Tauri.

Este módulo conserva `backend/` como fuente de verdad y actúa como una capa
adaptadora HTTP/WebSocket. En producción Tauri lo ejecuta como sidecar.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import html
import secrets
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Permite que el binario PyInstaller encuentre backend/ al ejecutarse como sidecar.
ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.logica import arqueo, clientes, configuracion, facturas, inventario, marcas, user, ventas  # noqa: E402

TAURI_DEV_ORIGIN = os.getenv("TAURI_DEV_ORIGIN", "http://localhost:1420")
REACT_DEV_ORIGIN = os.getenv("REACT_DEV_ORIGIN", "http://localhost:5173")

app = FastAPI(title="Tienda Local API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[TAURI_DEV_ORIGIN, REACT_DEV_ORIGIN, "tauri://localhost", "http://tauri.localhost", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
AUTH_SESSIONS: dict[str, dict[str, Any]] = {}


class LoginRequest(BaseModel):
    rut: str
    password: str


class LoginResponse(BaseModel):
    authenticated: bool
    rut: str
    is_admin: bool = False
    token: str


class RoleUpdateRequest(BaseModel):
    id_rol: int = Field(gt=0)


class PasswordUpdateRequest(BaseModel):
    nueva_clave: str = Field(min_length=8, max_length=128)


class EmployeeCreateRequest(BaseModel):
    rut: str = Field(min_length=3, max_length=15)
    nombre: str = Field(min_length=2, max_length=60)
    clave: str = Field(min_length=8, max_length=128)




class DiscountRequest(BaseModel):
    tipo: str = Field(min_length=1, max_length=100)
    valor: float = Field(ge=0, le=1)


class InventoryCreateRequest(BaseModel):
    nombre: str
    tipo: str | None = None
    marca: str | None = None
    precio: int = Field(ge=0)
    stock: int = Field(ge=0)
    barcode: str | None = None


class SaleItem(BaseModel):
    id: int | str | None = None
    nombre: str
    cantidad: int = Field(gt=0)
    precio: int = Field(ge=0)
    merma: int = Field(default=0, ge=0)


class SaleRequest(BaseModel):
    subtotal: int = Field(ge=0)
    productos: list[SaleItem]
    descuento_total: int = Field(default=0, ge=0)
    metodo_pago: Literal["efectivo", "debito", "credito", "credito_girasol", "transferencia", "otro"] = "efectivo"
    rut_empleado: str
    cliente_rut: str | None = None
    registrar_arqueo: bool = False


class CashOpenRequest(BaseModel):
    fecha: str


class ArqueoRequest(BaseModel):
    fecha: str
    efectivo_contado: float = Field(ge=0)
    gastos_turno: float = Field(default=0, ge=0)


class BrandCreateRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)


class ClientCreateRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    rut: str = Field(min_length=3, max_length=15)
    celular: str
    direccion: str | None = Field(default=None, max_length=50)
    actividad_economica: str | None = Field(default=None, max_length=100)
    descripcion: str | None = Field(default=None, max_length=250)
    fono: str | None = None


class PrintRequest(BaseModel):
    payload: dict[str, Any]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(data: LoginRequest) -> LoginResponse:
    if not data.rut.strip() or not data.password:
        raise HTTPException(status_code=422, detail="Usuario y clave son obligatorios")
    try:
        authenticated = user.verificar_contraseña(data.rut.strip(), data.password)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not authenticated:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    is_admin = user.verificacion_admin(data.rut)
    token = secrets.token_urlsafe(32)
    AUTH_SESSIONS[token] = {"rut": data.rut.strip(), "is_admin": is_admin}
    return LoginResponse(authenticated=True, rut=data.rut.strip(), is_admin=is_admin, token=token)


@app.post("/auth/logout")
def logout(authorization: Annotated[str | None, Header()] = None) -> dict[str, bool]:
    if authorization and authorization.startswith("Bearer "):
        AUTH_SESSIONS.pop(authorization[7:], None)
    return {"ok": True}


def require_admin(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sesión administrativa requerida")
    session = AUTH_SESSIONS.get(authorization[7:])
    if not session:
        raise HTTPException(status_code=401, detail="La sesión expiró; inicia sesión nuevamente")
    if not session["is_admin"]:
        raise HTTPException(status_code=403, detail="Acceso exclusivo para administradores")
    return session


@app.get("/admin/summary")
def admin_summary(_: dict[str, Any] = Depends(require_admin)) -> dict[str, int]:
    return configuracion.resumen()


@app.get("/admin/users")
def admin_users(_: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    return configuracion.listar_usuarios()


@app.get("/admin/roles")
def admin_roles(_: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    return configuracion.listar_roles()


@app.post("/admin/users", status_code=201)
def admin_create_employee(data: EmployeeCreateRequest, _: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    try:
        return configuracion.crear_empleado(**data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/admin/users/{rut}")
def admin_delete_employee(rut: str, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    if str(admin["rut"]).split("-", 1)[0] == str(rut).split("-", 1)[0]:
        raise HTTPException(status_code=409, detail="No puedes eliminar tu propia cuenta")
    try:
        result = configuracion.eliminar_empleado(rut)
        for token, active in list(AUTH_SESSIONS.items()):
            if str(active.get("rut", "")).split("-", 1)[0] == str(rut).split("-", 1)[0]:
                AUTH_SESSIONS.pop(token, None)
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.patch("/admin/users/{rut}/role")
def admin_update_role(rut: str, data: RoleUpdateRequest, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    if str(admin["rut"]) == str(rut):
        raise HTTPException(status_code=409, detail="No puedes modificar tu propio rol durante la sesión")
    try:
        return configuracion.actualizar_rol(rut, data.id_rol)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.patch("/admin/users/{rut}/password")
def admin_update_password(rut: str, data: PasswordUpdateRequest, _: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    try:
        return configuracion.cambiar_clave(rut, data.nueva_clave)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/admin/discounts")
def admin_discounts(_: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    return configuracion.listar_descuentos()


@app.post("/admin/discounts", status_code=201)
def admin_create_discount(data: DiscountRequest, _: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return configuracion.guardar_descuento(data.tipo, data.valor)


@app.put("/admin/discounts/{discount_id}")
def admin_update_discount(discount_id: int, data: DiscountRequest, _: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    try:
        return configuracion.guardar_descuento(data.tipo, data.valor, discount_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/inventory")
def list_inventory(search: str = "", marca: str = "") -> list[dict[str, Any]]:
    return inventario.consultar_inventario_ropa(search, marca)


@app.get("/brands")
def list_brands() -> list[dict[str, Any]]:
    return marcas.obtener_marcas()


@app.post("/brands", status_code=201)
def create_brand(data: BrandCreateRequest) -> dict[str, Any]:
    try:
        return marcas.agregar_nueva_marca(data.nombre)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/inventory/summary")
def get_inventory_summary(stock_bajo_maximo: int = 5) -> dict[str, int]:
    if stock_bajo_maximo < 0:
        raise HTTPException(status_code=422, detail="El umbral no puede ser negativo")
    return inventario.obtener_resumen_inventario(stock_bajo_maximo)


@app.get("/inventory/categories")
def get_inventory_categories() -> list[dict[str, Any]]:
    return inventario.obtener_categorias()


@app.get("/inventory/barcode/{barcode}")
def get_product_by_barcode(barcode: str) -> dict[str, Any]:
    product = inventario.obtener_producto_por_codigo(barcode)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@app.post("/inventory")
def create_inventory_item(data: InventoryCreateRequest) -> dict[str, Any]:
    """Ejemplo de punto de entrada para altas de inventario.

    Si `backend.logica.inventario` gana una función `crear_prenda`, esta ruta la
    usa sin cambiar React. Mientras tanto devuelve 501 para evitar escribir SQL
    duplicado fuera de la capa de negocio existente.
    """
    crear_prenda = getattr(inventario, "crear_prenda", None)
    if crear_prenda is None:
        raise HTTPException(status_code=501, detail="Implementar crear_prenda en backend.logica.inventario")
    try:
        return crear_prenda(**data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/clients")
def list_clients(search: str = "") -> list[dict[str, Any]]:
    try:
        return clientes.listar_clientas(search)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/clients/summary")
def get_clients_summary() -> dict[str, int]:
    try:
        return clientes.resumen_clientas()
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/clients", status_code=201)
def create_client(data: ClientCreateRequest) -> dict[str, Any]:
    try:
        return clientes.crear_clienta(**data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/clients/credit-search")
def search_credit_clients(search: str = "") -> list[dict[str, Any]]:
    try:
        return clientes.buscar_clientas_credito(search)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/clients/{rut}/credit")
def get_client_credit(rut: str) -> list[dict[str, Any]]:
    try:
        clientes.obtener_clienta(rut)
        return clientes.obtener_hoja_credito(rut)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, ConnectionError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/sales")
def create_sale(data: SaleRequest) -> dict[str, Any]:
    try:
        sale_result = ventas.registrar_venta(
            subtotal=data.subtotal,
            productos=[item.model_dump() for item in data.productos],
            descuento_total=data.descuento_total,
            metodo_pago=data.metodo_pago,
            rut_empleado=data.rut_empleado,
            cliente_rut=data.cliente_rut,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True, "sale": sale_result}


@app.get("/cash-register/status/{fecha}")
def get_cash_register_status(fecha: str) -> dict[str, Any]:
    return arqueo.estado_caja(fecha)


@app.post("/cash-register/open", status_code=201)
def open_cash_register(data: CashOpenRequest) -> dict[str, Any]:
    try:
        return arqueo.abrir_caja(data.fecha)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/cash-register/{fecha}")
def get_cash_register(fecha: str) -> dict[str, Any]:
    try:
        result = arqueo.consultar_arqueo_fecha(fecha)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result


@app.post("/cash-register/close")
def close_cash_register(data: ArqueoRequest) -> dict[str, Any]:
    try:
        return arqueo.cerrar_caja(**data.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/cash-register", include_in_schema=False)
def create_cash_register_legacy(data: ArqueoRequest) -> dict[str, Any]:
    return close_cash_register(data)


def _verify_invoice_token(token: str | None) -> None:
    expected = os.getenv("FACTURA_UPLOAD_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="Configura FACTURA_UPLOAD_TOKEN para habilitar la carga")
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Token de carga inválido")


@app.get("/facturas/subir", response_class=HTMLResponse)
def invoice_upload_page(token: str | None = None) -> str:
    _verify_invoice_token(token)
    safe_token = html.escape(token or "", quote=True)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Subir factura</title><style>*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;padding:20px;background:#191a15;color:#292923;font:15px system-ui}}.card{{width:min(100%,480px);padding:28px;border-radius:22px;background:#fff;box-shadow:0 24px 70px #0007}}h1{{margin:0 0 7px;font:700 30px Georgia,serif}}p{{margin:0 0 24px;color:#74736b}}.drop{{display:block;padding:28px 18px;border:2px dashed #d7c264;border-radius:16px;text-align:center;background:#fffaf0}}.drop b,.drop span{{display:block}}.drop span{{margin-top:7px;color:#888;font-size:12px}}input[type=file]{{width:100%;margin-top:16px}}button{{width:100%;margin-top:20px;padding:14px;border:0;border-radius:12px;background:#f4c62f;font-weight:800;font-size:15px}}button:disabled{{opacity:.55}}.msg{{margin:15px 0 0;text-align:center;font-size:13px}}.ok{{color:#197a50}}.error{{color:#b6403a}}</style></head><body><main class="card"><h1>Subir factura</h1><p>Toma una foto o selecciona una imagen/PDF.</p><form id="form"><input type="hidden" name="token" value="{safe_token}"><label class="drop"><b>Seleccionar archivo</b><span>Imagen o PDF · máximo 15 MB</span><input name="factura" type="file" accept="image/*,application/pdf,.pdf" required></label><button>Guardar factura</button><p id="msg" class="msg"></p></form></main><script>const f=document.querySelector('#form'),b=f.querySelector('button'),m=document.querySelector('#msg');f.onsubmit=async e=>{{e.preventDefault();b.disabled=true;b.textContent='Subiendo…';m.textContent='';try{{const r=await fetch('/facturas/upload',{{method:'POST',body:new FormData(f)}}),d=await r.json();if(!r.ok)throw new Error(d.detail||'No fue posible subir la factura');m.className='msg ok';m.textContent='Factura guardada correctamente';f.reset()}}catch(e){{m.className='msg error';m.textContent=e.message}}finally{{b.disabled=false;b.textContent='Guardar factura'}}}}</script></body></html>"""


async def _receive_invoice(factura: UploadFile, token: str | None) -> dict[str, Any]:
    _verify_invoice_token(token)
    data = await factura.read(facturas.MAX_FILE_SIZE + 1)
    filename = factura.filename or "factura"
    await factura.close()
    try:
        return facturas.guardar_factura(data, filename)
    except ValueError as exc:
        raise HTTPException(status_code=413 if "límite" in str(exc) else 415, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/facturas/upload", status_code=201)
async def upload_invoice(factura: UploadFile = File(...), token: str | None = Form(None)) -> dict[str, Any]:
    return await _receive_invoice(factura, token)


@app.post("/subir_factura", status_code=201, include_in_schema=False)
async def upload_invoice_legacy(factura: UploadFile = File(...), token: str | None = Form(None)) -> dict[str, Any]:
    return await _receive_invoice(factura, token)


@app.post("/peripherals/print")
def print_receipt(data: PrintRequest) -> dict[str, bool]:
    printer = importlib.import_module("backend.printer_test")
    printer.imprimir_boleta_abono(**data.payload)
    return {"ok": True}


@app.websocket("/ws/scanner")
async def scanner_events(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            # Adaptador inicial: el frontend puede enviar códigos capturados por un lector HID.
            # El lector HID envía el código al adaptador WebSocket.
            barcode = await websocket.receive_text()
            await websocket.send_json({"type": "barcode", "barcode": barcode})
    except WebSocketDisconnect:
        return


async def wait_until_cancelled() -> None:
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.getenv("TIENDA_API_HOST", "127.0.0.1"), port=int(os.getenv("TIENDA_API_PORT", "8765")))
