# Limpieza del backend y dependencias

## Alcance

La interfaz de escritorio activa es React dentro de Tauri. Se eliminó la implementación gráfica Python anterior, sus módulos `ui_*.py`, lanzadores y auxiliares exclusivos. El API local continúa en `server.py` y la lógica de negocio en `backend/logica/`.

También se retiraron herramientas experimentales de cámara/códigos de barra que no eran invocadas por el API. El lector vigente funciona como dispositivo HID: el frontend obtiene el texto y puede enviarlo a `/ws/scanner`.

## Funciones backend activas

### Conexiones (`backend/db/conexion.py`)

- `conectar_db()`: abre SQLite, activa claves foráneas y evita crear accidentalmente una base vacía.
- `conectar_mydb()`: abre MariaDB usando exclusivamente la configuración del entorno.

### Autenticación y administración

- `user.hashear_contraseña()`, `verificar_contraseña()` y `verificacion_admin()`: autenticación y autorización.
- `configuracion.listar_usuarios()`, `listar_roles()`, `crear_empleado()`, `eliminar_empleado()`, `actualizar_rol()` y `cambiar_clave()`: mantenimiento de usuarios.
- `configuracion.listar_descuentos()`, `guardar_descuento()` y `resumen()`: descuentos y métricas administrativas.

### Inventario y marcas

- `inventario.consultar_inventario_ropa()`, `obtener_resumen_inventario()`, `obtener_categorias()` y `obtener_producto_por_codigo()`: consultas usadas por React.
- `inventario.crear_prenda()`: alta transaccional de productos.
- `marcas.obtener_marcas()` y `agregar_nueva_marca()`: catálogo de marcas.

### Ventas y caja

- `ventas.registrar_venta()`: valida precios y stock canónicos, registra cabecera/detalle en MariaDB y descuenta inventario SQLite.
- `arqueo.asegurar_esquema()`, `estado_caja()`, `abrir_caja()`, `consultar_arqueo_fecha()` y `cerrar_caja()`: ciclo completo del arqueo diario.

### Clientas y documentos

- `clientes.listar_clientas()`, `buscar_clientas_credito()`, `crear_clienta()`, `obtener_clienta()`, `obtener_hoja_credito()` y `resumen_clientas()`: clientas y crédito.
- `facturas.guardar_factura()`: valida, almacena y registra facturas subidas.

## Impresora térmica preservada

Se mantienen:

- `backend/printer_test.py` y `imprimir_boleta_abono()`.
- El endpoint `POST /peripherals/print`.
- La dependencia `python-escpos`.

La inicialización USB se realiza sólo cuando se solicita una impresión. Se eliminó la impresión de demostración automática al importar el módulo, evitando accesos accidentales al dispositivo durante el arranque o las pruebas.

## Elementos retirados

- Todos los módulos Python de `frontend/`, incluidos los archivos `ui_*.py`.
- El lanzador raíz `app.py` y el script destructivo `test_def.py`.
- Funciones backend sin consumidores: `obtener_rut_usuario`, `registrar_contraseña`, `Sesion`, `busqueda_descuento`, `verificacion_encargado_local`, `crear_boleta`, `calcular_precio_total` y `registrar_prenda`.
- Scripts experimentales de escaneo, generación de códigos y migración que no formaban parte del API.
- PyQt5, Matplotlib, OpenCV, NumPy, pyzbar, python-barcode y paquetes auxiliares; también los conectores MySQL redundantes `mysql` y `mysqlclient`.

## Dependencias Python vigentes

`mysql-connector-python`, `fastapi`, `uvicorn`, `pydantic`, `pyinstaller`, `python-escpos`, `python-multipart` y `python-dotenv`.
