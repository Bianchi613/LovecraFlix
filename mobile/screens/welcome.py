import io
import os
import threading

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage, Image as KivyImage
from kivy.graphics import (Color, Rectangle, Ellipse, Line, RoundedRectangle,
                           PushMatrix, PopMatrix, Rotate)
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel

import api

_ACCENT_RGBA = (0.482, 0.176, 0.545, 1)
_WHITE       = (0.91,  0.878, 0.96,  1)
_MUTED       = (0.541, 0.498, 0.627, 1)

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "icone", "LovecraFlix.png")

COLS    = 6
_CELL_W = Window.width / COLS
_CELL_H = _CELL_W * 1.55
_ROWS   = int(Window.height / _CELL_H) + 2
NEEDED  = COLS * _ROWS

# Dimensões do logo: PNG ~380×120 (3.17:1)
_LOGO_W = Window.width              # largura total da tela
_LOGO_H = _LOGO_W / 3.17           # altura proporcional ≈ 126dp


def _transparent_texture(path):
    try:
        from PIL import Image as PILImage
        img = PILImage.open(path).convert("RGBA")
        data = img.getdata()
        new_data = [
            (r, g, b, 0) if (r > 220 and g > 220 and b > 220) else (r, g, b, a)
            for r, g, b, a in data
        ]
        img.putdata(new_data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        from kivy.core.image import Image as CoreImage
        return CoreImage(buf, ext="png").texture
    except Exception:
        return None


class _FilledButton(BoxLayout):
    def __init__(self, text, height, **kw):
        super().__init__(orientation="horizontal",
                         size_hint=(1, None), height=height, **kw)
        self._cb = None
        with self.canvas.before:
            Color(*_ACCENT_RGBA)
            self._bg = RoundedRectangle(radius=[dp(8)], pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)
        self.add_widget(MDLabel(
            text=text, halign="center", valign="middle",
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            font_style="Button",
        ))

    def _upd(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def bind(self, **kw):
        cb = kw.pop("on_release", None)
        if cb:
            self._cb = cb
        super().bind(**kw)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self._cb:
            self._cb(self)
            return True
        return super().on_touch_up(touch)


class _OutlineButton(BoxLayout):
    def __init__(self, text, height, **kw):
        super().__init__(orientation="horizontal",
                         size_hint=(1, None), height=height, **kw)
        self._cb = None
        with self.canvas.before:
            Color(1, 1, 1, 0.10)
            self._bg = RoundedRectangle(radius=[dp(8)], pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.30)
            self._border = Line(
                rounded_rectangle=[self.x, self.y, self.width, self.height, dp(8)],
                width=dp(1),
            )
        self.bind(pos=self._upd, size=self._upd)
        self.add_widget(MDLabel(
            text=text, halign="center", valign="middle",
            theme_text_color="Custom", text_color=(0.88, 0.85, 0.95, 1),
            font_style="Button",
        ))

    def _upd(self, *_):
        self._bg.pos    = self.pos
        self._bg.size   = self.size
        self._border.rounded_rectangle = [self.x, self.y, self.width, self.height, dp(8)]

    def bind(self, **kw):
        cb = kw.pop("on_release", None)
        if cb:
            self._cb = cb
        super().bind(**kw)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self._cb:
            self._cb(self)
            return True
        return super().on_touch_up(touch)


class WelcomeScreen(MDScreen):
    def __init__(self, nav_cb, **kw):
        super().__init__(name="welcome", **kw)
        self.nav_cb = nav_cb
        self._posters_loaded = False

        # ── Fundo sólido ──────────────────────────────────────────────────
        with self.canvas.before:
            Color(0.039, 0.039, 0.059, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *a: setattr(self._bg, "pos", self.pos),
            size=lambda *a: setattr(self._bg, "size", self.size),
        )

        # ── CAMADA 1: grid de posters ─────────────────────────────────────
        self.poster_grid = GridLayout(
            cols=COLS,
            size_hint=(None, None),
            width=Window.width,
            height=_ROWS * _CELL_H,
            pos_hint={"x": 0, "top": 1},
        )
        self.poster_grid.opacity = 0.40
        self.add_widget(self.poster_grid)

        # ── CAMADA 2: overlay escuro + glows ──────────────────────────────
        ov = BoxLayout(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        with ov.canvas.before:
            Color(0.039, 0.039, 0.059, 0.62)
            self._ov_rect = Rectangle(pos=ov.pos, size=ov.size)
            Color(0.29, 0.05, 0.43, 0.30)
            self._glow1 = Ellipse(pos=(0, 0), size=(1, 1))
            Color(0.42, 0.10, 0.10, 0.18)
            self._glow2 = Ellipse(pos=(0, 0), size=(1, 1))

        def _sync(inst, _):
            w, h, x, y = inst.width, inst.height, inst.x, inst.y
            self._ov_rect.pos  = (x, y)
            self._ov_rect.size = (w, h)
            self._glow1.pos  = (x - w * 0.05, y + h * 0.35)
            self._glow1.size = (w * 0.90, h * 0.70)
            self._glow2.pos  = (x + w * 0.30, y - h * 0.08)
            self._glow2.size = (w * 0.80, h * 0.65)

        ov.bind(pos=_sync, size=_sync)
        self.add_widget(ov)

        # ── CAMADA 3: logo direto no FloatLayout — tamanho garantido ──────
        # Posição: centralizado horizontalmente, 58% da tela de cima
        self._logo_img = KivyImage(
            size_hint=(None, None),
            size=(_LOGO_W, _LOGO_H),
            pos_hint={"center_x": 0.5, "top": 0.78},
            allow_stretch=True,
            keep_ratio=True,
            opacity=0,
        )
        if os.path.exists(_LOGO_PATH):
            tex = _transparent_texture(_LOGO_PATH)
            if tex:
                self._logo_img.texture = tex
        self.add_widget(self._logo_img)

        # ── CAMADA 4: textos e botões ──────────────────────────────────────
        content = BoxLayout(
            orientation="vertical",
            padding=[dp(20), dp(32)],
            spacing=dp(8),
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(content)

        # Espaço acima para não colidir com o logo (logo ocupa top 22% da tela)
        content.add_widget(BoxLayout(size_hint_y=None,
                                     height=Window.height * 0.44))

        self.lbl_sub = MDLabel(
            text="Seu acervo pessoal de filmes e séries",
            halign="center",
            font_style="H6",
            theme_text_color="Custom",
            text_color=_WHITE,
            bold=True,
            size_hint_y=None,
            height=dp(52),
            opacity=0,
        )
        content.add_widget(self.lbl_sub)

        content.add_widget(MDLabel(
            text="Filmes, séries e documentários do seu disco,\nprontos para assistir.",
            halign="center",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=_MUTED,
            size_hint_y=None,
            height=dp(40),
        ))

        content.add_widget(BoxLayout())  # flex

        btn_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            size_hint_y=None,
            height=dp(50),
            padding=[0, 0],
        )
        self.btn_entrar = _FilledButton(text="Entrar", height=dp(50), opacity=0)
        self.btn_entrar.bind(on_release=lambda *_: self.nav_cb("login"))

        self.btn_criar = _OutlineButton(text="Criar conta", height=dp(50), opacity=0)
        self.btn_criar.bind(on_release=lambda *_: self.nav_cb("cadastro"))

        btn_row.add_widget(self.btn_entrar)
        btn_row.add_widget(self.btn_criar)
        content.add_widget(btn_row)

        content.add_widget(BoxLayout(size_hint_y=None, height=dp(16)))

    # ── Animações e carregamento ──────────────────────────────────────────

    def on_enter(self, *args):
        for w in (self._logo_img, self.lbl_sub, self.btn_entrar, self.btn_criar):
            w.opacity = 0

        Clock.schedule_once(lambda dt: Animation(opacity=1, d=0.35).start(self._logo_img),  0.00)
        Clock.schedule_once(lambda dt: Animation(opacity=1, d=0.35).start(self.lbl_sub),    0.18)
        Clock.schedule_once(lambda dt: Animation(opacity=1, d=0.35).start(self.btn_entrar), 0.30)
        Clock.schedule_once(lambda dt: Animation(opacity=1, d=0.35).start(self.btn_criar),  0.36)

        if not self._posters_loaded:
            threading.Thread(target=self._load_bg_posters, daemon=True).start()

    def _load_bg_posters(self):
        paths = api.home_posters()
        if not paths:
            paths = [f["poster_local"] for f in api.filmes()
                     if f.get("poster_local")]
        if not paths:
            return
        paths_needed = (paths * (NEEDED // len(paths) + 1))[:NEEDED]
        Clock.schedule_once(lambda dt: self._fill_bg(paths_needed))

    def _fill_bg(self, paths):
        for i, p in enumerate(paths):
            img = AsyncImage(
                source=api.poster_url(p),
                allow_stretch=True,
                keep_ratio=False,
            )
            angle = -4 if i % 2 == 0 else 3
            with img.canvas.before:
                PushMatrix()
                rot = Rotate(angle=angle, axis=(0, 0, 1), origin=img.center)
            with img.canvas.after:
                PopMatrix()
            img.bind(center=lambda inst, val, r=rot: setattr(r, "origin", val))
            self.poster_grid.add_widget(img)
        self._posters_loaded = True
