DROP old versions (optional, for a clean reset)
DROP TABLE IF EXISTS passwords CASCADE;
DROP TABLE IF EXISTS exchangelog CASCADE;
DROP TABLE IF EXISTS cart CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY, -- Używamy SERIAL, aby pole było automatycznie inkrementowane i było kluczem głównym (PK)
    username VARCHAR(255) UNIQUE NOT NULL, -- Zakładamy, że nazwa użytkownika musi być unikalna
    email VARCHAR(255) UNIQUE NOT NULL -- Zakładamy, że email musi być unikalny
);

---

-- Utworzenie tabeli passwords (klucz obcy do users)
CREATE TABLE passwords (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE, -- Klucz główny jest jednocześnie kluczem obcym (FK) do tabeli users
    password VARCHAR(255) NOT NULL -- Miejsce na zaszyfrowany hasło
);

---

-- Utworzenie tabeli products
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY, -- Klucz główny (PK)
    name VARCHAR(255) NOT NULL,
    availability INTEGER NOT NULL DEFAULT 0, -- Domyślna dostępność to 0
    price NUMERIC(10, 2) NOT NULL, -- NUMERIC do precyzyjnych wartości pieniężnych (10 cyfr, 2 po przecinku)
    category VARCHAR(100)
);

---

-- Utworzenie tabeli orders (klucz obcy do users)
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY, -- Klucz główny (PK)
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE, -- Klucz obcy (FK) do tabeli users
    order_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Domyślnie bieżąca data i czas
    total_amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending'
);

---

-- Utworzenie tabeli cart (tabela łącząca wiele-do-wielu, używająca klucza kompozytowego)
CREATE TABLE cart (
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE, -- Klucz obcy (FK) do tabeli orders
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT, -- Klucz obcy (FK) do tabeli products
    quantity INTEGER NOT NULL CHECK (quantity > 0), -- Sprawdzamy, czy ilość jest większa niż 0
    PRIMARY KEY (order_id, product_id) -- Klucz kompozytowy (PK) składający się z obu kluczy obcych
);

