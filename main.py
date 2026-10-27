"""Punto de entrada de la aplicación Android (Kivy) de TKD Entrenador.

Ejecutar en escritorio para desarrollo/pruebas de la interfaz (sin
dispositivo): `python main.py` (requiere `pip install kivy`; ver
BUILD_ANDROID.md). Para el APK, Buildozer usa este mismo archivo como
`main.py` del proyecto.

No importa Tkinter ni nada exclusivo de Windows: toda la lógica compartida
viene de core.py; lo propio de Android está en el paquete `mobile`.
"""
from kivy.config import Config
# "Pause mode" entrega on_pause/on_resume reales en vez de detener la app
# al cambiar de aplicación o bloquear la pantalla (ver api-kivy.app.html).
Config.set("kivy", "pause_on_minimize", "1")

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.uix.scrollview import ScrollView

import core
from mobile import paths, screens
from mobile.widgets import DraftStore


class EntrenadorApp(App):
    title = "TKD Entrenador"

    def build(self):
        self.athlete_id = None
        self.store = None
        self._history = []
        Window.bind(on_keyboard=self._on_keyboard)

        root = BoxLayout(orientation="vertical")
        self.manager = ScreenManager(transition=NoTransition())
        for name, cls in screens.SCREENS:
            self.manager.add_widget(cls(name=name))

        nav_scroll = ScrollView(size_hint_y=None, height="56dp", do_scroll_y=False)
        nav = BoxLayout(size_hint_x=None, spacing=4, padding=4)
        nav.bind(minimum_width=nav.setter("width"))
        for name, _cls in screens.SCREENS:
            nav.add_widget(Button(text=screens.NAV_LABELS[name], size_hint_x=None, width="120dp",
                                   on_release=lambda *_a, n=name: self.goto(n)))
        nav_scroll.add_widget(nav)

        root.add_widget(self.manager)
        root.add_widget(nav_scroll)
        return root

    def on_start(self):
        # Base SQLite en el directorio privado de datos de la app (sección 7).
        self.store = core.Store(paths.data_directory() / "tkd_entrenador.sqlite3")
        self.drafts = DraftStore(paths.data_directory() / "borradores.json")
        self.goto("inicio")

    # -- Selección de deportista, compartida por todas las pantallas --------
    def current_athlete(self):
        if not self.athlete_id or not self.store:
            return None
        try:
            return self.store.athlete(self.athlete_id)
        except ValueError:
            self.athlete_id = None
            return None

    def select_athlete(self, athlete_id):
        self.athlete_id = athlete_id

    def reload_athlete(self):
        """Tras restaurar una copia, el id puede ya no existir o referirse
        a otro registro; se obliga a elegir de nuevo."""
        self.athlete_id = None

    # -- Navegación -----------------------------------------------------------
    def goto(self, name, record_history=True):
        if record_history and self.manager.current and self.manager.current != name:
            self._history.append(self.manager.current)
        self.manager.current = name

    def _on_keyboard(self, _window, key, *_args):
        if key != 27:  # botón Atrás de Android
            return False
        if self._history:
            self.goto(self._history.pop(), record_history=False)
            return True
        return False  # en Inicio, deja que Android envíe la app a segundo plano

    # -- Ciclo de vida ----------------------------------------------------------
    def on_pause(self):
        # Android puede terminar el proceso en segundo plano; los borradores ya
        # se escriben en cada cambio de campo (ver mobile/widgets.py) y cada
        # operación confirmada en Store se guarda de inmediato, sin depender
        # de on_stop.
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        if self.store:
            self.store.db.close()


if __name__ == "__main__":
    EntrenadorApp().run()
