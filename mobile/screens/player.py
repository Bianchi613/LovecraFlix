import threading
import re

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.slider import MDSlider

from kivy.uix.video import Video
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform

from store import state, ACCENT
import api


def _set_immersive(hide):
    """Esconde/mostra a barra de status e a barra de navegação no Android."""
    if platform != "android":
        return
    try:
        from jnius import autoclass
        View = autoclass("android.view.View")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        decor = activity.getWindow().getDecorView()
        if hide:
            decor.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            )
        else:
            decor.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE)
    except Exception:
        pass  # acabamento visual — nunca deve derrubar o player


class VideoContainer(RelativeLayout):
    """RelativeLayout que captura toques para mostrar/ocultar overlay de
    controles. Precisa ser RelativeLayout (não FloatLayout): seus filhos
    (`video`, `overlay`) são adicionados com size_hint=(1,1) e sem pos_hint,
    e só o RelativeLayout traduz automaticamente a posição deles para o
    canto deste container — um FloatLayout deixaria ambos travados em (0,0)."""

    def __init__(self, player_ref, **kw):
        super().__init__(**kw)
        self._player = player_ref

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if self._player.overlay.opacity == 0:
            self._player._show_overlay()
            return True
        self._player._cancel_hide_timer()
        handled = super().on_touch_down(touch)
        if handled:
            touch.grab(self)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._player._reset_hide_timer()
        return super().on_touch_up(touch)


class PlayerScreen(MDScreen):
    def __init__(self, nav_cb, filme_id, back_to="home", **kw):
        super().__init__(**kw)

        self.name = "player"
        self.nav_cb = nav_cb
        self.filme_id = filme_id
        self.back_to = back_to

        self._f = None
        self._timer = None
        self._countdown = [10]
        self.is_fullscreen = False
        self._hide_event = None
        self._last_volume = 1.0
        self._portrait_video_h = Window.width * 9 / 16

        root = MDBoxLayout(orientation="vertical")
        self.add_widget(root)
        self._root = root

        # ── Área do vídeo ──────────────────────────────────────────────────
        self.video_container = VideoContainer(
            self,
            size_hint=(1, None),
            height=self._portrait_video_h,
        )

        self.video = Video(state="stop", size_hint=(1, 1), volume=1.0)
        self.video_container.add_widget(self.video)

        # ── Overlay de controles (começa oculto) ───────────────────────────
        self.overlay = FloatLayout(size_hint=(1, 1), opacity=0)
        with self.overlay.canvas.before:
            Color(0, 0, 0, 0.55)
            self._bg_rect = Rectangle(pos=self.overlay.pos, size=self.overlay.size)
        self.overlay.bind(
            pos=lambda *_: setattr(self._bg_rect, "pos", self.overlay.pos),
            size=lambda *_: setattr(self._bg_rect, "size", self.overlay.size),
        )

        # Voltar — topo esquerdo
        back_btn = MDIconButton(
            icon="arrow-left",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 1),
            md_bg_color=(0, 0, 0, 0),
            pos_hint={"x": 0.01, "top": 0.98},
        )
        back_btn.bind(on_release=lambda x: self._voltar())
        self.overlay.add_widget(back_btn)

        # Play/Pause — centro
        self.play_pause_btn = MDIconButton(
            icon="pause",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 1),
            md_bg_color=(0, 0, 0, 0),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.play_pause_btn.bind(on_release=self._toggle_play_pause)
        self.overlay.add_widget(self.play_pause_btn)

        # Volume (ícone + slider) — base esquerda
        vol_row = MDBoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            width=dp(160),
            height=dp(44),
            pos_hint={"x": 0.02, "y": 0.04},
            spacing=dp(4),
        )
        self.mute_btn = MDIconButton(
            icon="volume-high",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 1),
            md_bg_color=(0, 0, 0, 0),
            size_hint=(None, None),
            width=dp(44),
            height=dp(44),
        )
        self.mute_btn.bind(on_release=self._toggle_mute)
        self.vol_slider = MDSlider(
            min=0, max=1, value=1.0,
            size_hint=(1, None),
            height=dp(30),
        )
        self.vol_slider.bind(value=self._on_volume_change)
        vol_row.add_widget(self.mute_btn)
        vol_row.add_widget(self.vol_slider)
        self.overlay.add_widget(vol_row)

        # Fullscreen — base direita
        self.fs_btn = MDIconButton(
            icon="fullscreen",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 1),
            md_bg_color=(0, 0, 0, 0),
            pos_hint={"right": 0.98, "y": 0.04},
        )
        self.fs_btn.bind(on_release=self._toggle_fullscreen)
        self.overlay.add_widget(self.fs_btn)

        self.video_container.add_widget(self.overlay)

        # ── Informações (abaixo do vídeo) ──────────────────────────────────
        self.info_scroll = MDScrollView(size_hint=(1, None))
        self.info_box = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(8),
            adaptive_height=True,
        )
        self.info_scroll.add_widget(self.info_box)

        # info_area é quem realmente ocupa "o espaço que sobra abaixo do
        # vídeo" perante o `root` (no lugar de info_scroll antes) — assim
        # _toggle_fullscreen continua colapsando/restaurando UM widget só
        # (igual já fazia, sem duplicar a contabilidade que causou o bug
        # do "vídeo voa pra fora da tela"). Por dentro, info_scroll fica do
        # tamanho do CONTEÚDO (sem vazio interno) e um spacer invisível
        # absorve a sobra como fundo neutro — sinopse curta não deixa vazio
        # e o vídeo continua colado no topo (spacer fica abaixo do texto).
        self.info_area = MDBoxLayout(orientation="vertical", size_hint=(1, 1))
        self.info_area.add_widget(self.info_scroll)
        self.info_area.add_widget(Widget(size_hint_y=1))
        self.info_box.bind(height=self._ajustar_altura_info)
        self._ajustar_altura_info()

        # No MDBoxLayout vertical: primeiro adicionado → topo, último → baixo.
        # video_container primeiro (topo), info_area depois (abaixo).
        root.add_widget(self.video_container)
        root.add_widget(self.info_area)

        threading.Thread(target=self._carregar, daemon=True).start()

    # ── Overlay ────────────────────────────────────────────────────────────

    def _show_overlay(self, *args):
        self.overlay.opacity = 1
        self._reset_hide_timer()

    def _hide_overlay_now(self, *args):
        self.overlay.opacity = 0
        if self._hide_event:
            self._hide_event.cancel()
            self._hide_event = None

    def _cancel_hide_timer(self):
        if self._hide_event:
            self._hide_event.cancel()
            self._hide_event = None

    def _reset_hide_timer(self):
        if self._hide_event:
            self._hide_event.cancel()
        self._hide_event = Clock.schedule_once(self._hide_overlay_now, 3)

    def _toggle_play_pause(self, *args):
        if self.video.state == "play":
            self.video.state = "pause"
            self.play_pause_btn.icon = "play"
        else:
            self.video.state = "play"
            self.play_pause_btn.icon = "pause"
        self._reset_hide_timer()

    def _on_volume_change(self, instance, value):
        self.video.volume = value
        if value == 0:
            self.mute_btn.icon = "volume-off"
        elif value < 0.4:
            self.mute_btn.icon = "volume-low"
        else:
            self.mute_btn.icon = "volume-high"

    def _toggle_mute(self, *args):
        if self.video.volume > 0:
            self._last_volume = self.video.volume
            self.vol_slider.value = 0
        else:
            self.vol_slider.value = self._last_volume if self._last_volume > 0 else 1.0
        self._reset_hide_timer()

    def _ajustar_altura_info(self, *_):
        """info_scroll fica do tamanho do CONTEÚDO (info_box), nunca maior —
        sinopse curta não deixa vazio dentro da área de descrição (o spacer
        elástico ao lado de info_scroll absorve a sobra como fundo neutro).
        Um teto (espaço disponível abaixo do vídeo) preserva o comportamento
        antigo para sinopses compridas: para de crescer e vira scroll.
        Não mexe durante o modo cinema — lá _toggle_fullscreen colapsa
        info_area inteiro de propósito (ver comentário lá)."""
        if self.is_fullscreen:
            return
        teto = max(0.0, self._root.height - self.video_container.height)
        self.info_scroll.height = min(self.info_box.height, teto)

    def _toggle_fullscreen(self, *args):
        # "Modo cinema" dentro da própria janela retrato — nunca mexer em
        # Window.size aqui: o app é travado em portrait (buildozer.spec) e
        # trocar as dimensões na mão descasava o layout da tela física.
        if not self.is_fullscreen:
            self.is_fullscreen = True
            self.fs_btn.icon = "fullscreen-exit"
            self.video_container.size_hint = (1, 1)
            # size_hint_y=0 NÃO colapsa no BoxLayout: o Kivy ainda conta o
            # widget como "participante elástico" mas pula o recálculo da
            # altura (in `if sh:`, e 0 é falso) — a altura antiga continuaria
            # reservada e empurraria o vídeo pra fora da tela. Para colapsar
            # de verdade: size_hint_y=None + height=0. Mexe em info_area (o
            # filho direto de root) — info_scroll e o spacer ficam dentro
            # dele e colapsam juntos, sem precisar de contabilidade dupla.
            self.info_area.size_hint_y = None
            self.info_area.height = 0
            self.info_area.opacity = 0
            _set_immersive(True)
        else:
            self.is_fullscreen = False
            self.fs_btn.icon = "fullscreen"
            self.video_container.size_hint = (1, None)
            self.video_container.height = Window.width * 9 / 16
            self.info_area.size_hint_y = 1
            self.info_area.opacity = 1
            self._ajustar_altura_info()
            _set_immersive(False)
        self._reset_hide_timer()

    def on_leave(self):
        """Restaura as barras do Android, não importa por onde se saia da tela."""
        _set_immersive(False)

    # ── Navegação ──────────────────────────────────────────────────────────

    def _voltar(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._hide_event:
            self._hide_event.cancel()
            self._hide_event = None

        self.video.state = "stop"
        try:
            self.video.unload()
        except Exception:
            pass

        self.nav_cb(self.back_to)

    # ── Carregamento e montagem ────────────────────────────────────────────

    def _carregar(self):
        try:
            f = api.filme(self.filme_id)
            self._f = f
            Clock.schedule_once(lambda dt: self._montar(f))
        except Exception as ex:
            Clock.schedule_once(
                lambda dt: self.info_box.add_widget(
                    MDLabel(text=f"Erro: {ex}", theme_text_color="Error")
                )
            )

    def _montar(self, f):
        arquivo = f.get("arquivo_novo", "")

        if arquivo:
            src = api.video_url(arquivo, f.get("needs_transcode", False))
            self.video.source = src
            self.video.state = "play"
            self.play_pause_btn.icon = "pause"

            if not hasattr(self, "_eos_bound"):
                self.video.bind(eos=self._on_fim)
                self._eos_bound = True

        self.info_box.clear_widgets()

        tipo = f.get("tipo", "")

        if tipo == "serie":
            self.info_box.add_widget(
                MDLabel(
                    text=f.get("titulo_pt", ""),
                    theme_text_color="Custom",
                    text_color=ACCENT,
                    font_style="Caption",
                    adaptive_height=True,
                )
            )

        titulo_display = f.get("titulo_pt") or f.get("titulo") or ""

        if tipo == "serie" and arquivo:
            fname = (
                arquivo.replace("\\", "/")
                .split("/")[-1]
                .rsplit(".", 1)[0]
            )
            m = re.search(r"[Ss](\d+)[Ee](\d+)", fname)
            m2 = re.match(r"^(\d+)\s*[-]\s*(.+)", fname)

            if m:
                titulo_display = f"T{m.group(1)}·E{m.group(2).zfill(2)} — {fname}"
            elif m2:
                titulo_display = f"Ep.{m2.group(1)} — {m2.group(2)}"

        self.info_box.add_widget(
            MDLabel(text=titulo_display, font_style="H6", adaptive_height=True)
        )

        meta = " · ".join(filter(None, [
            str(f.get("ano", "")),
            f.get("genero", ""),
            f.get("idioma", "")
        ]))
        self.info_box.add_widget(
            MDLabel(text=meta, theme_text_color="Secondary", adaptive_height=True)
        )

        if f.get("sinopse"):
            self.info_box.add_widget(
                MDLabel(text=f["sinopse"], theme_text_color="Secondary", adaptive_height=True)
            )

        if "dual" in f.get("idioma", "").lower():
            dual_row = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)
            dual_row.add_widget(
                MDLabel(text="Áudio:", adaptive_height=True, size_hint_x=None, width=dp(60))
            )
            for label, track in [("🇧🇷 PT", 0), ("🇬🇧 EN", 1)]:
                btn = MDRaisedButton(
                    text=label,
                    md_bg_color=ACCENT,
                    size_hint=(None, None),
                    height=dp(36),
                )
                btn._track = track
                btn.bind(on_release=self._trocar_audio)
                dual_row.add_widget(btn)
            self.info_box.add_widget(dual_row)

        self.info_box.add_widget(self._star_widget())

    # ── Métodos originais ──────────────────────────────────────────────────

    def _trocar_audio(self, btn):
        f = self._f
        if not f:
            return
        src = api.video_url(f.get("arquivo_novo", ""), True, btn._track)
        pos = self.video.position
        self.video.source = src
        self.video.state = "play"
        self.play_pause_btn.icon = "pause"
        if self.video.duration and self.video.duration > 0:
            self.video.seek(pos / self.video.duration)

    def _star_widget(self):
        box = MDBoxLayout(orientation="horizontal", spacing=dp(4), adaptive_height=True)
        box.add_widget(
            MDLabel(text="Avaliação:", adaptive_height=True, size_hint_x=None, width=dp(80))
        )

        self._star_btns = []
        nota_atual = [api.avaliacao(self.filme_id).get("nota", 0)]

        for i in range(1, 6):
            star = MDIconButton(
                icon="star" if i <= nota_atual[0] else "star-outline",
                theme_icon_color="Custom",
                icon_color=ACCENT if i <= nota_atual[0] else (0.5, 0.5, 0.5, 1),
            )
            star._val = i
            star._nota = nota_atual
            star.bind(on_release=self._tap_star)
            self._star_btns.append(star)
            box.add_widget(star)

        return box

    def _tap_star(self, btn):
        val = btn._val
        btn._nota[0] = val
        for s in self._star_btns:
            s.icon = "star" if s._val <= val else "star-outline"
            s.icon_color = ACCENT if s._val <= val else (0.5, 0.5, 0.5, 1)

        threading.Thread(target=lambda: api.avaliar(self.filme_id, val), daemon=True).start()

    def _on_fim(self, *_):
        if state.next_id:
            self._mostrar_autoplay()
        else:
            self._mostrar_recomendacoes()

    def _mostrar_autoplay(self):
        if self._timer:
            self._timer.cancel()
        self._countdown[0] = 10

        self._countdown_lbl = MDLabel(
            text=f"Próximo em {self._countdown[0]}s", halign="center", adaptive_height=True
        )
        self.info_box.add_widget(self._countdown_lbl)

        btns = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)
        btns.add_widget(MDRaisedButton(
            text="▶ Assistir agora",
            md_bg_color=ACCENT,
            on_release=lambda x: self._ir_proximo(),
        ))
        btns.add_widget(MDFlatButton(
            text="Cancelar",
            on_release=lambda x: self._cancelar(),
        ))
        self.info_box.add_widget(btns)
        self._tick()

    def _tick(self):
        if self._countdown[0] <= 0:
            self._ir_proximo()
            return
        self._countdown[0] -= 1
        if hasattr(self, "_countdown_lbl"):
            self._countdown_lbl.text = f"Próximo em {self._countdown[0]}s"
        self._timer = Clock.schedule_once(lambda dt: self._tick(), 1)

    def _ir_proximo(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self.video.state = "stop"
        try:
            self.video.unload()
        except Exception:
            pass
        self.nav_cb("player", id=state.next_id)

    def _cancelar(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _mostrar_recomendacoes(self):
        def _load():
            recs = api.recomendacoes(self.filme_id)
            Clock.schedule_once(lambda dt, r=recs: self._add_recs(r))
        threading.Thread(target=_load, daemon=True).start()

    def _add_recs(self, recs):
        self.info_box.add_widget(
            MDLabel(text="O que assistir agora?", font_style="Subtitle1", adaptive_height=True)
        )
        row = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)
        for r in recs[:5]:
            fid = r.get("id")
            btn = MDRaisedButton(
                text=(r.get("titulo_pt", "") or "")[:20],
                md_bg_color=ACCENT,
                size_hint=(None, None),
                height=dp(36),
            )
            btn.bind(on_release=lambda x, i=fid: self.nav_cb("player", id=i))
            row.add_widget(btn)
        self.info_box.add_widget(row)
