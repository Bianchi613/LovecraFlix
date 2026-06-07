"""Estado global e persistência."""
import json
from pathlib import Path

CFG = Path.home() / ".lovecraflix.json"

BG      = (0.039, 0.039, 0.059, 1)
CARD    = (0.086, 0.086, 0.161, 1)
ACCENT  = "#7b2d8b"
TEXT    = (0.91, 0.878, 0.96, 1)
MUTED   = (0.541, 0.498, 0.627, 1)

AVATARES = [
    {"id": "octopus", "emoji": "🐙", "label": "Cthulhu",     "bg": (0.10, 0.05, 0.18, 1), "icon": "jellyfish"},
    {"id": "skull",   "emoji": "💀", "label": "Caveira",      "bg": (0.10, 0.04, 0.04, 1), "icon": "skull"},
    {"id": "eye",     "emoji": "👁️", "label": "O Observador", "bg": (0.04, 0.10, 0.18, 1), "icon": "eye"},
    {"id": "ghost",   "emoji": "👻", "label": "Fantasma",     "bg": (0.07, 0.07, 0.16, 1), "icon": "ghost"},
    {"id": "bat",     "emoji": "🦇", "label": "Vampiro",      "bg": (0.05, 0.05, 0.10, 1), "icon": "bat"},
    {"id": "moon",    "emoji": "🌕", "label": "Lua Cheia",    "bg": (0.10, 0.08, 0.00, 1), "icon": "moon-full"},
    {"id": "spider",  "emoji": "🕷️", "label": "Aranha",       "bg": (0.08, 0.04, 0.04, 1), "icon": "spider"},
    {"id": "wolf",    "emoji": "🐺", "label": "Lobisomem",    "bg": (0.04, 0.06, 0.10, 1), "icon": "paw"},
    {"id": "alien",   "emoji": "👽", "label": "Alienígena",   "bg": (0.00, 0.10, 0.08, 1), "icon": "alien"},
    {"id": "crystal", "emoji": "🔮", "label": "Orbe",         "bg": (0.08, 0.04, 0.18, 1), "icon": "crystal-ball"},
    {"id": "fire",    "emoji": "🔥", "label": "Chama",        "bg": (0.10, 0.03, 0.00, 1), "icon": "fire"},
    {"id": "snake",   "emoji": "🐍", "label": "Serpente",     "bg": (0.02, 0.10, 0.02, 1), "icon": "snake"},
    {"id": "vampire", "emoji": "🧛", "label": "Drácula",      "bg": (0.10, 0.00, 0.06, 1), "icon": "coffin"},
    {"id": "zombie",  "emoji": "🧟", "label": "Zumbi",        "bg": (0.04, 0.10, 0.04, 1), "icon": "grave-stone"},
    {"id": "witch",   "emoji": "🧙", "label": "Feiticeiro",   "bg": (0.10, 0.05, 0.00, 1), "icon": "wizard-hat"},
    {"id": "demon",   "emoji": "😈", "label": "Demônio",      "bg": (0.10, 0.00, 0.02, 1), "icon": "emoticon-devil"},
    {"id": "star",    "emoji": "⭐", "label": "Estrela",      "bg": (0.04, 0.04, 0.10, 1), "icon": "star"},
    {"id": "book",    "emoji": "📖", "label": "Necronomicon", "bg": (0.10, 0.06, 0.00, 1), "icon": "book-open-page-variant"},
]

AVATAR_BY_ID  = {a["id"]: a for a in AVATARES}
AVATAR_ICONS  = {a["id"]: a["icon"] for a in AVATARES}
AVATAR_COLORS = {a["id"]: a["bg"]   for a in AVATARES}


def get_avatar(av_id):
    return AVATAR_BY_ID.get(av_id) or AVATAR_BY_ID["octopus"]

class State:
    base_url = "http://192.168.1.64:8000"
    token    = ""
    nome     = ""
    avatar   = "octopus"
    filme_atual = None
    next_id     = None
    next_titulo = ""

state = State()


def load():
    try:
        d = json.loads(CFG.read_text())
        state.base_url = d.get("base_url", "http://192.168.1.64:8000")
        state.token    = d.get("token", "")
        state.nome     = d.get("nome", "")
        state.avatar   = d.get("avatar", "octopus")
    except: pass


def save():
    try:
        CFG.write_text(json.dumps({
            "base_url": state.base_url,
            "token": state.token,
            "nome":  state.nome,
            "avatar": state.avatar,
        }))
    except: pass


def logout():
    state.token = state.nome = ""
    save()
