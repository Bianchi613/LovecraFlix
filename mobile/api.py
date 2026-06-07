"""Cliente HTTP para o backend LovecraFlix."""

import requests
from urllib.parse import quote
from store import state

_session = requests.Session()


def _h():
    return {"Authorization": f"Bearer {state.token}"} if state.token else {}


def _url(path):
    return f"{state.base_url}{path}"


def cadastrar(nome, email, senha):
    try:
        r = _session.post(
            _url("/auth/cadastro"),
            json={"nome": nome, "email": email, "senha": senha},
            timeout=8
        )
        return r.json(), r.status_code
    except Exception:
        return {}, 500


def login(email, senha):
    try:
        r = _session.post(
            _url("/auth/login"),
            json={"email": email, "senha": senha},
            timeout=8
        )
        return r.json(), r.status_code
    except Exception:
        return {}, 500


def me():
    try:
        r = _session.get(
            _url("/auth/me"),
            headers=_h(),
            timeout=5
        )
        return r.json() if r.ok else None
    except Exception:
        return None


def atualizar_perfil(dados):
    try:
        r = _session.put(
            _url("/api/perfil"),
            json=dados,
            headers=_h(),
            timeout=5
        )
        return r.json() if r.ok else None
    except Exception:
        return None


def generos(tipo=""):
    try:
        params = {"tipo": tipo} if tipo else {}
        return _session.get(
            _url("/api/generos"),
            params=params,
            headers=_h(),
            timeout=8
        ).json()
    except Exception:
        return []


def filmes(genero="", tipo="", busca=""):
    try:
        params = {
            k: v
            for k, v in {
                "genero": genero,
                "tipo": tipo,
                "busca": busca
            }.items()
            if v
        }

        return _session.get(
            _url("/api/filmes"),
            params=params,
            headers=_h(),
            timeout=10
        ).json()
    except Exception:
        return []


def series():
    try:
        return _session.get(
            _url("/api/series"),
            headers=_h(),
            timeout=10
        ).json()
    except Exception:
        return []


def colecoes():
    try:
        return _session.get(
            _url("/api/colecoes"),
            headers=_h(),
            timeout=10
        ).json()
    except Exception:
        return []


def destaques():
    try:
        return _session.get(
            _url("/api/destaques"),
            headers=_h(),
            timeout=10
        ).json()
    except Exception:
        return []


def home_posters():
    """Lista de paths de poster para a landing page."""
    try:
        r = _session.get(_url("/api/home-posters"), headers=_h(), timeout=8)
        return r.json() if r.ok else []
    except Exception:
        return []


def versoes(titulo):
    try:
        return _session.get(
            _url("/api/filmes/versoes"),
            params={"titulo": titulo},
            headers=_h(),
            timeout=8
        ).json()
    except Exception:
        return []


def episodios_serie(pasta):
    try:
        return _session.get(
            _url("/api/series/episodios"),
            params={"pasta": pasta},
            headers=_h(),
            timeout=8
        ).json()
    except Exception:
        return []


def episodios_colecao(colecao):
    try:
        return _session.get(
            _url("/api/colecoes/episodios"),
            params={"colecao": colecao},
            headers=_h(),
            timeout=8
        ).json()
    except Exception:
        return []


def filme(id):
    try:
        return _session.get(
            _url(f"/api/filmes/{id}"),
            headers=_h(),
            timeout=8
        ).json()
    except Exception:
        return {}


def avaliacao(filme_id):
    try:
        r = _session.get(
            _url("/api/avaliacao"),
            params={"filme_id": filme_id},
            headers=_h(),
            timeout=5
        )
        return r.json() if r.ok else {"nota": 0}
    except Exception:
        return {"nota": 0}


def avaliar(filme_id, nota):
    try:
        _session.post(
            _url("/api/avaliar"),
            json={
                "filme_id": filme_id,
                "nota": nota
            },
            headers=_h(),
            timeout=5
        )
    except Exception:
        pass


def recomendacoes(filme_id):
    try:
        r = _session.get(
            _url("/api/recomendacoes"),
            params={"id": filme_id},
            headers=_h(),
            timeout=8
        )
        return r.json() if r.ok else []
    except Exception:
        return []


def video_url(arquivo, needs_transcode, audio_track=0):
    p = quote(arquivo, safe="")

    if needs_transcode:
        return _url(
            f"/transcode?path={p}&audio_track={audio_track}"
        )

    return _url(f"/video?path={p}")


def poster_url(poster_local):
    return _url(
        f"/poster?path={quote(poster_local, safe='')}"
    )