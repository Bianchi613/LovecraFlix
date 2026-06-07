import threading
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.card import MDCard

from store import state, save, logout, ACCENT, AVATARES, get_avatar
from emoji_img import avatar_widget
import api

_BAR_BG = (0.078, 0.078, 0.125, 1)


def _lighter(bg):
    r, g, b, a = bg
    return (min(r * 1.8, 1.0), min(g * 1.8, 1.0), min(b * 1.8, 1.0), a)


class PerfilScreen(MDScreen):
    def __init__(self, nav_cb, **kw):
        super().__init__(name="perfil", **kw)
        self.nav_cb = nav_cb
        self._av_sel = state.avatar

        with self.canvas.before:
            Color(0.039, 0.039, 0.059, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *a: setattr(self._bg, "pos", self.pos),
            size=lambda *a: setattr(self._bg, "size", self.size),
        )

        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        # ── Header igual ao da home (mesma cor escura, sem roxo) ──────────
        bar = BoxLayout(orientation="horizontal", size_hint_y=None,
                        height=dp(56), padding=[dp(4), 0])
        with bar.canvas.before:
            Color(*_BAR_BG)
            self._bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda *a: setattr(self._bar_bg, "pos", bar.pos),
                 size=lambda *a: setattr(self._bar_bg, "size", bar.size))

        back_btn = MDIconButton(icon="arrow-left", theme_icon_color="Custom",
                                icon_color=(1, 1, 1, 1))
        back_btn.bind(on_release=lambda x: nav_cb("home"))
        bar.add_widget(back_btn)

        bar.add_widget(MDLabel(
            text="Perfil", font_style="H6", halign="center",
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
        ))

        logout_btn = MDIconButton(icon="logout-variant", theme_icon_color="Custom",
                                  icon_color=(1, 1, 1, 1))
        logout_btn.bind(on_release=lambda x: self._logout())
        bar.add_widget(logout_btn)

        root.add_widget(bar)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(14),
                            size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        root.add_widget(scroll)

        # ── Avatar display (topo) ──────────────────────────────────────────
        av = get_avatar(state.avatar)
        av_row = BoxLayout(orientation="horizontal", size_hint_y=None,
                           height=dp(100), spacing=dp(16))

        self.av_circle = MDCard(
            size_hint=(None, None), size=(dp(84), dp(84)),
            radius=[dp(42)], md_bg_color=av["bg"], elevation=4,
        )
        self.av_circle.add_widget(avatar_widget(av, 56))

        av_info = BoxLayout(orientation="vertical", spacing=dp(4))
        self.av_nome_lbl = MDLabel(
            text=state.nome or "Usuário",
            font_style="H6",
            theme_text_color="Custom",
            text_color=(0.91, 0.878, 0.96, 1),
        )
        self.av_tipo_lbl = MDLabel(
            text=av["label"],
            font_style="Caption",
            theme_text_color="Custom",
            text_color=(0.541, 0.498, 0.627, 1),
        )
        av_info.add_widget(self.av_nome_lbl)
        av_info.add_widget(self.av_tipo_lbl)

        av_row.add_widget(self.av_circle)
        av_row.add_widget(av_info)
        content.add_widget(av_row)

        # ── Campo nome ────────────────────────────────────────────────────
        self.nome_field = MDTextField(
            hint_text="Nome", text=state.nome,
            mode="rectangle", size_hint_y=None, height=dp(52),
        )
        content.add_widget(self.nome_field)

        # ── Título grid ───────────────────────────────────────────────────
        content.add_widget(MDLabel(
            text="Escolha seu avatar:",
            theme_text_color="Secondary",
            font_style="Caption",
            size_hint_y=None, height=dp(26),
        ))

        # ── Grid de avatares (cols=3) ─────────────────────────────────────
        self._av_cards = {}
        grid = GridLayout(cols=3, spacing=dp(10), padding=[0, 0], size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for av_data in AVATARES:
            av_id  = av_data["id"]
            is_sel = (av_id == self._av_sel)
            cell   = self._make_cell(av_data, is_sel)
            self._av_cards[av_id] = cell
            grid.add_widget(cell)

        content.add_widget(grid)

        # ── Botão salvar ──────────────────────────────────────────────────
        btn_salvar = MDRaisedButton(
            text="SALVAR", md_bg_color=ACCENT,
            size_hint=(1, None), height=dp(48),
        )
        btn_salvar.bind(on_release=self._salvar)
        content.add_widget(btn_salvar)

        self.msg = MDLabel(text="", halign="center", size_hint_y=None, height=dp(28))
        content.add_widget(self.msg)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_cell(self, av_data, selected):
        """Célula de avatar: círculo colorido com ícone Material + label."""
        av_id = av_data["id"]
        bg    = _lighter(av_data["bg"]) if selected else av_data["bg"]

        outer = BoxLayout(
            orientation="vertical", spacing=dp(2),
            size_hint=(None, None), size=(dp(90), dp(96)),
        )

        anchor = AnchorLayout(
            anchor_x="center", anchor_y="center",
            size_hint=(1, None), height=dp(68),
        )
        card = MDCard(
            size_hint=(None, None), size=(dp(64), dp(64)),
            radius=[dp(32)], md_bg_color=bg, elevation=4 if selected else 2,
        )
        card.add_widget(avatar_widget(av_data, 42))
        anchor.add_widget(card)
        outer.add_widget(anchor)

        name_lbl = MDLabel(
            text=av_data["label"], halign="center",
            font_style="Caption", font_size=dp(9),
            theme_text_color="Custom",
            text_color=ACCENT if selected else (0.541, 0.498, 0.627, 1),
            size_hint_y=None, height=dp(20),
        )
        outer.add_widget(name_lbl)

        outer.bind(on_touch_down=lambda inst, touch:
                   self._sel(av_id) if inst.collide_point(*touch.pos) else None)

        return outer

    def _sel(self, av_id):
        if av_id == self._av_sel:
            return
        old_id       = self._av_sel
        self._av_sel = av_id

        # Atualiza display grande no topo
        av = get_avatar(av_id)
        self.av_circle.md_bg_color = av["bg"]
        self.av_circle.clear_widgets()
        self.av_circle.add_widget(avatar_widget(av, 56))
        self.av_tipo_lbl.text      = av["label"]

        # Recolore células antiga e nova
        for aid, selected in ((old_id, False), (av_id, True)):
            cell = self._av_cards.get(aid)
            if not cell:
                continue
            av_data  = get_avatar(aid)
            # children em Kivy são invertidos: [0]=último adicionado
            card     = cell.children[1].children[0]  # anchor > MDCard
            lbl      = cell.children[0]              # MDLabel nome
            card.md_bg_color = _lighter(av_data["bg"]) if selected else av_data["bg"]
            card.elevation   = 4 if selected else 2
            lbl.text_color   = ACCENT if selected else (0.541, 0.498, 0.627, 1)

    def _salvar(self, *_):
        state.nome   = self.nome_field.text.strip() or state.nome
        state.avatar = self._av_sel
        self.av_nome_lbl.text = state.nome
        save()
        threading.Thread(
            target=lambda: api.atualizar_perfil({"nome": state.nome, "avatar": state.avatar}),
            daemon=True,
        ).start()
        self.msg.text = "✓ Salvo!"
        Clock.schedule_once(lambda dt: setattr(self.msg, "text", ""), 2)

    def _logout(self):
        logout()
        self.nav_cb("welcome")
