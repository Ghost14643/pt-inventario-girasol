-- Esquema base EasyStock / GirasolDB v0.1 (MariaDB, InnoDB, utf8mb4)
-- Solo DDL

USE tienda_online;

-- ========== Usuarios ==========
CREATE TABLE rol (
  id_rol      INT          NOT NULL AUTO_INCREMENT,
  nombre_rol  VARCHAR(50)  NOT NULL,
  PRIMARY KEY (id_rol),
  UNIQUE KEY uq_rol_nombre (nombre_rol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE usuario (
  id_usuario     INT           NOT NULL AUTO_INCREMENT,
  rut_usuario    INT           NOT NULL,
  dvrut_usuario  CHAR(1)       NOT NULL,
  nombre         VARCHAR(100)  NOT NULL,
  id_rol         INT           NOT NULL,
  `password`     VARCHAR(255)  NOT NULL,
  activo         BOOLEAN       NOT NULL DEFAULT 1,
  PRIMARY KEY (id_usuario),
  UNIQUE KEY uq_usuario_rut (rut_usuario),
  CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol) REFERENCES rol (id_rol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== Catálogo de productos ==========
CREATE TABLE marca (
  id_marca  INT          NOT NULL AUTO_INCREMENT,
  nombre    VARCHAR(50)  NOT NULL,
  PRIMARY KEY (id_marca),
  UNIQUE KEY uq_marca_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE producto (
  id_producto   INT            NOT NULL AUTO_INCREMENT,
  id_marca      INT            NOT NULL,
  codigo_base   VARCHAR(50)    NOT NULL,
  nombre        VARCHAR(100)   NOT NULL,
  descripcion   TEXT           NULL,
  precio_venta  DECIMAL(10,2)  NOT NULL,
  PRIMARY KEY (id_producto),
  UNIQUE KEY uq_producto_codigo_base (codigo_base),
  CONSTRAINT fk_producto_marca FOREIGN KEY (id_marca) REFERENCES marca (id_marca),
  CONSTRAINT ck_producto_precio CHECK (precio_venta >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE variante_producto (
  id_variante   INT          NOT NULL AUTO_INCREMENT,
  id_producto   INT          NOT NULL,
  sku           VARCHAR(50)  NOT NULL,
  talla         VARCHAR(10)  NULL,
  color         VARCHAR(30)  NULL,
  stock_actual  INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (id_variante),
  UNIQUE KEY uq_variante_sku (sku),
  CONSTRAINT fk_variante_producto FOREIGN KEY (id_producto) REFERENCES producto (id_producto),
  CONSTRAINT ck_variante_stock CHECK (stock_actual >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== Métodos de pago y clientes ==========
CREATE TABLE metodo_pago (
  id_metodo_pago  INT          NOT NULL AUTO_INCREMENT,
  nombre          VARCHAR(50)  NOT NULL,
  activo          BOOLEAN      NOT NULL DEFAULT 1,
  PRIMARY KEY (id_metodo_pago),
  UNIQUE KEY uq_metodo_pago_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cliente (
  rut_cliente          INT            NOT NULL,            -- el RUT es la PK, sin AUTO_INCREMENT
  dvrut_cliente        CHAR(1)        NOT NULL,
  nombre               VARCHAR(100)   NOT NULL,
  celular              VARCHAR(15)    NULL,
  direccion            VARCHAR(150)   NULL,
  actividad_economica  VARCHAR(100)   NULL,
  descripcion          TEXT           NULL,
  fono                 VARCHAR(15)    NULL,
  tope_credito         DECIMAL(10,2)  NOT NULL DEFAULT 0,
  activo               BOOLEAN        NOT NULL DEFAULT 1,
  PRIMARY KEY (rut_cliente),
  CONSTRAINT ck_cliente_tope CHECK (tope_credito >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== Ventas ==========
CREATE TABLE venta (
  id_venta        INT            NOT NULL AUTO_INCREMENT,
  fecha           DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  id_usuario      INT            NOT NULL,
  rut_cliente     INT            NULL,                     -- NULL si no es Crédito Girasol
  id_metodo_pago  INT            NOT NULL,
  subtotal        DECIMAL(10,2)  NOT NULL,
  descuento       DECIMAL(10,2)  NOT NULL DEFAULT 0,       -- porcentaje
  total           DECIMAL(10,2)  NOT NULL,
  PRIMARY KEY (id_venta),
  KEY idx_venta_fecha (fecha),
  CONSTRAINT fk_venta_usuario     FOREIGN KEY (id_usuario)     REFERENCES usuario (id_usuario),
  CONSTRAINT fk_venta_cliente     FOREIGN KEY (rut_cliente)    REFERENCES cliente (rut_cliente),
  CONSTRAINT fk_venta_metodo_pago FOREIGN KEY (id_metodo_pago) REFERENCES metodo_pago (id_metodo_pago),
  CONSTRAINT ck_venta_montos CHECK (
    subtotal >= 0 AND total >= 0 AND total <= subtotal
    AND descuento BETWEEN 0 AND 100
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE detalle_venta (
  id_detalle       INT            NOT NULL AUTO_INCREMENT,
  id_venta         INT            NOT NULL,
  id_variante      INT            NOT NULL,
  cantidad         INT            NOT NULL,
  precio_unitario  DECIMAL(10,2)  NOT NULL,
  PRIMARY KEY (id_detalle),
  CONSTRAINT fk_detalle_venta    FOREIGN KEY (id_venta)    REFERENCES venta (id_venta),
  CONSTRAINT fk_detalle_variante FOREIGN KEY (id_variante) REFERENCES variante_producto (id_variante),
  CONSTRAINT ck_detalle_valores CHECK (cantidad > 0 AND precio_unitario >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== Créditos ==========
CREATE TABLE estado_credito (
  id_estado_credito  INT          NOT NULL AUTO_INCREMENT,
  estado             VARCHAR(50)  NOT NULL,
  PRIMARY KEY (id_estado_credito),
  UNIQUE KEY uq_estado_credito_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE credito (
  id_credito         INT            NOT NULL AUTO_INCREMENT,
  id_venta           INT            NOT NULL,
  id_estado_credito  INT            NOT NULL,
  cantidad_cuotas    INT            NOT NULL,
  pie                DECIMAL(10,2)  NOT NULL DEFAULT 0,
  PRIMARY KEY (id_credito),
  UNIQUE KEY uq_credito_venta (id_venta),                  -- máximo un crédito por venta
  CONSTRAINT fk_credito_venta  FOREIGN KEY (id_venta)          REFERENCES venta (id_venta),
  CONSTRAINT fk_credito_estado FOREIGN KEY (id_estado_credito) REFERENCES estado_credito (id_estado_credito),
  CONSTRAINT ck_credito_valores CHECK (cantidad_cuotas > 0 AND pie >= 0)   -- RN-15
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cuota_credito (
  id_cuota_credito  INT            NOT NULL AUTO_INCREMENT,
  id_credito        INT            NOT NULL,
  numero_cuota      INT            NOT NULL,
  monto_cuota       DECIMAL(10,2)  NOT NULL,
  fecha_vencimiento DATE           NOT NULL,
  fecha_pago        DATE           NULL,                   -- NULL = pendiente
  PRIMARY KEY (id_cuota_credito),
  UNIQUE KEY uq_cuota_numero (id_credito, numero_cuota),
  KEY idx_cuota_estado_venc (fecha_pago, fecha_vencimiento),
  CONSTRAINT fk_cuota_credito FOREIGN KEY (id_credito) REFERENCES credito (id_credito),
  CONSTRAINT ck_cuota_valores CHECK (numero_cuota > 0 AND monto_cuota > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== Inventario ==========
CREATE TABLE movimiento_stock (
  id_movimiento  INT          NOT NULL AUTO_INCREMENT,
  id_variante    INT          NOT NULL,
  tipo           VARCHAR(10)  NOT NULL,
  cantidad       INT          NOT NULL,
  fecha          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  referencia     VARCHAR(100) NULL,
  id_usuario     INT          NOT NULL,
  PRIMARY KEY (id_movimiento),
  KEY idx_movimiento_variante_fecha (id_variante, fecha),
  CONSTRAINT fk_movimiento_variante FOREIGN KEY (id_variante) REFERENCES variante_producto (id_variante),
  CONSTRAINT fk_movimiento_usuario  FOREIGN KEY (id_usuario)  REFERENCES usuario (id_usuario),
  CONSTRAINT ck_movimiento_cantidad CHECK (cantidad > 0),
  CONSTRAINT ck_movimiento_tipo CHECK (tipo IN ('Entrada', 'Salida'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== Caja ==========
CREATE TABLE arqueo_caja (
  id_arqueo            INT            NOT NULL AUTO_INCREMENT,
  id_usuario           INT            NOT NULL,
  fecha                DATE           NOT NULL,
  hora_apertura        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  hora_cierre          DATETIME       NULL,
  monto_inicial        DECIMAL(10,2)  NOT NULL,
  monto_final          DECIMAL(10,2)  NULL,
  gastos               DECIMAL(10,2)  NOT NULL DEFAULT 0,
  usuario_caja_abierta INT            NULL,                -- = id_usuario mientras está abierta; NULL al cerrar
  PRIMARY KEY (id_arqueo),
  UNIQUE KEY uq_arqueo_caja_abierta (usuario_caja_abierta),  -- UNIQUE admite varios NULL (cajas cerradas)
  CONSTRAINT fk_arqueo_usuario FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario),
  CONSTRAINT ck_arqueo_montos CHECK (monto_inicial >= 0 AND gastos >= 0),
  CONSTRAINT ck_arqueo_cierre CHECK (
    (hora_cierre IS NULL AND monto_final IS NULL AND usuario_caja_abierta = id_usuario)
    OR
    (hora_cierre IS NOT NULL AND monto_final IS NOT NULL AND usuario_caja_abierta IS NULL
       AND hora_cierre >= hora_apertura)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE arqueo_detalle_pago (
  id_arqueo       INT            NOT NULL,
  id_metodo_pago  INT            NOT NULL,
  monto_esperado  DECIMAL(10,2)  NOT NULL,
  monto_contado   DECIMAL(10,2)  NOT NULL,
  PRIMARY KEY (id_arqueo, id_metodo_pago),
  CONSTRAINT fk_arqdet_arqueo FOREIGN KEY (id_arqueo)      REFERENCES arqueo_caja (id_arqueo),
  CONSTRAINT fk_arqdet_metodo FOREIGN KEY (id_metodo_pago) REFERENCES metodo_pago (id_metodo_pago),
  CONSTRAINT ck_arqdet_montos CHECK (monto_esperado >= 0 AND monto_contado >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;