"""
LovecraFlix — Setup inicial
Execute uma vez antes de iniciar o servidor pela primeira vez.
"""
import json, sqlite3, getpass, shutil, sys
from pathlib import Path

ROOT   = Path(__file__).parent.parent
CONFIG = ROOT / "config.json"

SCHEMA_FILMES = """
CREATE TABLE IF NOT EXISTS filmes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo          TEXT,
    titulo_pt       TEXT,
    titulo_original TEXT,
    ano             INTEGER,
    genero          TEXT,
    subgenero       TEXT,
    tipo            TEXT DEFAULT 'filme',
    formato         TEXT,
    idioma          TEXT,
    tem_legenda     INTEGER DEFAULT 0,
    arquivo_orig    TEXT,
    arquivo_novo    TEXT,
    status          TEXT,
    sinopse         TEXT,
    tmdb_id         TEXT,
    tmdb_url        TEXT,
    poster_local    TEXT
);
"""

SCHEMA_USUARIOS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    senha_hash  TEXT NOT NULL,
    avatar      TEXT DEFAULT 'octopus'
);
"""


def step(msg): print(f"\n  {msg}")
def ok(msg):   print(f"  ✓ {msg}")
def warn(msg): print(f"  ! {msg}")


def configurar():
    print("\n" + "="*55)
    print("  LovecraFlix — Configuração inicial")
    print("="*55)

    # Lê config existente
    cfg = {}
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    step("Onde estão seus filmes?")
    filmes_dir = input(f"  Pasta de filmes [{cfg.get('filmes_dir','')}]: ").strip()
    if not filmes_dir:
        filmes_dir = cfg.get("filmes_dir", "")

    step("Onde salvar o banco de dados?")
    default_db = str(Path(filmes_dir) / "_organizer" / "acervo.db") if filmes_dir else cfg.get("db_path", "")
    db_path = input(f"  Caminho do banco [{default_db}]: ").strip()
    if not db_path:
        db_path = default_db

    step("Porta do servidor (padrão 8000):")
    porta = input("  Porta [8000]: ").strip() or "8000"

    # Salva config
    cfg.update({"db_path": db_path, "filmes_dir": filmes_dir, "host": "127.0.0.1", "port": int(porta)})
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    ok(f"config.json salvo")

    return db_path


def criar_banco(db_path: str):
    step(f"Criando banco em: {db_path}")
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA_FILMES)
    conn.execute(SCHEMA_USUARIOS)
    conn.commit()
    conn.close()
    ok("Banco criado com schema completo")


def criar_usuario(db_path: str):
    step("Criar usuário administrador")
    nome  = input("  Seu nome: ").strip()
    email = input("  Email: ").strip()
    senha = getpass.getpass("  Senha (mínimo 6 caracteres): ")

    if len(senha) < 6:
        warn("Senha muito curta — usando 'lovecra' como padrão temporário.")
        senha = "lovecra"

    from passlib.context import CryptContext
    h = CryptContext(schemes=["bcrypt"]).hash(senha)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO usuarios (nome, email, senha_hash, avatar) VALUES (?,?,?,'octopus')",
        (nome, email, h)
    )
    conn.commit()
    conn.close()
    ok(f"Usuário '{nome}' criado")


def verificar_dependencias():
    step("Verificando dependências")
    ffmpeg = shutil.which("ffmpeg") or Path(r"C:\ffmpeg\bin\bin\ffmpeg.exe")
    if Path(str(ffmpeg)).exists():
        ok(f"ffmpeg encontrado: {ffmpeg}")
    else:
        warn("ffmpeg NÃO encontrado — transcodificação automática indisponível")
        warn("Instale com: winget install Gyan.FFmpeg")

    try:
        import fastapi, uvicorn, jose, passlib
        ok("Dependências Python OK")
    except ImportError as e:
        warn(f"Dependência faltando: {e}")
        warn("Execute: pip install -r requirements.txt")


if __name__ == "__main__":
    verificar_dependencias()
    db_path = configurar()
    criar_banco(db_path)
    criar_usuario(db_path)

    print("\n" + "="*55)
    print("  Setup concluído! Execute iniciar.bat para começar.")
    print("="*55 + "\n")
