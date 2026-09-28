-- ==========================================
-- SCRIPT DE CARGA DE DATOS: TIENDA ONLINE
-- ==========================================

USE tienda_online;

-- ------------------------------------------
-- 1. ROLES DEL SISTEMA
-- ------------------------------------------
START TRANSACTION;

INSERT INTO rol (id_rol, nombre_rol) VALUES
    (1, 'administrador'),
    (2, 'empleado');

COMMIT;

-- ------------------------------------------
-- 2. USUARIOS DEL SISTEMA
-- ------------------------------------------
START TRANSACTION;

INSERT INTO usuario
  (rut_usuario, dvrut_usuario, nombre, id_rol, password, activo)
SELECT 20572190, '8', 'Matias', 1, SHA2('0504', 256), 1
UNION ALL
SELECT 21153893, '7', 'Isa', 1, SHA2('1630', 256), 1
UNION ALL
SELECT 21381886, '4', 'Bárbara', 2, SHA2('2808', 256), 1;

COMMIT;

-- ------------------------------------------
-- 3. MARCAS, PRODUCTOS Y VARIANTES
-- ------------------------------------------
START TRANSACTION;

-- Marcas necesarias
INSERT IGNORE INTO marca (nombre) VALUES
    ('Girasol'),
    ('Urbana'),
    ('Andes'),
    ('Marea');

-- Productos
INSERT IGNORE INTO producto
    (id_marca, codigo_base, nombre, descripcion, precio_venta)
VALUES
    ((SELECT id_marca FROM marca WHERE nombre = 'Girasol'),
     'CAM-001', 'Camiseta basica',
     'Camiseta de algodon de corte regular para uso diario.', 12990.00),

    ((SELECT id_marca FROM marca WHERE nombre = 'Urbana'),
     'POL-001', 'Poleron con capucha',
     'Poleron abrigado con capucha y bolsillo delantero.', 29990.00),

    ((SELECT id_marca FROM marca WHERE nombre = 'Andes'),
     'JEA-001', 'Jeans clasico',
     'Jeans de mezclilla con corte recto y cinco bolsillos.', 34990.00),

    ((SELECT id_marca FROM marca WHERE nombre = 'Marea'),
     'VES-001', 'Vestido floreado',
     'Vestido liviano con estampado floral y manga corta.', 27990.00),

    ((SELECT id_marca FROM marca WHERE nombre = 'Girasol'),
     'CAM-002', 'Camisa de lino',
     'Camisa de lino manga larga, ideal para primavera y verano.', 24990.00),

    ((SELECT id_marca FROM marca WHERE nombre = 'Urbana'),
     'CHA-001', 'Chaqueta denim',
     'Chaqueta de mezclilla con cierre frontal y bolsillos.', 39990.00),

    ((SELECT id_marca FROM marca WHERE nombre = 'Andes'),
     'FAL-001', 'Falda plisada',
     'Falda plisada de tiro alto con pretina elastica.', 21990.00),

    ((SELECT id_marca FROM marca WHERE nombre = 'Marea'),
     'ABR-001', 'Abrigo largo',
     'Abrigo largo de paño con botones frontales.', 59990.00);

-- Variantes de productos
INSERT IGNORE INTO variante_producto
    (id_producto, sku, talla, color, stock_actual)
SELECT
    p.id_producto,
    v.sku,
    v.talla,
    v.color,
    v.stock_actual
FROM producto p
INNER JOIN (
    SELECT 'CAM-001' AS codigo_base, 'CAM-001-BL-S' AS sku, 'S' AS talla, 'Blanco' AS color, 12 AS stock_actual
    UNION ALL SELECT 'CAM-001', 'CAM-001-BL-M', 'M', 'Blanco', 18
    UNION ALL SELECT 'CAM-001', 'CAM-001-NE-L', 'L', 'Negro', 10

    UNION ALL SELECT 'POL-001', 'POL-001-GR-M', 'M', 'Gris', 8
    UNION ALL SELECT 'POL-001', 'POL-001-AZ-L', 'L', 'Azul marino', 6
    UNION ALL SELECT 'POL-001', 'POL-001-NE-XL', 'XL', 'Negro', 4

    UNION ALL SELECT 'JEA-001', 'JEA-001-AZ-38', '38', 'Azul denim', 7
    UNION ALL SELECT 'JEA-001', 'JEA-001-AZ-40', '40', 'Azul denim', 9
    UNION ALL SELECT 'JEA-001', 'JEA-001-NE-42', '42', 'Negro', 5

    UNION ALL SELECT 'VES-001', 'VES-001-FL-S', 'S', 'Floral rojo', 6
    UNION ALL SELECT 'VES-001', 'VES-001-FL-M', 'M', 'Floral rojo', 8
    UNION ALL SELECT 'VES-001', 'VES-001-FL-L', 'L', 'Floral azul', 5

    UNION ALL SELECT 'CAM-002', 'CAM-002-BE-S', 'S', 'Beige', 5
    UNION ALL SELECT 'CAM-002', 'CAM-002-BE-M', 'M', 'Beige', 7
    UNION ALL SELECT 'CAM-002', 'CAM-002-CE-L', 'L', 'Celeste', 4

    UNION ALL SELECT 'CHA-001', 'CHA-001-AZ-S', 'S', 'Azul denim', 4
    UNION ALL SELECT 'CHA-001', 'CHA-001-AZ-M', 'M', 'Azul denim', 6
    UNION ALL SELECT 'CHA-001', 'CHA-001-NE-L', 'L', 'Negro', 3

    UNION ALL SELECT 'FAL-001', 'FAL-001-NE-S', 'S', 'Negro', 6
    UNION ALL SELECT 'FAL-001', 'FAL-001-VE-M', 'M', 'Verde oliva', 5
    UNION ALL SELECT 'FAL-001', 'FAL-001-NE-L', 'L', 'Negro', 4

    UNION ALL SELECT 'ABR-001', 'ABR-001-CA-M', 'M', 'Camel', 3
    UNION ALL SELECT 'ABR-001', 'ABR-001-NE-L', 'L', 'Negro', 4
    UNION ALL SELECT 'ABR-001', 'ABR-001-GR-XL', 'XL', 'Gris', 2
) AS v
    ON p.codigo_base = v.codigo_base;

COMMIT;

-- ------------------------------------------
-- 4. MÉTODOS DE PAGO
-- ------------------------------------------
START TRANSACTION;

INSERT INTO metodo_pago (nombre, activo) VALUES
    ('Efectivo', 1),
    ('Débito', 1),
    ('Crédito', 1),
    ('Crédito Girasol', 1);

COMMIT;

-- ------------------------------------------
-- 5. CLIENTES
-- ------------------------------------------
START TRANSACTION;

INSERT INTO cliente (
    rut_cliente, dvrut_cliente, nombre, celular, direccion,
    actividad_economica, descripcion, fono, tope_credito, activo
) VALUES
    (5210450, '5', 'Maria Elena Masquereña Mascareña', 652622439, 'Pudeto 207', 'COMERCIAL DIAZ', '18 CADA MES ,  ,', NULL, 100000.00, 1),
    (5983192, '5', 'Alicia Barrientos Riquelme', 945502994, 'Panamericana Sur Km 5 S/N', '', '', NULL, 100000.00, 1),
    (6166060, '7', 'Irma Henriquez Romero', 990511472, 'Pupelde S/N', '', '', NULL, 100000.00, 1),
    (6174721, '4', 'Rosario Oyarzo Miranda', 974313756, 'Heihuen 236', '', '', NULL, 100000.00, 1),
    (6418076, '2', 'Gladyz Cardenas Peran', 998200738, 'Villa Ohigginis Pasaje 2 N2', '', 'PAGO 20 DE CADA MES ,  ,', NULL, 100000.00, 1),
    (6601013, '9', 'Viola Saldivia Chacon', 984396237, 'Eleutrio Ramirez 364', '', '', NULL, 100000.00, 1),
    (7312438, '7', 'Karla Ramirez Osorio', 998646503, 'Pudeto 670 Interior', '', '30 DE CADA MES ,  ,', NULL, 100000.00, 1),
    (7953926, '0', 'Ceccilia Carrasco Latif', 977313392, 'Costanera Norte 285', 'CAMARA DE COMERCIO', '20 DE CADA MES , DEBE ARTO ESTA CON PROBLEMAS DE SALUD  ,', NULL, 100000.00, 1),
    (8211335, '5', 'Roxana Aguila Pizarro', 997119020, 'Lechagua S/N', 'FECHA DE PAGO 30 DE CADA MES', 'FECHA DE PAGO 20 C/M ,  ,', NULL, 100000.00, 1),
    (8273888, '6', 'Sonia Barria Alvarez', 986281202, 'Los Alerces 681', '', '', NULL, 100000.00, 1),
    (8796204, '0', 'Yolanda Ojeda Maldonado', 984075209, 'Villa Chiloe El Meolin Nº 33', '', '', 652621901, 100000.00, 1),
    (8810077, '8', 'Sandra Jacqueline Santana Yañez', 998418457, 'Calle Pudeto 1209', '', '', 652622413, 100000.00, 1),
    (9040267, '6', 'Patricia Diaz Mascareña', 967607263, 'Caicumeo 1292', 'Profesora Escuela Bahia de Linao', ', Jessica Alarcon Diaz (hija) ,', NULL, 100000.00, 1),
    (9059773, '6', 'Sonia Villar Gonzales', 963264797, 'Calle Pudeto 248', '', '', 652622257, 100000.00, 1),
    (9067949, 'K', 'Nelda Guesel Ojeda', 652623527, 'Errazuriz 377', '', '', NULL, 100000.00, 1),
    (9340465, '3', 'Blanca Bahamondes Contrera', 998194730, 'La Curuña 366', 'POLICIA LOCAL', '', NULL, 100000.00, 1),
    (9348196, '8', 'Patricia Garcia Ruiz', 956631156, 'Jorge Sepulveda 2119', '', '', NULL, 100000.00, 1),
    (9521464, '9', 'Maria Alicia Solis Gallardo', 940012068, 'Nicolas Macardi 1201', 'TIENDA OUTDOR CALLE MAIPU', '30 DE CADA MES ,  ,', NULL, 100000.00, 1),
    (9948764, 'K', 'Maria Eugenia Mayorga Barrientos', 994121113, 'Errazuriz Interior 309', '', '', NULL, 100000.00, 1),
    (9984927, '4', 'Roxana Munoz Garcia', 998865196, 'Panamericana Sur S/N', '', '', NULL, 100000.00, 1),
    (9997720, '5', 'Rosa Yañez Oyarzo', 963008041, 'Hueihuen 286', '', '', NULL, 100000.00, 1),
    (11083333, '4', 'Mireya Ramirez Gonzales', 992808215, 'Villa Jardin Del Alto Psje Nivaldo Jose Peña 154', '', 'PAGO 05 DE CADA MES ,  ,', NULL, 100000.00, 1),
    (11118115, '2', 'Elly Perez Cardenas', 652622734, 'Avenida Prat 289', '', 'PAGO 5 DE CADA MES ,  , 15 DE CADA MES', NULL, 100000.00, 1),
    (11454117, '6', 'Sandra Velasques Carcamo', 975624053, 'Punta Chilen Rural', '', '', 988101560, 100000.00, 1),
    (11595162, '9', 'Roswita Lucic Figueroa', 652627179, 'Villa Fuerte Real Fuerte Corona 51', '', ', COMPRA PERO PAGA CON TARJETA MARAVILLOSO ,', NULL, 100000.00, 1),
    (11598324, '5', 'Paola Ampuero Alvarado', 995974250, 'Quemchi', '', ',  , 10 DE CADA MES', NULL, 100000.00, 1),
    (12141938, '6', 'Yasna Diaz Vargas', 984179190, 'Quemchi Pedro Montt 461', '', '05 DE CADA MES ,  ,', NULL, 100000.00, 1),
    (12641531, '1', 'Sandra Paola Bravo Vargas', 974501234, 'Villa Las Araucarias Calle El Cerro 142', 'CAJERO BANCO', ',  , LOS 5 CADA MES', NULL, 100000.00, 1),
    (13000812, '7', 'Angela Villegas Carcamo', 985951157, 'Fragata Independencia 1030 Poblacion Bellavista', 'PROFESORA', 'PAGO 30 DE CADA MES ,  ,', NULL, 100000.00, 1),
    (13525586, '6', 'Vanesa Elena Mayorga Morales', 977441950, 'Via Mozart C 24', 'ENFERMERA', 'PAGO LOS 5 DE CADA M ,  ,', NULL, 100000.00, 1),
    (13593477, '1', 'Marcela Alejandra Quezada Silva', 961351776, 'Olegario Muñoz 860', 'TRABAJA SII', 'PAGO 20 DE CADA MES ,  , 20 DE CADA MES', NULL, 100000.00, 1),
    (14041491, '3', 'Karen Adriana Shulback Navarrete', 968397443, 'Pudeto 893', 'CONSULTORIO MANUEL FERREIRA', 'FECHA PAGO 05 DE C/M ,  ,', NULL, 100000.00, 1),
    (14529762, '1', 'Sidonia Hernandez Soto', 994324976, 'Los Alerces 778', '', ',  ,', NULL, 100000.00, 1),
    (14531587, '5', 'Edith Ramirez Gonzales', 942834854, 'Almirante La Torre 887', '', 'FECHA DE PAGO 25 C/M ,  ,', NULL, 100000.00, 1),
    (15305182, '8', 'Marianela Andrea Gomez Cadin', 975701762, 'Bernardo Ohiggins 351', '', 'PAGO 05 DE CADA MES ,  ,', NULL, 100000.00, 1),
    (16206184, '4', 'Romina Solange Duncker Asenjo', 977248285, 'Condominio Altos De Pupelde Calle Rio Huicha 209', 'DENTISTA HOSIPITAL', ',  , FECHA DE PAGO 26 DE CADA MES', NULL, 100000.00, 1),
    (16779600, '1', 'Paulina Zuñiga Vera', 987545615, 'Poblacion Bonilla 1 Ramon Angel Jara 388', '', '', NULL, 100000.00, 1),
    (17144787, '9', 'Karina Silva Silva', 954057771, 'San Antonio 302', '', 'PAGO 15 Y 30 C/MES , X Cali Constenla , Marido Adm Notaria de Ancud', NULL, 100000.00, 1),
    (17714350, '2', 'Isabel Paz Oyarzun Viveros', 997577837, 'Calle Pudeto 1246', '', ', NO DAR MAS CREDITO SOLO TIENE QIE TERMINAR DE PAGAR , 05 DE CADA MES', NULL, 100000.00, 1),
    (17714410, 'K', 'Carolamz Valeska Aguilar Vidal', 930218670, 'Camino Huicha Rural - Pudeto 276', '', 'PAGO 30 DE CADA MES , TOPE MAXIMO DE CREDITO $ 100.000.- PIE Y 2 CUOTAS , MARIDO RAMON CARCAMO', NULL, 100000.00, 1),
    (19000652, '2', 'Marcela Igancia Soto Salazar', 992790083, 'Condomio Pupelde Rio Puntra 25', '', ',  , 20 DE CADA MES', NULL, 100000.00, 1),
    (24864727, '2', 'Scarlett Danet Garcia Aguirre', 976833164, 'Pudeto 248', '', ',  , 05 DE CADA MES', NULL, 100000.00, 1);

COMMIT;