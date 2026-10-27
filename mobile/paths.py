"""Rutas de datos y acceso a archivos específicos de Android.

Este módulo concentra lo que de verdad depende de la plataforma:

- Dónde vive la base SQLite: el directorio privado de datos de la app
  (`App.user_data_dir` en Android), nunca una ruta de Windows ni el interior
  del APK.
- Cómo exportar/importar archivos mediante el Storage Access Framework (SAF):
  las URI `content://` se tratan como flujos que hay que copiar, no como
  rutas de archivo convencionales.

En escritorio (necesario para poder probar la interfaz Kivy sin un
dispositivo Android) se ofrece un selector de archivos propio de Kivy
(`FileChooser`), nunca Tkinter, para no introducir una dependencia exclusiva
de Windows en este paquete.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from kivy.utils import platform

import core

SUFFIX_BACKUP = ".sqlite3"


def data_directory() -> Path:
    """Directorio privado de datos de la app (ver sección 7 del encargo).

    En Android, `App.user_data_dir` es interno a la aplicación: se borra al
    desinstalar, por eso la interfaz insiste en conservar copias externas
    antes de desinstalar o actualizar. Fuera de Android (desarrollo o
    pruebas manuales de esta interfaz en un PC) se reutiliza el mismo
    directorio base que la versión Windows, en una subcarpeta separada para
    no mezclar datos de prueba con los de la app de escritorio.
    """
    if platform == "android":
        from kivy.app import App
        root = Path(App.get_running_app().user_data_dir)
    else:
        root = core.data_directory() / "mobile_dev"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _content_resolver():
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    return PythonActivity.mActivity.getContentResolver()


def import_from_uri(uri_string: str, destination: Path) -> Path:
    """Copia el contenido de una URI (típicamente `content://`) a un archivo
    local. No se asume nunca que la URI sea una ruta de archivo."""
    if platform == "android":
        from jnius import autoclass
        Uri = autoclass("android.net.Uri")
        stream = _content_resolver().openInputStream(Uri.parse(uri_string))
        try:
            with destination.open("wb") as out:
                while True:
                    chunk = stream.read(65536)
                    if chunk is None or len(chunk) == 0:
                        break
                    out.write(bytes(chunk))
        finally:
            stream.close()
    else:
        shutil.copyfile(uri_string, destination)
    return destination


def export_to_uri(source: Path, uri_string: str) -> None:
    """Copia un archivo local ya generado (p. ej. una copia de seguridad
    hecha con `Store.backup`) al destino `content://` elegido por SAF."""
    if platform == "android":
        from jnius import autoclass
        Uri = autoclass("android.net.Uri")
        stream = _content_resolver().openOutputStream(Uri.parse(uri_string))
        try:
            with source.open("rb") as inp:
                while True:
                    chunk = inp.read(65536)
                    if not chunk:
                        break
                    stream.write(chunk)
            stream.flush()
        finally:
            stream.close()
    else:
        shutil.copyfile(source, uri_string)


def share_file(path: Path, mimetype="application/octet-stream"):
    """Comparte o abre un archivo ya generado (informe, CSV) con las apps
    instaladas en el dispositivo. En escritorio, usa el navegador/visor
    predeterminado como hace la versión Windows."""
    if platform == "android":
        from plyer import share
        share.share(filepath=str(path), mimetype=mimetype)
    else:
        import webbrowser
        webbrowser.open(Path(path).resolve().as_uri())


def pick_file_to_import(callback, title="Elegir una copia de seguridad"):
    """Selector de ARCHIVO EXISTENTE (restaurar). Llama a `callback(uri_o_ruta)`
    o `callback(None)` si se cancela."""
    if platform == "android":
        from plyer import filechooser
        filechooser.open_file(
            title=title, on_selection=lambda sel: callback(sel[0] if sel else None),
            filters=[("Copia TKD", "*.sqlite3")])
    else:
        _desktop_chooser(callback, title)


def pick_destination_to_export(callback, suggested_name, title="Guardar copia de seguridad"):
    """Selector de DESTINO (crear copia). Llama a `callback(uri_o_ruta)` o
    `callback(None)` si se cancela."""
    if platform == "android":
        from plyer import filechooser
        filechooser.save_file(
            title=title, filename=suggested_name,
            on_selection=lambda sel: callback(sel[0] if sel else None))
    else:
        _desktop_chooser(callback, title, save_as=suggested_name)


def _desktop_chooser(callback, title, save_as=None):
    """Selector de archivos propio de Kivy para desarrollo/pruebas en
    escritorio (NO se usa en Android: allí se emplea SAF mediante plyer)."""
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.filechooser import FileChooserListView
    from kivy.uix.popup import Popup
    from kivy.uix.textinput import TextInput

    layout = BoxLayout(orientation="vertical", spacing=6, padding=6)
    chooser = FileChooserListView(path=str(data_directory()), filters=["*.sqlite3"])
    layout.add_widget(chooser)
    name_input = None
    if save_as:
        name_input = TextInput(text=save_as, multiline=False, size_hint_y=None, height="44dp")
        layout.add_widget(name_input)
    buttons = BoxLayout(size_hint_y=None, height="48dp", spacing=6)
    layout.add_widget(buttons)
    popup = Popup(title=title, content=layout, size_hint=(0.95, 0.95))

    def confirm(_btn):
        if save_as:
            folder = chooser.path
            result = str(Path(folder) / (name_input.text or save_as))
        else:
            result = chooser.selection[0] if chooser.selection else None
        popup.dismiss()
        callback(result)

    def cancel(_btn):
        popup.dismiss()
        callback(None)

    buttons.add_widget(Button(text="Cancelar", on_release=cancel))
    buttons.add_widget(Button(text="Elegir", on_release=confirm))
    popup.open()
