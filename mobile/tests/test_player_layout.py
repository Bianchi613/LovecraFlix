"""
Testes da tela do player focados no que o usuário reportou quebrado:
posição dos elementos na tela, resposta dos botões, e o modo "tela cheia"
(modo cinema). Não testam reprodução de vídeo em si.

Constroem a PlayerScreen de verdade (api.* mockado — sem servidor/APK),
forçam o layout e *medem* onde cada coisa fica, em vez de adivinhar a
partir de prints. Cada falha mostra os números exatos (posição/tamanho)
em vez de "parece errado".

Rodar:  python tests/test_player_layout.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.core.window import Window
Window.size = (400, 750)

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from kivy.clock import Clock
from kivy.metrics import dp

import api
from store import state


FILME = {
    "id": 1,
    "titulo_pt": "1917",
    "titulo": "1917",
    "ano": 2019,
    "genero": "Guerra",
    "idioma": "Portugues (dublado)",
    "tipo": "filme",
    "arquivo_novo": "C:/fake/1917.mp4",
    "needs_transcode": False,
    "sinopse": (
        "Os cabos Schofield e Blake sao jovens soldados britanicos durante "
        "a Primeira Guerra Mundial. Quando eles sao encarregados de uma "
        "missao aparentemente impossivel, os dois precisam atravessar "
        "territorio inimigo, lutando contra o tempo, para entregar uma "
        "mensagem que pode salvar cerca de 1600 colegas de batalhao."
    ),
}


def _build_screen():
    """Cria a PlayerScreen com api mockada (sem rede), espera _montar
    popular o info_box e força várias passadas de layout."""
    api.filme = lambda fid: FILME
    api.avaliacao = lambda fid: {"nota": 0}
    api.video_url = lambda *a, **k: ""
    api.recomendacoes = lambda fid: []
    state.token = "fake-token-de-teste"
    state.next_id = None

    _limpar_janela()  # cada teste monta sua própria tela — sem sobras na Window

    from screens.player import PlayerScreen
    screen = PlayerScreen(nav_cb=lambda *a, **k: None, filme_id=1)

    # Monta exatamente como o main.py faz (ScreenManager dentro da Window) —
    # sem isso a tela nunca recebe o tamanho real da janela e fica 100x100
    # (default do Kivy), o que produz números sem sentido.
    sm = ScreenManager()
    sm.add_widget(screen)
    sm.current = screen.name
    Window.add_widget(sm)

    deadline = time.time() + 5
    while not screen.info_box.children and time.time() < deadline:
        Clock.tick()
        time.sleep(0.01)
    if not screen.info_box.children:
        raise RuntimeError("_montar não populou info_box em 5s — algo travou no carregamento")

    for _ in range(6):
        Clock.tick()
        screen.do_layout()
        screen._root.do_layout()
        screen.video_container.do_layout()
        screen.info_box.do_layout()

    screen._sm = sm  # mantém vivo + permite limpeza entre testes
    return screen


def _limpar_janela():
    for child in list(Window.children):
        Window.remove_widget(child)


def _fmt(label, w):
    print(f"  {label:16s} pos=({w.x:7.1f},{w.y:7.1f})  size=({w.width:6.1f}x{w.height:6.1f})  top={w.top:7.1f}  right={w.right:7.1f}")


def _retangulo_na_janela(widget):
    """pos/right/top de `widget` convertidos para coordenadas de JANELA.
    Necessário porque widget.pos é sempre relativo ao PAI — e um RelativeLayout
    no meio do caminho (como o video_container, de propósito) faz os filhos
    "pularem" para um sistema de coordenadas local. Comparar dois widgets que
    não compartilham o mesmo pai-de-referência só é válido depois de converter
    ambos pra um referencial comum: a janela."""
    x, y = widget.to_window(widget.x, widget.y)
    r, t = widget.to_window(widget.right, widget.top)
    return x, y, r, t


def _dentro(widget, area):
    wx, wy = widget.to_window(*widget.center)
    ax, ay, ar, atop = _retangulo_na_janela(area)
    return ax <= wx <= ar and ay <= wy <= atop


def _checar_botoes_dentro_da_area(screen, area, contexto):
    """Verifica se cada botão do overlay cai dentro de `area` (a região
    onde o usuário de fato vê e toca o vídeo), MEDINDO NA JANELA — onde o
    toque realmente acontece. Se a área errar de tamanho/posição na tela,
    os botões saem do alvo dos toques — 'os botões não funcionam'."""
    ax, ay, ar, atop = _retangulo_na_janela(area)
    botoes = {
        "voltar": screen.overlay.children[-1],
        "play/pause": screen.play_pause_btn,
        "mute": screen.mute_btn,
        "fullscreen": screen.fs_btn,
    }
    for nome, btn in botoes.items():
        _fmt(f"  [{contexto}] {nome}", btn)
        wx, wy = btn.to_window(*btn.center)
        assert _dentro(btn, area), (
            f"[{contexto}] botão '{nome}' aparece na tela em ({wx:.1f}, {wy:.1f}), "
            f"FORA da área tocável do vídeo na tela "
            f"(x:{ax:.1f}-{ar:.1f}, y:{ay:.1f}-{atop:.1f}) "
            f"— um toque na posição visível do botão não vai acioná-lo"
        )


def test_video_no_topo_info_logo_abaixo_sem_overlap_sem_gap():
    """Vídeo deve ficar no topo da tela e a área de informações logo
    abaixo, sem espaço vazio nem sobreposição entre os dois."""
    print("\n[1] posição: vídeo em cima, info embaixo, contíguos (sem overlap/gap)")
    screen = _build_screen()
    vc, isc = screen.video_container, screen.info_scroll
    _fmt("video_container", vc)
    _fmt("info_scroll", isc)

    assert vc.y > isc.y, (
        f"video_container (y={vc.y:.1f}) deveria estar ACIMA de info_scroll "
        f"(y={isc.y:.1f}) — layout estilo Netflix exige vídeo no topo"
    )
    overlap = isc.top - vc.y
    assert overlap <= 0.5, (
        f"video_container e info_scroll se SOBREPÕEM em {overlap:.1f}px "
        f"(video.y={vc.y:.1f}, info.top={isc.top:.1f}) — 'a descrição "
        f"sobrescrevendo o vídeo'"
    )
    gap = vc.y - isc.top
    assert gap <= 1.0, (
        f"espaço vazio de {gap:.1f}px ENTRE os widgets "
        f"(video.y={vc.y:.1f}, info.top={isc.top:.1f}) — 'espaço enorme "
        f"entre a descrição e o vídeo'"
    )
    print(f"  -> OK (overlap={overlap:.1f}px, gap={gap:.1f}px)")


def test_info_scroll_nao_reserva_vazio_gigante():
    """A área de informações não deveria ser muito maior que o conteúdo
    real — isso aparece visualmente como um vazio enorme dentro dela."""
    print("\n[2] posição: info_scroll não sobra um vazio gigante por dentro")
    screen = _build_screen()
    isc, box = screen.info_scroll, screen.info_box
    _fmt("info_scroll", isc)
    _fmt("info_box (conteúdo)", box)

    folga = isc.height - box.height
    print(f"  folga (scroll - conteúdo): {folga:.1f}px")
    assert folga <= dp(80), (
        f"info_scroll tem {isc.height:.1f}px de altura mas o conteúdo só "
        f"ocupa {box.height:.1f}px — sobram {folga:.1f}px de área vazia "
        f"dentro do scroll, visualmente o 'espaço enorme que não faz sentido'"
    )
    print(f"  -> OK (folga de {folga:.1f}px é razoável)")


def test_botoes_modo_normal_caem_dentro_do_video():
    """No modo normal (retrato), os botões do overlay devem cair dentro
    da área do vídeo — onde o usuário realmente vê e toca."""
    print("\n[3] botões: posição correta no modo normal")
    screen = _build_screen()
    _checar_botoes_dentro_da_area(screen, screen.video_container, "normal")
    print("  -> OK")


def test_botoes_modo_cinema_caem_dentro_do_video_expandido():
    """Ao entrar em modo cinema (tela cheia), os botões precisam continuar
    dentro da nova área (agora maior) do vídeo — senão o usuário entra em
    fullscreen e perde a capacidade de tocar nos controles."""
    print("\n[4] botões: posição correta dentro do modo cinema")
    screen = _build_screen()
    win_antes = tuple(Window.size)

    screen._toggle_fullscreen()
    for _ in range(4):
        Clock.tick()
        screen._root.do_layout()
        screen.video_container.do_layout()

    vc = screen.video_container
    _fmt("video_container (cinema)", vc)
    assert tuple(Window.size) == win_antes, "modo cinema não deve alterar Window.size"
    assert screen.is_fullscreen is True

    # Não basta o TAMANHO bater com a tela — a POSIÇÃO também precisa.
    # (silenciosamente comparar só a altura deixa passar o vídeo do tamanho
    # certo só que deslocado/pra fora da área visível — exatamente o jeito
    # como esse bug já escapou de uma checagem mais fraca antes)
    tela = _retangulo_na_janela(screen._root)
    area = _retangulo_na_janela(vc)
    print(f"  tela visível (janela): x:{tela[0]:.1f}-{tela[2]:.1f}  y:{tela[1]:.1f}-{tela[3]:.1f}")
    print(f"  video_container (janela): x:{area[0]:.1f}-{area[2]:.1f}  y:{area[1]:.1f}-{area[3]:.1f}")
    assert all(abs(a - b) < 1.0 for a, b in zip(area, tela)), (
        f"em modo cinema o video_container deveria cobrir a tela toda, mas "
        f"na JANELA ele ocupa x:{area[0]:.1f}-{area[2]:.1f} y:{area[1]:.1f}-{area[3]:.1f} "
        f"enquanto a tela visível é x:{tela[0]:.1f}-{tela[2]:.1f} y:{tela[1]:.1f}-{tela[3]:.1f} "
        f"— o vídeo fica deslocado/cortado para fora da área visível"
    )
    _checar_botoes_dentro_da_area(screen, vc, "cinema")

    screen._toggle_fullscreen()
    for _ in range(4):
        Clock.tick()
        screen._root.do_layout()
    assert screen.is_fullscreen is False
    print("  -> OK (entra, posiciona botões certo, e volta)")


def test_botao_play_pause_funciona():
    """Tocar o botão play/pause precisa de fato alternar o estado do
    vídeo e o ícone — não só existir no lugar certo."""
    print("\n[5] função: play/pause realmente alterna o vídeo")
    screen = _build_screen()
    screen.video.state = "play"
    screen.play_pause_btn.icon = "pause"

    screen.play_pause_btn.dispatch("on_release")
    assert screen.video.state == "pause", f"esperava 'pause', veio '{screen.video.state}'"
    assert screen.play_pause_btn.icon == "play", f"ícone não trocou: '{screen.play_pause_btn.icon}'"

    screen.play_pause_btn.dispatch("on_release")
    assert screen.video.state == "play", f"esperava 'play', veio '{screen.video.state}'"
    assert screen.play_pause_btn.icon == "pause"
    print("  -> OK (play <-> pause + ícone)")


def test_botao_voltar_funciona():
    """Tocar 'voltar' precisa parar o vídeo e navegar de volta — sem
    travar mesmo se o vídeo nunca carregou (unload pode falhar)."""
    print("\n[6] função: botão voltar para o vídeo e navega")
    screen = _build_screen()
    destinos = []
    screen.nav_cb = lambda dest, **kw: destinos.append(dest)

    screen.overlay.children[-1].dispatch("on_release")  # back_btn
    assert screen.video.state == "stop"
    assert destinos == ["home"], f"esperava navegar para 'home', navegou para {destinos}"
    print("  -> OK (para o vídeo + navega para 'home')")


def test_botao_fullscreen_alterna_modo_cinema():
    """Tocar o botão de fullscreen precisa de fato alternar is_fullscreen
    (e não só mudar o ícone)."""
    print("\n[7] função: botão fullscreen alterna o modo cinema")
    screen = _build_screen()
    assert screen.is_fullscreen is False

    screen.fs_btn.dispatch("on_release")
    assert screen.is_fullscreen is True
    assert screen.fs_btn.icon == "fullscreen-exit"

    screen.fs_btn.dispatch("on_release")
    assert screen.is_fullscreen is False
    assert screen.fs_btn.icon == "fullscreen"
    print("  -> OK (alterna is_fullscreen + ícone nos dois sentidos)")


def _run(fn):
    try:
        fn()
        print(f"PASS: {fn.__name__}")
        return True
    except AssertionError as e:
        print(f"FAIL: {fn.__name__}\n  {e}")
        return False
    except Exception as e:
        import traceback
        print(f"ERRO: {fn.__name__}\n  {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    app = MDApp()
    app.theme_cls.theme_style = "Dark"
    app.theme_cls.primary_palette = "DeepPurple"
    from kivy.base import EventLoop
    EventLoop.ensure_window()
    Window.size = (400, 750)
    Clock.tick()
    print(f"Window.size pedido: (400, 750)  |  Window.size real: {tuple(Window.size)}")
    if tuple(Window.size) != (400, 750):
        print(
            "  (!) o Kivy ajustou para o DPI da tela — é o que vai acontecer "
            "no app real também, então os testes calculam tudo a partir do "
            "Window.size REAL, igual o código de produção faz."
        )

    testes = [
        test_video_no_topo_info_logo_abaixo_sem_overlap_sem_gap,
        test_info_scroll_nao_reserva_vazio_gigante,
        test_botoes_modo_normal_caem_dentro_do_video,
        test_botoes_modo_cinema_caem_dentro_do_video_expandido,
        test_botao_play_pause_funciona,
        test_botao_voltar_funciona,
        test_botao_fullscreen_alterna_modo_cinema,
    ]
    resultados = [_run(t) for t in testes]
    print(f"\n{'='*60}\n{sum(resultados)}/{len(resultados)} passaram")
    sys.exit(0 if all(resultados) else 1)
