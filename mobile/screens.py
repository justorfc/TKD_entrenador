"""Pantallas táctiles de TKD Entrenador para Android.

Toda la validación y persistencia se delega en `core.py` (Store y funciones
de cálculo); aquí solo hay presentación y navegación. No se duplica ninguna
fórmula ni regla de negocio respecto de la versión Windows (app.py).
"""
from __future__ import annotations

from datetime import date, timedelta

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.app import App

import core
from core import (CATEGORIES, UNITS, PHASES, MEASURE_TYPES,
                   ORTHOSTATIC_NEUTRAL_MESSAGE, age_on, manual_pulse,
                   orthostatic_risk, composition, report_html, export_sessions)
from historical import HISTORICAL

from mobile import paths
from mobile.widgets import FormPopup, InfoPopup, ConfirmPopup, big_button


def app():
    return App.get_running_app()


def store():
    return app().store


# ---------------------------------------------------------------------------
# Utilidades comunes de pantalla
# ---------------------------------------------------------------------------

class BaseScreen(Screen):
    """Pantalla con cabecera fija (identificación permanente del deportista
    seleccionado) y un cuerpo desplazable para no tapar contenido con el
    teclado en pantallas pequeñas."""

    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.root_box = BoxLayout(orientation="vertical")
        self.add_widget(self.root_box)
        self.root_box.add_widget(Label(text=title, size_hint_y=None, height="40dp",
                                        font_size="20sp", bold=True))
        self.athlete_label = Label(text="Ningún deportista seleccionado", size_hint_y=None,
                                    height="30dp", font_size="15sp", color=(0.2, 0.4, 0.5, 1))
        self.root_box.add_widget(self.athlete_label)
        self.scroll = ScrollView()
        self.body = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=(10, 10))
        self.body.bind(minimum_height=self.body.setter("height"))
        self.scroll.add_widget(self.body)
        self.root_box.add_widget(self.scroll)

    def on_pre_enter(self):
        self.update_athlete_label()
        self.refresh()

    def update_athlete_label(self):
        a = app().current_athlete()
        if a:
            years = age_on(a["birth"], date.today().isoformat())
            minor = " · Menor: referencias individuales, sin zonas cardíacas automáticas." if years < 18 else ""
            self.athlete_label.text = f"Deportista: {a['name']} · {years} años{minor}"
        else:
            self.athlete_label.text = "Ningún deportista seleccionado (vaya a Deportistas)"

    def need_athlete(self):
        a = app().current_athlete()
        if not a:
            InfoPopup("Seleccione un deportista", "Primero elija o cree un deportista en la pantalla «Deportistas».").open()
            return None
        return a

    def refresh(self):
        pass


def row_button(text, callback):
    return big_button(text, on_release=lambda *_: callback())


# ---------------------------------------------------------------------------
# Inicio
# ---------------------------------------------------------------------------

class HomeScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__("TKD Entrenador · Inicio", **kwargs)
        self.summary = Label(text="", size_hint_y=None, font_size="16sp", halign="left")
        self.summary.bind(width=lambda *_: self.summary.setter("text_size")(self.summary, (self.summary.width, None)))
        self.summary.bind(texture_size=lambda *_: setattr(self.summary, "height", self.summary.texture_size[1] + 10))
        self.body.add_widget(self.summary)
        self.body.add_widget(row_button("Deportistas y grupos", lambda: app().goto("deportistas")))
        self.body.add_widget(row_button("Registrar medición de hoy", lambda: app().goto("mediciones")))
        self.body.add_widget(row_button("Registrar sesión de hoy", lambda: app().goto("sesiones")))
        self.body.add_widget(row_button("Planificación semanal", lambda: app().goto("planificacion")))
        self.body.add_widget(row_button("Progreso e informes", lambda: app().goto("progreso")))
        self.body.add_widget(row_button("Ajustes y copias de seguridad", lambda: app().goto("ajustes")))

    def refresh(self):
        a = app().current_athlete()
        if not a:
            self.summary.text = "Seleccione o cree un deportista para empezar."
            return
        s = store()
        sessions = s.rows("SELECT COUNT(*) AS n FROM sessions WHERE athlete_id=? AND void=0", (a["id"],))[0]["n"]
        measures = s.rows("SELECT COUNT(*) AS n FROM measurements WHERE athlete_id=? AND void=0", (a["id"],))[0]["n"]
        self.summary.text = (f"Entrenamiento de hoy: {date.today().isoformat()}\n"
                              f"Sesiones registradas: {sessions} · Mediciones registradas: {measures}\n"
                              "Una semana sin registros no se interpreta automáticamente como descanso.")


# ---------------------------------------------------------------------------
# Deportistas
# ---------------------------------------------------------------------------

class AthletesScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__("Deportistas y grupos", **kwargs)
        self.body.add_widget(row_button("Nuevo deportista", self.new_athlete))
        self.list_box = GridLayout(cols=1, spacing=6, size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.body.add_widget(self.list_box)

    def refresh(self):
        self.list_box.clear_widgets()
        rows = store().rows("SELECT * FROM athletes ORDER BY name,id")
        if not rows:
            self.list_box.add_widget(Label(text="Sin deportistas todavía.", size_hint_y=None, height="30dp"))
        for r in rows:
            years = age_on(r["birth"], date.today().isoformat())
            btn = big_button(f"{r['name']} · {years} años · {r['sex']}",
                              on_release=lambda *_, rid=r["id"]: self.select(rid))
            self.list_box.add_widget(btn)

    def select(self, athlete_id):
        app().select_athlete(athlete_id)
        app().goto("ficha")

    def new_athlete(self):
        fields = [("name", "Nombre completo", "", None),
                  ("birth", "Nacimiento (AAAA-MM-DD)", date.today().replace(year=date.today().year - 15).isoformat(), None),
                  ("sex", "Sexo", "Sin registrar", ("Masculino", "Femenino", "Sin registrar")),
                  ("experience", "Experiencia / cinturón", "", None),
                  ("guardian", "Acudiente / autorización registrada", "", None),
                  ("notes", "Observaciones", "", None)]

        def save(v):
            aid = store().add_athlete(v["name"], v["birth"], v["sex"], v["experience"], v["guardian"], v["notes"])
            app().select_athlete(aid)
            self.refresh()
            return "Deportista guardado."
        FormPopup("Nuevo deportista", fields, save,
                  "Registre solo información necesaria. Peso y pulsos se guardan con fecha en Mediciones.",
                  draft_key="nuevo_deportista", draft_store=app().drafts).open()


# ---------------------------------------------------------------------------
# Ficha (detalle e historial)
# ---------------------------------------------------------------------------

class ProfileScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__("Ficha e historial", **kwargs)
        self.detail = Label(text="", size_hint_y=None, font_size="16sp", halign="left")
        self.detail.bind(width=lambda *_: self.detail.setter("text_size")(self.detail, (self.detail.width, None)))
        self.detail.bind(texture_size=lambda *_: setattr(self.detail, "height", self.detail.texture_size[1] + 10))
        self.body.add_widget(self.detail)
        self.body.add_widget(row_button("Editar ficha", self.edit_athlete))
        self.history = Label(text="", size_hint_y=None, font_size="14sp", halign="left")
        self.history.bind(width=lambda *_: self.history.setter("text_size")(self.history, (self.history.width, None)))
        self.history.bind(texture_size=lambda *_: setattr(self.history, "height", self.history.texture_size[1] + 10))
        self.body.add_widget(self.history)

    def refresh(self):
        a = app().current_athlete()
        if not a:
            self.detail.text = "Seleccione un deportista en la pantalla «Deportistas»."
            self.history.text = ""
            return
        years = age_on(a["birth"], date.today().isoformat())
        threshold = a["orthostatic_threshold"]
        self.detail.text = (f"{a['name']}\nNacimiento: {a['birth']} ({years} años) · Sexo: {a['sex']}\n"
                             f"Experiencia: {a['experience'] or '—'}\nAcudiente: {a['guardian'] or '—'}\n"
                             f"Observaciones: {a['notes'] or '—'}\n"
                             f"Umbral de seguimiento postural: {threshold if threshold is not None else 'no configurado (opcional)'}")
        s = store()
        measures = s.rows("SELECT * FROM measurements WHERE athlete_id=? AND void=0 ORDER BY date DESC,id DESC LIMIT 5", (a["id"],))
        sessions = s.rows("SELECT *,duration*rpe AS load FROM sessions WHERE athlete_id=? AND void=0 ORDER BY date DESC,id DESC LIMIT 5", (a["id"],))
        text = "ÚLTIMAS MEDICIONES\n"
        text += "\n".join(f"{m['date']} · {m['kind']} · {m['value']:g}" for m in measures) or "Sin mediciones."
        text += "\n\nÚLTIMAS SESIONES\n"
        text += "\n".join(f"{s2['date']} · {s2['duration']:g} min · RPE {s2['rpe']:g} · {s2['load']:g} UA" for s2 in sessions) or "Sin sesiones."
        self.history.text = text

    def edit_athlete(self):
        a = self.need_athlete()
        if not a:
            return
        fields = [("name", "Nombre completo", a["name"], None),
                  ("birth", "Nacimiento (AAAA-MM-DD)", a["birth"], None),
                  ("sex", "Sexo", a["sex"], ("Masculino", "Femenino", "Sin registrar")),
                  ("experience", "Experiencia / cinturón", a["experience"], None),
                  ("guardian", "Acudiente / autorización registrada", a["guardian"], None),
                  ("notes", "Observaciones", a["notes"], None)]

        def save(v):
            store().add_athlete(v["name"], v["birth"], v["sex"], v["experience"], v["guardian"], v["notes"], athlete_id=a["id"])
            self.refresh()
            return "Ficha actualizada."
        FormPopup("Editar ficha", fields, save, draft_key=f"editar_deportista_{a['id']}", draft_store=app().drafts).open()


# ---------------------------------------------------------------------------
# Mediciones
# ---------------------------------------------------------------------------

class MeasurementsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__("Mediciones", **kwargs)
        self.body.add_widget(Label(text="PR/bpm = pulso; SpO₂/% = saturación. Registre también la presión arterial "
                                         "(sistólica y diastólica) como mediciones separadas.",
                                    size_hint_y=None, height="60dp", font_size="13sp"))
        self.body.add_widget(row_button("Nueva medición", self.new_measurement))
        self.body.add_widget(row_button("Convertir conteo manual de pulso", self.pulse_tool))
        self.body.add_widget(row_button("Prueba ortostática (acostado/de pie)", self.orthostatic_tool))
        self.body.add_widget(row_button("Umbral de seguimiento postural (opcional)", self.threshold_tool))
        self.list_box = GridLayout(cols=1, spacing=4, size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.body.add_widget(self.list_box)

    def refresh(self):
        self.list_box.clear_widgets()
        a = app().current_athlete()
        if not a:
            return
        rows = store().rows("SELECT * FROM measurements WHERE athlete_id=? AND void=0 ORDER BY date DESC,id DESC LIMIT 30", (a["id"],))
        for m in rows:
            self.list_box.add_widget(Label(text=f"{m['date']} · {m['kind']} · {m['value']:g} · {m['method']}",
                                            size_hint_y=None, height="28dp", font_size="13sp"))

    def new_measurement(self):
        if not self.need_athlete():
            return
        fields = [("when", "Fecha (AAAA-MM-DD)", date.today().isoformat(), None),
                  ("kind", "Tipo", MEASURE_TYPES[0], MEASURE_TYPES),
                  ("value", "Valor", "", None, True),
                  ("method", "Método, dispositivo y postura", "", None),
                  ("delay", "Segundos desde fin (solo recuperación)", "", None, True),
                  ("notes", "Observaciones / hora", "", None)]

        def save(v):
            store().add_measurement(app().athlete_id, v["when"], v["kind"], v["value"], v["method"], v["delay"], v["notes"])
            self.refresh()
            return "Medición guardada."
        FormPopup("Nueva medición", fields, save,
                   "Una medición no se interpreta como aptitud para entrenar.",
                   draft_key="nueva_medicion", draft_store=app().drafts).open()

    def pulse_tool(self):
        fields = [("beats", "Latidos contados", "", None, True), ("seconds", "Duración del conteo, segundos", "6", None, True)]

        def calculate(v):
            pulse = manual_pulse(v["beats"], v["seconds"])
            return (f"Estimación: {pulse:.0f} latidos/min.\n"
                    "Registre por separado el contexto y la demora tras el esfuerzo.")
        FormPopup("Conversión de conteo manual", fields, calculate).open()

    def orthostatic_tool(self):
        a = self.need_athlete()
        if not a:
            return
        threshold = a["orthostatic_threshold"]
        fields = [("supine", "FC acostado tras reposo (lpm)", "", None, True),
                  ("standing", "FC de pie, inmediatamente al levantarse (lpm)", "", None, True)]

        def calculate(v):
            r = orthostatic_risk(v["supine"], v["standing"], threshold)
            if r["flagged"] is None:
                aviso = "Sin umbral de seguimiento configurado para este deportista (opcional)."
            elif r["flagged"]:
                aviso = ORTHOSTATIC_NEUTRAL_MESSAGE
            else:
                aviso = f"Diferencia dentro del umbral configurado (≤{threshold:g} lpm)."
            return (f"FC acostado: {r['supine']:.0f} lpm · FC de pie: {r['standing']:.0f} lpm\n"
                    f"Diferencia: {r['difference']:.0f} lpm\n{aviso}\n"
                    "Criterio personal de seguimiento, no diagnóstico.")
        FormPopup("Prueba ortostática", fields, calculate,
                   "Reposar acostado unos minutos, medir la FC, levantarse y medir de inmediato de pie. "
                   "Registre también ambos valores en Mediciones.").open()

    def threshold_tool(self):
        a = self.need_athlete()
        if not a:
            return
        fields = [("threshold", "Umbral de seguimiento (lpm, vacío = desactivado)",
                   a["orthostatic_threshold"] if a["orthostatic_threshold"] is not None else "", None, True)]

        def save(v):
            store().set_orthostatic_threshold(a["id"], v["threshold"])
            return "Umbral actualizado."
        FormPopup("Umbral de seguimiento postural", fields, save,
                   "Opcional; no activado por defecto. Criterio personal de seguimiento, no diagnóstico. "
                   "El valor histórico de referencia era 15 lpm.").open()


# ---------------------------------------------------------------------------
# Referencias y planificación semanal
# ---------------------------------------------------------------------------

class PlanningScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__("Referencias y planificación semanal", **kwargs)
        self.body.add_widget(row_button("Añadir referencia semanal", self.new_ref))
        self.refs_box = GridLayout(cols=1, spacing=4, size_hint_y=None)
        self.refs_box.bind(minimum_height=self.refs_box.setter("height"))
        self.body.add_widget(self.refs_box)
        self.body.add_widget(row_button("Generar borrador de microciclo", self.new_plan))
        self.body.add_widget(row_button("Revisar último borrador", self.review_latest))
        self.plan_summary = Label(text="", size_hint_y=None, font_size="14sp", halign="left")
        self.plan_summary.bind(width=lambda *_: self.plan_summary.setter("text_size")(self.plan_summary, (self.plan_summary.width, None)))
        self.plan_summary.bind(texture_size=lambda *_: setattr(self.plan_summary, "height", self.plan_summary.texture_size[1] + 10))
        self.body.add_widget(self.plan_summary)
        self.items_box = GridLayout(cols=1, spacing=4, size_hint_y=None)
        self.items_box.bind(minimum_height=self.items_box.setter("height"))
        self.body.add_widget(self.items_box)

    def refresh(self):
        self.refs_box.clear_widgets()
        self.items_box.clear_widgets()
        self.plan_summary.text = ""
        a = app().current_athlete()
        if not a:
            return
        refs = store().rows("SELECT * FROM refs WHERE athlete_id=? ORDER BY category,exercise", (a["id"],))
        for r in refs:
            self.refs_box.add_widget(Label(text=f"{r['exercise']} ({r['category']}): {r['quantity']:g} {r['unit']}/semana",
                                            size_hint_y=None, height="26dp", font_size="13sp"))
        plan = store().rows("SELECT * FROM plans WHERE athlete_id=? ORDER BY id DESC LIMIT 1", (a["id"],))
        if plan:
            p = plan[0]
            items = store().rows("SELECT * FROM items WHERE plan_id=? ORDER BY date,id", (p["id"],))
            comp = composition(items)
            text = " · ".join(f"{c}: {m:.1f} min ({pc:.1f} %)" for c, (m, pc) in comp.items())
            self.plan_summary.text = f"Último microciclo: {p['start']} · {p['phase']} · {p['status']}\n{text}"
            for it in items:
                self.items_box.add_widget(Label(
                    text=f"{it['date']} · {it['category']} · {it['exercise']} · {it['quantity']:g} {it['unit']}",
                    size_hint_y=None, height="26dp", font_size="12sp"))

    def new_ref(self):
        if not self.need_athlete():
            return
        fields = [("exercise", "Nombre del ejercicio", "", None),
                  ("category", "Formación", "General", CATEGORIES),
                  ("unit", "Unidad", "minutos", UNITS),
                  ("quantity", "Referencia semanal al 100 %", "", None, True),
                  ("active_minutes", "Min activos al 100 % (solo repeticiones)", "", None, True),
                  ("round_minutes", "Minutos por asalto", "3", None, True),
                  ("pause_seconds", "Pausa orientativa (s)", "60", None, True)]

        def save(v):
            store().save_ref(app().athlete_id, v["exercise"], v["category"], v["unit"], v["quantity"],
                              v["active_minutes"], v["round_minutes"], v["pause_seconds"])
            self.refresh()
            return "Referencia guardada."
        FormPopup("Referencia semanal individual", fields, save,
                   "100 % es una referencia de planificación, no un máximo obligatorio.",
                   draft_key="nueva_referencia", draft_store=app().drafts).open()

    def new_plan(self):
        if not self.need_athlete():
            return
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        fields = [("start", "Lunes de inicio (AAAA-MM-DD)", monday.isoformat(), None),
                  ("phase", "Fase", PHASES[0], PHASES),
                  ("days", "Días: 1=Lun ... 7=Dom", "1,3,5", None),
                  ("general", "% referencia General", "0", None, True),
                  ("special", "% referencia Especial", "0", None, True),
                  ("competitive", "% referencia Competitiva", "0", None, True),
                  ("notes", "Objetivo y criterio de carga", "", None)]

        def save(v):
            try:
                days = [int(x.strip()) - 1 for x in v["days"].split(",")]
            except ValueError:
                raise ValueError("Días: escriba números del 1 al 7 separados por comas.") from None
            store().create_plan(app().athlete_id, v["start"], v["phase"], days,
                                 dict(zip(CATEGORIES, [v["general"], v["special"], v["competitive"]])), v["notes"])
            self.refresh()
            return "Borrador de microciclo generado."
        FormPopup("Borrador de microciclo semanal", fields, save,
                   "El borrador reparte por igual: ajuste cada actividad antes de marcarlo revisado.",
                   draft_key="nuevo_plan", draft_store=app().drafts).open()

    def review_latest(self):
        a = self.need_athlete()
        if not a:
            return
        plan = store().rows("SELECT * FROM plans WHERE athlete_id=? AND status='Borrador' ORDER BY id DESC LIMIT 1", (a["id"],))
        if not plan:
            InfoPopup("Sin borradores", "No hay ningún borrador pendiente de revisión para este deportista.").open()
            return
        pid = plan[0]["id"]
        fields = [("name", "Nombre del responsable", "", None)]

        def save(v):
            store().review_plan(pid, v["name"])
            self.refresh()
            return "Plan revisado y congelado."
        FormPopup("Revisión del entrenador", fields, save,
                   "Revise calendario, descansos, técnica, duración, experiencia y recuperación antes de confirmar.").open()


# ---------------------------------------------------------------------------
# Sesiones
# ---------------------------------------------------------------------------

class SessionsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__("Registro de sesiones", **kwargs)
        self.body.add_widget(row_button("Registrar sesión realizada", self.new_session))
        self.list_box = GridLayout(cols=1, spacing=4, size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.body.add_widget(self.list_box)

    def refresh(self):
        self.list_box.clear_widgets()
        a = app().current_athlete()
        if not a:
            return
        rows = store().rows("SELECT *,duration*rpe AS load FROM sessions WHERE athlete_id=? AND void=0 ORDER BY date DESC,id DESC LIMIT 20", (a["id"],))
        for s in rows:
            self.list_box.add_widget(Label(text=f"{s['date']} · {s['duration']:g} min · RPE {s['rpe']:g} · {s['load']:g} UA",
                                            size_hint_y=None, height="28dp", font_size="13sp"))

    def new_session(self):
        a = self.need_athlete()
        if not a:
            return
        plans = store().rows("SELECT * FROM plans WHERE athlete_id=? AND status='Revisado' ORDER BY start DESC,id DESC", (a["id"],))
        plan_choices = {"Sin vínculo": None}
        plan_choices.update({f"{p['id']} · {p['start']} · {p['phase']}": p["id"] for p in plans})
        fields = [("when", "Fecha (AAAA-MM-DD)", date.today().isoformat(), None),
                  ("plan", "Plan revisado", "Sin vínculo", tuple(plan_choices)),
                  ("duration", "Duración total de sesión (min)", "", None, True),
                  ("rpe", "RPE deportista (0–10)", "", None, True),
                  ("coach_rpe", "RPE previsto entrenador (opcional)", "", None, True),
                  ("rpe_delay", "Minutos tras sesión al preguntar RPE", "30", None, True),
                  ("general_min", "Min activos generales", "0", None, True),
                  ("special_min", "Min activos especiales", "0", None, True),
                  ("competitive_min", "Min activos competitivos", "0", None, True),
                  ("actual_work", "Ejercicios y cantidades realizadas", "", None),
                  ("sleep", "Sueño: duración/calidad", "", None),
                  ("fatigue", "Cansancio comunicado", "", None),
                  ("pain", "Dolor o molestias comunicadas", "", None),
                  ("notes", "Observaciones / cambios", "", None)]

        def save(v):
            plan_id = plan_choices[v.pop("plan")]
            store().add_session(a["id"], v["when"], v["duration"], v["rpe"], v["coach_rpe"], v["rpe_delay"],
                                 v["general_min"], v["special_min"], v["competitive_min"], v["actual_work"],
                                 v["sleep"], v["fatigue"], v["pain"], v["notes"], plan_id)
            self.refresh()
            return "Sesión registrada."
        FormPopup("Sesión realizada", fields, save,
                   "Duración total incluye pausas; minutos activos las excluyen. Describa lo realmente completado.",
                   draft_key="nueva_sesion", draft_store=app().drafts).open()


# ---------------------------------------------------------------------------
# Progreso e informes
# ---------------------------------------------------------------------------

class ProgressScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__("Progreso e informes", **kwargs)
        self.summary = Label(text="", size_hint_y=None, font_size="15sp", halign="left")
        self.summary.bind(width=lambda *_: self.summary.setter("text_size")(self.summary, (self.summary.width, None)))
        self.summary.bind(texture_size=lambda *_: setattr(self.summary, "height", self.summary.texture_size[1] + 10))
        self.body.add_widget(self.summary)
        self.body.add_widget(row_button("Generar y compartir informe (HTML)", self.full_report))
        self.body.add_widget(row_button("Exportar y compartir sesiones (CSV)", self.csv_report))

    def refresh(self):
        a = app().current_athlete()
        if not a:
            self.summary.text = "Seleccione un deportista."
            return
        rows = store().rows("SELECT *,duration*rpe AS load FROM sessions WHERE athlete_id=? AND void=0 ORDER BY date,id", (a["id"],))
        if rows:
            text = (f"Sesiones registradas: {len(rows)}\n"
                    f"Duración acumulada: {sum(r['duration'] for r in rows):.1f} minutos\n"
                    f"Carga acumulada registrada: {sum(r['load'] for r in rows):.1f} UA")
        else:
            text = "Todavía no hay sesiones realizadas."
        self.summary.text = text + ("\n\nMás carga no significa necesariamente mejor progreso: revise técnica, "
                                     "consistencia, bienestar y desempeño junto con estos indicadores.")

    def full_report(self):
        a = self.need_athlete()
        if not a:
            return
        path = paths.data_directory() / "informe_tkd.html"
        path.write_text(report_html(store(), a["id"]), encoding="utf-8")
        paths.share_file(path, "text/html")

    def csv_report(self):
        a = self.need_athlete()
        if not a:
            return
        path = paths.data_directory() / "sesiones_tkd.csv"
        export_sessions(store(), a["id"], path)
        paths.share_file(path, "text/csv")


# ---------------------------------------------------------------------------
# Ajustes y copias de seguridad
# ---------------------------------------------------------------------------

class SettingsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__("Ajustes y copias de seguridad", **kwargs)
        self.info = Label(text="", size_hint_y=None, font_size="14sp", halign="left")
        self.info.bind(width=lambda *_: self.info.setter("text_size")(self.info, (self.info.width, None)))
        self.info.bind(texture_size=lambda *_: setattr(self.info, "height", self.info.texture_size[1] + 10))
        self.body.add_widget(self.info)
        self.body.add_widget(row_button("Crear copia de seguridad", self.backup))
        self.body.add_widget(row_button("Restaurar copia de seguridad", self.restore))
        self.body.add_widget(row_button("Ver curvas históricas (archivo)", self.show_history))

    def refresh(self):
        self.info.text = (f"Versión: {core.VERSION}\nBase de datos (privada de la app): {store().path}\n\n"
                           "La aplicación no cifra la base ni tiene cuentas: proteja el bloqueo del teléfono. "
                           "Un PIN visual no equivale a cifrado de SQLite. Conserve una copia externa antes de "
                           "desinstalar o cambiar de equipo: los datos de la app se borran al desinstalar.")

    def backup(self):
        suggested = f"copia_tkd_{date.today().isoformat()}.sqlite3"

        def after_pick(destination):
            if not destination:
                return
            temp = paths.data_directory() / ("_tmp_" + suggested)
            try:
                store().backup(temp)
                paths.export_to_uri(temp, destination)
                InfoPopup("Copia creada", "Copia comprobada. Conserve una copia adicional en otro medio protegido.").open()
            except ValueError as exc:
                InfoPopup("No se pudo crear la copia", str(exc)).open()
            finally:
                temp.unlink(missing_ok=True)
        paths.pick_destination_to_export(after_pick, suggested)

    def restore(self):
        def after_pick(source):
            if not source:
                return

            def do_restore():
                temp = paths.data_directory() / "_tmp_restaurar.sqlite3"
                try:
                    paths.import_from_uri(source, temp)
                    before = store().restore(temp)
                    app().reload_athlete()
                    InfoPopup("Restaurado", f"Copia previa guardada en:\n{before}").open()
                except ValueError as exc:
                    InfoPopup("No se pudo restaurar", str(exc)).open()
                finally:
                    temp.unlink(missing_ok=True)
            ConfirmPopup("Restaurar copia",
                         "Esto reemplazará todos los registros activos por los de la copia elegida. "
                         "Se conservará una copia previa automática. ¿Continuar?", do_restore).open()
        paths.pick_file_to_import(after_pick)

    def show_history(self):
        from core import bars_svg, table_html
        body = ("<h1>Curvas históricas de referencia</h1><p>Archivo de referencia: 48 semanas. "
                "Valores transcritos, no recomendaciones actuales. No se aplican automáticamente a deportistas.</p>")
        for sheet, rows in HISTORICAL.items():
            body += f"<h2>{sheet}</h2>"
            body += bars_svg([str(x["week"]) for x in rows],
                              [("Volumen %", [x["volume"] for x in rows]), ("Intensidad histórica %", [x["intensity"] for x in rows])],
                              sheet + " · semanas 1-48")
            body += table_html(["Semana", "Volumen %", "Intensidad histórica %"], [[x["week"], x["volume"], x["intensity"]] for x in rows])
        path = paths.data_directory() / "curvas_historicas.html"
        path.write_text('<!doctype html><html lang="es"><meta charset="utf-8">' + body + "</html>", encoding="utf-8")
        paths.share_file(path, "text/html")


SCREENS = [
    ("inicio", HomeScreen),
    ("deportistas", AthletesScreen),
    ("ficha", ProfileScreen),
    ("mediciones", MeasurementsScreen),
    ("planificacion", PlanningScreen),
    ("sesiones", SessionsScreen),
    ("progreso", ProgressScreen),
    ("ajustes", SettingsScreen),
]

NAV_LABELS = {
    "inicio": "Inicio", "deportistas": "Deportistas", "ficha": "Ficha",
    "mediciones": "Mediciones", "planificacion": "Planes", "sesiones": "Sesiones",
    "progreso": "Progreso", "ajustes": "Ajustes",
}
