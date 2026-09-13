# Sistema de Gestión de Tienda

Aplicación de escritorio moderno para punto de venta (POS) y gestión integral de tienda, con arquitectura basada en tecnologías actuales y separación clara entre frontend, orquestación nativa y backend.

![Tauri](https://img.shields.io/badge/Tauri-3.13+-blue?style=flat-square&logo=tauri)
![React](https://img.shields.io/badge/React-18+-61dafb?style=flat-square&logo=react)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python)
![SQLite](https://img.shields.io/badge/SQLite-3+-003b57?style=flat-square&logo=sqlite)

## Descripción General

Sistema integral de punto de venta y gestión de tienda diseñado para comercios minoristas. Proporciona herramientas para administración de ventas, control de inventario, gestión de usuarios, arqueo de caja e integración directa con periféricos como escáneres de código de barras e impresoras térmicas.

La aplicación adopta una arquitectura moderna de tres capas:

- **Frontend**: Interfaz React moderna con Vite y Tailwind CSS ejecutada en Webview de Tauri
- **Shell de Escritorio**: Tauri (Rust) gestiona la ventana nativa, eventos del sistema y comunicación inter-procesos
- **Backend**: Servidor Python (FastAPI/Flask) que expone endpoints REST/WebSockets para la lógica de negocio
- **Base de Datos**: SQLite local para almacenamiento de datos transaccionales

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                      Aplicación Tauri                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │    React Frontend (Vite + Tailwind CSS)                 │  │
│  │    - Interfaz de Usuario                                │  │
│  │    - Gestión de Estado (Redux/Context)                  │  │
│  │    - Llamadas HTTP/WebSocket                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓ ↑                                    │
│                    (HTTP REST Local)                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │    Tauri Runtime (Rust)                                 │  │
│  │    - Ventana Nativa                                     │  │
│  │    - Gestión del Sidecar                                │  │
│  │    - Integración del Sistema Operativo                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           ↓ ↑
            (Proceso Sidecar - Python Backend)
                           ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│           Python Backend (FastAPI/Flask)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────┐    ┌──────────────────────────┐  │
│  │   Lógica de Negocio      │    │   Drivers de Hardware    │  │
│  │   - Gestión de Ventas    │    │   - Escáner de Códigos   │  │
│  │   - Inventario           │    │   - Impresora Térmica    │  │
│  │   - Usuarios/Sesiones    │    │   - Periféricos          │  │
│  │   - Reportes             │    │                          │  │
│  └──────────────────────────┘    └──────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │    Base de Datos (SQLite)                               │  │
│  │    - reuso.db / girasol.db                              │  │
│  │    - Tablas: Productos, Ventas, Usuarios, etc.          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Estructura del Proyecto

```
Tienda/
├── src/                              # Código fuente principal (TypeScript/React)
│   ├── components/                   # Componentes React reutilizables
│   ├── pages/                        # Páginas principales (Ventas, Inventario, etc.)
│   ├── hooks/                        # Hooks personalizados
│   ├── services/                     # Servicios HTTP/API (axios, fetch)
│   ├── store/                        # Gestión de estado (Redux/Context)
│   ├── styles/                       # Estilos globales (Tailwind)
│   ├── App.tsx                       # Componente raíz
│   └── main.tsx                      # Punto de entrada React
├── src-tauri/                        # Configuración y código Tauri (Rust)
│   ├── tauri.conf.json               # Configuración de Tauri
│   ├── src/main.rs                   # Punto de entrada Rust
│   ├── Cargo.toml                    # Dependencias Rust
│   └── icons/                        # Iconos de la aplicación
├── backend/                          # Backend Python (FastAPI/Flask)
│   ├── app.py                        # Punto de entrada del servidor
│   ├── requirements.txt               # Dependencias Python
│   ├── api/                          # Endpoints REST
│   │   ├── sales.py                  # Lógica de ventas
│   │   ├── inventory.py              # Gestión de inventario
│   │   ├── users.py                  # Gestión de usuarios
│   │   └── reports.py                # Generación de reportes
│   ├── models/                       # Modelos de datos (SQLAlchemy/Pydantic)
│   ├── utils/                        # Funciones utilitarias
│   │   ├── barcode_reader.py         # Lectura de códigos de barras
│   │   └── printer.py                # Control de impresora térmica
│   ├── database/                     # Conexión y operaciones de BD
│   │   └── db.py                     # Configuración SQLite
│   └── migrations/                   # Migraciones de base de datos
├── public/                           # Archivos públicos estáticos
├── package.json                      # Dependencias Node.js
├── vite.config.ts                    # Configuración de Vite
├── tailwind.config.js                # Configuración de Tailwind CSS
├── tsconfig.json                     # Configuración de TypeScript
└── README.md                         # Este archivo

```

---

## Requisitos Previos

Antes de instalar y ejecutar el proyecto, asegúrate de contar con:

### Sistema Operativo
- Windows 10+, macOS 10.13+ o Linux (Ubuntu 20.04+ recomendado)

### Node.js y npm
- **Node.js**: 18.x LTS o superior
- **npm**: 9.x o superior

Verifica la instalación:
```bash
node --version
npm --version
```

### Python
- **Python**: 3.10 o superior
- **pip**: gestor de paquetes de Python

Verifica la instalación:
```bash
python --version
pip --version
```

### Rust (requerido para Tauri)
- **Rust**: 1.70 o superior
- **Cargo**: incluido con Rust

Descarga desde [rust-lang.org](https://www.rust-lang.org/tools/install).

Verifica la instalación:
```bash
rustc --version
cargo --version
```

### Dependencias del Sistema (según SO)

#### En Linux (Ubuntu/Debian)
```bash
sudo apt-get install libwebkit2gtk-4.1-dev \
    build-essential \
    curl \
    wget \
    libssl-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev
```

#### En Windows
- Requiere Microsoft C++ Build Tools (descargable desde Visual Studio)
- WebView2 Runtime (descargable de Microsoft)

#### En macOS
- Xcode y Command Line Tools instalados

### Periféricos (opcional)
- Escáner USB de código de barras compatible
- Impresora térmica ESC/POS compatible

---

## Instalación y Configuración para Desarrollo

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Het0c/Tienda.git
cd Tienda
```

### 2. Configurar el Backend Python

#### 2.1 Crear entorno virtual

En **Linux/macOS**:
```bash
python3 -m venv venv
source venv/bin/activate
```

En **Windows (PowerShell)**:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### 2.2 Instalar dependencias Python

```bash
cd backend
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Las dependencias de ejecución incluyen:
- `fastapi` y `uvicorn`: API local ASGI
- `mysql-connector-python`: acceso a MariaDB
- `pydantic`: validación de solicitudes
- `python-multipart`: carga de facturas
- `python-dotenv`: configuración local por variables de entorno
- `python-escpos`: integración conservada con la impresora térmica

#### 2.3 Configurar la base de datos

```bash
# Crear archivo de base de datos (si no existe)
python -c "import sqlite3; sqlite3.connect('data/girasol.db').close()"

# Ejecutar migraciones (si están disponibles)
python -m alembic upgrade head
```

Verifica que exista `data/girasol.db` en el directorio del proyecto.

### 3. Configurar el Frontend y Tauri

#### 3.1 Instalar dependencias Node.js

Desde la raíz del proyecto:
```bash
npm install
```

#### 3.2 Instalar dependencias de Tauri CLI

```bash
npm install @tauri-apps/cli
```

#### 3.3 Verificar configuración de Tauri

Revisa `src-tauri/tauri.conf.json` y ajusta si es necesario:
- URL del backend Python (puerto y host)
- Rutas del ejecutable del Sidecar

Ejemplo:
```json
{
  "build": {
    "sidecarCommand": "python ../backend/app.py"
  }
}
```

---

## Ejecución en Entorno de Desarrollo

### Opción 1: Ejecución Integrada con `npm run tauri dev`

Este comando inicia automáticamente tanto el backend como el frontend en modo desarrollo:

```bash
npm run tauri dev
```

Esto:
1. Inicia el servidor Python como Sidecar
2. Compila el código React con Vite
3. Abre la ventana de Tauri con hot-reload
4. Permanece escuchando cambios en archivos

### Opción 2: Ejecución Manual Separada (para debugging)

#### Terminal 1: Backend Python
```bash
cd backend
source venv/bin/activate  # En Windows: .\venv\Scripts\Activate.ps1
python app.py
```

Debería mostrar:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

#### Terminal 2: Frontend React + Tauri
```bash
npm run tauri dev
```

El frontend estará disponible en modo desarrollo con hot-reload.

### Estructura de URLs en Desarrollo

- **Frontend**: `http://tauri.localhost/` (dentro de la Webview)
- **Backend**: `http://127.0.0.1:8000/` (endpoints REST)
- **API Docs**: `http://127.0.0.1:8000/docs` (Swagger interactivo)

---

## Empaquetado y Construcción (Production Build)

### 1. Preparar el Backend Python

#### Opción A: PyInstaller (recomendado para Sidecar)

```bash
cd backend
pip install pyinstaller

# Generar ejecutable de una sola carpeta
pyinstaller --onedir --windowed --name tienda_backend app.py

# El ejecutable estará en: backend/dist/tienda_backend/
```

Luego, actualiza la ruta en `src-tauri/tauri.conf.json`:
```json
{
  "build": {
    "sidecarCommand": "../backend/dist/tienda_backend/tienda_backend"
  }
}
```

#### Opción B: PyInstaller con archivo único
```bash
pyinstaller --onefile --windowed --name tienda_backend app.py
```

### 2. Compilar la Aplicación Tauri

```bash
npm run tauri build
```

Esto:
1. Compila el código React para producción (minificado)
2. Compila el código Rust de Tauri
3. Empaqueta todo en un ejecutable nativo

Los artefacactos generados se localizan en:
- **Windows**: `src-tauri/target/release/Tienda.exe`
- **macOS**: `src-tauri/target/release/Tienda.app`
- **Linux**: `src-tauri/target/release/tienda`

### 3. Generación de Instaladores (opcional)

Tauri puede generar instaladores nativos:

- **Windows**: MSI (`.msi`) con NSIS
- **macOS**: DMG (`.dmg`) o APP Bundle
- **Linux**: AppImage (`.AppImage`) o Deb (`.deb`)

Configura en `src-tauri/tauri.conf.json` bajo `bundle`.

---

## Módulos Principales de la Aplicación

### 1. Gestión de Ventas
Módulo principal para captura de transacciones:
- Escaneo rápido de códigos de barras
- Búsqueda de productos
- Aplicación de descuentos y promociones
- Múltiples métodos de pago (efectivo, tarjeta, mixto)
- Historial de transacciones
- Integración con impresora térmica para tickets

### 2. Control de Inventario
Seguimiento y administración de stock:
- Catálogo de productos con SKU
- Niveles de stock en tiempo real
- Alertas de reabastecimiento
- Ajustes manuales de inventario
- Auditoría de movimientos
- Importación/exportación de datos

### 3. Arqueo de Caja
Conciliación y cierre de turnos:
- Reconciliación de efectivo vs. sistema
- Detección de diferencias
- Generación de reportes diarios
- Historial de arqueos
- Exportación en múltiples formatos

### 4. Gestión de Usuarios
Control de acceso y permisos:
- Autenticación de empleados
- Roles y permisos granulares (Vendedor, Gerente, Admin)
- Auditoría de acciones por usuario
- Gestión de horarios y turnos
- Historial de cambios

### 5. Impresión de Tickets
Generación de comprobantes de venta:
- Formato ESC/POS para impresoras térmicas
- Información detallada de producto y transacción
- Códigos QR/barcodes en tickets
- Personalización de logotipo y datos de tienda
- Respaldo de tickets en base de datos

### 6. Lectura de Códigos de Barras
Captura rápida de artículos:
- Soporte para códigos UPC, EAN-13, Code128
- Lectura desde escáner USB HID
- Validación de checksum
- Búsqueda de producto por código
- Manejo de códigos internos/personalizados

### 7. Reportes y Análisis (Bonus)
Generación de informes gerenciales:
- Ventas por período
- Productos más vendidos
- Análisis de inventario
- Performance por usuario
- Gráficos y estadísticas
- Exportación a Excel/PDF

---

## Desarrollo

### Scripts npm Disponibles

```bash
# Iniciar en modo desarrollo (con hot-reload)
npm run tauri dev

# Construir para producción
npm run tauri build

# Ejecutar solo Vite (sin Tauri)
npm run dev

# Construir solo frontend
npm run build

# Preview de la build de producción
npm run preview

# Lint del código TypeScript/React
npm run lint
```

### Estructura de Branches Recomendada

- `main`: rama de producción (releases estables)
- `develop`: rama de desarrollo integradora
- `feature/*`: ramas de features nuevas
- `bugfix/*`: ramas de correcciones
- `release/*`: ramas de preparación de releases

### Convenciones de Código

- **Frontend**: Componentes funcionales con Hooks, TypeScript strict
- **Backend**: Siguiendo PEP-8, type hints en Python 3.10+
- **Commits**: Formato convencional (`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`)

---

## Configuración Avanzada

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Backend
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
DATABASE_URL=sqlite:///./data/girasol.db

# Frontend
VITE_API_BASE_URL=http://127.0.0.1:8000

# Desarrollo
DEBUG=False
```

### Configuración de Periféricos

#### Escáner de Código de Barras
En `backend/utils/barcode_reader.py`:
```python
BARCODE_DEVICE_PATH = "/dev/ttyUSB0"  # Linux
# BARCODE_DEVICE_PATH = "COM3"  # Windows
BARCODE_BAUD_RATE = 9600
```

#### Impresora Térmica
En `backend/utils/printer.py`:
```python
PRINTER_DEVICE_PATH = "/dev/ttyUSB1"  # Linux
# PRINTER_DEVICE_PATH = "COM4"  # Windows
PRINTER_WIDTH = 80  # caracteres
```

---

## Troubleshooting

### Problema: El backend no inicia en modo `tauri dev`

**Solución**:
1. Verifica que Python esté en el PATH
2. Comprueba la ruta del Sidecar en `src-tauri/tauri.conf.json`
3. Revisa los logs en la consola de Tauri

### Problema: Errores de conexión HTTP 127.0.0.1:8000

**Solución**:
1. Asegúrate de que el backend Python esté ejecutándose
2. Verifica que no haya otro proceso usando el puerto 8000: `lsof -i :8000` (Linux/macOS) o `netstat -ano | findstr :8000` (Windows)
3. Cambia el puerto en `.env` si es necesario

### Problema: Escáner/Impresora no funciona

**Solución**:
1. Identifica el puerto: `ls /dev/tty*` (Linux) o Administrador de dispositivos (Windows)
2. Actualiza la configuración en `backend/utils/`
3. Verifica permisos de acceso al puerto serie
4. Prueba la conexión con herramientas como `miniterm.py` (pyserial)

### Problema: PyInstaller genera ejecutable muy grande

**Solución**:
Usa la opción `--optimize=2` y UPX:
```bash
pyinstaller --onedir --optimize=2 --upx-dir=/usr/bin app.py
```

---

## Contribuciones

Si deseas contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commits con mensajes descriptivos
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

Asegúrate de:
- Mantener la compatibilidad con Python 3.10+
- Seguir las convenciones de código
- Documentar cambios significativos
- Incluir pruebas cuando sea posible

---

## Licencia

Este proyecto está bajo licencia [MIT](LICENSE). Consulta el archivo LICENSE para más detalles.

---

## Contacto y Soporte

Para reportar issues, sugerencias o consultas técnicas:

- **Issues**: [GitHub Issues](https://github.com/Het0c/Tienda/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Het0c/Tienda/discussions)

---

## Recursos Adicionales

- [Documentación oficial de Tauri](https://tauri.app/docs/)
- [React Documentation](https://react.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

---

**Última actualización**: julio 2026  
**Versión**: 2.0.0 (Arquitectura moderna Tauri + React + Python)
