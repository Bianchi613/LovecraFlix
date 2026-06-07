import io
import os
import threading

from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.image import AsyncImage, Image as KivyImage
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.animation import Animation

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.spinner import MDSpinner

from store import state, ACCENT, get_avatar
from emoji_img import avatar_widget
import api

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "icone", "LovecraFlix.png")
_BAR_BG    = (0.078, 0.078, 0.125, 1)

COLS = 3


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


def cw():
    return (Window.width - dp(16)) / COLS


class FilmeCard(MDCard):
    def __init__(self, item, tipo, nav_cb, **kw):
        super().__init__(
            orientation="vertical",
            size_hint=(None, None),
            size=(cw(), cw() * 1.55),
            md_bg_color=(0.08, 0.08, 0.16, 1),
            radius=[dp(12)],
            elevation=8,
            ripple_behavior=True,
            **kw
        )
        self.item = item
        self.tipo = tipo
        self.nav_cb = nav_cb

        poster = item.get("poster_local")
        titulo = item.get("titulo_pt") or item.get("colecao") or "Sem título"

        self.img_box = BoxLayout(orientation="vertical", size_hint=(1, 1))

        if poster:
            self.img = AsyncImage(
                allow_stretch=True,
                keep_ratio=False,
                opacity=0,
            )
            self.img.bind(texture=lambda inst, tex: Animation(opacity=1, d=0.2).start(inst) if tex else None)
            self.img.source = api.poster_url(poster)
            self.img_box.add_widget(self.img)
        else:
            self.img_box.add_widget(MDLabel(
                text=titulo[:2].upper(),
                halign="center",
                valign="middle",
                font_style="H5",
                theme_text_color="Custom",
                text_color=(0.7, 0.4, 0.9, 0.6)
            ))

        # Overlay leve (posters claros)
        overlay = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(68),
            pos_hint={"bottom": 1},
            padding=[dp(14), dp(12)],
        )

        overlay.add_widget(MDLabel(
            text=titulo,
            font_style="Caption",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 0.98),
            shorten=True,
            shorten_from="right",
            halign="left",
        ))

        with overlay.canvas.before:
            Color(0, 0, 0, 0.40)   # Equilibrado
            self._rect = Rectangle(size=overlay.size, pos=overlay.pos)

        overlay.bind(size=self._update_rect, pos=self._update_rect)
        self.img_box.add_widget(overlay)
        self.add_widget(self.img_box)

        self.bind(on_release=self._tap)

    def _update_rect(self, *args):
        self._rect.size = self.size
        self._rect.pos = self.pos

    _BG_NORMAL  = (0.08, 0.08, 0.16, 1)
    _BG_PRESSED = (0.14, 0.10, 0.24, 1)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._pressed    = True
            self.elevation   = 16
            self.md_bg_color = self._BG_PRESSED
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if getattr(self, '_pressed', False):
            self._pressed    = False
            self.elevation   = 8
            self.md_bg_color = self._BG_NORMAL
            if self.collide_point(*touch.pos):
                self.dispatch('on_release')
                return True
        return super().on_touch_up(touch)

    def _tap(self, *_):
        item, tipo = self.item, self.tipo
        if tipo == "filme":
            v = api.versoes(item.get("titulo_pt", ""))
            if len(v) > 1:
                self.nav_cb("versoes", item=item, versoes=v)
            else:
                state.filme_atual = v[0] if v else item
                self.nav_cb("player", id=item.get("id"))
        elif tipo == "serie":
            self.nav_cb("serie", pasta=item.get("pasta", ""), nome=item.get("titulo_pt", ""))
        else:
            self.nav_cb("colecao", colecao=item.get("colecao", ""))

# ====================== HomeScreen (mantido) ======================
class HomeScreen(MDScreen):
    def __init__(self, nav_cb, **kw):
        super().__init__(**kw)
        self.name = "home"
        self.nav_cb = nav_cb
        self.nav_index = 0
        self.genero = ""
        self.generos = []

        with self.canvas.before:
            Color(0.035, 0.035, 0.055, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=lambda *a: setattr(self._bg, "pos", self.pos),
                  size=lambda *a: setattr(self._bg, "size", self.size))

        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        # ── Header com logo (mesma cor escura do buscador, sem roxo) ──────
        bar = BoxLayout(orientation="horizontal", size_hint_y=None,
                        height=dp(56), padding=[dp(8), 0])
        with bar.canvas.before:
            Color(*_BAR_BG)
            self._bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda *a: setattr(self._bar_bg, "pos", bar.pos),
                 size=lambda *a: setattr(self._bar_bg, "size", bar.size))

        # Tamanho da logo = só isto controla o quão grande ela aparece
        # (proporção 1.5:1, igual à textura 1536x1024). A bar precisa ter
        # pelo menos essa altura, senão a imagem é cortada pela tela.
        logo_img = KivyImage(
            size_hint=(None, None),
            size=(dp(138), dp(92)),
            allow_stretch=True, keep_ratio=True,
        )
        if os.path.exists(_LOGO_PATH):
            tex = _transparent_texture(_LOGO_PATH)
            if tex:
                logo_img.texture = tex

        # Cada item (logo / caveira) fica num AnchorLayout próprio que
        # ocupa toda a altura útil da bar e centraliza no eixo Y — assim
        # os dois ficam garantidamente na mesma linha, independente de
        # como cada widget se posicionaria sozinho dentro do BoxLayout.
        logo_wrap = AnchorLayout(anchor_x="left", anchor_y="center",
                                 size_hint=(None, 1), width=dp(138))
        logo_wrap.add_widget(logo_img)
        bar.add_widget(logo_wrap)
        bar.add_widget(BoxLayout())  # flex

        self._profile_wrap = AnchorLayout(anchor_x="right", anchor_y="center",
                                           size_hint=(None, 1), width=dp(48))
        self._profile_wrap.add_widget(
            avatar_widget(get_avatar(state.avatar), 32, on_tap=lambda: nav_cb("perfil"))
        )
        bar.add_widget(self._profile_wrap)

        self.bar = bar
        root.add_widget(bar)

        search_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52),
                               padding=[dp(4), 0])
        search_icon = MDIconButton(icon="magnify", theme_icon_color="Custom",
                                   icon_color=(0.6, 0.6, 0.6, 1),
                                   size_hint=(None, None), width=dp(44), height=dp(52))
        self.busca = MDTextField(
            hint_text="Buscar filmes...",
            mode="round",
            fill_color_normal=(0.09, 0.09, 0.17, 1),
            fill_color_focus=(0.12, 0.10, 0.22, 1),
            line_color_normal=(0.09, 0.09, 0.17, 1),
            line_color_focus=ACCENT,
            size_hint_y=None,
            height=dp(48),
        )
        self.busca.bind(text=lambda *a: self._buscar())
        search_row.add_widget(search_icon)
        search_row.add_widget(self.busca)
        root.add_widget(search_row)

        root.add_widget(BoxLayout(size_hint_y=None, height=dp(6)))
        sv_chips = ScrollView(size_hint=(1, None), height=dp(52), do_scroll_y=False, bar_width=0)
        self.chips = BoxLayout(orientation="horizontal", spacing=dp(8), padding=[dp(8), dp(6)], size_hint_x=None)
        self.chips.bind(minimum_width=self.chips.setter("width"))
        sv_chips.add_widget(self.chips)
        root.add_widget(sv_chips)

        self.active_filter_row = BoxLayout(orientation="horizontal", spacing=dp(6),
                                           padding=[dp(8), dp(2)], size_hint=(1, None), height=0)
        root.add_widget(self.active_filter_row)

        root.add_widget(BoxLayout(size_hint_y=None, height=dp(4)))
        self.sv_grid = ScrollView(size_hint=(1, 1), bar_width=dp(4), bar_color=(0.48, 0.18, 0.55, 0.7))
        self.grid = GridLayout(cols=COLS, spacing=dp(10), padding=dp(8), size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.sv_grid.add_widget(self.grid)
        root.add_widget(self.sv_grid)

        self.nav_labels = ["Tudo", "Filmes", "Series", "Docs"]
        self.nav_icons = ["home", "movie-outline", "television-play", "play-box-multiple"]

        nav_bar = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(56))
        from kivy.graphics import Color as C2, Rectangle as R2

        with nav_bar.canvas.before:
            C2(0.086, 0.086, 0.161, 1)
            self._nav_bg = R2(pos=nav_bar.pos, size=nav_bar.size)

        nav_bar.bind(pos=lambda *a: setattr(self._nav_bg, "pos", nav_bar.pos),
                     size=lambda *a: setattr(self._nav_bg, "size", nav_bar.size))

        self._nav_btns = []
        for i, (lbl, ico) in enumerate(zip(self.nav_labels, self.nav_icons)):
            col = BoxLayout(orientation="vertical", spacing=0)
            btn = MDIconButton(
                icon=ico,
                theme_icon_color="Custom",
                icon_color=ACCENT if i == 0 else (0.4, 0.4, 0.4, 1),
                icon_size=dp(24),
                pos_hint={"center_x": .5}
            )
            btn.bind(on_release=lambda b, idx=i: self._nav_tap(idx))

            txt = MDLabel(
                text=lbl,
                halign="center",
                font_style="Caption",
                size_hint_y=None,
                height=dp(14),
                theme_text_color="Custom",
                text_color=ACCENT if i == 0 else (0.4, 0.4, 0.4, 1)
            )

            col.add_widget(btn)
            col.add_widget(txt)

            with col.canvas.after:
                ind_color = Color(0.48, 0.18, 0.55, 1 if i == 0 else 0)
                ind_rect  = Rectangle(pos=col.pos, size=(col.width, dp(3)))
            col.bind(pos =lambda *a, r=ind_rect, c=col: setattr(r, 'pos',  c.pos),
                     size=lambda *a, r=ind_rect, c=col: setattr(r, 'size', (c.width, dp(3))))

            self._nav_btns.append((btn, txt, ind_color))
            nav_bar.add_widget(col)

        root.add_widget(nav_bar)
        self._bt = None

    # ====================== Seus métodos (mantidos) ======================
    def on_pre_enter(self, *args):
        self._profile_wrap.clear_widgets()
        self._profile_wrap.add_widget(
            avatar_widget(get_avatar(state.avatar), 32, on_tap=lambda: self.nav_cb("perfil"))
        )

    def on_enter(self):
        self._load()

    def _buscar(self):
        self._update_active_filters()
        if self._bt: self._bt.cancel()
        self._bt = Clock.schedule_once(lambda dt: self._load(), 0.8)

    def _nav_tap(self, idx):
        self.nav_index = idx
        for i, (btn, lbl, ind) in enumerate(self._nav_btns):
            active = (i == idx)
            c = ACCENT if active else (0.4, 0.4, 0.4, 1)
            btn.icon_color = c
            lbl.text_color = c
            Animation(a=1 if active else 0, d=0.15).start(ind)
        self._load()

    def _load(self):
        self.grid.clear_widgets()
        self.grid.add_widget(MDSpinner(size_hint=(None, None), size=(dp(40), dp(40)), pos_hint={"center_x": .5}))
        threading.Thread(target=self._load_generos, daemon=True).start()
        threading.Thread(target=self._load_items, daemon=True).start()

    def _load_generos(self):
        tipo_map = ["", "filme", "serie", "documentario"]
        tipo = tipo_map[self.nav_index] if self.nav_index < len(tipo_map) else ""
        try:
            self.generos = api.generos(tipo)
        except Exception:
            self.generos = []
        Clock.schedule_once(lambda dt: self._build_chips())

    def _build_chips(self):
        self.chips.clear_widgets()
        for lbl, g in [("Todos", "")] + [(x["genero"], x["genero"]) for x in self.generos]:
            ativo = self.genero == g
            disp = "H.Cosmico" if g == "Horror Cosmico" else lbl
            btn = MDRaisedButton(
                text=disp,
                md_bg_color=ACCENT if ativo else (0.117, 0.117, 0.208, 1),
                size_hint=(None, None),
                height=dp(36),
                font_size=dp(12.5),
            )
            btn.bind(on_release=lambda b, genre=g: self._sel(genre))
            self.chips.add_widget(btn)

    def _sel(self, g):
        if self.genero == g: return
        self.genero = g
        self._build_chips()
        self._update_active_filters()
        threading.Thread(target=self._load_items, daemon=True).start()

    def _update_active_filters(self):
        self.active_filter_row.clear_widgets()
        has = False
        if self.genero:
            has = True
            chip = MDRaisedButton(text=f"{self.genero}  ×",
                                  md_bg_color=(0.3, 0.1, 0.45, 1),
                                  size_hint=(None, None), height=dp(28), font_size=dp(11))
            chip.bind(on_release=lambda *_: self._sel(""))
            self.active_filter_row.add_widget(chip)
        busca = self.busca.text.strip() if hasattr(self, 'busca') else ""
        if busca:
            has = True
            chip2 = MDRaisedButton(text=f'"{busca}"  ×',
                                   md_bg_color=(0.2, 0.2, 0.35, 1),
                                   size_hint=(None, None), height=dp(28), font_size=dp(11))
            chip2.bind(on_release=lambda *_: setattr(self.busca, 'text', ''))
            self.active_filter_row.add_widget(chip2)
        self.active_filter_row.height = dp(36) if has else 0

    def _load_items(self):
        tipo_map = ["", "filme", "serie", "documentario"]
        tipo = tipo_map[self.nav_index] if self.nav_index < len(tipo_map) else ""
        busca = self.busca.text if hasattr(self, 'busca') else ""

        items = []
        try:
            if self.nav_index in (0, 1):
                seen = set()
                for f in api.filmes(genero=self.genero, tipo=tipo, busca=busca):
                    titulo = f.get("titulo_pt", "")
                    if titulo not in seen:
                        seen.add(titulo)
                        items.append(("filme", f))

            if self.nav_index in (0, 2):
                for s in api.series():
                    if not self.genero or s.get("genero") == self.genero:
                        items.append(("serie", s))

            if self.nav_index in (0, 3):
                for d in api.colecoes():
                    if not self.genero or d.get("genero") == self.genero:
                        items.append(("doc", d))
        except Exception as ex:
            print(f"[HOME ERR] {ex}")

        items = items[:40]
        Clock.schedule_once(lambda dt, it=items: self._show(it))

    def _show(self, items):
        self.grid.clear_widgets()
        if not items:
            self.grid.add_widget(MDLabel(text="Nenhum item encontrado", halign="center", height=dp(100)))
            return

        for tipo, item in items:
            self.grid.add_widget(FilmeCard(item, tipo, self.nav_cb))

        Clock.schedule_once(self._fix_grid_height, 0.1)

    def _fix_grid_height(self, *_):
        try:
            self.grid.height = self.grid.minimum_height
        except Exception:
            pass

    def refresh(self):
        self._load()

    def limpar_busca(self):
        self.busca.text = ""
        self._load()

    def voltar_topo(self):
        try:
            self.sv_grid.scroll_y = 1
        except Exception:
            pass

    def on_leave(self):
        if self._bt:
            self._bt.cancel()