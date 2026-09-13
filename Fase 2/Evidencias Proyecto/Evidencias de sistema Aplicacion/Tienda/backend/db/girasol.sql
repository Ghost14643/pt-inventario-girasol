/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-12.2.2-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: tienda_online
-- ------------------------------------------------------
-- Server version	12.2.2-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Current Database: `tienda_online`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `tienda_online` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `tienda_online`;

--
-- Table structure for table `arqueo_caja`
--

DROP TABLE IF EXISTS `arqueo_caja`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `arqueo_caja` (
  `id_arqueo` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` date NOT NULL,
  `monto_inicial` decimal(10,2) DEFAULT NULL,
  `monto_final` decimal(10,2) DEFAULT NULL,
  `diferencia` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id_arqueo`),
  KEY `idx_arqueo_fecha` (`fecha`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `arqueo_caja`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `arqueo_caja` WRITE;
/*!40000 ALTER TABLE `arqueo_caja` DISABLE KEYS */;
/*!40000 ALTER TABLE `arqueo_caja` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `cliente`
--

DROP TABLE IF EXISTS `cliente`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cliente` (
  `rut` int(11) NOT NULL,
  `digito_ver` varchar(1) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `celular` int(11) NOT NULL,
  `direccion` varchar(50) DEFAULT NULL,
  `actividad_economica` varchar(100) DEFAULT NULL,
  `descripcion` varchar(250) DEFAULT NULL,
  `fono` int(11) DEFAULT NULL,
  PRIMARY KEY (`rut`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cliente`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `cliente` WRITE;
/*!40000 ALTER TABLE `cliente` DISABLE KEYS */;
INSERT INTO `cliente` VALUES
(123,'4','123',123,'123',NULL,NULL,NULL),
(5210450,'5','MARIA ELENA MASQUERE�A MASCARE�A',652622439,'PUDETO 207','COMERCIAL DIAZ','18 CADA MES ,  ,',NULL),
(5983192,'5','ALICIA BARRIENTOS RIQUELME',945502994,'PANAMERICANA SUR KM 5 S/N','','',NULL),
(6166060,'7','IRMA HENRIQUEZ ROMERO',990511472,'PUPELDE S/N','','',NULL),
(6174721,'4','ROSARIO OYARZO MIRANDA',974313756,'HEIHUEN 236','','',NULL),
(6418076,'2','GLADYZ CARDENAS PERAN',998200738,'VILLA OHIGGINIS PASAJE 2 N2','','PAGO 20 DE CADA MES ,  ,',NULL),
(6601013,'9','VIOLA SALDIVIA CHACON',984396237,'ELEUTRIO RAMIREZ 364','','',NULL),
(7312438,'7','KARLA RAMIREZ OSORIO',998646503,'PUDETO 670 INTERIOR','','30 DE CADA MES ,  ,',NULL),
(7953926,'0','CECCILIA CARRASCO LATIF',977313392,'COSTANERA NORTE 285','CAMARA DE COMERCIO','20 DE CADA MES , DEBE ARTO ESTA CON PROBLEMAS DE SALUD  ,',NULL),
(8211335,'5','ROXANA AGUILA PIZARRO',997119020,'LECHAGUA S/N','FECHA DE PAGO 30 DE CADA MES','FECHA DE PAGO 20 C/M ,  ,',NULL),
(8273888,'6','SONIA BARRIA ALVAREZ',986281202,'LOS ALERCES 681','','',NULL),
(8796204,'0','YOLANDA OJEDA MALDONADO',984075209,'VILLA CHILOE EL MEOLIN N� 33','','',652621901),
(8810077,'8','SANDRA JACQUELINE SANTANA YA�EZ',998418457,'CALLE PUDETO 1209','','',652622413),
(9040267,'6','PATRICIA DIAZ MASCARE�A',967607263,'Caicumeo 1292','Profesora Escuela Bahia de Linao',', Jessica Alarcon Diaz (hija) ,',NULL),
(9059773,'6','SONIA VILLAR GONZALES',963264797,'CALLE PUDETO 248','','',652622257),
(9067949,'K','NELDA GUESEL OJEDA',652623527,'ERRAZURIZ 377','','',NULL),
(9340465,'3','BLANCA BAHAMONDES CONTRERA',998194730,'LA CURU�A 366','POLICIA LOCAL','',NULL),
(9348196,'8','PATRICIA GARCIA RUIZ',956631156,'JORGE SEPULVEDA 2119','','',NULL),
(9521464,'9','MARIA ALICIA SOLIS GALLARDO',940012068,'NICOLAS MACARDI 1201','TIENDA OUTDOR CALLE MAIPU','30 DE CADA MES ,  ,',NULL),
(9948764,'K','MARIA EUGENIA MAYORGA BARRIENTOS',994121113,'ERRAZURIZ INTERIOR 309','','',NULL),
(9984927,'4','ROXANA MUNOZ GARCIA',998865196,'PANAMERICANA SUR S/N','','',NULL),
(9997720,'5','ROSA YA�EZ OYARZO',963008041,'HUEIHUEN 286','','',NULL),
(11083333,'4','MIREYA RAMIREZ GONZALES',992808215,'villa jardin del alto psje nivaldo jose pe�a 154','','PAGO 05 DE CADA MES ,  ,',NULL),
(11118115,'2','ELLY PEREZ CARDENAS',652622734,'AVENIDA PRAT 289','','PAGO 5 DE CADA MES ,  , 15 DE CADA MES',NULL),
(11454117,'6','SANDRA VELASQUES CARCAMO',975624053,'PUNTA CHILEN RURAL','','',988101560),
(11595162,'9','ROSWITA LUCIC FIGUEROA',652627179,'VILLA FUERTE REAL FUERTE CORONA 51','',', COMPRA PERO PAGA CON TARJETA MARAVILLOSO ,',NULL),
(11598324,'5','PAOLA AMPUERO ALVARADO',995974250,'QUEMCHI','',',  , 10 DE CADA MES',NULL),
(12141938,'6','YASNA DIAZ VARGAS',984179190,'QUEMCHI PEDRO MONTT 461','','05 DE CADA MES ,  ,',NULL),
(12641531,'1','SANDRA PAOLA BRAVO VARGAS',974501234,'VILLA LAS ARAUCARIAS CALLE EL CERRO 142','CAJERO BANCO',',  , LOS 5 CADA MES',NULL),
(13000812,'7','ANGELA VILLEGAS CARCAMO',985951157,'FRAGATA INDEPENDENCIA 1030 POBLACION BELLAVISTA','PROFESORA','PAGO 30 DE CADA MES ,  ,',NULL),
(13525586,'6','VANESA ELENA MAYORGA MORALES',977441950,'VIA MOZART C 24','ENFERMERA','PAGO LOS 5 DE CADA M ,  ,',NULL),
(13593477,'1','MARCELA ALEJANDRA QUEZADA SILVA',961351776,'OLEGARIO MU�OZ 860','TRABAJA SII','PAGO 20 DE CADA MES ,  , 20 DE CADA MES',NULL),
(14041491,'3','KAREN ADRIANA SHULBACK NAVARRETE',968397443,'PUDETO 893','CONSULTORIO MANUEL FERREIRA','FECHA PAGO 05 DE C/M ,  ,',NULL),
(14529762,'1','SIDONIA HERNANDEZ SOTO',994324976,'LOS ALERCES 778','',',  ,',NULL),
(14531587,'5','EDITH RAMIREZ GONZALES',942834854,'ALMIRANTE LA TORRE 887','','FECHA DE PAGO 25 C/M ,  ,',NULL),
(15305182,'8','MARIANELA ANDREA GOMEZ CADIN',975701762,'BERNARDO OHIGGINS 351','','PAGO 05 DE CADA MES ,  ,',NULL),
(16206184,'4','ROMINA SOLANGE DUNCKER ASENJO',977248285,'CONDOMINIO ALTOS DE PUPELDE CALLE RIO HUICHA 209','DENTISTA HOSIPITAL',',  , FECHA DE PAGO 26 DE CADA MES',NULL),
(16779600,'1','PAULINA ZU�IGA VERA',987545615,'POBLACION BONILLA 1 RAMON ANGEL JARA 388','','',NULL),
(17144787,'9','KARINA SILVA SILVA',954057771,'SAN ANTONIO 302','','PAGO 15 Y 30 C/MES , X Cali Constenla , Marido Adm Notaria de Ancud',NULL),
(17714350,'2','ISABEL PAZ OYARZUN VIVEROS',997577837,'CALLE PUDETO 1246','',', NO DAR MAS CREDITO SOLO TIENE QIE TERMINAR DE PAGAR , 05 DE CADA MES',NULL),
(17714410,'K','CAROLAMZ VALESKA AGUILAR VIDAL',930218670,'CAMINO HUICHA RURAL - PUDETO 276','','PAGO 30 DE CADA MES , TOPE MAXIMO DE CREDITO $ 100.000.- PIE Y 2 CUOTAS , MARIDO RAMON CARCAMO',NULL),
(19000652,'2','MARCELA IGANCIA SOTO SALAZAR',992790083,'CONDOMIO PUPELDE RIO PUNTRA 25','',',  , 20 DE CADA MES',NULL),
(24864727,'2','SCARLETT DANET GARCIA AGUIRRE',976833164,'PUDETO 248','',',  , 05 DE CADA MES',NULL);
/*!40000 ALTER TABLE `cliente` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `detalle_venta`
--

DROP TABLE IF EXISTS `detalle_venta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `detalle_venta` (
  `id_detalle` int(11) NOT NULL AUTO_INCREMENT,
  `id_venta` int(11) NOT NULL,
  `id_producto` int(11) NOT NULL,
  `nombre_producto` varchar(100) NOT NULL,
  `cantidad` int(11) NOT NULL,
  `precio_unitario` int(11) NOT NULL,
  `total_producto` int(11) NOT NULL,
  PRIMARY KEY (`id_detalle`),
  KEY `id_venta` (`id_venta`),
  CONSTRAINT `1` FOREIGN KEY (`id_venta`) REFERENCES `ventas` (`id_venta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detalle_venta`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `detalle_venta` WRITE;
/*!40000 ALTER TABLE `detalle_venta` DISABLE KEYS */;
/*!40000 ALTER TABLE `detalle_venta` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `detalle_venta_historico`
--

DROP TABLE IF EXISTS `detalle_venta_historico`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `detalle_venta_historico` (
  `id_detalle` int(11) NOT NULL AUTO_INCREMENT,
  `id_venta` int(11) DEFAULT NULL,
  `id_producto` int(11) DEFAULT NULL,
  `cantidad` int(11) DEFAULT NULL,
  `subtotal` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id_detalle`),
  KEY `fk_dvh_venta` (`id_venta`),
  KEY `fk_dvh_producto` (`id_producto`),
  CONSTRAINT `fk_dvh_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto_historico` (`id_producto`),
  CONSTRAINT `fk_dvh_venta` FOREIGN KEY (`id_venta`) REFERENCES `venta_historica` (`id_venta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detalle_venta_historico`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `detalle_venta_historico` WRITE;
/*!40000 ALTER TABLE `detalle_venta_historico` DISABLE KEYS */;
/*!40000 ALTER TABLE `detalle_venta_historico` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `estado_credito`
--

DROP TABLE IF EXISTS `estado_credito`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `estado_credito` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `estado` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `estado_credito`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `estado_credito` WRITE;
/*!40000 ALTER TABLE `estado_credito` DISABLE KEYS */;
INSERT INTO `estado_credito` VALUES
(1,'Pendiente'),
(2,'Atrasado'),
(3,'Completado');
/*!40000 ALTER TABLE `estado_credito` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `factura`
--

DROP TABLE IF EXISTS `factura`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `factura` (
  `id_factura` int(11) NOT NULL AUTO_INCREMENT,
  `imagen` blob NOT NULL,
  `fecha_subida` datetime NOT NULL,
  PRIMARY KEY (`id_factura`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `factura`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `factura` WRITE;
/*!40000 ALTER TABLE `factura` DISABLE KEYS */;
INSERT INTO `factura` VALUES
(1,'EMP2103_Evaluación Examen Transversal_Estudiante.pdf','2025-12-18 17:00:23'),
(2,'Screenshot from 2025-12-03 19-04-00.png','2025-12-18 17:01:57'),
(3,'INSTRODUCCIÓN SELLO USS (1) - Tagged.pdf','2026-03-08 20:41:46');
/*!40000 ALTER TABLE `factura` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `hoja_credito`
--

DROP TABLE IF EXISTS `hoja_credito`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `hoja_credito` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cliente` int(11) NOT NULL,
  `id_boleta` int(11) NOT NULL,
  `fecha_pago` date NOT NULL,
  `cuotas_por_pagar` int(11) NOT NULL,
  `estado` int(11) NOT NULL DEFAULT 1,
  `precio_cuota` int(11) DEFAULT NULL,
  `pie` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `hoja_credito_estado_credito_FK` (`estado`),
  KEY `hoja_credito_cliente_FK` (`cliente`),
  CONSTRAINT `hoja_credito_cliente_FK` FOREIGN KEY (`cliente`) REFERENCES `cliente` (`rut`),
  CONSTRAINT `hoja_credito_estado_credito_FK` FOREIGN KEY (`estado`) REFERENCES `estado_credito` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `hoja_credito`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `hoja_credito` WRITE;
/*!40000 ALTER TABLE `hoja_credito` DISABLE KEYS */;
INSERT INTO `hoja_credito` VALUES
(1,123,999999,'2026-03-06',33529,1,NULL,10000),
(2,123,999999,'2026-03-06',33529,1,NULL,10000),
(3,123,999999,'2026-03-06',33529,1,NULL,1111);
/*!40000 ALTER TABLE `hoja_credito` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `producto_historico`
--

DROP TABLE IF EXISTS `producto_historico`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `producto_historico` (
  `id_producto` int(11) NOT NULL,
  `nombre` varchar(100) DEFAULT NULL,
  `categoria` varchar(50) DEFAULT NULL,
  `talla` varchar(10) DEFAULT NULL,
  `color` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `producto_historico`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `producto_historico` WRITE;
/*!40000 ALTER TABLE `producto_historico` DISABLE KEYS */;
/*!40000 ALTER TABLE `producto_historico` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `reporte`
--

DROP TABLE IF EXISTS `reporte`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `reporte` (
  `id_reporte` int(11) NOT NULL AUTO_INCREMENT,
  `tipo` enum('VENTAS','PRODUCTOS','ARQUEO') DEFAULT NULL,
  `fecha_generacion` datetime DEFAULT current_timestamp(),
  `fecha_inicio` date DEFAULT NULL,
  `fecha_fin` date DEFAULT NULL,
  `id_tienda` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_reporte`),
  KEY `fk_reporte_tienda` (`id_tienda`),
  CONSTRAINT `fk_reporte_tienda` FOREIGN KEY (`id_tienda`) REFERENCES `tienda` (`id_tienda`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reporte`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `reporte` WRITE;
/*!40000 ALTER TABLE `reporte` DISABLE KEYS */;
/*!40000 ALTER TABLE `reporte` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `rol`
--

DROP TABLE IF EXISTS `rol`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `rol` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `roles` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rol`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `rol` WRITE;
/*!40000 ALTER TABLE `rol` DISABLE KEYS */;
INSERT INTO `rol` VALUES
(1,'empleado'),
(2,'admin'),
(3,'developer');
/*!40000 ALTER TABLE `rol` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `tienda`
--

DROP TABLE IF EXISTS `tienda`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tienda` (
  `id_tienda` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `ubicacion` varchar(150) DEFAULT NULL,
  `region` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_tienda`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tienda`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `tienda` WRITE;
/*!40000 ALTER TABLE `tienda` DISABLE KEYS */;
/*!40000 ALTER TABLE `tienda` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `usuario`
--

DROP TABLE IF EXISTS `usuario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario` (
  `rut` int(11) NOT NULL,
  `digito_ver` varchar(1) NOT NULL,
  `nombre` varchar(60) NOT NULL,
  `id_rol` int(11) NOT NULL,
  `password` varchar(100) NOT NULL,
  PRIMARY KEY (`rut`),
  KEY `usuario_rol_FK` (`id_rol`),
  CONSTRAINT `usuario_rol_FK` FOREIGN KEY (`id_rol`) REFERENCES `rol` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuario`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `usuario` WRITE;
/*!40000 ALTER TABLE `usuario` DISABLE KEYS */;
INSERT INTO `usuario` VALUES
(21300379,'8','Hector',3,'8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918'),
(22032622,'5','benja',2,'123');
/*!40000 ALTER TABLE `usuario` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `venta_historica`
--

DROP TABLE IF EXISTS `venta_historica`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `venta_historica` (
  `id_venta` int(11) NOT NULL,
  `fecha` datetime DEFAULT NULL,
  `total` decimal(10,2) DEFAULT NULL,
  `metodo_pago` varchar(20) DEFAULT NULL,
  `id_tienda` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_venta`),
  KEY `idx_venta_hist_fecha` (`fecha`),
  KEY `idx_venta_hist_tienda` (`id_tienda`),
  CONSTRAINT `fk_venta_hist_tienda` FOREIGN KEY (`id_tienda`) REFERENCES `tienda` (`id_tienda`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `venta_historica`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `venta_historica` WRITE;
/*!40000 ALTER TABLE `venta_historica` DISABLE KEYS */;
/*!40000 ALTER TABLE `venta_historica` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `ventas`
--

DROP TABLE IF EXISTS `ventas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `ventas` (
  `id_venta` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` datetime NOT NULL,
  `rut_empleado` varchar(12) NOT NULL,
  `metodo_pago` varchar(50) NOT NULL,
  `subtotal` int(11) NOT NULL,
  `descuento` int(11) NOT NULL,
  `total` int(11) NOT NULL,
  PRIMARY KEY (`id_venta`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ventas`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `ventas` WRITE;
/*!40000 ALTER TABLE `ventas` DISABLE KEYS */;
INSERT INTO `ventas` VALUES
(1,'2026-01-21 05:19:18','21300379','Efectivo',10000,0,10000),
(2,'2026-01-21 13:15:36','21300379','Efectivo',10000,0,10000);
/*!40000 ALTER TABLE `ventas` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2026-03-15 21:54:09
