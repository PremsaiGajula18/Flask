-- Trip Planner MySQL Schema
-- Creates database and tables for users, trips, activities, and place_suggestions

CREATE DATABASE IF NOT EXISTS trip_planner_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE trip_planner_db;

-- 1. users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. trips table
CREATE TABLE IF NOT EXISTS trips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    owner_id INT NOT NULL,
    destination VARCHAR(120) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_trips_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_trip_dates CHECK (end_date >= start_date),
    CONSTRAINT chk_trip_budget CHECK (budget >= 0),
    INDEX idx_trips_owner (owner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. activities table
CREATE TABLE IF NOT EXISTS activities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    activity_date DATE NOT NULL,
    activity_time TIME NOT NULL,
    category VARCHAR(50) NOT NULL,
    place VARCHAR(150) NOT NULL,
    cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_activities_trip FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
    CONSTRAINT chk_activity_cost CHECK (cost >= 0),
    INDEX idx_activities_trip (trip_id),
    INDEX idx_activities_date (activity_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. place_suggestions table
CREATE TABLE IF NOT EXISTS place_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    destination VARCHAR(120) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    image_url VARCHAR(255) NULL,
    INDEX idx_places_destination (destination),
    INDEX idx_places_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed Sample Place Suggestions
INSERT INTO place_suggestions (name, destination, category, description, image_url) VALUES
('Eiffel Tower', 'Paris, France', 'Sightseeing', 'Iconic 19th-century iron lattice tower offering breathtaking panoramic views of Paris.', 'https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?auto=format&fit=crop&w=800&q=80'),
('Louvre Museum', 'Paris, France', 'Culture', 'World famous art museum housing landmark works like the Mona Lisa and Venus de Milo.', 'https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=800&q=80'),
('Le Marais Bakery Tour', 'Paris, France', 'Food', 'Taste traditional French croissants, baguettes, and artisan macarons through historic streets.', 'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=800&q=80'),
('Senso-ji Temple', 'Tokyo, Japan', 'Culture', 'Tokyo ancient Buddhist temple with vibrant Nakamise shopping street and sacred pagoda.', 'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=800&q=80'),
('Tsukiji Outer Market Food Crawl', 'Tokyo, Japan', 'Food', 'Savor world-class fresh sashimi, tamagoyaki, wagyu skewers, and matcha sweets.', 'https://images.unsplash.com/photo-1540648639573-8c848de23f0a?auto=format&fit=crop&w=800&q=80'),
('Mount Fuji Hiking Tour', 'Tokyo, Japan', 'Adventure', 'Ascend scenic trails with views across the Five Lakes and breathtaking sunrise vistas.', 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=800&q=80'),
('Uluwatu Cliff Temple & Sunset', 'Bali, Indonesia', 'Culture', 'Cliffside Balinese sea temple perched high above crashing Indian Ocean waves.', 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=800&q=80'),
('Tegallalang Rice Terraces', 'Bali, Indonesia', 'Nature', 'Emerald green stepped rice paddies surrounded by palm trees and jungle swing trails.', 'https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?auto=format&fit=crop&w=800&q=80'),
('Grand Bazaar Shopping', 'Istanbul, Turkey', 'Shopping', 'One of the world largest and oldest covered markets with spices, lanterns, and textiles.', 'https://images.unsplash.com/photo-1527838832700-5059252407fa?auto=format&fit=crop&w=800&q=80'),
('Bosphorus Sunset Cruise', 'Istanbul, Turkey', 'Sightseeing', 'Sail between Europe and Asia past waterfront palaces, fortresses, and skyline minarets.', 'https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=800&q=80'),
('Colosseum & Roman Forum Tour', 'Rome, Italy', 'Sightseeing', 'Step into ancient gladiatorial arena history and the vibrant civic heart of classical Rome.', 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=800&q=80'),
('Trastevere Artisan Trattoria Dinner', 'Rome, Italy', 'Food', 'Authentic handmade cacio e pepe, carbonara, and Italian wine in cobblestone alleyways.', 'https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=800&q=80');
