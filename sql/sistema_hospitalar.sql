CREATE DATABASE  IF NOT EXISTS `prontuario_hospitalar` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `prontuario_hospitalar`;
-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: localhost    Database: prontuario_hospitalar
-- ------------------------------------------------------
-- Server version	9.5.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'de453b30-c68e-11f0-9fa7-d09466b49817:1-1061';

--
-- Table structure for table `administracaomedicamentos`
--

DROP TABLE IF EXISTS `administracaomedicamentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `administracaomedicamentos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `paciente_id` int NOT NULL,
  `medicamento_nome` varchar(100) NOT NULL,
  `quantidade_administrada` decimal(6,2) NOT NULL,
  `se_necessario` tinyint(1) DEFAULT NULL,
  `data_hora` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `paciente_id` (`paciente_id`),
  CONSTRAINT `administracaomedicamentos_ibfk_1` FOREIGN KEY (`paciente_id`) REFERENCES `pacientes` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `administracaomedicamentos`
--

LOCK TABLES `administracaomedicamentos` WRITE;
/*!40000 ALTER TABLE `administracaomedicamentos` DISABLE KEYS */;
INSERT INTO `administracaomedicamentos` VALUES (1,1,'Paracetamol',0.08,1,'2025-12-05 14:00:00'),(2,3,'Dipirona',1.00,0,'2025-12-05 15:30:00'),(3,4,'Dramin',1.00,0,'2025-12-05 13:00:00'),(4,5,'Dipirona',1.00,0,'2025-12-08 15:30:00'),(5,6,'Omeprazol',1.00,0,'2025-10-10 10:10:00'),(6,7,'Paracetamol',1.00,0,'2025-12-11 23:50:00'),(7,8,'Dipirona',1.00,0,'2025-12-12 10:00:00'),(8,9,'Dipirona',2.00,0,'2025-12-11 13:30:00'),(9,11,'Dipirona',1.00,0,'2025-12-11 14:30:00'),(10,12,'Paracetamol',1.00,0,'2025-12-11 12:15:00'),(11,13,'Dipirona',1.00,0,'2025-12-11 13:15:00'),(12,13,'Rivotril',0.25,1,'2025-12-11 13:15:00');
/*!40000 ALTER TABLE `administracaomedicamentos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `estoque`
--

DROP TABLE IF EXISTS `estoque`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `estoque` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome_medicamento` varchar(100) NOT NULL,
  `quantidade` int NOT NULL,
  `unidade` varchar(10) DEFAULT NULL,
  `data_ultima_entrada` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome_medicamento` (`nome_medicamento`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `estoque`
--

LOCK TABLES `estoque` WRITE;
/*!40000 ALTER TABLE `estoque` DISABLE KEYS */;
INSERT INTO `estoque` VALUES (1,'Paracetamol',98,'100','2025-12-06 16:40:05'),(2,'Dipirona',28,'1','2025-12-12 10:38:13'),(3,'Rivotril',25,'0,25','2025-12-12 11:08:30'),(4,'Diazepan',10,'10mg','2025-12-12 18:08:18');
/*!40000 ALTER TABLE `estoque` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pacientes`
--

DROP TABLE IF EXISTS `pacientes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pacientes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `data_nascimento` date DEFAULT NULL,
  `cpf` varchar(11) DEFAULT NULL,
  `cep` varchar(10) DEFAULT NULL,
  `endereco` varchar(255) DEFAULT NULL,
  `bairro` varchar(100) DEFAULT NULL,
  `data_entrada` datetime NOT NULL,
  `usuario_internacao` varchar(100) DEFAULT NULL,
  `nome_baixa` varchar(100) DEFAULT NULL,
  `data_baixa` date DEFAULT NULL,
  `procedimento` text,
  `cid_10` varchar(10) DEFAULT NULL,
  `observacoes_entrada` text,
  `prioridade_atencao` enum('verde','amarelo','vermelho') DEFAULT 'verde',
  `status` enum('internado','alta') DEFAULT 'internado',
  PRIMARY KEY (`id`),
  UNIQUE KEY `cpf` (`cpf`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pacientes`
--

LOCK TABLES `pacientes` WRITE;
/*!40000 ALTER TABLE `pacientes` DISABLE KEYS */;
INSERT INTO `pacientes` VALUES (1,'teste','1999-04-12',NULL,'92511-565','Rua Manoel de Souza Moraes, 123','Progresso','2025-12-05 14:00:00',NULL,'admin','2025-12-12','Fazer curativo no braço(fratura)',NULL,NULL,'verde','alta'),(2,'teste1','1995-09-09',NULL,'92511-560','Rua Frederico Lampert, 125','Progresso','2025-12-01 10:00:00',NULL,'tgreff','2025-12-12','teste',NULL,NULL,'verde','alta'),(3,'teste','1989-10-10',NULL,'92510030','Rua José Luís, 654','Centro','2025-12-05 15:30:00',NULL,'admin','2025-12-12','Enfaixar a perna',NULL,NULL,'verde','alta'),(4,'Carlos','2000-10-10',NULL,'92511565','Rua Manoel de Souza Moraes, 145','Progresso','2025-12-05 13:00:00',NULL,'admin','2025-12-09','testando os procedimentos',NULL,NULL,'verde','alta'),(5,'Magda Angus','1986-08-15',NULL,'92511565','Rua Manoel de Souza Moraes, 456','Progresso','2025-12-08 15:30:00',NULL,'admin','2025-12-09','Fazer cirurgia de apêndice!',NULL,NULL,'verde','alta'),(6,'testando1','2010-10-10',NULL,'92511565','Rua Manoel de Souza Moraes, 185','Progresso','2025-10-10 10:10:00','admin','admin','2025-12-09','testando apenas',NULL,NULL,'verde','alta'),(7,'Antônio Fagundes','1960-05-10',NULL,'93320052','Avenida Nações Unidas, 563','Centro','2025-12-11 23:50:00','admin',NULL,NULL,'Anestesiar e encaminhar para cirurgia.',NULL,NULL,'verde','internado'),(8,'Magda Antonella','1973-03-19',NULL,'93320052','Avenida Nações Unidas, 975','Centro','2025-12-12 10:00:00','admin',NULL,NULL,'Realizar a costura de um dedo cortado.',NULL,NULL,'verde','internado'),(9,'Jairo Manoel','1963-07-03',NULL,'93320052','Avenida Nações Unidas, 2850','Centro','2025-12-11 13:30:00','admin',NULL,NULL,'Fazer curativo contra queimadura.',NULL,NULL,'verde','internado'),(10,'Luisa Soares','2001-10-03',NULL,'93320052','Avenida Nações Unidas, 3001','Centro','2025-12-11 22:15:00','admin','admin','2025-12-12','Realizar costura do dedo.',NULL,NULL,'verde','alta'),(11,'Liliane Fonseca','1971-08-27',NULL,'93320052','Avenida Nações Unidas, 3975','Centro','2025-12-11 14:30:00','admin',NULL,NULL,'Curativo','','Paciente fará um curativo, pois teve seu dedo cortado enquanto cozinhava.','verde','internado'),(12,'Bill Gates','1962-01-10','13685200145','92511560','Rua Frederico Lampert, 953','Progresso','2025-12-11 12:15:00','admin',NULL,NULL,'Gripe','','Internado para curar a gripe!','verde','internado'),(13,'Elena Gilbert','2000-12-31','99563200145','92510560','Rua João Candido, 985','Rui Barbosa','2025-12-11 13:15:00','admin',NULL,NULL,'Cirurgia de apendicite','','Paciente com dores.','vermelho','internado');
/*!40000 ALTER TABLE `pacientes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `provasdevida`
--

DROP TABLE IF EXISTS `provasdevida`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `provasdevida` (
  `id` int NOT NULL AUTO_INCREMENT,
  `paciente_id` int NOT NULL,
  `data_hora` datetime NOT NULL,
  `pressao_arterial` varchar(20) DEFAULT NULL,
  `glicose` decimal(6,2) DEFAULT NULL,
  `saturacao` decimal(4,2) DEFAULT NULL,
  `batimentos_cardiacos` int DEFAULT NULL,
  `quem_efetuou` varchar(100) DEFAULT NULL,
  `observacoes` text,
  PRIMARY KEY (`id`),
  KEY `paciente_id` (`paciente_id`),
  CONSTRAINT `provasdevida_ibfk_1` FOREIGN KEY (`paciente_id`) REFERENCES `pacientes` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `provasdevida`
--

LOCK TABLES `provasdevida` WRITE;
/*!40000 ALTER TABLE `provasdevida` DISABLE KEYS */;
INSERT INTO `provasdevida` VALUES (1,3,'2025-12-06 16:42:00','120/80',96.00,97.00,85,'admin','O paciente está bem! Pouco de dor de cabeça apenas!'),(2,5,'2025-12-09 10:00:00','120/80',86.00,99.00,91,'admin','Apenas com dores, mas já está medicada!'),(3,5,'2025-12-09 10:25:00','120/70',76.00,98.00,81,'edufbarreto','Segue bem, sem dores!'),(4,7,'2025-12-12 11:13:00','110/80',83.00,98.00,79,'admin','O paciente está bem.'),(5,7,'2025-12-12 18:10:00','130/70',91.00,99.00,96,'admin','Paciente segue bem!'),(6,9,'2025-12-12 18:12:00','110/80',83.00,98.00,82,'tgreff','Paciente bem!'),(7,7,'2025-12-15 19:46:00','13/80',83.00,97.00,90,'admin','');
/*!40000 ALTER TABLE `provasdevida` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario` varchar(50) NOT NULL,
  `senha` varchar(255) NOT NULL,
  `nivel_acesso` enum('admin','enfermeiro','estagiario') NOT NULL,
  `nome_completo` varchar(150) NOT NULL,
  `data_nascimento` varchar(10) NOT NULL,
  `nacionalidade` varchar(2) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuario` (`usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (2,'admin','scrypt:32768:8:1$ilf0Mzgb6l9i84MV$eeabe0c602ff6a3f80e960cfc2264031d8c9899e82657cddac671a4b9d913074f7b99978f1f34b6aeb8ccab7fe6528bdc8ae3fcf046f727f4bc74ad2a0a53d9e','admin','','',''),(5,'efbarreto','scrypt:32768:8:1$6uLwYi6B8RIwKIsm$ae0320aa9a27c5179cab1c97f7c2f6abdcef7232961e859bd05393ca452bc38940b6f236c1ac80a2e9ac4f81a8d4ea8c49f35d16164eb25bae2d31b9998ee28b','enfermeiro','Eduardo Filippsen Barreto','1987-07-11','BR'),(6,'tgreff','scrypt:32768:8:1$10RZBOPvlf3FXBul$efdf0550591ed243a37c849cef8558b1a190e229a15e3e7fcff1fa3c8d6928e10fe7c7e3d1ad39ccd93092dac91c9878bd41bd35675e0b06a1eec2b87720bc19','enfermeiro','Thamise Greff','1992-12-22','BR'),(7,'edu','scrypt:32768:8:1$Y1kr43U4z33QcmUZ$640ad109abbb13bdfa26ae9df6014a5f815acc3838f7c9caf1b628ba1fbd0be1251b40689bf0d18c21d2e1d1c6a991277b0aa2b72f90e4535e7d5541b5edbc3a','estagiario','Eduardo Barreto','1987-07-11','BR');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-29  9:59:41
