-- DROP old versions (optional, for a clean reset)
--DROP TABLE IF EXISTS exchangelog CASCADE;
--DROP TABLE IF EXISTS cart CASCADE;
--DROP TABLE IF EXISTS orders CASCADE;
--DROP TABLE IF EXISTS products CASCADE;
--DROP TABLE IF EXISTS users CASCADE;

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    user_id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username  VARCHAR(25) NOT NULL UNIQUE,
    email     VARCHAR(255) NOT NULL UNIQUE,
    password  VARCHAR(255) NOT NULL
);

-- 2. PRODUCTS
CREATE TABLE IF NOT EXISTS products (
    product_id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         VARCHAR(25) NOT NULL UNIQUE,
    availability INT NOT NULL
);

-- 3. ORDERS
CREATE TABLE IF NOT EXISTS orders (
    order_id     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username     VARCHAR(25) REFERENCES users(username),
    order_date   TIMESTAMP DEFAULT NOW(),
    total_amount NUMERIC(10,2),
    status       VARCHAR(20) DEFAULT 'pending'
);

-- 4. CART (depends on orders + products)
CREATE TABLE IF NOT EXISTS cart (
    order_id   INT REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
    quantity   INT NOT NULL DEFAULT 1,
    PRIMARY KEY (order_id, product_id)
);

-- 5. EXCHANGELOG (depends on orders + users + products)
CREATE TABLE IF NOT EXISTS exchangelog (
    history_id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id     INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    username     VARCHAR(25) NOT NULL REFERENCES users(username),
    event_time   TIMESTAMP NOT NULL DEFAULT NOW(),
    product_id   INT NOT NULL REFERENCES products(product_id),
    product_name VARCHAR(255) NOT NULL,
    quantity     INT NOT NULL,
    change_type  VARCHAR(50) NOT NULL,
    note         TEXT
);

-- 6. TEST SELECT
SELECT
  o.order_id,
  o.username,
  p.name AS product_name,
  c.quantity
FROM orders o
JOIN cart c ON o.order_id = c.order_id
JOIN products p ON c.product_id = p.product_id;
