"""Componentes táctiles reutilizables para la interfaz Android.

Reproduce, con widgets de Kivy, el mismo patrón de formulario validado que
`Form` en app.py (Tkinter): un conjunto de campos, una función `on_save` que
valida contra `core.py`/`Store` y puede lanzar `ValueError`, y un mensaje de
resultado opcional. Aquí además se añaden: botones y campos grandes para uso
táctil, teclado numérico en campos numéricos, prevención de doble envío por
toques repetidos y conservación de borradores entre pausas de la app.
"""
from __future__ import annotations

import json
from pathlib import Path

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

BIG_FONT = "20sp"
FIELD_HEIGHT = "52dp"

_DECIMAL_CHARS = set("0123456789.,-")


def _decimal_filter(value, _from_undo):
    """Filtro de teclado numérico que ACEPTA coma decimal (requisito de la
    sección 4). El filtro 'float' integrado de Kivy solo admite el punto y
    bloquearía los teclados numéricos en español, que muestran coma. La
    validación real de número y signo ocurre en `core.number` al guardar."""
    return "".join(ch for ch in value if ch in _DECIMAL_CHARS)


class DraftStore:
    """Persiste borradores de formularios sin confirmar en un archivo JSON,
    separados de los registros definitivos guardados en SQLite.

    Android puede terminar el proceso en segundo plano; guardar en cada
    cambio de campo (en vez de solo en `on_pause`) evita perder el borrador
    incluso si el sistema no llega a avisar antes de matar el proceso.
    """
    def __init__(self, path: Path):
        self.path = Path(path)

    def _read_all(self):
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}

    def save(self, key, values: dict):
        data = self._read_all()
        data[key] = values
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load(self, key):
        return self._read_all().get(key)

    def clear(self, key):
        data = self._read_all()
        if key in data:
            del data[key]
            self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def big_button(text, **kwargs):
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("height", "56dp")
    kwargs.setdefault("font_size", BIG_FONT)
    return Button(text=text, **kwargs)


class InfoPopup(Popup):
    """Reemplazo táctil de messagebox: un aviso con botón Aceptar."""
    def __init__(self, title, message, **kwargs):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=16)
        scroll = ScrollView()
        label = Label(text=message, font_size=BIG_FONT, size_hint_y=None,
                      halign="left", valign="top")
        label.bind(width=lambda *_: label.setter("text_size")(label, (label.width, None)))
        label.bind(texture_size=lambda *_: setattr(label, "height", label.texture_size[1]))
        scroll.add_widget(label)
        layout.add_widget(scroll)
        layout.add_widget(big_button("Aceptar", on_release=lambda *_: self.dismiss()))
        super().__init__(title=title, content=layout, size_hint=(0.9, 0.8), **kwargs)


class ConfirmPopup(Popup):
    """Confirmación explícita (anular registro, restaurar copia, etc.)."""
    def __init__(self, title, message, on_confirm, **kwargs):
        layout = BoxLayout(orientation="vertical", spacing=10, padding=16)
        label = Label(text=message, font_size=BIG_FONT)
        layout.add_widget(label)
        buttons = BoxLayout(size_hint_y=None, height="56dp", spacing=10)
        buttons.add_widget(big_button("Cancelar", on_release=lambda *_: self.dismiss()))

        def confirm(_btn):
            self.dismiss()
            on_confirm()
        buttons.add_widget(big_button("Confirmar", on_release=confirm))
        layout.add_widget(buttons)
        super().__init__(title=title, content=layout, size_hint=(0.9, 0.5), **kwargs)


class FormPopup(Popup):
    """Formulario táctil validado. `fields`: lista de tuplas
    (clave, etiqueta, valor_inicial, opciones_o_None[, es_numerico]).
    `on_save(valores)` valida y persiste; puede lanzar ValueError o
    devolver un texto de resultado (igual que `Form` en app.py)."""

    def __init__(self, title, fields, on_save, help_text="", draft_key=None,
                 draft_store: DraftStore = None, **kwargs):
        self._on_save = on_save
        self._saving = False
        self._draft_key = draft_key
        self._draft_store = draft_store
        self.inputs = {}

        outer = BoxLayout(orientation="vertical", spacing=8, padding=12)
        if help_text:
            help_label = Label(text=help_text, size_hint_y=None, font_size="14sp",
                                color=(0.3, 0.3, 0.3, 1))
            help_label.bind(width=lambda *_: help_label.setter("text_size")(help_label, (help_label.width, None)))
            help_label.bind(texture_size=lambda *_: setattr(help_label, "height", help_label.texture_size[1] + 8))
            outer.add_widget(help_label)

        draft = draft_store.load(draft_key) if (draft_key and draft_store) else None
        if draft:
            banner = BoxLayout(size_hint_y=None, height="40dp", spacing=6)
            banner.add_widget(Label(text="Hay un borrador sin guardar; se restauró abajo.", font_size="13sp"))
            banner.add_widget(Button(text="Descartar", size_hint_x=None, width="110dp",
                                      on_release=lambda *_: self._discard_draft()))
            outer.add_widget(banner)

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=(0, 6))
        grid.bind(minimum_height=grid.setter("height"))

        for spec in fields:
            key, label, initial, options = spec[:4]
            numeric = spec[4] if len(spec) > 4 else False
            value = draft.get(key, initial) if draft else initial
            field_label = Label(text=label, size_hint_y=None, height="26dp", font_size="14sp")
            grid.add_widget(field_label)
            if options:
                widget = Spinner(text=str(value) if value in options else options[0],
                                  values=[str(o) for o in options], size_hint_y=None,
                                  height=FIELD_HEIGHT, font_size="16sp")
            else:
                widget = TextInput(text="" if value is None else str(value), multiline=False,
                                    size_hint_y=None, height=FIELD_HEIGHT, font_size="16sp",
                                    input_filter=(_decimal_filter if numeric else None),
                                    input_type=("number" if numeric else "text"),
                                    write_tab=False)
            widget.bind(text=lambda inst, val, k=key: self._on_field_change(k, val))
            self.inputs[key] = widget
            grid.add_widget(widget)
        scroll.add_widget(grid)
        outer.add_widget(scroll)

        self.error_label = Label(text="", color=(0.8, 0.1, 0.1, 1), size_hint_y=None,
                                  height="0dp", font_size="14sp")
        outer.add_widget(self.error_label)

        buttons = BoxLayout(size_hint_y=None, height="56dp", spacing=10)
        buttons.add_widget(big_button("Cancelar", on_release=lambda *_: self.dismiss()))
        self.save_button = big_button("Guardar", on_release=self._save)
        buttons.add_widget(self.save_button)
        outer.add_widget(buttons)

        super().__init__(title=title, content=outer, size_hint=(0.95, 0.9), **kwargs)

    def _on_field_change(self, key, value):
        if not (self._draft_key and self._draft_store):
            return
        values = {k: (w.text if hasattr(w, "text") else "") for k, w in self.inputs.items()}
        self._draft_store.save(self._draft_key, values)

    def _discard_draft(self):
        if self._draft_key and self._draft_store:
            self._draft_store.clear(self._draft_key)
        self.dismiss()

    def _save(self, _btn):
        if self._saving:
            return  # evita registros duplicados por toques repetidos sobre Guardar
        self._saving = True
        self.save_button.disabled = True
        try:
            values = {k: w.text for k, w in self.inputs.items()}
            result = self._on_save(values)
            if self._draft_key and self._draft_store:
                self._draft_store.clear(self._draft_key)
            self.dismiss()
            InfoPopup("Guardado", str(result) if result else "Registro guardado correctamente.").open()
        except ValueError as exc:
            self.error_label.text = str(exc)
            self.error_label.height = "40dp"
            self._saving = False
            self.save_button.disabled = False
            return
        self._saving = False
        self.save_button.disabled = False
