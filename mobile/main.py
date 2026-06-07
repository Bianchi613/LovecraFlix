"""LovecraFlix — App Android com KivyMD"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.utils import platform
from store import state, load

# Simula tamanho de celular no PC (no Android o app já roda em tela cheia)
if platform not in ("android", "ios"):
    Window.size = (400, 750)
from screens.login   import LoginScreen
from screens.home    import HomeScreen
from screens.welcome import WelcomeScreen


class LovecraFlixApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.primary_hue     = "700"
        self.title = "LovecraFlix"

        load()

        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.add_widget(WelcomeScreen(nav_cb=self.navigate))
        self.sm.add_widget(LoginScreen(nav_cb=self.navigate))
        self.sm.add_widget(HomeScreen(nav_cb=self.navigate))

        self.sm.current = "home" if state.token else "welcome"
        return self.sm

    def navigate(self, dest, **kwargs):
        from kivy.clock import Clock

        if dest == "player":
            from screens.player import PlayerScreen
            if self.sm.has_screen("player"):
                self.sm.remove_widget(self.sm.get_screen("player"))
            self.sm.add_widget(PlayerScreen(nav_cb=self.navigate,
                                             filme_id=kwargs.get("id"),
                                             back_to="home"))
            self.sm.current = "player"

        elif dest == "serie":
            from screens.series import SerieScreen
            if self.sm.has_screen("serie"):
                self.sm.remove_widget(self.sm.get_screen("serie"))
            self.sm.add_widget(SerieScreen(nav_cb=self.navigate,
                                            pasta=kwargs.get("pasta",""),
                                            nome=kwargs.get("nome","")))
            self.sm.current = "serie"

        elif dest == "colecao":
            from screens.series import ColecaoScreen
            if self.sm.has_screen("colecao"):
                self.sm.remove_widget(self.sm.get_screen("colecao"))
            self.sm.add_widget(ColecaoScreen(nav_cb=self.navigate,
                                              colecao=kwargs.get("colecao","")))
            self.sm.current = "colecao"

        elif dest == "versoes":
            from screens.series import VersoesScreen
            if self.sm.has_screen("versoes"):
                self.sm.remove_widget(self.sm.get_screen("versoes"))
            self.sm.add_widget(VersoesScreen(nav_cb=self.navigate,
                                              item=kwargs.get("item"),
                                              versoes=kwargs.get("versoes",[])))
            self.sm.current = "versoes"

        elif dest == "perfil":
            from screens.perfil import PerfilScreen
            if self.sm.has_screen("perfil"):
                self.sm.remove_widget(self.sm.get_screen("perfil"))
            self.sm.add_widget(PerfilScreen(nav_cb=self.navigate))
            self.sm.current = "perfil"

        elif dest == "home":
            self.sm.current = "home"

        elif dest == "login":
            self.sm.current = "login"

        elif dest == "cadastro":
            from screens.cadastro import CadastroScreen
            if self.sm.has_screen("cadastro"):
                self.sm.remove_widget(self.sm.get_screen("cadastro"))
            self.sm.add_widget(CadastroScreen(nav_cb=self.navigate))
            self.sm.current = "cadastro"

        elif dest == "welcome":
            self.sm.current = "welcome"


if __name__ == "__main__":
    LovecraFlixApp().run()
