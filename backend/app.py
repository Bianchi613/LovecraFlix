"""LovecraFlix - Servidor local"""
import asyncio, json, random, re, sqlite3
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
import uvicorn

_ROOT      = Path(__file__).parent.parent
_CFG_FILE  = _ROOT / "config.json"
_CFG       = json.loads(_CFG_FILE.read_text(encoding="utf-8")) if _CFG_FILE.exists() else {}

DB_PATH    = Path(_CFG.get("db_path", _ROOT / "acervo.db"))
STATIC_DIR = _ROOT / "frontend"
_HOST      = _CFG.get("host", "127.0.0.1")
_PORT      = int(_CFG.get("port", 8000))

JWT_SECRET = "lovecraflix-local-secret-2024"
JWT_ALG    = "HS256"
pwd_ctx    = CryptContext(schemes=["bcrypt"])
bearer     = HTTPBearer(auto_error=False)

app = FastAPI(title="LovecraFlix")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Garante tabela de usuários
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            avatar TEXT DEFAULT 'octopus'
        )
    """)
    # Migração: adiciona coluna parte se não existir
    colunas = [r[1] for r in conn.execute("PRAGMA table_info(filmes)").fetchall()]
    if "parte" not in colunas:
        conn.execute("ALTER TABLE filmes ADD COLUMN parte INTEGER DEFAULT NULL")
        conn.commit()

    # Migração: adiciona coluna poster_hd se não existir
    if "poster_hd" not in colunas:
        conn.execute("ALTER TABLE filmes ADD COLUMN poster_hd TEXT")
        conn.commit()

    # Migração: adiciona coluna backdrop_hd se não existir
    if "backdrop_hd" not in colunas:
        conn.execute("ALTER TABLE filmes ADD COLUMN backdrop_hd TEXT")
        conn.commit()

    # Migração: adiciona coluna tmdb_keywords se não existir
    if "tmdb_keywords" not in colunas:
        conn.execute("ALTER TABLE filmes ADD COLUMN tmdb_keywords TEXT")
        conn.commit()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            filme_id   INTEGER NOT NULL,
            nota       INTEGER NOT NULL CHECK(nota BETWEEN 1 AND 5),
            criado_em  TEXT DEFAULT (datetime('now')),
            UNIQUE(usuario_id, filme_id)
        )
    """)
    conn.commit()
    return conn


def make_token(email: str) -> str:
    return jwt.encode({"sub": email}, JWT_SECRET, algorithm=JWT_ALG)


def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(401, "Não autenticado")
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise HTTPException(401, "Token inválido")
    return credentials.credentials


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.get("/home", response_class=HTMLResponse)
def home_page():
    return FileResponse(str(STATIC_DIR / "home.html"))

@app.get("/api/home-posters")
def home_posters():
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT poster_local FROM filmes
        WHERE poster_local IS NOT NULL
          AND poster_local NOT LIKE '%_organizer%'
        ORDER BY RANDOM() LIMIT 60
    """).fetchall()
    conn.close()
    return [r["poster_local"] for r in rows if Path(r["poster_local"]).exists()]


@app.get("/api/destaques")
def destaques():
    conn = get_db()
    # Horror Cósmico primeiro, depois os demais aleatórios
    horror = conn.execute("""
        SELECT id, titulo_pt, ano, genero, subgenero, sinopse, poster_local, poster_hd, backdrop_hd
        FROM filmes
        WHERE subgenero = 'Horror Cosmico'
          AND poster_local IS NOT NULL
          AND poster_local NOT LIKE '%_organizer%'
          AND arquivo_novo IS NOT NULL
        GROUP BY titulo_pt
        ORDER BY RANDOM() LIMIT 3
    """).fetchall()
    outros = conn.execute("""
        SELECT id, titulo_pt, ano, genero, subgenero, sinopse, poster_local, poster_hd, backdrop_hd
        FROM filmes
        WHERE (subgenero IS NULL OR subgenero != 'Horror Cosmico')
          AND poster_local IS NOT NULL
          AND poster_local NOT LIKE '%_organizer%'
          AND arquivo_novo IS NOT NULL
          AND tipo NOT IN ('serie','documentario')
        GROUP BY titulo_pt
        ORDER BY RANDOM() LIMIT 20
    """).fetchall()
    conn.close()
    resultado = list(horror) + list(outros)
    random.shuffle(resultado)
    return [dict(r) for r in resultado if Path(r["poster_local"]).exists()]

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return FileResponse(str(STATIC_DIR / "login.html"))

@app.get("/cadastro", response_class=HTMLResponse)
def cadastro_page():
    return FileResponse(str(STATIC_DIR / "cadastro.html"))


@app.post("/auth/cadastro")
def auth_cadastro(dados: dict):
    nome  = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip()
    senha = dados.get("senha") or ""
    if not nome or not email or len(senha) < 6:
        raise HTTPException(400, "Preencha todos os campos (senha mínimo 6 caracteres)")
    conn = get_db()
    if conn.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone():
        conn.close()
        raise HTTPException(409, "Email já cadastrado")
    conn.execute("INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
                 (nome, email, pwd_ctx.hash(senha)))
    conn.commit()
    conn.close()
    return {"token": make_token(email), "nome": nome}


@app.post("/auth/login")
def auth_login(dados: dict):
    conn = get_db()
    row  = conn.execute("SELECT * FROM usuarios WHERE email = ?", (dados.get("email",""),)).fetchone()
    conn.close()
    if not row or not pwd_ctx.verify(dados.get("senha",""), row["senha_hash"]):
        raise HTTPException(401, "Email ou senha incorretos")
    return {"token": make_token(row["email"]), "nome": row["nome"]}


@app.get("/auth/me")
def auth_me(token: str = Depends(verificar_token)):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    conn = get_db()
    row = conn.execute("SELECT id, nome, email, avatar FROM usuarios WHERE email = ?",
                       (payload["sub"],)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    return dict(row)


@app.post("/api/avaliar")
def avaliar(dados: dict, token: str = Depends(verificar_token)):
    nota = dados.get("nota")
    filme_id = dados.get("filme_id")
    if not isinstance(nota, int) or nota < 1 or nota > 5:
        raise HTTPException(400, "Nota deve ser entre 1 e 5")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    conn = get_db()
    user = conn.execute("SELECT id FROM usuarios WHERE email=?", (payload["sub"],)).fetchone()
    if not user:
        conn.close(); raise HTTPException(404)
    conn.execute("""
        INSERT INTO avaliacoes (usuario_id, filme_id, nota) VALUES (?,?,?)
        ON CONFLICT(usuario_id, filme_id) DO UPDATE SET nota=excluded.nota, criado_em=datetime('now')
    """, (user["id"], filme_id, nota))
    conn.commit()
    conn.close()
    return {"ok": True, "nota": nota}


@app.get("/api/avaliacao")
def get_avaliacao(filme_id: int, token: str = Depends(verificar_token)):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    conn = get_db()
    user = conn.execute("SELECT id FROM usuarios WHERE email=?", (payload["sub"],)).fetchone()
    if not user:
        conn.close(); return {"nota": 0}
    row = conn.execute(
        "SELECT nota FROM avaliacoes WHERE usuario_id=? AND filme_id=?",
        (user["id"], filme_id)
    ).fetchone()
    conn.close()
    return {"nota": row["nota"] if row else 0}


@app.get("/api/avaliacoes/media")
def media_avaliacao(filme_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT AVG(nota) as media, COUNT(*) as total FROM avaliacoes WHERE filme_id=?",
        (filme_id,)
    ).fetchone()
    conn.close()
    return {"media": round(row["media"], 1) if row["media"] else 0, "total": row["total"]}


@app.put("/api/perfil")
def atualizar_perfil(dados: dict, token: str = Depends(verificar_token)):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    conn    = get_db()
    if "nome" in dados:
        conn.execute("UPDATE usuarios SET nome = ? WHERE email = ?", (dados["nome"], payload["sub"]))
    if "avatar" in dados:
        conn.execute("UPDATE usuarios SET avatar = ? WHERE email = ?", (dados["avatar"], payload["sub"]))
    conn.commit()
    row = conn.execute("SELECT id, nome, email, avatar FROM usuarios WHERE email = ?",
                       (payload["sub"],)).fetchone()
    conn.close()
    return dict(row)


@app.get("/perfil", response_class=HTMLResponse)
def perfil_page():
    return FileResponse(str(STATIC_DIR / "perfil.html"))


# ── Páginas ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/player", response_class=HTMLResponse)
def player():
    return FileResponse(str(STATIC_DIR / "player.html"))

@app.get("/series", response_class=HTMLResponse)
def serie_page():
    return FileResponse(str(STATIC_DIR / "series.html"))

@app.get("/filme", response_class=HTMLResponse)
def filme_page():
    return FileResponse(str(STATIC_DIR / "filme.html"))


# ── API ────────────────────────────────────────────────────────────────────

@app.get("/api/series")
def listar_series():
    conn = get_db()
    rows = conn.execute("""
        SELECT id, titulo_pt, genero, ano, sinopse, poster_local, arquivo_novo
        FROM filmes
        WHERE tipo = 'serie' AND arquivo_novo IS NOT NULL
    """).fetchall()
    conn.close()

    # Agrupa pela pasta pai do arquivo
    grupos: dict[str, dict] = {}
    for r in rows:
        arq  = r["arquivo_novo"]
        pasta = Path(arq).parent
        chave = str(pasta)
        nome_pasta = pasta.name

        if chave not in grupos:
            grupos[chave] = {
                "pasta": chave,
                "nome_pasta": nome_pasta,
                "titulo_pt": r["titulo_pt"],
                "genero": r["genero"],
                "ano": r["ano"],
                "sinopse": r["sinopse"],
                "poster_local": r["poster_local"],
                "titulos": set(),
                "total_eps": 0,
            }
        grupos[chave]["titulos"].add(r["titulo_pt"])
        grupos[chave]["total_eps"] += 1
        if not grupos[chave]["poster_local"] and r["poster_local"]:
            grupos[chave]["poster_local"] = r["poster_local"]

    result = []
    for g in grupos.values():
        # Se todos os eps têm o mesmo titulo_pt, usa ele; senão usa nome da pasta
        titulo = g["titulo_pt"] if len(g["titulos"]) == 1 else g["nome_pasta"]
        result.append({
            "titulo_pt": titulo,
            "pasta": g["pasta"],
            "genero": g["genero"],
            "ano": g["ano"],
            "sinopse": g["sinopse"],
            "poster_local": g["poster_local"],
            "total_eps": len(set(r["arquivo_novo"] for r in rows if str(Path(r["arquivo_novo"]).parent) == g["pasta"])),
        })

    result.sort(key=lambda x: x["titulo_pt"])
    return result


@app.get("/api/series/episodios")
def episodios_serie(pasta: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT id, titulo_pt, arquivo_novo, idioma, tem_legenda, poster_local
        FROM filmes
        WHERE tipo = 'serie' AND arquivo_novo LIKE ? AND arquivo_novo IS NOT NULL
        ORDER BY arquivo_novo
    """, (pasta + "%",)).fetchall()
    conn.close()

    def parse_ep(path: str):
        fname = path.replace("\\", "/").split("/")[-1]
        m = re.search(r'[Ss](\d+)[Ee](\d+)', fname)
        if m:
            return int(m.group(1)), int(m.group(2))
        m = re.search(r'\b(\d)(\d{2})\b', fname)
        if m:
            return int(m.group(1)), int(m.group(2))
        m = re.match(r'^(\d+)\s*-', fname)
        if m:
            return 1, int(m.group(1))
        return 0, 0

    seen = set()
    episodios = []
    for r in rows:
        arq = r["arquivo_novo"]
        if arq in seen:
            continue
        seen.add(arq)
        ep = dict(r)
        ep["temporada"], ep["episodio"] = parse_ep(arq)
        episodios.append(ep)

    episodios.sort(key=lambda e: (e["temporada"], e["episodio"]))
    return episodios


@app.get("/api/colecoes")
def listar_colecoes():
    conn = get_db()
    rows = conn.execute("""
        SELECT titulo_pt, poster_local, sinopse, genero, ano
        FROM filmes
        WHERE tipo = 'documentario' AND arquivo_novo IS NOT NULL
    """).fetchall()
    conn.close()

    grupos: dict[str, dict] = {}
    for r in rows:
        titulo = r["titulo_pt"] or ""
        prefixo = titulo.split(":")[0].strip() if ":" in titulo else titulo
        if prefixo not in grupos:
            grupos[prefixo] = {
                "colecao": prefixo,
                "poster_local": r["poster_local"],
                "sinopse": r["sinopse"],
                "genero": r["genero"],
                "total": 0,
            }
        grupos[prefixo]["total"] += 1
        if not grupos[prefixo]["poster_local"] and r["poster_local"]:
            grupos[prefixo]["poster_local"] = r["poster_local"]

    return sorted(grupos.values(), key=lambda x: x["colecao"])


@app.get("/api/colecoes/episodios")
def episodios_colecao(colecao: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT id, titulo_pt, arquivo_novo, idioma, tem_legenda, poster_local
        FROM filmes
        WHERE tipo = 'documentario' AND arquivo_novo IS NOT NULL
          AND (titulo_pt LIKE ? OR titulo_pt = ?)
        ORDER BY titulo_pt
    """, (colecao + ":%", colecao)).fetchall()
    conn.close()
    seen = set()
    result = []
    for r in rows:
        if r["arquivo_novo"] not in seen:
            seen.add(r["arquivo_novo"])
            result.append(dict(r))
    return result


@app.get("/documentario", response_class=HTMLResponse)
def documentario_page():
    return FileResponse(str(STATIC_DIR / "documentario.html"))


@app.get("/api/generos")
def generos(tipo: str = ""):
    conn = get_db()
    if tipo:
        rows = conn.execute("""
            SELECT genero, COUNT(DISTINCT titulo_pt) as total
            FROM filmes
            WHERE tipo = ? AND genero IS NOT NULL
            GROUP BY genero ORDER BY total DESC
        """, (tipo,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT genero, COUNT(DISTINCT titulo_pt) as total
            FROM filmes
            WHERE genero IS NOT NULL
            GROUP BY genero ORDER BY total DESC
        """).fetchall()

    result = [dict(r) for r in rows]

    # Adiciona Horror Cósmico filtrado pelo mesmo tipo
    if tipo:
        horror_row = conn.execute("""
            SELECT COUNT(DISTINCT titulo_pt) as total FROM filmes
            WHERE subgenero = 'Horror Cosmico' AND tipo = ? AND arquivo_novo IS NOT NULL
        """, (tipo,)).fetchone()
    else:
        horror_row = conn.execute("""
            SELECT COUNT(DISTINCT titulo_pt) as total FROM filmes
            WHERE subgenero = 'Horror Cosmico' AND arquivo_novo IS NOT NULL
        """).fetchone()
    conn.close()

    if horror_row and horror_row["total"] > 0:
        result.append({"genero": "Horror Cosmico", "total": horror_row["total"], "is_subgenero": True})

    return result


@app.get("/api/filmes")
def listar_filmes(genero: str = "", busca: str = "", tipo: str = ""):
    conn = get_db()
    sql  = """
        SELECT id, titulo_pt, titulo_original, ano, genero, subgenero,
               tipo, idioma, tem_legenda, sinopse,
               CASE WHEN poster_local NOT LIKE '%_organizer%' THEN poster_local ELSE NULL END as poster_local,
               arquivo_novo, tmdb_url
        FROM filmes
        WHERE arquivo_novo IS NOT NULL
          AND tipo NOT IN ('serie', 'documentario')
    """
    params = []
    if genero == "Horror Cosmico":
        sql += " AND subgenero = 'Horror Cosmico'"
    elif genero:
        sql += " AND genero = ?"
        params.append(genero)
    if busca:
        sql += " AND (titulo_pt LIKE ? OR titulo_original LIKE ?)"
        params += [f"%{busca}%", f"%{busca}%"]
    if tipo:
        sql += " AND tipo = ?"
        params.append(tipo)
    sql += " GROUP BY arquivo_novo ORDER BY titulo_pt"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


VLC_PATH = Path(r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe")

@app.get("/api/open-vlc")
def open_vlc(path: str):
    import subprocess
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    vlc = VLC_PATH if VLC_PATH.exists() else Path("vlc")
    subprocess.Popen([str(vlc), str(p)], creationflags=0x00000008)  # DETACHED_PROCESS
    return {"ok": True}


@app.get("/api/filmes/versoes")
def versoes_filme(titulo: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT id, titulo_pt, titulo_original, ano, genero, idioma,
               tem_legenda, sinopse, poster_local, arquivo_novo, tmdb_url, subgenero, parte
        FROM filmes
        WHERE titulo_pt = ? AND arquivo_novo IS NOT NULL AND tipo != 'serie'
        ORDER BY COALESCE(parte, 0), idioma, arquivo_novo
    """, (titulo,)).fetchall()
    conn.close()
    seen = set()
    result = []
    for r in rows:
        if r["arquivo_novo"] not in seen:
            seen.add(r["arquivo_novo"])
            result.append(dict(r))
    return result


@app.put("/api/filmes/{id}/parte")
def set_parte(id: int, dados: dict, token: str = Depends(verificar_token)):
    parte = dados.get("parte")  # None para limpar, 1/2/3... para marcar
    conn = get_db()
    conn.execute("UPDATE filmes SET parte = ? WHERE id = ?", (parte, id))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/filmes/nav")
def nav_filme(id: int):
    conn = get_db()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM filmes WHERE arquivo_novo IS NOT NULL ORDER BY titulo_pt"
    ).fetchall()]
    conn.close()
    try:
        idx = ids.index(id)
    except ValueError:
        return {"prev": None, "next": None}
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx < len(ids) - 1 else None

    conn = get_db()
    def titulo(fid):
        if not fid: return None
        r = conn.execute("SELECT titulo_pt FROM filmes WHERE id=?", (fid,)).fetchone()
        return r[0] if r else None
    result = {"prev": prev_id, "prev_titulo": titulo(prev_id),
              "next": next_id, "next_titulo": titulo(next_id)}
    conn.close()
    return result


FFPROBE = r"C:\ffmpeg\bin\bin\ffprobe.exe"
BROWSER_VIDEO = {"h264", "vp8", "vp9", "av1"}
BROWSER_AUDIO = {"aac", "mp3", "vorbis", "opus", "flac", "pcm_s16le", "pcm_s24le", "pcm_f32le"}

def precisa_transcodificar(arquivo: str) -> bool:
    import subprocess, json
    try:
        out = subprocess.check_output([
            FFPROBE, "-v", "quiet",
            "-show_entries", "stream=codec_name,codec_type",
            "-of", "json", arquivo
        ], timeout=5)
        streams = json.loads(out).get("streams", [])
        for s in streams:
            codec = s.get("codec_name", "").lower()
            tipo  = s.get("codec_type", "")
            if tipo == "video" and codec not in BROWSER_VIDEO:
                return True
            if tipo == "audio" and codec not in BROWSER_AUDIO:
                return True
        return False
    except Exception:
        return False


@app.get("/api/filmes/{id}")
def detalhe_filme(id: int):
    conn = get_db()
    row  = conn.execute("SELECT * FROM filmes WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Não encontrado")
    data = dict(row)
    if data.get("arquivo_novo"):
        data["needs_transcode"] = precisa_transcodificar(data["arquivo_novo"])
    return data


@app.get("/api/indicacoes")
def indicacoes(token: str = Depends(verificar_token)):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    conn = get_db()

    user = conn.execute("SELECT id FROM usuarios WHERE email=?", (payload["sub"],)).fetchone()
    uid  = user["id"] if user else None

    generos_fav = []
    if uid:
        rows = conn.execute("""
            SELECT f.genero, AVG(a.nota) as media
            FROM avaliacoes a JOIN filmes f ON f.id = a.filme_id
            WHERE a.usuario_id = ? AND a.nota >= 4
            GROUP BY f.genero ORDER BY media DESC LIMIT 3
        """, (uid,)).fetchall()
        generos_fav = [r["genero"] for r in rows if r["genero"]]

    genero_sql = ",".join(f"'{g}'" for g in generos_fav)

    base_sql = """
        SELECT DISTINCT f.id, f.titulo_pt, f.titulo, f.genero, f.ano, f.tipo,
               f.poster_local, f.poster_hd,
               COALESCE(a.nota, 0) as minha_nota,
               (SELECT AVG(a2.nota) FROM avaliacoes a2 JOIN filmes f2 ON f2.id = a2.filme_id
                WHERE f2.titulo_pt = f.titulo_pt) as media_geral
        FROM filmes f
        LEFT JOIN avaliacoes a ON a.filme_id = f.id AND a.usuario_id = ?
        WHERE f.arquivo_novo IS NOT NULL AND f.tipo NOT IN ('serie','documentario')
          AND (a.nota IS NULL OR a.nota >= 3)
          {filtro_genero}
        GROUP BY f.titulo_pt
        ORDER BY COALESCE(media_geral, 0) DESC, f.ano DESC LIMIT {limite}
    """

    resultado = []
    if generos_fav:
        resultado = list(conn.execute(
            base_sql.format(filtro_genero=f"AND f.genero IN ({genero_sql})", limite=10),
            (uid or 0,)
        ).fetchall())

    if len(resultado) < 10:
        ja_ids = tuple(r["id"] for r in resultado) or (0,)
        placeholders = ",".join("?" * len(ja_ids))
        extra = conn.execute(
            base_sql.format(filtro_genero=f"AND f.id NOT IN ({placeholders})", limite=10 - len(resultado)),
            (uid or 0, *ja_ids)
        ).fetchall()
        resultado += list(extra)

    conn.close()
    return [dict(r) for r in resultado]


@app.get("/api/recomendacoes")
def recomendacoes(id: int, token: str = Depends(verificar_token)):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    conn = get_db()

    user = conn.execute("SELECT id FROM usuarios WHERE email=?", (payload["sub"],)).fetchone()
    uid  = user["id"] if user else None

    origem = conn.execute("SELECT genero, tipo FROM filmes WHERE id=?", (id,)).fetchone()
    genero = origem["genero"] if origem else None

    # Gêneros que o usuário gosta (nota >= 4)
    generos_fav = []
    if uid:
        rows = conn.execute("""
            SELECT f.genero, AVG(a.nota) as media
            FROM avaliacoes a JOIN filmes f ON f.id = a.filme_id
            WHERE a.usuario_id = ? AND a.nota >= 4
            GROUP BY f.genero ORDER BY media DESC LIMIT 3
        """, (uid,)).fetchall()
        generos_fav = [r["genero"] for r in rows if r["genero"]]

    # Usa gêneros favoritos ou o gênero do conteúdo atual
    generos_busca = generos_fav if generos_fav else ([genero] if genero else [])
    genero_sql    = ",".join(f"'{g}'" for g in generos_busca) if generos_busca else "''"

    filmes = conn.execute(f"""
        SELECT DISTINCT f.id, f.titulo_pt, f.genero, f.ano, f.tipo,
               CASE WHEN f.poster_local NOT LIKE '%_organizer%' THEN f.poster_local ELSE NULL END as poster_local,
               COALESCE(a.nota, 0) as minha_nota
        FROM filmes f
        LEFT JOIN avaliacoes a ON a.filme_id = f.id AND a.usuario_id = ?
        WHERE f.arquivo_novo IS NOT NULL AND f.tipo NOT IN ('serie','documentario')
          AND f.id != ?
          AND (f.genero IN ({genero_sql}) OR '{genero}' IS NULL)
          AND (a.nota IS NULL OR a.nota >= 3)
        GROUP BY f.titulo_pt
        ORDER BY a.nota DESC NULLS LAST, RANDOM() LIMIT 5
    """, (uid or 0, id)).fetchall()

    series = conn.execute("""
        SELECT titulo_pt, genero, poster_local, MIN(id) as id
        FROM filmes
        WHERE tipo = 'serie' AND arquivo_novo IS NOT NULL
          AND poster_local IS NOT NULL AND poster_local NOT LIKE '%_organizer%'
        GROUP BY titulo_pt ORDER BY RANDOM() LIMIT 2
    """).fetchall()
    conn.close()

    result = []
    for f in filmes:
        d = dict(f)
        d["url"] = f"/player?id={d['id']}"
        result.append(d)
    for s in series:
        d = dict(s)
        d["url"] = f"/series?nome={d['titulo_pt']}"
        result.append(d)
    return result


# ── Mídia ──────────────────────────────────────────────────────────────────

@app.get("/poster")
def serve_poster(path: str):
    p = Path(path)
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(str(p), media_type="image/jpeg")


@app.get("/subtitle")
def serve_subtitle(path: str):
    """Converte SRT para WebVTT on-the-fly."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(404)
    srt = p.read_text(encoding="utf-8", errors="replace")
    # SRT -> WebVTT: troca vírgula por ponto nos timestamps
    vtt = "WEBVTT\n\n" + re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", srt)
    return HTMLResponse(content=vtt, media_type="text/vtt")


@app.get("/video")
async def stream_video(request: Request, path: str):
    p = Path(path)
    if not p.exists():
        raise HTTPException(404)

    file_size = p.stat().st_size
    range_header = request.headers.get("range")

    # Tipo MIME
    ext = p.suffix.lower()
    mime = {"mp4": "video/mp4", "mkv": "video/x-matroska",
            "avi": "video/x-msvideo", "m4v": "video/mp4"}.get(ext.lstrip("."), "video/mp4")

    if not range_header:
        return StreamingResponse(
            _file_iter(p, 0, file_size - 1),
            media_type=mime,
            headers={"Content-Length": str(file_size),
                     "Accept-Ranges": "bytes"}
        )

    # Parse Range
    m = re.match(r"bytes=(\d+)-(\d*)", range_header)
    start = int(m.group(1))
    end   = int(m.group(2)) if m.group(2) else file_size - 1
    end   = min(end, file_size - 1)
    length = end - start + 1

    return StreamingResponse(
        _file_iter(p, start, end),
        status_code=206,
        media_type=mime,
        headers={
            "Content-Range":  f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
            "Accept-Ranges":  "bytes",
        }
    )


@app.get("/transcode")
async def transcode_video(path: str, audio_track: int = 0):
    import shutil
    p = Path(path)
    if not p.exists():
        raise HTTPException(404)

    ffmpeg_bin = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\bin\ffmpeg.exe"
    if not Path(ffmpeg_bin).exists():
        from fastapi.responses import RedirectResponse
        from urllib.parse import quote
        return RedirectResponse(f"/video?path={quote(path, safe='')}")

    # Detectar codecs para só re-encodar o necessário
    import subprocess as _sp, json as _json
    try:
        _probe = _sp.check_output([
            FFPROBE, "-v", "quiet",
            "-show_entries", "stream=codec_name,codec_type",
            "-of", "json", str(p)
        ], timeout=5)
        _streams = _json.loads(_probe).get("streams", [])
    except Exception:
        _streams = []

    _vcodec = next((s["codec_name"] for s in _streams if s.get("codec_type") == "video"), "")
    _acodec = next((s["codec_name"] for s in _streams if s.get("codec_type") == "audio"), "")

    vc = "copy" if _vcodec in BROWSER_VIDEO else "libx264"
    ac = "copy" if _acodec in BROWSER_AUDIO else "aac"

    extra_v = [] if vc == "copy" else ["-preset", "ultrafast", "-profile:v", "main", "-pix_fmt", "yuv420p"]
    extra_a = [] if ac == "copy" else ["-b:a", "192k"]

    cmd = [
        ffmpeg_bin, "-i", str(p),
        "-map", "0:v:0", "-map", f"0:a:{audio_track}",
        "-c:v", vc, *extra_v,
        "-c:a", ac, *extra_a,
        "-f", "mp4", "-movflags", "frag_keyframe+empty_moov",
        "-loglevel", "error",
        "pipe:1"
    ]

    async def stream():
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            while True:
                chunk = await proc.stdout.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            try:
                proc.kill()
            except Exception:
                pass

    return StreamingResponse(stream(), media_type="video/mp4")


async def _file_iter(path: Path, start: int, end: int, chunk: int = 1024 * 1024):
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining:
            data = f.read(min(chunk, remaining))
            if not data:
                break
            yield data
            remaining -= len(data)


if __name__ == "__main__":
    print("\n🐙  LovecraFlix  →  http://localhost:8000\n")
    uvicorn.run("app:app", host=_HOST, port=_PORT, reload=False)
