"""Renderiza emojis coloridos como PNGs (cache em disco) para uso em KivyImage.

KivyMD só inclui ícones Material Design (glifos monocromáticos finos), que
ficavam "feios"/genéricos como avatares. Os emojis já definidos em
store.AVATARES são muito mais expressivos — aqui nós os rasterizamos com a
fonte de emoji colorida do sistema via Pillow, já que Kivy não consegue
desenhar fontes de emoji coloridas (CBDT/COLR) diretamente.
"""
from pathlib import Path

from kivy.metrics import dp
from kivy.uix.image import Image as KivyImage
from kivy.uix.anchorlayout import AnchorLayout
from kivymd.uix.button import MDIconButton

_CACHE_DIR = Path(__file__).parent / ".emoji_cache"

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\seguiemj.ttf",                                    # Windows
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",                 # Linux
    "/System/Library/Fonts/Apple Color Emoji.ttc",                       # macOS
]

_font_path = next((p for p in _FONT_CANDIDATES if Path(p).exists()), None)


# U+FE0E/FE0F ("variation selectors") só sinalizam apresentação
# texto-vs-emoji — não desenham nada, mas confundem o cálculo de
# bounding box de alguns glifos coloridos (ex.: 👁️ e 🕷️ ficavam
# desalinhados nos seus círculos). O glifo colorido sai idêntico sem eles.
_VARIATION_SELECTORS = str.maketrans("", "", "︎️")


def emoji_image_path(emoji: str, px: int = 128):
    """Retorna o caminho de um PNG com o emoji renderizado (ou None se
    nenhuma fonte de emoji colorida estiver disponível no sistema)."""
    if not _font_path:
        return None

    glyph = emoji.translate(_VARIATION_SELECTORS)

    _CACHE_DIR.mkdir(exist_ok=True)
    fname = f"{px}_{'_'.join(f'{ord(c):x}' for c in glyph)}.png"
    path = _CACHE_DIR / fname
    if not path.exists():
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.truetype(_font_path, int(px * 0.86))
        img  = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        d    = ImageDraw.Draw(img)
        x0, y0, x1, y1 = d.textbbox((0, 0), glyph, font=font, embedded_color=True)
        d.text(((px - (x1 - x0)) / 2 - x0, (px - (y1 - y0)) / 2 - y0),
               glyph, font=font, embedded_color=True)
        img.save(path)
    return str(path)


def avatar_widget(av_data, size_dp, on_tap=None):
    """Rosto do avatar pronto para uso: imagem colorida do emoji centralizada
    num AnchorLayout que preenche o espaço do pai (ou, se o sistema não tiver
    fonte de emoji colorida, o ícone MDI de reserva definido em AVATARES).

    Sempre devolve o mesmo tipo de "caixa" (AnchorLayout 1x1) — assim o
    chamador pode trocar o widget exibido sem se preocupar com o tamanho/
    posicionamento mudar conforme a fonte de emoji existe ou não.
    """
    path = emoji_image_path(av_data["emoji"])
    if path:
        face = KivyImage(source=path, size_hint=(None, None),
                         size=(dp(size_dp), dp(size_dp)),
                         allow_stretch=True, keep_ratio=True)
    else:
        face = MDIconButton(icon=av_data["icon"], theme_icon_color="Custom",
                            icon_color=(1, 1, 1, 0.9), icon_size=dp(size_dp * 0.65),
                            md_bg_color=(0, 0, 0, 0))

    wrap = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 1))
    wrap.add_widget(face)
    if on_tap:
        wrap.bind(on_touch_down=lambda inst, touch:
                  on_tap() if inst.collide_point(*touch.pos) else None)
    return wrap
