from fastapi import FastAPI, HTTPException, Form, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from datetime import datetime, timedelta
import psycopg2, bcrypt, os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("postgresql://postgres:password@localhost:5432/postgres")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- DB ---
def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- HELPERS ---
def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=1))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_user_by_email(email: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, password FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    conn.close()
    return user

# --- SIGNUP (form-based) ---
@app.post("/signup")
def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    conn = get_db()
    cur = conn.cursor()

    # Check duplicates
    cur.execute("SELECT id FROM users WHERE email=%s OR username=%s", (email, username))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email or username already taken")

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cur.execute(
        "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id, username, email",
        (username, email, hashed_pw)
    )
    new_user = cur.fetchone()
    conn.commit()
    conn.close()
    return {"id": new_user[0], "username": new_user[1], "email": new_user[2]}

# --- LOGIN (still uses email + password) ---
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form_data.username)  # OAuth2 form uses "username" field
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id, username, email, password = user
    if not bcrypt.checkpw(form_data.password.encode("utf-8"), password.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": user_id, "username": username})
    return {"access_token": token, "token_type": "bearer"}

# --- PROTECTED ROUTE ---
@app.get("/me")
def me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"id": user[0], "username": user[1], "email": user[2]}
