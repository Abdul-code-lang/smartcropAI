CREATE DATABASE IF NOT EXISTS smartcrop_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smartcrop_ai;

CREATE TABLE IF NOT EXISTS crops (id INT AUTO_INCREMENT PRIMARY KEY, crop_name VARCHAR(80) NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS markets (id INT AUTO_INCREMENT PRIMARY KEY, market_name VARCHAR(120) NOT NULL UNIQUE, location VARCHAR(120) NOT NULL, latitude DECIMAL(9,6), longitude DECIMAL(9,6));
CREATE TABLE IF NOT EXISTS historical_prices (id BIGINT AUTO_INCREMENT PRIMARY KEY, crop_id INT NOT NULL, market_id INT NOT NULL, price_date DATE NOT NULL, price_per_kg DECIMAL(10,2) NOT NULL, CONSTRAINT fk_price_crop FOREIGN KEY (crop_id) REFERENCES crops(id), CONSTRAINT fk_price_market FOREIGN KEY (market_id) REFERENCES markets(id), UNIQUE KEY uq_crop_market_date (crop_id, market_id, price_date));
CREATE TABLE IF NOT EXISTS predictions (id BIGINT AUTO_INCREMENT PRIMARY KEY, crop_id INT NOT NULL, market_id INT NOT NULL, prediction_date DATE NOT NULL, predicted_price DECIMAL(10,2) NOT NULL, prediction_period VARCHAR(30) NOT NULL, model_version VARCHAR(40), FOREIGN KEY (crop_id) REFERENCES crops(id), FOREIGN KEY (market_id) REFERENCES markets(id));
CREATE TABLE IF NOT EXISTS prediction_history (id BIGINT AUTO_INCREMENT PRIMARY KEY, crop VARCHAR(80) NOT NULL, location VARCHAR(120) NOT NULL, period VARCHAR(30) NOT NULL, predicted_price DECIMAL(10,2) NOT NULL, best_market VARCHAR(120) NOT NULL, created_at DATETIME NOT NULL, result_json JSON NOT NULL);

INSERT IGNORE INTO crops(crop_name) VALUES ('Tomato'),('Onion'),('Potato'),('Brinjal'),('Banana'),('Paddy'),('Groundnut'),('Coconut');
INSERT IGNORE INTO markets(market_name,location,latitude,longitude) VALUES ('Tirunelveli','Tirunelveli',8.7139,77.7567),('Palayamkottai','Palayamkottai',8.7274,77.7042),('Thoothukudi','Thoothukudi',8.7642,78.1348),('Madurai','Madurai',9.9252,78.1198),('Nagercoil','Nagercoil',8.1833,77.4119);
