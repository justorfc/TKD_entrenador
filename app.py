"""Interfaz local en español. Ejecutar: python app.py

Tkinter/ttk evita dependencias externas para el entrenador. La lógica deportiva
y SQLite están en core.py y pueden comprobarse sin abrir ventanas.
"""
from datetime import date, timedelta
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser

from core import (VERSION, CATEGORIES, UNITS, PHASES, MEASURE_TYPES, Store,
                  data_directory, age_on, adult_hr, manual_pulse, orthostatic_risk,
                  ORTHOSTATIC_NEUTRAL_MESSAGE, composition, report_html, export_sessions)
from historical import HISTORICAL

HELP = """TKD ENTRENADOR · GUÍA RÁPIDA

1. Cree un deportista y selecciónelo arriba. Registre fecha de nacimiento,
   experiencia y el acuerdo de tratamiento de datos con su acudiente.
2. Registre mediciones con fecha, método y contexto.
3. Defina referencias semanales INDIVIDUALES para cada ejercicio.
   El 100 % es una referencia de planificación: no es un test máximo.
4. Genere un borrador de microciclo. Sus porcentajes multiplican las
   referencias de cada categoría; no son proporciones del tiempo total.
5. Revise la tabla: puede cambiar el día, cantidad, tiempo, pausa y notas de
   cada actividad, o retirarla. La distribución inicial es uniforme, no una
   alternancia fisiológica validada. Evite duplicaciones al mover actividades.
6. Revise con su nombre cuando el plan esté completo. Queda congelado.
   Para cambiarlo, genere otro borrador; conserva la versión anterior.
7. Registre lo realizado y el esfuerzo que comunica el deportista.
8. Consulte Progreso y exporte un informe para imprimir o guardar en PDF.

REFERENCIAS HISTÓRICAS
Cross: 90 min/semana. Escalera: 70 min/semana. Patadas: 200/semana.
Combate condicionado: 16 asaltos; libre: 12. Cada asalto: 3 minutos.
Las referencias NO incluyen un objetivo semanal universal para adolescentes.
Para patadas hay que introducir el tiempo activo previsto; no se conoce a
partir del número de repeticiones. Saco y canilleras requieren definir sus
unidades antes de añadirlos. Las pausas no están incluidas en minutos activos.

PULSO Y FRECUENCIA CARDÍACA (FC)
FC basal: al despertar, antes de levantarse, con protocolo estable.
FC de reposo: tras reposo tranquilo, registrando postura y condiciones.
Son definiciones operativas; no se consideran intercambiables automáticamente.
FC durante: medida efectivamente durante el esfuerzo.
FC de recuperación: después de detenerse, registrando segundos transcurridos.
Un pulsioxímetro de dedo suele necesitar inmovilidad y una señal estable.
Leer PR/bpm (pulso), no SpO2/% (saturación). No diagnostica aptitud deportiva.
Contar latidos durante 6 segundos y multiplicar por 10 estima lpm;
un latido de diferencia equivale a 10 lpm. Registrar la medición real,
sin intentar reconstruir el pulso previo a la detención.

PRESIÓN ARTERIAL Y PRUEBA ORTOSTÁTICA
Registre presión arterial sistólica y diastólica (mmHg) como mediciones,
con fecha, método/dispositivo y postura, igual que el resto de valores.
Prueba ortostática: FC acostado tras reposo y FC de pie al levantarse.
La diferencia (de pie − acostado) se calcula siempre; evaluarla contra un
umbral es opcional y se configura por deportista en «Umbral de seguimiento
postural» (NO activado por defecto; el valor histórico de referencia era
15 lpm). Superar el umbral no es un diagnóstico ni indica por sí mismo
sobreentrenamiento: requiere revisar condiciones de medición y contexto
junto con el entrenador y, si procede, valoración clínica. Use la
calculadora dedicada y registre también ambos valores en Mediciones.

CARGAS
Volumen: cantidad × porcentaje de referencia / 100.
Composición: minutos activos de categoría / minutos activos totales × 100.
No sumar minutos con repeticiones ni usar los porcentajes como FC de reserva.
Carga de sesión: duración total (minutos) × esfuerzo percibido (RPE, 0–10).
Preguntar por el conjunto de la sesión con un protocolo consistente;
la app registra cuándo se preguntó. Enseñar la escala al deportista primero.
RPE 0 = ningún esfuerzo; 10 = esfuerzo máximo percibido. No es una orden.
Anotar sueño, cansancio, dolor, participación y otros deportes en observaciones.
No aplicar automáticamente un descuento del 25 % por ser menor.
La carga propuesta requiere criterio del entrenador y consideración del
crecimiento, experiencia, salud, técnica, recuperación y calendario escolar.
Ante síntomas relevantes, interrumpir el ejercicio y solicitar evaluación.

CALCULADORA ADULTA
Opcional y separada de los planes. Solo orienta ejercicio aeróbico adulto.
FCmáx estimada = 208 − 0,7 × edad (Tanaka, adultos sanos).
FC objetivo = FCreposo + fracción × (FCmáx − FCreposo) (Karvonen).
La FC máxima predicha no es un límite clínico. No usar en menores ni cuando
la respuesta cardíaca esté alterada por enfermedad o medicación sin valoración.
El porcentaje de una curva histórica no se introduce automáticamente aquí.

DATOS
La base se guarda fuera del ejecutable. Haga copias periódicas en otro medio.
Restaurar reemplaza los datos activos: antes se guarda una copia automática.
La aplicación no tiene cifrado ni cuentas: proteja la sesión del sistema
operativo, el disco, los informes y las copias. Cada portátil trabaja por separado.
Los registros equivocados se anulan y se vuelven a introducir; se conserva
una auditoría local. No existe sincronización ni lectura automática de sensores.
"""


class Form(tk.Toplevel):
    """Formulario modal con desplazamiento y validación al guardar.

    fields: (clave, etiqueta, valor inicial, opciones o None).
    La función on_save valida y persiste; devuelve texto opcional de resultado.
    """
    def __init__(self, parent, title, fields, on_save, explanation=""):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.geometry("700x650")
        self.minsize(540,400)
        self.vars={}
        outer=ttk.Frame(self,padding=14);outer.pack(fill="both",expand=True)
        if explanation:
            ttk.Label(outer,text=explanation,wraplength=640,foreground="#176b87").pack(fill="x",pady=(0,12))
        area=ttk.Frame(outer);area.pack(fill="both",expand=True)
        canvas=tk.Canvas(area,highlightthickness=0)
        scroll=ttk.Scrollbar(area,orient="vertical",command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right",fill="y");canvas.pack(side="left",fill="both",expand=True)
        content=ttk.Frame(canvas,padding=6);win=canvas.create_window((0,0),window=content,anchor="nw")
        content.bind("<Configure>",lambda _:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda ev:canvas.itemconfigure(win,width=ev.width))
        content.columnconfigure(1,weight=1)
        for i,(key,label,value,options) in enumerate(fields):
            ttk.Label(content,text=label,wraplength=250).grid(row=i,column=0,sticky="w",padx=(0,12),pady=7)
            var=tk.StringVar(value="" if value is None else str(value));self.vars[key]=var
            widget=ttk.Combobox(content,textvariable=var,values=options,state="readonly") if options else ttk.Entry(content,textvariable=var)
            widget.grid(row=i,column=1,sticky="ew",pady=7)
        def save():
            try:
                result=on_save({k:v.get() for k,v in self.vars.items()})
            except (ValueError,sqlite3.Error,OSError) as exc:
                messagebox.showerror("Revise los datos",str(exc),parent=self)
                return
            self.destroy()
            if result:
                messagebox.showinfo("Resultado",str(result),parent=parent)
        buttons=ttk.Frame(outer);buttons.pack(fill="x",pady=(12,0))
        ttk.Button(buttons,text="Guardar / calcular",command=save).pack(side="right")
        ttk.Button(buttons,text="Cancelar",command=self.destroy).pack(side="right",padx=8)
        self.grab_set()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"TKD Entrenador · {VERSION} · versión piloto")
        self.geometry("1180x760");self.minsize(900,580)
        style=ttk.Style(self);style.theme_use("clam")
        style.configure("TButton",padding=7)
        style.configure("Treeview",rowheight=29,font=("Segoe UI",10))
        style.configure("Treeview.Heading",font=("Segoe UI",10,"bold"))
        style.configure("Title.TLabel",font=("Segoe UI",18,"bold"),foreground="#176b87")
        self.store=Store(data_directory()/"entrenamiento.sqlite3")
        self.athlete_id=None;self.plan_id=None
        self.protocol("WM_DELETE_WINDOW",self.close)
        header=ttk.Frame(self,padding=14);header.pack(fill="x")
        ttk.Label(header,text="TKD · Planificar, registrar y aprender",style="Title.TLabel").pack(anchor="w")
        row=ttk.Frame(header);row.pack(fill="x",pady=(12,0))
        ttk.Label(row,text="Deportista:").pack(side="left")
        self.selected=tk.StringVar()
        self.athlete_box=ttk.Combobox(row,textvariable=self.selected,state="readonly",width=38)
        self.athlete_box.pack(side="left",padx=8)
        self.athlete_box.bind("<<ComboboxSelected>>",self.select_athlete)
        ttk.Button(row,text="Nuevo",command=self.new_athlete).pack(side="left")
        ttk.Button(row,text="Editar ficha",command=lambda:self.new_athlete(True)).pack(side="left",padx=8)
        self.summary=tk.StringVar(value="Seleccione o cree un deportista para comenzar.")
        ttk.Label(header,textvariable=self.summary,wraplength=1090).pack(anchor="w",pady=(10,0))
        self.book=ttk.Notebook(self);self.book.pack(fill="both",expand=True,padx=14,pady=(0,12))
        self.tabs={}
        for name in ("Mediciones","Referencias","Microciclo","Sesiones","Progreso","Ayuda y copias"):
            tab=ttk.Frame(self.book,padding=10);self.book.add(tab,text=name);self.tabs[name]=tab
        self.make_measurements();self.make_refs();self.make_plans();self.make_sessions();self.make_progress();self.make_help()
        self.reload_athletes()

    def report_callback_exception(self, exc_type, exc_value, traceback):
        messagebox.showerror("No se pudo completar",str(exc_value),parent=self)

    def close(self):
        self.store.db.close();self.destroy()

    def need_athlete(self):
        if self.athlete_id is None:
            raise ValueError("Primero seleccione o cree un deportista.")
        return self.store.athlete(self.athlete_id)

    def selected_id(self,tree):
        ids=tree.selection()
        if not ids:
            raise ValueError("Seleccione una fila de la tabla.")
        return int(ids[0])

    def tree(self,parent,columns):
        frame=ttk.Frame(parent);frame.pack(fill="both",expand=True,pady=8)
        tree=ttk.Treeview(frame,columns=[k for k,_,_ in columns],show="headings",selectmode="browse")
        for key,label,width in columns:
            tree.heading(key,text=label);tree.column(key,width=width,minwidth=70,stretch=True)
        ys=ttk.Scrollbar(frame,orient="vertical",command=tree.yview)
        xs=ttk.Scrollbar(frame,orient="horizontal",command=tree.xview)
        tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)
        frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        tree.grid(row=0,column=0,sticky="nsew");ys.grid(row=0,column=1,sticky="ns");xs.grid(row=1,column=0,sticky="ew")
        return tree

    @staticmethod
    def fill(tree,rows,columns):
        tree.delete(*tree.get_children())
        for r in rows:
            tree.insert("","end",iid=r['id'],values=["" if r[k] is None else f"{r[k]:.2f}" if isinstance(r[k],float) else r[k] for k in columns])

    def buttons(self,tab,actions):
        bar=ttk.Frame(tab);bar.pack(fill="x")
        for label,callback in actions:
            ttk.Button(bar,text=label,command=callback).pack(side="left",padx=(0,7))

    def reload_athletes(self,selected_id=None):
        rows=self.store.rows("SELECT * FROM athletes ORDER BY name,id")
        self.athletes={f"{r['id']} · {r['name']}":r['id'] for r in rows}
        self.athlete_box['values']=list(self.athletes)
        if selected_id:
            self.selected.set(next(k for k,v in self.athletes.items() if v==selected_id));self.select_athlete()

    def select_athlete(self,_event=None):
        self.athlete_id=self.athletes.get(self.selected.get());self.plan_id=None
        a=self.need_athlete();age=age_on(a['birth'],date.today().isoformat())
        self.summary.set(f"{a['name']} · {age} años · {a['sex']} · "+("Menor: referencias individuales; sin zonas cardíacas automáticas." if age<18 else "Las referencias requieren revisión individual del entrenador."))
        self.refresh()

    def new_athlete(self,edit=False):
        a=self.need_athlete() if edit else {}
        fields=[('name','Nombre completo',a.get('name',''),None),('birth','Nacimiento (AAAA-MM-DD)',a.get('birth',''),None),('sex','Sexo',a.get('sex','Sin registrar'),('Masculino','Femenino','Sin registrar')),('experience','Experiencia / cinturón',a.get('experience',''),None),('guardian','Acudiente / autorización registrada',a.get('guardian',''),None),('notes','Observaciones',a.get('notes',''),None)]
        def save(v):
            aid=self.store.add_athlete(**v,athlete_id=a.get('id'));self.reload_athletes(aid)
        Form(self,"Ficha del deportista",fields,save,"Registre solo información necesaria. Peso y pulsos se guardan con fecha en Mediciones.")

    def make_measurements(self):
        tab=self.tabs['Mediciones']
        self.buttons(tab,[("Nueva medición",self.new_measurement),("Anular selección",lambda:self.void('measurements',self.mt)),("Convertir conteo manual",self.pulse_tool),("Calculadora FC adulta",self.hr_tool),("Prueba ortostática (acostado/de pie)",self.orthostatic_tool),("Umbral de seguimiento postural",self.orthostatic_threshold_tool)])
        ttk.Label(tab,text="PR/bpm = pulso; SpO₂/% = saturación. Un pulso leído después del esfuerzo se registra como recuperación. Registre también la presión arterial (sistólica y diastólica) como mediciones.",wraplength=1030).pack(anchor="w",pady=8)
        self.mt=self.tree(tab,[('date','Fecha',100),('kind','Medición',160),('value','Valor',90),('method','Método / postura',220),('delay_seconds','Seg. tras fin',100),('notes','Observaciones',220)])

    def new_measurement(self):
        self.need_athlete()
        fields=[('when','Fecha',date.today(),None),('kind','Tipo',MEASURE_TYPES[0],MEASURE_TYPES),('value','Valor','',None),('method','Método, dispositivo y postura','',None),('delay','Segundos desde fin (recuperación)','',None),('notes','Observaciones / hora','',None)]
        def save(v):
            self.store.add_measurement(self.athlete_id,**v);self.refresh()
        Form(self,"Nueva medición",fields,save,"En FC de recuperación indique cuánto tiempo pasó desde que terminó el esfuerzo. Una medición no se interpreta como aptitud para entrenar.")

    def pulse_tool(self):
        def calculate(v):
            pulse=manual_pulse(v['beats'],v['seconds'])
            return f"Estimación: {pulse:.0f} latidos/min.\nUn latido de diferencia representa {60/float(v['seconds'].replace(',','.')):.1f} lpm.\nRegistre por separado el contexto y la demora tras el esfuerzo."
        Form(self,"Conversión de conteo manual",[('beats','Latidos contados','',None),('seconds','Duración del conteo, segundos',6,None)],calculate)

    def orthostatic_tool(self):
        a=self.need_athlete()
        threshold=a['orthostatic_threshold']
        def calculate(v):
            r=orthostatic_risk(v['supine'],v['standing'],threshold)
            if r['flagged'] is None:
                aviso="Sin umbral de seguimiento configurado para este deportista (opcional, botón «Umbral de seguimiento postural»)."
            elif r['flagged']:
                aviso=ORTHOSTATIC_NEUTRAL_MESSAGE
            else:
                aviso=f"Diferencia dentro del umbral de seguimiento configurado (≤{threshold:g} lpm)."
            return f"FC acostado: {r['supine']:.0f} lpm · FC de pie: {r['standing']:.0f} lpm\nDiferencia: {r['difference']:.0f} lpm\n{aviso}\nCriterio personal de seguimiento, no diagnóstico: no sustituye el criterio del entrenador ni, si procede, una valoración clínica."
        Form(self,"Prueba ortostática",[('supine','FC acostado tras reposo (lpm)','',None),('standing','FC de pie, inmediatamente al levantarse (lpm)','',None)],calculate,"Protocolo histórico: reposar acostado unos minutos, medir la FC, levantarse y medir de inmediato de pie. Registre también ambos valores en Mediciones (FC acostado / FC de pie).")

    def orthostatic_threshold_tool(self):
        a=self.need_athlete()
        fields=[('threshold','Umbral de seguimiento (lpm, vacío = desactivado)',a['orthostatic_threshold'] if a['orthostatic_threshold'] is not None else '',None)]
        def save(v):
            self.store.set_orthostatic_threshold(self.athlete_id,v['threshold']);self.select_athlete()
        Form(self,"Umbral de seguimiento postural",fields,save,"Opcional. No está activado por defecto en ningún deportista. Es un criterio personal de seguimiento, no un valor validado como diagnóstico. El valor histórico de referencia era 15 lpm.")

    def hr_tool(self):
        a=self.need_athlete()
        if age_on(a['birth'],date.today().isoformat())<18:
            raise ValueError("Esta calculadora es solo para adultos. Para este menor registre observaciones y una planificación individual revisada.")
        def calculate(v):
            r=adult_hr(a['birth'],date.today().isoformat(),v['rest'],v['intensity'],v['maximum'])
            return f"Método: {r['method']}\nFC máxima de referencia: {r['maximum']:.0f} lpm\nFC objetivo orientativa: {r['target']:.0f} lpm\nNo se incorpora automáticamente al microciclo."
        Form(self,"Orientación aeróbica adulta",[('rest','FC de reposo medida (lpm)','',None),('intensity','Porcentaje de reserva cardíaca','',None),('maximum','FC máxima evaluada (opcional)','',None)],calculate,"Si deja la máxima vacía se estima con Tanaka. El porcentaje debe elegirse para el objetivo aeróbico; no copiar la intensidad de las curvas históricas. No aplicable automáticamente con enfermedad o fármacos que alteren la FC.")

    def make_refs(self):
        tab=self.tabs['Referencias']
        self.buttons(tab,[("Añadir referencia",self.new_ref),("Editar selección",lambda:self.new_ref(True)),("Referencias históricas adultas",self.old_refs)])
        ttk.Label(tab,text="100 % = referencia semanal individual, no máximo obligatorio. Para repeticiones indique también minutos activos.",wraplength=1030).pack(anchor="w",pady=8)
        self.rt=self.tree(tab,[('exercise','Ejercicio',200),('category','Formación',110),('quantity','Cantidad / semana',130),('unit','Unidad',120),('active_minutes','Min activos / semana',150),('round_minutes','Min/asalto',100),('pause_seconds','Pausa s',90)])

    def new_ref(self,edit=False):
        self.need_athlete()
        r=self.store.rows("SELECT * FROM refs WHERE id=?",(self.selected_id(self.rt),))[0] if edit else {}
        fields=[('exercise','Nombre del ejercicio',r.get('exercise',''),None),('category','Formación',r.get('category','General'),CATEGORIES),('unit','Unidad',r.get('unit','minutos'),UNITS),('quantity','Referencia semanal al 100 %',r.get('quantity',''),None),('active_minutes','Min activos al 100 % (repeticiones)',r.get('active_minutes',''),None),('round_minutes','Minutos por asalto',r.get('round_minutes',3) or 3,None),('pause_seconds','Pausa orientativa entre series/asaltos (s)',r.get('pause_seconds',60),None)]
        def save(v):
            if edit and v['exercise'].strip()!=r['exercise']:
                raise ValueError("Conserve el nombre al editar; use Añadir para otro ejercicio.")
            self.store.save_ref(self.athlete_id,**v);self.refresh()
        Form(self,"Referencia semanal individual",fields,save,"Minutos: cantidad = tiempo activo. Asaltos: tiempo = cantidad × minutos por asalto. Repeticiones: introduzca un tiempo propio, sin convertirlo desde el pulso. Pausa: indicación que debe detallarse por actividad.")

    def old_refs(self):
        a=self.need_athlete()
        if age_on(a['birth'],date.today().isoformat())<18:
            raise ValueError("Las referencias adultas históricas no se cargan en menores. Añada referencias individuales evaluadas por el entrenador.")
        if not messagebox.askyesno("Referencias históricas", "Se añadirán cross 90 min, escalera 70 min y combates 16 y 12 asaltos de 3 min, solo si no existen. No son una recomendación actual. Patadas (200) debe añadirse con un tiempo activo definido por usted. ¿Cargar estas referencias para revisarlas?",parent=self):
            return
        names={r['exercise'] for r in self.store.rows("SELECT exercise FROM refs WHERE athlete_id=?",(self.athlete_id,))}
        for name,cat,unit,qty in [('Cross','General','minutos',90),('Escalera','General','minutos',70),('Combate condicionado','Competitiva','asaltos',16),('Combate libre','Competitiva','asaltos',12)]:
            if name not in names:
                self.store.save_ref(self.athlete_id,name,cat,unit,qty,round_minutes=3,pause_seconds=60)
        self.refresh()

    def make_plans(self):
        tab=self.tabs['Microciclo']
        self.buttons(tab,[("Nuevo borrador",self.new_plan),("Editar actividad",self.edit_activity),("Retirar actividad",self.remove_activity),("Marcar revisado",self.review),("Informe del plan",self.plan_report)])
        bar=ttk.Frame(tab);bar.pack(fill="x",pady=8)
        ttk.Label(bar,text="Plan:").pack(side="left")
        self.plan_var=tk.StringVar();self.plan_box=ttk.Combobox(bar,textvariable=self.plan_var,state="readonly",width=75);self.plan_box.pack(side="left",padx=8)
        self.plan_box.bind("<<ComboboxSelected>>",self.load_plan)
        self.plan_summary=tk.StringVar(value="Genere un borrador y revise su distribución por días.")
        ttk.Label(tab,textvariable=self.plan_summary,wraplength=1040).pack(anchor="w")
        self.pt=self.tree(tab,[('date','Fecha',100),('category','Formación',110),('exercise','Ejercicio',170),('quantity','Cantidad',80),('unit','Unidad',100),('active_minutes','Min activos',90),('pause_seconds','Pausa s',75),('target_rpe','RPE objetivo',90),('notes','Indicaciones',190)])

    def new_plan(self):
        self.need_athlete();today=date.today();monday=today-timedelta(days=today.weekday())
        fields=[('start','Lunes de inicio',monday,None),('phase','Fase',PHASES[0],PHASES),('days','Días: 1=Lun, ... 7=Dom','1,3,5',None),('general','% referencia General',0,None),('special','% referencia Especial',0,None),('competitive','% referencia Competitiva',0,None),('notes','Objetivo y criterio de carga','',None)]
        def save(v):
            try:
                days=[int(x.strip())-1 for x in v['days'].split(',')]
            except ValueError:
                raise ValueError("Días: escriba números del 1 al 7 separados por comas.") from None
            pid=self.store.create_plan(self.athlete_id,v['start'],v['phase'],days,dict(zip(CATEGORIES,[v['general'],v['special'],v['competitive']])),v['notes'])
            self.refresh();self.plan_id=pid
            self.plan_var.set(next(k for k,x in self.plans.items() if x==pid));self.load_plan()
        Form(self,"Borrador de microciclo semanal",fields,save,"Seleccione porcentajes de las referencias individuales, entre 0 y 100. No existe una proporción Matveyev predeterminada. El borrador reparte por igual: ajuste cada actividad antes de marcarlo revisado.")

    def load_plan(self,_event=None):
        self.plan_id=self.plans.get(self.plan_var.get())
        items=self.store.rows("SELECT * FROM items WHERE plan_id=? ORDER BY date,id",(self.plan_id,))
        self.fill(self.pt,items,['date','category','exercise','quantity','unit','active_minutes','pause_seconds','target_rpe','notes'])
        text=' · '.join(f"{c}: {m:.1f} min ({p:.1f} %)" for c,(m,p) in composition(items).items())
        self.plan_summary.set(text+". Proporciones de tiempo activo; pausas excluidas.")

    def edit_activity(self):
        iid=self.selected_id(self.pt);r=self.store.rows("SELECT * FROM items WHERE id=?",(iid,))[0]
        fields=[('when','Fecha dentro de la semana',r['date'],None),('quantity',f"Cantidad ({r['unit']})",r['quantity'],None),('active_minutes','Min activos (solo repeticiones)',r['active_minutes'],None),('pause_seconds','Pausa entre series/asaltos (s)',r['pause_seconds'],None),('target_rpe','RPE objetivo orientativo (opcional)',r['target_rpe'],None),('notes','Series, ritmo, técnica y descansos',r['notes'],None)]
        def save(v):
            self.store.edit_item(iid,**v);self.load_plan()
        Form(self,r['exercise'],fields,save,"Para minutos y asaltos el tiempo se recalcula desde la cantidad. Solo puede editarse un borrador.")

    def remove_activity(self):
        iid=self.selected_id(self.pt)
        if messagebox.askyesno("Retirar actividad","¿Retirar esta actividad del borrador? Quedará constancia en la auditoría.",parent=self):
            self.store.remove_item(iid);self.load_plan()

    def review(self):
        if not self.plan_id:
            raise ValueError("Seleccione un plan.")
        def save(v):
            self.store.review_plan(self.plan_id,v['name']);self.refresh()
        Form(self,"Revisión del entrenador",[('name','Nombre del responsable','',None)],save,"Revise calendario, descansos, técnica, duración, experiencia y recuperación. El plan quedará congelado; no implica autorización médica.")

    def make_sessions(self):
        tab=self.tabs['Sesiones']
        self.buttons(tab,[("Registrar sesión",self.new_session),("Anular selección",lambda:self.void('sessions',self.st))])
        ttk.Label(tab,text="Anote el trabajo REAL. La carga se calcula con duración total × RPE del deportista; no equivale a calorías.",wraplength=1030).pack(anchor="w",pady=8)
        self.st=self.tree(tab,[('date','Fecha',110),('plan_id','Plan',65),('duration','Duración min',110),('rpe','RPE',65),('coach_rpe','RPE previsto',105),('load','Carga UA',105),('actual_work','Trabajo realizado',280)])

    def new_session(self):
        self.need_athlete()
        choices={'Sin vínculo':None}
        choices.update({f"{r['id']} · {r['start']} · {r['phase']}":r['id'] for r in self.store.rows("SELECT * FROM plans WHERE athlete_id=? AND status='Revisado' ORDER BY start DESC,id DESC",(self.athlete_id,))})
        fields=[('when','Fecha',date.today(),None),('plan','Plan revisado','Sin vínculo',tuple(choices)),('duration','Duración total de sesión (min)','',None),('rpe','RPE deportista (0–10)','',None),('coach_rpe','RPE previsto entrenador (opcional)','',None),('rpe_delay','Minutos tras sesión al preguntar RPE',30,None),('general_min','Min activos generales',0,None),('special_min','Min activos especiales',0,None),('competitive_min','Min activos competitivos',0,None),('actual_work','Ejercicios y cantidades realizadas','',None),('sleep','Sueño: duración/calidad','',None),('fatigue','Cansancio comunicado','',None),('pain','Dolor o molestias comunicadas','',None),('notes','Observaciones / cambios','',None)]
        def save(v):
            v['plan_id']=choices[v.pop('plan')];self.store.add_session(self.athlete_id,**v);self.refresh()
        Form(self,"Sesión realizada",fields,save,"Duración total incluye las pausas de entrenamiento según su protocolo. Minutos activos excluyen pausas. Mantenga el mismo criterio. Describa cantidades realmente completadas, incluso cuando difieran del plan.")

    def void(self,table,tree):
        rid=self.selected_id(tree)
        def save(v):
            self.store.void_record(table,rid,v['reason']);self.refresh()
        Form(self,"Anular registro erróneo",[('reason','Motivo','',None)],save,"Se conserva el registro anulado para auditoría y se excluye del informe. Introduzca después la medición o sesión correcta.")

    def make_progress(self):
        tab=self.tabs['Progreso']
        self.buttons(tab,[("Informe individual / imprimir",self.full_report),("Exportar sesiones CSV",self.csv_report),("Actualizar",self.refresh)])
        self.progress_text=tk.Text(tab,wrap="word",font=("Segoe UI",12),padx=16,pady=16,state="disabled")
        self.progress_text.pack(fill="both",expand=True,pady=10)

    def write_progress(self):
        rows=self.store.rows("SELECT *,duration*rpe AS load FROM sessions WHERE athlete_id=? AND void=0 ORDER BY date,id",(self.athlete_id,))
        text="PROGRESO INDIVIDUAL\n\n"
        if rows:
            text+=f"Sesiones registradas: {len(rows)}\nDuración acumulada: {sum(r['duration'] for r in rows):.1f} minutos\nCarga acumulada registrada: {sum(r['load'] for r in rows):.1f} UA\n\n"
            for r in rows[-8:]:
                text+=f"{r['date']} · {r['duration']:g} min · RPE {r['rpe']:g} · {r['load']:g} UA\n"
        else:
            text+="Todavía no hay sesiones realizadas.\n"
        text+="\nEl informe incluye gráficos y las mediciones registradas.\nUna semana sin registros no se interpreta automáticamente como descanso.\nMás carga no significa necesariamente mejor progreso: revise técnica,\nconsistencia, bienestar y desempeño junto con estos indicadores."
        self.progress_text.configure(state="normal");self.progress_text.delete("1.0","end");self.progress_text.insert("1.0",text);self.progress_text.configure(state="disabled")

    def save_report(self,plan_id):
        self.need_athlete()
        path=filedialog.asksaveasfilename(parent=self,title="Guardar informe",defaultextension=".html",initialfile="informe_tkd.html",filetypes=[('Informe web','*.html')])
        if path:
            Path(path).write_text(report_html(self.store,self.athlete_id,plan_id),encoding='utf-8')
            webbrowser.open(Path(path).resolve().as_uri())

    def full_report(self):
        self.save_report(None)

    def plan_report(self):
        if not self.plan_id:
            raise ValueError("Seleccione un plan.")
        self.save_report(self.plan_id)

    def csv_report(self):
        self.need_athlete()
        path=filedialog.asksaveasfilename(parent=self,defaultextension=".csv",initialfile="sesiones_tkd.csv",filetypes=[('CSV','*.csv')])
        if path:
            export_sessions(self.store,self.athlete_id,path);messagebox.showinfo("Exportación","Archivo guardado.",parent=self)

    def make_help(self):
        tab=self.tabs['Ayuda y copias']
        self.buttons(tab,[("Crear copia de seguridad",self.backup),("Restaurar copia",self.restore),("Ver curvas históricas",self.show_history)])
        ttk.Label(tab,text=f"Base de datos: {self.store.path}",wraplength=1030).pack(anchor="w",pady=8)
        frame=ttk.Frame(tab);frame.pack(fill='both',expand=True)
        text=tk.Text(frame,wrap='word',font=('Segoe UI',11));scroll=ttk.Scrollbar(frame,command=text.yview)
        text.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');text.pack(fill='both',expand=True)
        text.insert('1.0',HELP);text.configure(state='disabled')

    def backup(self):
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.sqlite3',initialfile=f"copia_tkd_{date.today()}.sqlite3",filetypes=[('Copia TKD','*.sqlite3')])
        if path:
            self.store.backup(path);messagebox.showinfo("Copia creada","Copia comprobada. Conserve una copia adicional en otro medio protegido.",parent=self)

    def restore(self):
        path=filedialog.askopenfilename(parent=self,filetypes=[('Copia TKD','*.sqlite3')])
        if path and messagebox.askyesno("Restaurar", "Esto reemplazará todos los registros activos por los de la copia. Se conservará una copia previa automática. ¿Continuar?",parent=self):
            before=self.store.restore(path);self.athlete_id=None;self.plan_id=None;self.selected.set('');self.reload_athletes();self.refresh()
            self.summary.set('Copia restaurada. Seleccione un deportista.')
            messagebox.showinfo("Restaurado",f"Copia previa guardada en:\n{before}",parent=self)

    def show_history(self):
        from core import bars_svg,table_html
        body='<h1>Curvas históricas de la plantilla de Justo</h1><p>Archivo de referencia: 48 semanas. Valores transcritos, no recomendaciones actuales ni porcentajes de reserva cardíaca. No se aplican automáticamente a deportistas.</p>'
        for sheet,rows in HISTORICAL.items():
            body+=f'<h2>{sheet}</h2>'
            body+=bars_svg([str(x['week']) for x in rows],[('Volumen %',[x['volume'] for x in rows]),('Intensidad histórica %',[x['intensity'] for x in rows])],sheet+' · semanas 1–48')
            body+=table_html(['Semana','Volumen %','Intensidad histórica %'],[[x['week'],x['volume'],x['intensity']] for x in rows])
        path=data_directory()/'curvas_historicas.html'
        path.write_text('<!doctype html><html lang="es"><meta charset="utf-8"><title>Archivo histórico TKD</title><style>body{font:16px Arial;max-width:950px;margin:30px auto}svg{width:100%}td,th{padding:6px;border:1px solid #ccc}table{border-collapse:collapse}</style>'+body+'</html>',encoding='utf-8')
        webbrowser.open(path.as_uri())

    def refresh(self):
        aid=self.athlete_id
        self.fill(self.mt,self.store.rows("SELECT * FROM measurements WHERE athlete_id=? AND void=0 ORDER BY date DESC,id DESC",(aid,)),['date','kind','value','method','delay_seconds','notes'])
        self.fill(self.rt,self.store.rows("SELECT * FROM refs WHERE athlete_id=? ORDER BY category,exercise",(aid,)),['exercise','category','quantity','unit','active_minutes','round_minutes','pause_seconds'])
        self.fill(self.st,self.store.rows("SELECT *,duration*rpe AS load FROM sessions WHERE athlete_id=? AND void=0 ORDER BY date DESC,id DESC",(aid,)),['date','plan_id','duration','rpe','coach_rpe','load','actual_work'])
        rows=self.store.rows("SELECT * FROM plans WHERE athlete_id=? ORDER BY start DESC,id DESC",(aid,))
        self.plans={f"{p['id']} · {p['start']} · {p['phase']} · {p['status']}":p['id'] for p in rows}
        self.plan_box['values']=list(self.plans)
        self.plan_var.set(next((k for k,v in self.plans.items() if v==self.plan_id),''));self.load_plan();self.write_progress()


if __name__ == '__main__':
    app=App()
    app.mainloop()
