import io
import os
import threading

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image as KivyImage
from kivy.graphics import Color, Rectangle, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton

from store import state, save, ACCENT
import api

_MUTED  = (0.541, 0.498, 0.627, 1)
_CARD   = (0.078, 0.078, 0.125, 1)
_FILL   = (0.10,  0.08,  0.17,  1)
_FILL_F = (0.13,  0.10,  0.22,  1)

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "icone", "LovecraFlix.png")


def _transparent_texture(path):
    try:
        from PIL import Image as PILImage
        img = PILImage.open(path).convert("RGBA")
        data = img.getdata()
        img.putdata([
            (r, g, b, 0) if (r > 220 and g > 220 and b > 220) else (r, g, b, a)
            for r, g, b, a in data
        ])
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        from kivy.core.image import Image as CoreImage
        return CoreImage(buf, ext="png").texture
    except Exception:
        return None


def _field_block(label_text, hint, password=False):
    block = BoxLayout(orientation="vertical", spacing=dp(4),
                      size_hint_y=None, height=dp(76))
    block.add_widget(MDLabel(
        text=label_text, font_size=dp(10.5),
        theme_text_color="Custom", text_color=_MUTED,
        size_hint_y=None, height=dp(18),
    ))
    field = MDTextField(
        hint_text=hint, password=password, mode="fill",
        fill_color_normal=_FILL, fill_color_focus=_FILL_F,
        line_color_focus=ACCENT,
        size_hint_y=None, height=dp(50),
    )
    block.add_widget(field)
    return block, field


class LoginScreen(MDScreen):
    def __init__(self, nav_cb=None, **kw):
        super().__init__(name="login", **kw)
        self.nav_cb = nav_cb

        # ── Fundo + glow ─────────────────────────────────────────────────
        with self.canvas.before:
            Color(0.039, 0.039, 0.059, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(0.29, 0.05, 0.43, 0.22)
            self._glow1 = Ellipse(pos=(0, 0), size=(1, 1))
            Color(0.42, 0.10, 0.10, 0.14)
            self._glow2 = Ellipse(pos=(0, 0), size=(1, 1))

        self.bind(pos=self._upd_bg, size=self._upd_bg)

        # ── ScrollView ────────────────────────────────────────────────────
        # Estrutura idêntica ao cadastro: ScrollView > inner (mesmo padding,
        # spacing e minimum_height binding) — elimina qualquer diferença
        # estrutural que pudesse afetar o tamanho/posição do logo.
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.add_widget(scroll)

        inner = BoxLayout(
            orientation="vertical",
            padding=[0, dp(24)],
            spacing=dp(12),
            size_hint_y=None,
        )
        inner.bind(minimum_height=inner.setter("height"))
        scroll.add_widget(inner)

        # ── Logo igual ao cadastro ────────────────────────────────────────
        _logo_w = Window.width
        _logo_h = _logo_w / 3.17

        logo_anchor = AnchorLayout(
            anchor_x="center",
            size_hint_y=None,
            height=_logo_h,
        )
        logo_img = KivyImage(
            size_hint=(None, None),
            size=(Window.width, dp(230)),
            allow_stretch=True,
            keep_ratio=True,
        )
        if os.path.exists(_LOGO_PATH):
            tex = _transparent_texture(_LOGO_PATH)
            if tex:
                logo_img.texture = tex
        logo_anchor.add_widget(logo_img)
        inner.add_widget(logo_anchor)

        inner.add_widget(MDLabel(
            text="Acervo pessoal de filmes e séries",
            halign="center", font_style="Caption",
            theme_text_color="Custom", text_color=_MUTED,
            size_hint_y=None, height=dp(28),
        ))

        # ── Card (com margem horizontal própria) ─────────────────────────
        card_wrap = BoxLayout(size_hint_y=None, height=dp(260),
                              padding=[dp(24), 0])
        inner.add_widget(card_wrap)

        card = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(20), dp(22)],
            size_hint=(1, 1),
        )
        with card.canvas.before:
            Color(*_CARD)
            self._card_bg = RoundedRectangle(radius=[dp(14)],
                                              pos=card.pos, size=card.size)
            Color(1, 1, 1, 0.07)
            self._card_border = Line(
                rounded_rectangle=[card.x, card.y, card.width, card.height, dp(14)],
                width=dp(1),
            )

        def _upd_card(*_):
            self._card_bg.pos  = card.pos
            self._card_bg.size = card.size
            self._card_border.rounded_rectangle = [
                card.x, card.y, card.width, card.height, dp(14)]

        card.bind(pos=_upd_card, size=_upd_card)

        email_block, self.email = _field_block("EMAIL", "seu@email.com")
        senha_block, self.senha = _field_block("SENHA", "••••••••", password=True)

        btn = MDRaisedButton(
            text="Entrar", md_bg_color=ACCENT,
            size_hint=(1, None), height=dp(50),
            font_size=dp(16), elevation=6,
        )
        btn.bind(on_release=self._entrar)

        card.add_widget(email_block)
        card.add_widget(senha_block)
        card.add_widget(btn)
        card_wrap.add_widget(card)

        # ── Mensagem ──────────────────────────────────────────────────────
        self._msg_box = BoxLayout(size_hint_y=None, height=0,
                                  padding=[dp(24), dp(6)])
        with self._msg_box.canvas.before:
            Color(0.75, 0.22, 0.17, 0.15)
            self._msg_bg = RoundedRectangle(
                radius=[dp(6)], pos=self._msg_box.pos, size=self._msg_box.size)
            Color(0.75, 0.22, 0.17, 0.35)
            self._msg_border = Line(
                rounded_rectangle=[
                    self._msg_box.x, self._msg_box.y,
                    self._msg_box.width, self._msg_box.height, dp(6)],
                width=dp(1))

        def _upd_msg(*_):
            self._msg_bg.pos    = self._msg_box.pos
            self._msg_bg.size   = self._msg_box.size
            self._msg_border.rounded_rectangle = [
                self._msg_box.x, self._msg_box.y,
                self._msg_box.width, self._msg_box.height, dp(6)]

        self._msg_box.bind(pos=_upd_msg, size=_upd_msg)
        self.msg = MDLabel(text="", halign="left", font_style="Caption",
                           theme_text_color="Custom",
                           text_color=(0.91, 0.36, 0.29, 1))
        self._msg_box.add_widget(self.msg)
        inner.add_widget(BoxLayout(size_hint_y=None, height=dp(8)))
        inner.add_widget(self._msg_box)

        lbl_cadastro = MDLabel(
            text="Não tem conta? Criar conta",
            halign="center", font_style="Caption",
            theme_text_color="Custom", text_color=ACCENT,
            size_hint_y=None, height=dp(40),
        )
        lbl_cadastro.bind(on_touch_down=lambda inst, touch:
                          self.nav_cb("cadastro") if self.nav_cb and inst.collide_point(*touch.pos) else None)
        inner.add_widget(lbl_cadastro)

        inner.add_widget(BoxLayout(size_hint_y=None, height=dp(16)))

    def _upd_bg(self, *_):
        w, h, x, y = self.width, self.height, self.x, self.y
        self._bg.pos   = (x, y)
        self._bg.size  = (w, h)
        self._glow1.pos  = (x - w * 0.05, y + h * 0.42)
        self._glow1.size = (w * 0.75, h * 0.62)
        self._glow2.pos  = (x + w * 0.35, y - h * 0.06)
        self._glow2.size = (w * 0.75, h * 0.62)

    def _set_msg(self, text, is_error=True):
        self.msg.text        = text
        self._msg_box.height = dp(36) if text else 0
        self.msg.text_color  = (0.91, 0.36, 0.29, 1) if is_error else (0.56, 0.56, 0.56, 1)

    def _entrar(self, *_):
        self._set_msg("Entrando...", is_error=False)
        email = self.email.text.strip()
        senha = self.senha.text

        def _do():
            try:
                dados, status = api.login(email, senha)
                if status == 200:
                    state.token = dados["token"]
                    state.nome  = dados["nome"]
                    u = api.me()
                    if u:
                        state.avatar = u.get("avatar", "octopus")
                    save()
                    Clock.schedule_once(lambda dt: (
                        self._set_msg(""),
                        setattr(self.manager, "current", "home"),
                    ))
                else:
                    msg = dados.get("detail", "Email ou senha incorretos.")
                    Clock.schedule_once(lambda dt: self._set_msg(msg))
            except Exception as ex:
                Clock.schedule_once(lambda dt: self._set_msg(f"Erro: {ex}"))

        threading.Thread(target=_do, daemon=True).start()
