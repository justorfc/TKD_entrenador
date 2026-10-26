"""Cálculos y persistencia de TKD Entrenador. Solo biblioteca estándar.

Las cantidades de referencia son decisiones del entrenador, no capacidades
máximas determinadas por el programa. No se prescriben cargas por edad o sexo.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import csv
import html
import json
import math
import os
from pathlib import Path
import sqlite3

VERSION = "0.1.0"
CATEGORIES = ("General", "Especial", "Competitiva")
UNITS = ("minutos", "repeticiones", "asaltos")
PHASES = ("Preparación general", "Preparación especial", "Precompetición",
          "Competición", "Transición", "Adaptación / retorno")
MEASURE_TYPES = ("Peso (kg)", "Talla (cm)", "FC basal (lpm)",
                 "FC reposo (lpm)", "FC durante (lpm)", "FC recuperación (lpm)")


def number(value, label, minimum=0, maximum=None):
    """Acepta coma decimal; rechaza NaN, infinito y valores fuera del dominio."""
    try:
        result = float(str(value).strip().replace(",", "."))
    except (ValueError, TypeError):
        raise ValueError(f"{label}: escriba un número.") from None
    if not math.isfinite(result) or result < minimum or (maximum is not None and result > maximum):
        raise ValueError(f"{label}: valor fuera del intervalo permitido ({minimum} a {maximum or 'sin límite superior'}).")
    return result


def iso_date(value):
    """Valida fechas del calendario, sin aproximar meses por cuatro semanas."""
    try:
        result = date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError("Use una fecha válida con formato AAAA-MM-DD.") from None
    return result


def age_on(birth, when):
    b, d = iso_date(birth), iso_date(when)
    if d < b:
        raise ValueError("La fecha no puede ser anterior al nacimiento.")
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def manual_pulse(beats, seconds):
    """Conversión de latidos contados durante un intervalo; no reconstruye FC previa."""
    return number(beats, "Latidos", 1) * 60 / number(seconds, "Segundos", 1)


def adult_hr(birth, when, resting, intensity, assessed_max=None):
    """Orientación aeróbica adulta con Karvonen. Nunca se aplica a menores.

    Tanaka es una estimación poblacional para adultos sanos. Una FC máxima
    evaluada tiene que proceder de una evaluación apropiada; un pico observado
    en entrenamiento no constituye por sí solo esa evaluación.
    """
    age = age_on(birth, when)
    if age < 18:
        raise ValueError("En menores no se calculan objetivos cardíacos automáticos por edad.")
    rest = number(resting, "FC de reposo", 1, 300)
    p = number(intensity, "% de reserva cardíaca", 0, 100) / 100
    maximum = (208 - .7 * age) if assessed_max in (None, "") else number(assessed_max, "FC máxima evaluada", 1, 300)
    if rest >= maximum:
        raise ValueError("La FC máxima debe superar la FC de reposo; revise los datos.")
    return {"maximum": maximum, "target": rest + p * (maximum - rest),
            "method": "Tanaka 208 − 0,7 × edad" if assessed_max in (None, "") else "FC máxima evaluada aportada"}


def distribute(total, count, integer=False):
    """Reparte por igual y conserva exactamente el total redondeado.

    Para repeticiones y asaltos se redondea el total semanal una sola vez,
    al entero más próximo (mitades hacia arriba), y se reparte el resto.
    Para minutos, la resolución es 0,1 min. No redondea cada día por separado.
    """
    if count < 1:
        raise ValueError("Seleccione al menos un día.")
    scale = 1 if integer else 10
    ticks = math.floor(number(total, "Volumen") * scale + .5)
    quotient, remainder = divmod(ticks, count)
    return [(quotient + (i < remainder)) / scale for i in range(count)]


def build_week(refs, start, days, percentages):
    """Genera un borrador, no una prescripción ni una progresión automática.

    Días: desplazamientos 0..6 desde un lunes. Minutos activos excluyen pausas.
    Todas las actividades se distribuyen uniformemente: el entrenador ajusta
    después días, pausas, duración y contenidos antes de validar el microciclo.
    """
    first = iso_date(start)
    if first.weekday() != 0:
        raise ValueError("El microciclo debe comenzar un lunes.")
    days = sorted(set(days))
    if not days or any(d not in range(7) for d in days):
        raise ValueError("Seleccione días válidos de la semana.")
    pct = {c: number(percentages[c], f"Porcentaje {c}", 0, 100) for c in CATEGORIES}
    items = []
    for r in refs:
        raw_total = r["quantity"] * pct[r["category"]] / 100
        allocations = distribute(raw_total, len(days), r["unit"] != "minutos")
        # El tiempo se deriva del volumen efectivamente redondeado.
        per_unit = (1 if r["unit"] == "minutos" else
                    r["round_minutes"] if r["unit"] == "asaltos" else
                    r["active_minutes"] / r["quantity"])
        for offset, qty in zip(days, allocations):
            if qty == 0:
                continue
            items.append({"date": (first + timedelta(days=offset)).isoformat(),
                          "exercise": r["exercise"], "category": r["category"],
                          "unit": r["unit"], "quantity": qty,
                          "active_minutes": qty * per_unit,
                          "round_minutes": r["round_minutes"],
                          "pause_seconds": r["pause_seconds"], "target_rpe": None, "notes": ""})
    if not items:
        raise ValueError("El borrador está vacío. Registre referencias y un porcentaje mayor que cero.")
    return sorted(items, key=lambda x: (x["date"], CATEGORIES.index(x["category"]), x["exercise"]))


def composition(items):
    """Composición por minutos activos. No suma unidades heterogéneas."""
    totals = {c: sum(x["active_minutes"] for x in items if x["category"] == c) for c in CATEGORIES}
    total = sum(totals.values())
    return {c: (v, 100 * v / total if total else 0) for c, v in totals.items()}


def data_directory():
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "TKD_Entrenador"
    root.mkdir(parents=True, exist_ok=True)
    return root


SCHEMA = """
CREATE TABLE IF NOT EXISTS athletes (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, birth TEXT NOT NULL,
 sex TEXT NOT NULL, experience TEXT NOT NULL DEFAULT '',
 guardian TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS measurements (
 id INTEGER PRIMARY KEY, athlete_id INTEGER NOT NULL REFERENCES athletes(id),
 date TEXT NOT NULL, kind TEXT NOT NULL, value REAL NOT NULL CHECK(value>0),
 method TEXT NOT NULL, delay_seconds REAL, notes TEXT NOT NULL DEFAULT '',
 void INTEGER NOT NULL DEFAULT 0 CHECK(void IN (0,1)));
CREATE TABLE IF NOT EXISTS refs (
 id INTEGER PRIMARY KEY, athlete_id INTEGER NOT NULL REFERENCES athletes(id),
 exercise TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL,
 quantity REAL NOT NULL CHECK(quantity>0), active_minutes REAL NOT NULL CHECK(active_minutes>0),
 round_minutes REAL NOT NULL DEFAULT 3, pause_seconds REAL NOT NULL DEFAULT 60,
 updated TEXT NOT NULL, UNIQUE(athlete_id,exercise));
CREATE TABLE IF NOT EXISTS plans (
 id INTEGER PRIMARY KEY, athlete_id INTEGER NOT NULL REFERENCES athletes(id),
 start TEXT NOT NULL, phase TEXT NOT NULL, created TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'Borrador', reviewer TEXT NOT NULL DEFAULT '',
 notes TEXT NOT NULL, basis TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS items (
 id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES plans(id),
 date TEXT NOT NULL, exercise TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL,
 quantity REAL NOT NULL CHECK(quantity>0), active_minutes REAL NOT NULL CHECK(active_minutes>0),
 round_minutes REAL NOT NULL, pause_seconds REAL NOT NULL,
 target_rpe REAL CHECK(target_rpe BETWEEN 0 AND 10), notes TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS sessions (
 id INTEGER PRIMARY KEY, athlete_id INTEGER NOT NULL REFERENCES athletes(id),
 plan_id INTEGER REFERENCES plans(id), date TEXT NOT NULL,
 duration REAL NOT NULL CHECK(duration>0), rpe REAL NOT NULL CHECK(rpe BETWEEN 0 AND 10),
 coach_rpe REAL CHECK(coach_rpe BETWEEN 0 AND 10), rpe_delay REAL NOT NULL,
 general_min REAL NOT NULL, special_min REAL NOT NULL, competitive_min REAL NOT NULL,
 actual_work TEXT NOT NULL, sleep TEXT NOT NULL, fatigue TEXT NOT NULL,
 pain TEXT NOT NULL, notes TEXT NOT NULL, void INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS measure_athlete_date ON measurements(athlete_id,date);
CREATE INDEX IF NOT EXISTS sessions_athlete_date ON sessions(athlete_id,date);
PRAGMA user_version=1;
"""


class Store:
    """SQLite local. Escrituras atómicas, parámetros SQL y copias mediante backup()."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            self.db.close()
            raise ValueError("Base creada por otra versión. No se modificará.")
        self.db.executescript(SCHEMA)

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def audit(self, action, detail):
        self.db.execute("INSERT INTO audit(timestamp,action,detail) VALUES(?,?,?)",
                        (datetime.now().isoformat(timespec="seconds"), action, json.dumps(detail, ensure_ascii=False)))

    def athlete(self, athlete_id):
        rows = self.rows("SELECT * FROM athletes WHERE id=?", (athlete_id,))
        if not rows:
            raise ValueError("Seleccione un deportista.")
        return rows[0]

    def add_athlete(self, name, birth, sex, experience="", guardian="", notes="", athlete_id=None):
        if not name.strip():
            raise ValueError("Escriba el nombre.")
        age_on(birth, date.today().isoformat())
        if sex not in ("Masculino", "Femenino", "Sin registrar"):
            raise ValueError("Seleccione el sexo.")
        values = (name.strip(), iso_date(birth).isoformat(), sex, experience, guardian, notes)
        with self.db:
            if athlete_id:
                old = self.athlete(athlete_id)
                # No permitir que una corrección haga anteriores al nacimiento los registros.
                dates = self.rows("SELECT date FROM measurements WHERE athlete_id=? UNION ALL SELECT date FROM sessions WHERE athlete_id=? UNION ALL SELECT start AS date FROM plans WHERE athlete_id=?", (athlete_id,)*3)
                if any(iso_date(x['date']) < iso_date(birth) for x in dates):
                    raise ValueError("La fecha de nacimiento contradice registros existentes.")
                self.db.execute("UPDATE athletes SET name=?,birth=?,sex=?,experience=?,guardian=?,notes=? WHERE id=?", values + (athlete_id,))
                self.audit("Editar deportista", old)
            else:
                athlete_id = self.db.execute("INSERT INTO athletes(name,birth,sex,experience,guardian,notes) VALUES(?,?,?,?,?,?)", values).lastrowid
                self.audit("Crear deportista", {"id": athlete_id})
        return athlete_id

    def check_record_date(self, athlete_id, when, future=False):
        d = iso_date(when)
        age_on(self.athlete(athlete_id)["birth"], when)
        if not future and d > date.today():
            raise ValueError("Una medición o sesión realizada no puede tener fecha futura.")
        return d.isoformat()

    def add_measurement(self, athlete_id, when, kind, value, method, delay="", notes=""):
        when = self.check_record_date(athlete_id, when)
        if kind not in MEASURE_TYPES:
            raise ValueError("Tipo de medición desconocido.")
        value = number(value, kind, .01, 500)
        if not method.strip():
            raise ValueError("Indique dispositivo, postura o protocolo de medición.")
        delay_value = number(delay, "Segundos desde fin del esfuerzo", 0) if str(delay).strip() else None
        if kind == "FC recuperación (lpm)" and delay_value is None:
            raise ValueError("Registre los segundos transcurridos desde el fin del esfuerzo.")
        if kind != "FC recuperación (lpm)":
            delay_value = None
        with self.db:
            rid = self.db.execute("INSERT INTO measurements(athlete_id,date,kind,value,method,delay_seconds,notes) VALUES(?,?,?,?,?,?,?)", (athlete_id,when,kind,value,method,delay_value,notes)).lastrowid
            self.audit("Medición", {"id":rid})
        return rid

    def save_ref(self, athlete_id, exercise, category, unit, quantity, active_minutes="", round_minutes=3, pause_seconds=60):
        self.athlete(athlete_id)
        if not exercise.strip() or category not in CATEGORIES or unit not in UNITS:
            raise ValueError("Complete ejercicio, categoría y unidad.")
        q = number(quantity, "Referencia semanal", .01)
        if unit != "minutos" and not q.is_integer():
            raise ValueError("Repeticiones y asaltos deben ser enteros.")
        rd = number(round_minutes, "Minutos por asalto", .01) if unit == "asaltos" else 0
        minutes = q if unit == "minutos" else q * rd if unit == "asaltos" else number(active_minutes, "Minutos activos semanales", .01)
        pause = number(pause_seconds, "Pausa (segundos)", 0)
        with self.db:
            self.db.execute("""INSERT INTO refs(athlete_id,exercise,category,unit,quantity,active_minutes,round_minutes,pause_seconds,updated)
                VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(athlete_id,exercise) DO UPDATE SET
                category=excluded.category,unit=excluded.unit,quantity=excluded.quantity,
                active_minutes=excluded.active_minutes,round_minutes=excluded.round_minutes,
                pause_seconds=excluded.pause_seconds,updated=excluded.updated""",
                (athlete_id,exercise.strip(),category,unit,q,minutes,rd,pause,datetime.now().isoformat()))
            self.audit("Referencia individual", {"athlete_id":athlete_id,"exercise":exercise,"quantity":q,"minutes":minutes})

    def create_plan(self, athlete_id, start, phase, days, percentages, notes):
        start = self.check_record_date(athlete_id, start, future=True)
        if phase not in PHASES or not notes.strip():
            raise ValueError("Seleccione fase y explique el objetivo y el criterio de carga de la semana.")
        refs = self.rows("SELECT * FROM refs WHERE athlete_id=? ORDER BY id", (athlete_id,))
        items = build_week(refs, start, days, percentages)
        basis = json.dumps({"version":VERSION,"references":refs,"percentages":percentages,"days":days}, ensure_ascii=False)
        with self.db:
            pid = self.db.execute("INSERT INTO plans(athlete_id,start,phase,created,notes,basis) VALUES(?,?,?,?,?,?)", (athlete_id,start,phase,datetime.now().isoformat(),notes,basis)).lastrowid
            for item in items:
                self.db.execute("INSERT INTO items(plan_id,date,exercise,category,unit,quantity,active_minutes,round_minutes,pause_seconds,notes) VALUES(?,?,?,?,?,?,?,?,?,?)", (pid,)+tuple(item[k] for k in ("date","exercise","category","unit","quantity","active_minutes","round_minutes","pause_seconds","notes")))
            self.audit("Crear borrador", {"id":pid})
        return pid

    def edit_item(self, item_id, when, quantity, active_minutes, pause_seconds, notes, target_rpe=""):
        rows = self.rows("SELECT i.*,p.start,p.status FROM items i JOIN plans p ON p.id=i.plan_id WHERE i.id=?",(item_id,))
        if not rows or rows[0]["status"] != "Borrador":
            raise ValueError("Solo se editan actividades de borradores.")
        old = rows[0]
        d, start = iso_date(when), iso_date(old["start"])
        if not start <= d <= start + timedelta(days=6):
            raise ValueError("El día debe pertenecer a este microciclo.")
        q = number(quantity, "Cantidad", .01)
        if old["unit"] != "minutos" and not q.is_integer():
            raise ValueError("Repeticiones y asaltos deben ser enteros.")
        mins = q if old["unit"] == "minutos" else q*old["round_minutes"] if old["unit"] == "asaltos" else number(active_minutes,"Minutos activos",.01)
        pause = number(pause_seconds,"Pausa",0)
        target = number(target_rpe,"RPE objetivo",0,10) if str(target_rpe).strip() else None
        with self.db:
            self.db.execute("UPDATE items SET date=?,quantity=?,active_minutes=?,pause_seconds=?,target_rpe=?,notes=? WHERE id=?",(d.isoformat(),q,mins,pause,target,notes,item_id))
            self.audit("Editar actividad", old)

    def remove_item(self, item_id):
        rows = self.rows("SELECT i.*,p.status FROM items i JOIN plans p ON p.id=i.plan_id WHERE i.id=?",(item_id,))
        if not rows or rows[0]["status"] != "Borrador":
            raise ValueError("Solo se eliminan actividades de borradores.")
        with self.db:
            self.db.execute("DELETE FROM items WHERE id=?",(item_id,))
            self.audit("Retirar actividad de borrador",rows[0])

    def review_plan(self, plan_id, reviewer):
        if not reviewer.strip():
            raise ValueError("Indique el nombre del entrenador responsable.")
        if not self.rows("SELECT id FROM items WHERE plan_id=?",(plan_id,)):
            raise ValueError("El plan no tiene actividades.")
        with self.db:
            self.db.execute("UPDATE plans SET status='Revisado',reviewer=? WHERE id=? AND status='Borrador'",(reviewer.strip(),plan_id))
            self.audit("Revisar plan",{"id":plan_id,"reviewer":reviewer})

    def add_session(self, athlete_id, when, duration, rpe, coach_rpe, rpe_delay,
                    general_min, special_min, competitive_min, actual_work,
                    sleep="", fatigue="", pain="", notes="", plan_id=None):
        when = self.check_record_date(athlete_id,when)
        duration = number(duration,"Duración total",.01,1440)
        rpe = number(rpe,"RPE deportista",0,10)
        coach = number(coach_rpe,"RPE previsto",0,10) if str(coach_rpe).strip() else None
        delay = number(rpe_delay,"Minutos hasta preguntar RPE",0)
        mins = [number(v,"Minutos activos",0,1440) for v in (general_min,special_min,competitive_min)]
        if sum(mins) > duration + 1e-8:
            raise ValueError("Los minutos activos no pueden superar la duración total de la sesión.")
        if not actual_work.strip():
            raise ValueError("Describa el trabajo realizado: ejercicios, cantidades y pausas.")
        if plan_id is not None:
            plans = self.rows("SELECT * FROM plans WHERE id=? AND athlete_id=?",(plan_id,athlete_id))
            if not plans or plans[0]["status"] != "Revisado":
                raise ValueError("Vincule un plan revisado del mismo deportista.")
            start = iso_date(plans[0]["start"])
            if not start <= iso_date(when) <= start + timedelta(days=6):
                raise ValueError("La sesión debe pertenecer a la semana del plan.")
        with self.db:
            sid = self.db.execute("""INSERT INTO sessions(athlete_id,plan_id,date,duration,rpe,coach_rpe,rpe_delay,general_min,special_min,competitive_min,actual_work,sleep,fatigue,pain,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(athlete_id,plan_id,when,duration,rpe,coach,delay,*mins,actual_work,sleep,fatigue,pain,notes)).lastrowid
            self.audit("Sesión realizada",{"id":sid})
        return sid

    def void_record(self, table, record_id, reason):
        if table not in ("sessions","measurements") or not reason.strip():
            raise ValueError("Indique el motivo de anulación.")
        with self.db:
            self.db.execute(f"UPDATE {table} SET void=1 WHERE id=?",(record_id,))
            self.audit("Anular registro",{"table":table,"id":record_id,"reason":reason})

    def backup(self, destination):
        target = Path(destination).resolve()
        if target == self.path.resolve():
            raise ValueError("Seleccione una ubicación diferente de la base activa.")
        # sqlite3.connect() como gestor de contexto solo confirma/revierte; hay que cerrar
        # la conexión explícitamente o el archivo queda bloqueado en Windows.
        other = sqlite3.connect(target)
        try:
            with other:
                self.db.backup(other)
                if other.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("La copia no pasó la comprobación de integridad.")
        finally:
            other.close()

    def restore(self, source):
        """Valida primero; guarda copia de seguridad previa; revierte al fallar."""
        source = Path(source).resolve()
        if source == self.path.resolve() or not source.is_file():
            raise ValueError("Seleccione una copia existente, diferente de la base activa.")
        other = sqlite3.connect(source.as_uri()+"?mode=ro",uri=True)
        try:
            if other.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or other.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("La copia no es válida o corresponde a otra versión.")
            for table in ("athletes","measurements","refs","plans","items","sessions","audit"):
                expected = [tuple(r)[1:3] for r in self.db.execute(f"PRAGMA table_info({table})")]
                actual = [tuple(r)[1:3] for r in other.execute(f"PRAGMA table_info({table})")]
                if actual != expected:
                    raise ValueError("La estructura de la copia no corresponde a esta aplicación.")
            if other.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("La copia contiene relaciones inválidas.")
            before = self.path.with_name("antes_restaurar_"+datetime.now().strftime("%Y%m%d_%H%M%S_%f")+".sqlite3")
            self.backup(before)
            other.backup(self.db)
        finally:
            other.close()
        return before


def table_html(headers, rows):
    esc = lambda v: html.escape("" if v is None else str(v))
    return "<table><thead><tr>"+"".join(f"<th>{esc(x)}</th>" for x in headers)+"</tr></thead><tbody>"+"".join("<tr>"+"".join(f"<td>{esc(x)}</td>" for x in row)+"</tr>" for row in rows)+"</tbody></table>"


def bars_svg(labels, series, title):
    """Gráfico SVG autónomo; cada serie se identifica con texto y color."""
    colors = ["#176b87", "#c46c22", "#6651a1"]
    highest = max((v for _,values in series for v in values),default=0) or 1
    out = [f'<svg viewBox="0 0 900 {100+len(labels)*40}" role="img" aria-label="{html.escape(title)}">']
    out.append(f'<text x="8" y="20" font-size="16">{html.escape(title)}</text>')
    for j,(name,_) in enumerate(series):
        out.append(f'<text x="{8+j*275}" y="44" fill="{colors[j%3]}" font-size="12">{html.escape(name)}</text>')
    for i,label in enumerate(labels):
        y=75+i*40
        out.append(f'<text x="8" y="{y+8}" font-size="11">{html.escape(label)}</text>')
        for j,(_,values) in enumerate(series):
            v=values[i]
            width=v/highest*650
            out.append(f'<rect x="120" y="{y+j*11}" width="{width:.2f}" height="9" fill="{colors[j%3]}"/><text x="{125+width:.2f}" y="{y+j*11+9}" font-size="10">{v:.1f}</text>')
    return "".join(out)+"</svg>"


def report_html(store, athlete_id, plan_id=None):
    """Informe local imprimible. Escapa textos y excluye registros anulados."""
    a=store.athlete(athlete_id)
    e=lambda x:html.escape(str(x))
    body=f"<h1>TKD · Seguimiento individual</h1><p><b>{e(a['name'])}</b> · Nacimiento: {e(a['birth'])} · Generado: {date.today()}</p>"
    body+="<p>Los porcentajes son referencias de planificación. Un plan revisado expresa la revisión del entrenador, no una certificación clínica.</p>"
    sessions=store.rows("SELECT *,duration*rpe AS load FROM sessions WHERE athlete_id=? AND void=0 ORDER BY date,id",(athlete_id,))
    if plan_id:
        p=store.rows("SELECT * FROM plans WHERE id=? AND athlete_id=?",(plan_id,athlete_id))
        if not p:
            raise ValueError("Plan no encontrado para este deportista.")
        p=p[0]
        items=store.rows("SELECT * FROM items WHERE plan_id=? ORDER BY date,id",(plan_id,))
        body+=f"<h2>Microciclo {e(p['start'])} · {e(p['phase'])}</h2><p>Estado: {e(p['status'])}. Responsable: {e(p['reviewer'])}. {e(p['notes'])}</p>"
        body+=table_html(["Fecha","Tipo","Ejercicio","Cantidad","Unidad","Min activos","Min/asalto","Pausa s","RPE objetivo","Indicaciones"],[[x['date'],x['category'],x['exercise'],f"{x['quantity']:g}",x['unit'],f"{x['active_minutes']:.1f}",x['round_minutes'] or "—",x['pause_seconds'],x['target_rpe'],x['notes']] for x in items])
        body+=table_html(["Formación","Minutos activos previstos","Proporción %"],[[k,f"{v[0]:.1f}",f"{v[1]:.1f}"] for k,v in composition(items).items()])
        labels=[(iso_date(p['start'])+timedelta(days=d)).isoformat() for d in range(7)]
        planned=[sum(x['active_minutes'] for x in items if x['date']==d) for d in labels]
        # Solo las sesiones vinculadas evitan mezclar dos planes alternativos.
        actual=[sum(x['general_min']+x['special_min']+x['competitive_min'] for x in sessions if x['plan_id']==plan_id and x['date']==d) for d in labels]
        body+=bars_svg(labels,[("Plan: minutos activos",planned),("Realizado vinculado: minutos activos",actual)],"Planificado y realizado (ausencia de registro no significa descanso)")
    weekly=defaultdict(float)
    for s in sessions:
        d=iso_date(s['date']); monday=(d-timedelta(days=d.weekday())).isoformat(); weekly[monday]+=s['load']
    labels=sorted(weekly)[-12:]
    if labels:
        body+=bars_svg(labels,[("Duración total × RPE, unidades arbitrarias",[weekly[d] for d in labels])],"Carga registrada: últimas 12 semanas con datos")
    body+="<h2>Sesiones realizadas</h2>"+table_html(["Fecha","Plan","Duración min","RPE","RPE previsto","Carga UA","Trabajo realizado","Observaciones"],[[s['date'],s['plan_id'],s['duration'],s['rpe'],s['coach_rpe'],round(s['load'],1),s['actual_work'],s['notes']] for s in sessions])
    measures=store.rows("SELECT * FROM measurements WHERE athlete_id=? AND void=0 ORDER BY date,id",(athlete_id,))
    body+="<h2>Mediciones</h2>"+table_html(["Fecha","Medición","Valor","Método","Segundos desde fin","Notas"],[[m['date'],m['kind'],m['value'],m['method'],m['delay_seconds'],m['notes']] for m in measures])
    return '<!doctype html><html lang="es"><meta charset="utf-8"><title>Seguimiento TKD</title><style>body{font:15px Arial,sans-serif;max-width:1100px;margin:30px auto;color:#172d3b;padding:16px}h1,h2{color:#176b87}table{border-collapse:collapse;width:100%;font-size:12px;margin:18px 0}td,th{border:1px solid #b8cbd2;padding:7px;text-align:left;overflow-wrap:anywhere}th{background:#eaf3f6}svg{width:100%;margin:20px 0}p{line-height:1.5}@media print{body{margin:0;padding:0}tr{break-inside:avoid}thead{display:table-header-group}}</style>'+body+'</html>'


def export_sessions(store, athlete_id, destination):
    rows=store.rows("SELECT date,duration,rpe,coach_rpe,duration*rpe AS carga_ua,general_min,special_min,competitive_min,actual_work,notes FROM sessions WHERE athlete_id=? AND void=0 ORDER BY date,id",(athlete_id,))
    headers=['date','duration','rpe','coach_rpe','carga_ua','general_min','special_min','competitive_min','actual_work','notes']
    def safe(v):
        if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')):
            return "'"+v
        return v
    with open(destination,'w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f,delimiter=';');writer.writerow(headers)
        writer.writerows([[safe(row[h]) for h in headers] for row in rows])
