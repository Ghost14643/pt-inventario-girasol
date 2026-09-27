# Resumen de integración frontend/backend

Fecha: 2026-08-07. API: `http://127.0.0.1:8765`.

## Clientas: integración completada

Toda la lógica nueva está en `backend/logica/clientes.py`; `server.py` solo adapta HTTP.

- `GET /clients`: listado/búsqueda real. Verificado HTTP 200.
- `GET /clients/summary`: métricas reales. Verificado: 43 clientas, 1 crédito activo.
- `POST /clients`: alta persistente y validación de duplicados. Verificado sin insertar datos: HTTP 409 para `123-4`.
- `GET /clients/{rut}/credit`: hoja de crédito real. Verificado para `123-4`: HTTP 200.
- Estados reales: 1 Pendiente, 2 Atrasado, 3 Completado.
- El frontend no crea registros ficticios cuando falla el API.

## Ausencias, incompatibilidades y funciones no utilizadas

### Hoja de crédito

- Los registros actuales de `123-4` tienen `cuotas_por_pagar = 33529` y `precio_cuota = NULL`. La implementación histórica guardaba el total en `cuotas_por_pagar`; estos datos requieren corrección/migración.
- Al ser nulo `precio_cuota`, el saldo valorizado resulta $0 aunque haya crédito activo.
- No hay flujo React/API para crear, editar, pagar o eliminar cuotas; la solicitud actual solo contempla consulta.
- La capa gráfica Python heredada fue retirada; React consume exclusivamente el API local.

### Inventario e ingreso

- Inventario fue integrado en modo lectura con SQLite (`/data/girasol.db`, con alternativa local `data/girasol.db`).
- `GET /inventory`, `GET /inventory/summary`, `GET /inventory/categories` y `GET /inventory/barcode/{barcode}` están implementados.
- Métricas verificadas solo con `SELECT`: 1.548 prendas, 2.341 unidades, 3 categorías y 1.519 prendas con stock de hasta 5 unidades.
- La base disponible contiene `familiaRopa` pero no `seccionRopa` ni una relación entre `prenda` y `familiaRopa`. Por ello el contador muestra 3 categorías globales, mientras cada prenda queda como `Sin categoría` hasta incorporar una clave de relación.
- `POST /inventory` ya cuenta con `crear_prenda` en `backend/logica/inventario.py` y se utiliza al confirmar el ingreso de mercadería. No se ejecutó ninguna inserción de prueba.
- `GET /brands` y `POST /brands` permiten listar y crear marcas; no se ejecutó ninguna creación de prueba.
- El filtro de Inventario usa la marca seleccionada mediante `LIKE`, necesario porque las prendas históricas guardan variantes como `TEJIDO FBO` mientras `marcas` conserva `FBO`.

- Se retiró `registrar_prenda`, que apuntaba a la tabla inexistente `prendas`; el API utiliza `crear_prenda` sobre `prenda`.

### Arqueo

- `GET /cash-register/{fecha}` devuelve HTTP 500: SQLite no contiene `arqueo_diario`.
- MySQL contiene `arqueo_caja`, pero sus columnas no coinciden con la lógica actual.
- Falta endpoint para `cerrar_caja` y un resumen backend por método de pago.

### Ventas y otros módulos

- `POST /sales` existe; no se probó escribiendo para no alterar ventas reales.
- Ventas aún no selecciona clienta ni genera una hoja al vender a crédito.
- El WebSocket del lector es eco; no consume directamente la cola del lector físico.
- Edición y eliminación de clientas no fueron solicitadas y no tienen endpoints nuevos.

## Verificación

- `python3 -m py_compile server.py backend/logica/clientes.py`: correcto.
- `frontend/npm run build`: correcto.
- API actualizado y activo en `127.0.0.1:8765` con el entorno `.venv`.
- Las advertencias de Tailwind/Lightning CSS son preexistentes y no bloquean el build.


## Carga web segura de facturas

- `GET /facturas/subir?token=...` ofrece un formulario responsive para navegador móvil.
- `POST /facturas/upload` recibe multipart (`factura`, `token`); `/subir_factura` es alias compatible.
- Admite PDF, JPG, PNG, WEBP, GIF y HEIC por firma binaria, hasta 15 MB.
- Guarda en `FACTURAS_UPLOAD_DIR`, `/data/facturas` o `data/facturas`, y registra `factura(imagen, fecha_subida)` en MySQL. Si MySQL falla, elimina el archivo.
- Requiere `FACTURA_UPLOAD_TOKEN`. Para acceso móvil en una red confiable, iniciar además con `TIENDA_API_HOST=0.0.0.0` y abrir `http://IP_DEL_EQUIPO:8765/facturas/subir?token=TOKEN`.
- El servidor conserva `127.0.0.1` como host predeterminado para no exponer una ruta de escritura accidentalmente.


## Arranque del API en el ejecutable Tauri

- El instalador no necesita scripts Flask `start/stop/restart`: Tauri inicia `tienda-api` como sidecar al abrir la aplicación y lo termina al salir.
- `main.rs` conserva el proceso hijo, captura stdout/stderr y prepara una copia escribible de `girasol.db` en el directorio de datos de la aplicación.
- `tauri.conf.json` incluye la base semilla como recurso. La copia del usuario no se sobrescribe en actualizaciones posteriores.
- `scripts/build_sidecar.sh` construye y copia el binario con el sufijo de plataforma exigido por Tauri.
- Construcción completa: `npm run build:desktop`. No ejecutar solamente `cargo tauri build`, porque podría empaquetar un sidecar antiguo.


## Variables MariaDB en desarrollo y ejecutable

- Python carga automáticamente `backend/.env` y `.env` en desarrollo, sin sobrescribir variables ya exportadas.
- Puede indicarse otra ubicación mediante `DB_ENV_FILE`.
- Tauri apunta a `database.env` dentro del directorio de datos persistente de la aplicación. Ese archivo debe crearse externamente y no se incrusta en el instalador.
- Variables admitidas: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_DATABASE` y `DB_CONNECT_TIMEOUT`.
- Después de cambiar el archivo hay que reiniciar el API o la aplicación; `load_dotenv` se ejecuta al iniciar el proceso.


## Auditoría de `registrar_venta` y prueba controlada

- Se eliminó una definición antigua y rota de `registrar_venta` que estaba duplicada y era sobrescrita silenciosamente por Python.
- La implementación activa valida empleado autenticado, método de pago, identificadores, cantidades, stock, subtotal canónico y descuento.
- Los productos repetidos se consolidan antes de validar y descontar stock.
- El frontend ahora usa el RUT de la sesión autenticada; antes enviaba `rut: ''`, provocando HTTP 409 (`La venta requiere un empleado autenticado` / `El empleado no existe`).
- Prueba autorizada ejecutada una sola vez con prenda TEST, ID 2082, barcode 111, cantidad 1, precio 999999 y empleado 21300379. Resultado: HTTP 200, venta MariaDB ID 4, detalle ID 2.
- Al pasar de stock 1 a 0, el trigger SQLite `mover_y_borrar_stock0` eliminó la fila de `prenda` y la registró en `prenda0stock`; no fue una pérdida accidental.
- Limitación arquitectónica: SQLite y MariaDB no ofrecen una transacción distribuida atómica. La función coordina rollback antes de los commits, pero un fallo excepcional entre ambos commits podría requerir reconciliación manual.
- Se retiraron `crear_boleta` y `calcular_precio_total` porque no tenían consumidores y dependían de un esquema obsoleto.


## Acceso y validación de credenciales

- El login valida localmente usuario y clave vacíos con mensajes específicos.
- Credenciales incorrectas reciben HTTP 401 sin revelar si falló el usuario o la clave.
- Una conexión MariaDB no disponible recibe HTTP 503 y se presenta como problema de servicio.
- Incluye mostrar/ocultar clave, estado de carga, campos inválidos y persistencia de la sesión autenticada.


## Configuración administrativa

- El acceso «Informes» fue reemplazado por «Configuración» y solo aparece para sesiones administradoras.
- La API entrega un token de sesión al iniciar sesión y protege todas las rutas `/admin/*`; ocultar el botón no es el único control de acceso.
- Permite consultar usuarios y roles, cambiar el rol de otras cuentas y restablecer claves de al menos 8 caracteres. Las claves existentes y sus hashes nunca se exponen al frontend.
- Evita que el administrador conectado modifique su propio rol para reducir el riesgo de perder acceso accidentalmente.
- Permite consultar, crear y editar descuentos de SQLite. Los porcentajes se validan entre 0% y 100%.
- Incluye resumen de usuarios, roles y descuentos, estado de seguridad, diseño responsive y modo oscuro.
- No se hicieron inserciones ni actualizaciones de prueba en usuarios, roles, claves o descuentos.


## Sesión diaria y arqueo de caja

- El cierre de sesión solicita confirmación y revoca el token en el servidor antes de limpiar la sesión local.
- Después del login, el frontend consulta `GET /cash-register/status/{fecha}`. Si no existe registro diario, ofrece abrir caja; solo `POST /cash-register/open` crea la constancia.
- La apertura guarda fecha y hora. Las columnas nuevas de cierre quedan `NULL`; por compatibilidad, las columnas financieras antiguas que eran `NOT NULL` se inicializan en cero.
- `arqueo_diario` se migra de forma aditiva: no se reconstruye ni elimina la tabla. Se añadieron apertura, cierre, cantidad de ventas, débito, crédito, otros, gastos de turno, efectivo esperado/contado y diferencia.
- El resumen consulta `ventas` en MariaDB desde la hora de apertura y agrupa efectivo, débito, crédito, transferencia y otros. Al cerrar, congela esos totales en SQLite.
- No se abrió ninguna caja ni se insertaron registros de prueba. La migración se aplicó con cero filas y se respaldó previamente en `/tmp/girasol-before-arqueo-20260809.db`.

- `consultar_arqueo_fecha` ya no retorna `None` cuando falta el día: devuelve `existe: false`, un `aviso` legible y `puede_abrir: true`. La consulta no inserta filas.
- La vista de Arqueo interpreta esa respuesta HTTP 200, muestra el aviso y ofrece abrir caja tanto en el aviso superior como en el panel lateral.


## Crédito Girasol en ventas

- Ventas permite buscar una clienta registrada por nombre o RUT y seleccionarla antes de usar `credito_girasol`.
- `GET /clients/credit-search` entrega tope, deuda activa y disponible. Para hojas históricas con `precio_cuota=NULL`, usa `cuotas_por_pagar` como saldo legado.
- `POST /sales` vuelve a calcular y bloquear el saldo de la clienta dentro de la transacción; rechaza la venta si supera `tope_credito`.
- Una venta aprobada crea una hoja de crédito de una cuota, vencimiento a 30 días, pie cero y referencia al ID de venta.
- Arqueo distingue Crédito Girasol del crédito bancario.
- Actualmente las 43 clientas tienen `tope_credito=NULL`; aparecerán con $0 disponible hasta que se configuren límites reales. No se modificaron topes ni se registraron ventas de prueba.


## Altas y bajas de empleados

- Configuración permite crear cuentas con RUT, nombre y clave inicial; el servidor asigna siempre el rol real `empleado`.
- Solo cuentas cuyo rol actual sea `empleado` pueden eliminarse. Admin y developer están protegidos en frontend y backend.
- Los roles privilegiados tampoco pueden degradarse para evitar convertirlos en empleados y eliminarlos después.
- La eliminación revoca cualquier sesión activa del empleado. Si existen relaciones que impiden borrarlo, la API conserva la cuenta y devuelve un conflicto claro.
- No se crearon ni eliminaron usuarios de prueba.
