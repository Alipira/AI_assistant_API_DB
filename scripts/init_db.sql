-- Sample database schema for testing
-- Run this in your PostgreSQL database to create sample tables

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    country VARCHAR(50)
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    total_amount DECIMAL(10, 2),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending'
);

-- Insert sample data
INSERT INTO users (email, username, country, is_active) VALUES
('john@example.com', 'john_doe', 'USA', true),
('jane@example.com', 'jane_smith', 'UK', true),
('bob@example.com', 'bob_wilson', 'Canada', true),
('alice@example.com', 'alice_jones', 'USA', false),
('charlie@example.com', 'charlie_brown', 'Australia', true);

INSERT INTO products (name, category, price, stock_quantity) VALUES
('Laptop', 'Electronics', 999.99, 50),
('Mouse', 'Electronics', 29.99, 200),
('Keyboard', 'Electronics', 79.99, 150),
('Monitor', 'Electronics', 299.99, 75),
('Desk Chair', 'Furniture', 199.99, 30);

INSERT INTO orders (user_id, product_id, quantity, total_amount, status) VALUES
(1, 1, 1, 999.99, 'completed'),
(1, 2, 2, 59.98, 'completed'),
(2, 3, 1, 79.99, 'shipped'),
(3, 4, 1, 299.99, 'pending'),
(5, 5, 2, 399.98, 'completed');
