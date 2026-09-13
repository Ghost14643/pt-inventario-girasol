# Migración Tauri + React + Python

## Arquitectura propuesta

La aplicación se divide en tres capas: Tauri como shell nativo, React como interfaz y `server.py` como API local FastAPI. La carpeta `backend/` permanece como capa de negocio y acceso a datos; la API solo adapta sus funciones a contratos HTTP/WebSocket.

```text
Tauri window -> React/Vite -> HTTP/WebSocket localhost:8765 -> FastAPI server.py -> backend/logica + backend/db
```

## Paso 1: API Python

`server.py` expone endpoints REST para login, inventario, ventas, arqueo y periféricos. CORS habilita los orígenes de desarrollo de Vite/Tauri y los orígenes usados por la webview empaquetada.

Endpoints iniciales:

- `POST /auth/login`: valida credenciales con `backend.logica.user`.
- `GET /inventory?search=`: consulta productos con `backend.logica.inventario`.
- `GET /inventory/barcode/{barcode}`: busca producto por código de barras.
- `POST /inventory`: punto de extensión para altas de inventario sin duplicar SQL fuera de la capa de negocio.
- `POST /sales`: registra ventas con `backend.logica.ventas`.
- `GET|POST /cash-register`: consulta o registra arqueos con `backend.logica.arqueo`.
- `POST /peripherals/print`: carga el módulo de impresión bajo demanda.
- `WS /ws/scanner`: canal inicial para eventos de scanner.

Ejecución local:

```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8765 --reload
```

## Paso 2: React

La interfaz activa vive en `frontend/src` y está implementada completamente con React.

```text
frontend/
├── index.html
├── package.json
└── src
    ├── components/
    ├── hooks/
    ├── pages/
    │   ├── LoginPage.jsx
    │   ├── VentasPage.jsx
    │   └── InventarioPage.jsx
    ├── services/
    │   └── api.js
    └── styles.css
```

`src/services/api.js` centraliza el `baseURL` (`VITE_API_BASE_URL` o `http://127.0.0.1:8765`) y mantiene aislados los componentes de cambios futuros en FastAPI.

## Paso 3: Tauri y sidecar

`src-tauri/tauri.conf.json` define la ventana principal, comandos de desarrollo/build de Vite y el binario externo `binaries/tienda-api`. `src-tauri/src/main.rs` inicializa `tauri-plugin-shell` y levanta el sidecar al iniciar la app.

Construcción del sidecar Python:

```bash
pip install -r requirements.txt
pip install pyinstaller fastapi uvicorn pydantic
./scripts/build_sidecar.sh
```

Luego se puede empaquetar la aplicación Tauri:

```bash
cd frontend && npm install
cd ../src-tauri && cargo tauri build
```

`server.py` incluye un bloque `if __name__ == "__main__"` para que el ejecutable creado por PyInstaller levante Uvicorn directamente en `127.0.0.1:8765`.
