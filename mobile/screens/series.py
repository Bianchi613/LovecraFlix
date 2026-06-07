import threading, re
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.list import MDList, TwoLineListItem
from kivymd.uix.toolbar import MDTopAppBar
from kivy.metrics import dp
from kivy.clock import Clock
from store import state, ACCENT
import api


def _ep_titulo(arq):
    fname = arq.replace("\\","/").split("/")[-1].rsplit(".",1)[0] if arq else ""
    m  = re.search(r"[Ss](\d+)[Ee](\d+)", fname)
    m2 = re.match(r"^(\d+)\s*[-]\s*(.+)", fname)
    if m:  return f"T{m.group(1)}·E{m.group(2).zfill(2)}", fname
    if m2: return f"Ep.{m2.group(1)}", m2.group(2).strip()
    return "", fname


class EpList(MDScreen):
    def __init__(self, titulo, nav_cb, loader_fn, **kw):
        super().__init__(**kw)
        self.nav_cb = nav_cb

        root = MDBoxLayout(orientation="vertical")
        self.add_widget(root)

        bar = MDTopAppBar(title=titulo, md_bg_color=ACCENT)
        bar.left_action_items = [["arrow-left", lambda x: nav_cb("home")]]
        root.add_widget(bar)

        scroll = MDScrollView()
        self.lst = MDList()
        scroll.add_widget(self.lst)
        root.add_widget(scroll)

        threading.Thread(target=lambda: self._load(loader_fn), daemon=True).start()

    def _load(self, loader_fn):
        try:
            eps = loader_fn()
            Clock.schedule_once(lambda dt, e=eps: self._montar(e))
        except Exception as ex:
            msg = str(ex)
            Clock.schedule_once(lambda dt, m=msg: self.lst.add_widget(
                MDLabel(text=f"Erro: {m}", theme_text_color="Error")))

    def _montar(self, eps):
        self.lst.clear_widgets()
        all_eps = eps
        for i, ep in enumerate(eps):
            arq  = ep.get("arquivo_novo","")
            num, titulo = _ep_titulo(arq)
            next_ep = all_eps[i+1] if i+1 < len(all_eps) else None
            item = TwoLineListItem(
                text=f"{num}  {titulo}" if num else titulo,
                secondary_text=ep.get("idioma",""),
            )
            item._ep      = ep
            item._next_ep = next_ep
            item.bind(on_release=lambda x, e=ep, n=next_ep: self._tap(e, n))
            self.lst.add_widget(item)

    def _tap(self, ep, next_ep):
        state.filme_atual = ep
        if next_ep:
            state.next_id    = next_ep.get("id")
            nf = next_ep.get("arquivo_novo","")
            state.next_titulo = nf.replace("\\","/").split("/")[-1].rsplit(".",1)[0] if nf else ""
        else:
            state.next_id    = None
            state.next_titulo = ""
        self.nav_cb("player", id=ep.get("id"))


class SerieScreen(EpList):
    def __init__(self, nav_cb, pasta, nome, **kw):
        super().__init__(
            titulo=nome, nav_cb=nav_cb,
            loader_fn=lambda: api.episodios_serie(pasta),
            name="serie", **kw
        )


class ColecaoScreen(EpList):
    def __init__(self, nav_cb, colecao, **kw):
        super().__init__(
            titulo=colecao, nav_cb=nav_cb,
            loader_fn=lambda: api.episodios_colecao(colecao),
            name="colecao", **kw
        )


class VersoesScreen(MDScreen):
    def __init__(self, nav_cb, item, versoes, **kw):
        super().__init__(name="versoes", **kw)
        self.nav_cb = nav_cb

        root = MDBoxLayout(orientation="vertical")
        self.add_widget(root)

        bar = MDTopAppBar(title=item.get("titulo_pt","") if item else "",
                           md_bg_color=ACCENT)
        bar.left_action_items = [["arrow-left", lambda x: nav_cb("home")]]
        root.add_widget(bar)

        root.add_widget(MDLabel(text="Escolha a versão:", padding=(dp(16),dp(8)),
                                  adaptive_height=True))

        scroll = MDScrollView()
        lst = MDList()
        scroll.add_widget(lst)
        root.add_widget(scroll)

        tem_partes = any(v.get("parte") for v in versoes)
        for i, v in enumerate(versoes):
            fname  = (v.get("arquivo_novo","")).replace("\\","/").split("/")[-1]
            rotulo = f"Parte {v['parte']}" if tem_partes and v.get("parte") else (v.get("idioma") or "Versão")
            next_v = versoes[i+1] if tem_partes and i+1 < len(versoes) else None

            item2 = TwoLineListItem(text=rotulo, secondary_text=fname)
            item2.bind(on_release=lambda x, vv=v, nv=next_v: self._tap(vv, nv))
            lst.add_widget(item2)

    def _tap(self, v, next_v):
        state.filme_atual = v
        if next_v:
            state.next_id    = next_v.get("id")
            state.next_titulo = f"Parte {next_v.get('parte','')}" if next_v.get("parte") else ""
        else:
            state.next_id = None
        self.nav_cb("player", id=v.get("id"))
