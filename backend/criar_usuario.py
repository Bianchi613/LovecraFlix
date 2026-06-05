"""Cria ou atualiza um usuário no banco. Rode uma vez pelo terminal."""
import sqlite3, getpass
from pathlib import Path
from passlib.context import CryptContext

DB     = Path(r"E:\Filmes\_organizer\acervo.db")
pwd    = CryptContext(schemes=["bcrypt"])
conn   = sqlite3.connect(DB)

conn.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL
    )
""")
conn.commit()

nome  = input("Nome: ").strip()
email = input("Email: ").strip()
senha = getpass.getpass("Senha: ")

hash_ = pwd.hash(senha)
conn.execute("""
    INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)
    ON CONFLICT(email) DO UPDATE SET nome=excluded.nome, senha_hash=excluded.senha_hash
""", (nome, email, hash_))
conn.commit()
conn.close()
print(f"\nUsuário '{nome}' criado/atualizado com sucesso.")
