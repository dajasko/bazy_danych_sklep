from fastapi import FastAPI, HTTPException, Form, Depends, Path
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt, os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    availability: int = Field(..., ge=0)
    price: float = Field(..., gt=0)
    category: str = Field(..., max_length=100)

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    product_id: int
    
    class Config:
        from_attributes = True

class CartItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
class CartItemRemove(BaseModel):
    product_id: int = Field(..., gt=0)

os.chdir("C:/Users/admsl/auth_api")
load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET") or "TWOJ_SEKRETNY_KLUCZ_JWT"
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM") or "HS256"

DB_HOST = "localhost"
DB_NAME = "sklep"
DB_USER = "admsl"
DB_PASSWORD = "bajojajo1"
DB_PORT = 5432

print(f"Baza danych: {DB_NAME}, Użytkownik: {DB_USER}")

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        cursor_factory=RealDictCursor
    )
    return conn

def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=1))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_user_by_email(email: str):
    """Pobiera dane użytkownika i hasło, łącząc tabele users i passwords."""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            u.user_id, 
            u.username, 
            u.email, 
            p.password 
        FROM users u
        JOIN passwords p ON u.user_id = p.user_id
        WHERE u.email = %s;
    """, (email,))
    
    user = cur.fetchone()
    conn.close()
    return user

@app.post("/signup")
def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    if not username or not email or not password:
        raise HTTPException(
            status_code=400, 
            detail="Wszystkie pola (nazwa użytkownika, email i hasło) muszą być wypełnione."
        )
    
    if '@' not in email:
        raise HTTPException(
            status_code=400,
            detail="Podany adres email jest nieprawidłowy."
        )

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE email=%s OR username=%s", (email, username))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email lub nazwa użytkownika są już zajęte")

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    try:
        cur.execute(
            "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING user_id, username, email",
            (username, email)
        )
        new_user = cur.fetchone()
        user_id = new_user["user_id"]
        
        cur.execute(
            "INSERT INTO passwords (user_id, password) VALUES (%s, %s)",
            (user_id, hashed_pw)
        )
        
        conn.commit()
        
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd bazy danych podczas rejestracji: {e}")
        
    finally:
        conn.close()
        
    return {"user_id": new_user["user_id"], "username": new_user["username"], "email": new_user["email"]}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form_data.username) 
    
    if not user:
        raise HTTPException(status_code=401, detail="Nieprawidłowe dane logowania (użytkownik)")

    if not bcrypt.checkpw(form_data.password.encode("utf-8"), user["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Nieprawidłowe dane logowania (hasło)")

    token = create_access_token({"user_id": user["user_id"], "username": user["username"]})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
def me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
             raise JWTError
             
    except JWTError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy token (brak dostępu)")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, email FROM users WHERE user_id=%s", (user_id,))
    user = cur.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")

    return {"user_id": user["user_id"], "username": user["username"], "email": user["email"]}

def get_current_user_id(token: str = Depends(oauth2_scheme)):
    """Pobiera ID użytkownika z tokena. Używana jako dependencja w zabezpieczonych endpointach."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
             raise JWTError
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy token (brak dostępu)")


@app.post("/products", response_model=Product)
def create_product(product_data: ProductCreate, user_id: int = Depends(get_current_user_id)):
    """Dodaje nowy produkt do bazy. (Na razie: każdy zalogowany może dodać)."""
        
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO products (name, availability, price, category)
            VALUES (%s, %s, %s, %s)
            RETURNING product_id, name, availability, price, category;
            """,
            (product_data.name, product_data.availability, product_data.price, product_data.category)
        )
        new_product = cur.fetchone()
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd bazy danych: {e}")
    finally:
        conn.close()
        
    return new_product

@app.get("/products", response_model=list[Product])
def read_products():
    """Pobiera listę wszystkich dostępnych produktów."""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT product_id, name, availability, price, category FROM products WHERE availability > 0;")
    products = cur.fetchall()
    conn.close()
    
    return products
@app.post("/cart/add")
def add_to_cart(item: CartItemCreate, user_id: int = Depends(get_current_user_id)):
    """Dodaje produkt do aktywnego koszyka użytkownika."""
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT order_id FROM orders WHERE user_id = %s AND status = 'Pending';",
            (user_id,)
        )
        active_order = cur.fetchone()

        if active_order:
            order_id = active_order["order_id"]
        else:
            cur.execute(
                """
                INSERT INTO orders (user_id, total_amount, status)
                VALUES (%s, 0.00, 'Pending') 
                RETURNING order_id;
                """,
                (user_id,)
            )
            order_id = cur.fetchone()["order_id"]
            print(f"Utworzono nowe zamówienie/koszyk: {order_id}")

        cur.execute("SELECT price, availability FROM products WHERE product_id = %s;", (item.product_id,))
        product_info = cur.fetchone()
        
        if not product_info:
            raise HTTPException(status_code=404, detail="Produkt nie znaleziony.")
        
        if product_info["availability"] < item.quantity:
            raise HTTPException(status_code=400, detail="Brak wystarczającej liczby produktów w magazynie.")

        product_price = product_info["price"]

        cur.execute(
            """
            INSERT INTO cart (order_id, product_id, quantity)
            VALUES (%s, %s, %s)
            ON CONFLICT (order_id, product_id)
            DO UPDATE SET quantity = cart.quantity + EXCLUDED.quantity
            RETURNING quantity;
            """,
            (order_id, item.product_id, item.quantity)
        )
        
        cur.execute(
            """
            UPDATE orders
            SET total_amount = (
                SELECT COALESCE(SUM(c.quantity * p.price), 0)
                FROM cart c
                JOIN products p ON c.product_id = p.product_id
                WHERE c.order_id = %s
            )
            WHERE order_id = %s;
            """,
            (order_id, order_id)
        )

        conn.commit()

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd bazy danych: {e}")
    finally:
        conn.close()

    return {"message": "Produkt dodany do koszyka", "order_id": order_id}
@app.post("/checkout")
def checkout(user_id: int = Depends(get_current_user_id)):
    """Finalizuje aktywne zamówienie użytkownika i zmienia jego status na 'Completed'."""
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT order_id, total_amount FROM orders WHERE user_id = %s AND status = 'Pending';",
            (user_id,)
        )
        active_order = cur.fetchone()

        if not active_order:
            raise HTTPException(status_code=404, detail="Brak aktywnego koszyka do sfinalizowania.")
            
        order_id = active_order["order_id"]
        total_amount = active_order["total_amount"]
        
        cur.execute(
            "UPDATE orders SET status = 'Paid', order_date = CURRENT_TIMESTAMP WHERE order_id = %s;",
            (order_id,)
        )
        
        cur.execute("""
            UPDATE products p
            SET availability = p.availability - c.quantity
            FROM cart c
            WHERE c.order_id = %s AND p.product_id = c.product_id;
        """, (order_id,))

        conn.commit()

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd bazy danych podczas finalizacji: {e}")
    finally:
        conn.close()

    return {
        "message": "Zamówienie opłacone.", 
        "order_id": order_id, 
        "total_amount": float(total_amount)
    }
@app.post("/orders/{order_id}/ship")
def ship_order(
    order_id: int = Path(..., description="ID zamówienia, które ma zostać wysłane"),
    user_id: int = Depends(get_current_user_id)
):
    """
    Zmienia status opłaconego zamówienia na 'Shipped' (Wysłane).
    Wymaga podania ID zamówienia.
    """
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT status FROM orders WHERE order_id = %s;",
            (order_id,)
        )
        order = cur.fetchone()

        if not order:
            raise HTTPException(status_code=404, detail=f"Zamówienie o ID {order_id} nie znalezione.")
        
        if order["status"] != 'Paid':
            raise HTTPException(status_code=400, detail=f"Nie można wysłać zamówienia. Aktualny status to '{order['status']}', oczekiwano 'Paid'.")

        cur.execute(
            "UPDATE orders SET status = 'Shipped' WHERE order_id = %s;",
            (order_id,)
        )

        conn.commit()

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd bazy danych podczas wysyłki: {e}")
    finally:
        conn.close()

    return {"message": f"Status zamówienia {order_id} zaktualizowany na 'Shipped'.", "order_id": order_id}
@app.post("/cart/remove")
def remove_from_cart(item: CartItemRemove, user_id: int = Depends(get_current_user_id)):
    """Usuwa określoną pozycję z aktywnego koszyka użytkownika."""
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT order_id FROM orders WHERE user_id = %s AND status = 'Pending';",
            (user_id,)
        )
        active_order = cur.fetchone()

        if not active_order:
            raise HTTPException(status_code=404, detail="Brak aktywnego koszyka.")

        order_id = active_order["order_id"]

        cur.execute(
            "DELETE FROM cart WHERE order_id = %s AND product_id = %s RETURNING product_id;",
            (order_id, item.product_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Produkt nie znaleziony w koszyku.")

        cur.execute(
            """
            UPDATE orders
            SET total_amount = (
                SELECT COALESCE(SUM(c.quantity * p.price), 0)
                FROM cart c
                JOIN products p ON c.product_id = p.product_id
                WHERE c.order_id = %s
            )
            WHERE order_id = %s;
            """,
            (order_id, order_id)
        )

        conn.commit()

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd bazy danych: {e}")
    finally:
        conn.close()

    return {"message": "Produkt usunięty z koszyka, suma zaktualizowana.", "order_id": order_id}

@app.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int = Path(..., description="ID zamówienia do anulowania"),
    user_id: int = Depends(get_current_user_id)
):
    """
    Anuluje zamówienie, zmieniając jego status na 'Cancelled' i przywracając stan magazynowy,
    jeśli zamówienie było już opłacone/wysłane.
    """
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT status, user_id FROM orders WHERE order_id = %s;",
            (order_id,)
        )
        order = cur.fetchone()

        if not order:
            raise HTTPException(status_code=404, detail=f"Zamówienie o ID {order_id} nie znalezione.")
        
        if order["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Brak uprawnień do anulowania tego zamówienia.")

        original_status = order["status"]
        
        if original_status in ['Cancelled', 'Returned', 'Shipped']:
            raise HTTPException(status_code=400, detail=f"Nie można anulować zamówienia w statusie: {original_status}.")
        
        if original_status in ['Paid', 'Completed']:
            cur.execute("""
                UPDATE products p
                SET availability = p.availability + c.quantity
                FROM cart c
                WHERE c.order_id = %s AND p.product_id = c.product_id;
            """, (order_id,))
            
            new_status = 'Cancelled'
            cur.execute(
                "UPDATE orders SET status = %s WHERE order_id = %s;",
                (new_status, order_id)
            )
            
        elif original_status == 'Pending':

            new_status = 'Cancelled'
            cur.execute(
                "UPDATE orders SET status = %s WHERE order_id = %s;",
                (new_status, order_id)
            )
            
        conn.commit()

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd bazy danych podczas anulowania: {e}")
    finally:
        conn.close()

    return {"message": f"Zamówienie {order_id} zostało anulowane. Status: {new_status}", "order_id": order_id}
