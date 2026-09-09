-- ============================================================
-- Script de base de datos para el sistema de detección de placas
-- Proyecto: deteccion-placas (app.py)
--
-- Cómo ejecutarlo:
--   Opción A (phpMyAdmin / XAMPP): pestaña "Importar" y selecciona este archivo.
--   Opción B (consola):  mysql -u root < database.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS control_vehicular
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE control_vehicular;

-- ------------------------------------------------------------
-- Tabla de usuarios (login / registro)
-- La columna password guarda el hash de werkzeug (scrypt),
-- que puede superar los 160 caracteres: usar VARCHAR(255).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Tabla de detecciones (capturas de placas)
-- Columnas según el INSERT de app.py:
--   placa, fecha, hora, imagen, confianza, track_id, tiempo_observacion
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detecciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    placa VARCHAR(20) NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    imagen VARCHAR(255) NOT NULL,
    confianza FLOAT DEFAULT NULL,
    track_id INT DEFAULT NULL,
    tiempo_observacion FLOAT DEFAULT NULL,
    INDEX idx_placa (placa),
    INDEX idx_fecha (fecha)
);

-- ------------------------------------------------------------
-- Usuario inicial para poder entrar al sistema:
--   usuario:    admin
--   contraseña: admin123
-- ⚠️ Cambia esta contraseña después del primer inicio de sesión.
-- ------------------------------------------------------------
INSERT INTO usuarios (username, password)
SELECT 'admin', 'scrypt:32768:8:1$LojHbeyEgvGLLkAO$a41ea2c36b652681778a219e3fec5d2132ae24b023b6ac720faee7af58215703d62bba84c4faccc36e39a9db1b0c525b08c268260512bfe7969cd08f252a5ae8'
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE username = 'admin');
