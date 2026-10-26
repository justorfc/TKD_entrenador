# TKD Entrenador — versión piloto 0.1.0

Aplicación local en español para recuperar la organización del entrenamiento de
Justo y registrar la evolución individual. Incluye código fuente, pruebas,
manual, curvas originales y preparación del ejecutable Windows.

**Estado:** cálculos y persistencia verificados con pruebas automatizadas en
Linux. La interfaz gráfica y el ejecutable deben probarse en un equipo Windows
antes de usar datos reales. El paquete no contiene un `.exe` ya compilado ni
una validación clínica/deportiva de las cargas.

## Inicio

1. Extraer todo el ZIP; conservar juntos `app.py`, `core.py` e `historical.py`.
2. En el equipo de desarrollo, instalar Python con Tcl/Tk y el lanzador `py`.
   El código utiliza sintaxis de Python 3.10 o posterior. Para empaquetar,
   utilizar una versión compatible con la versión instalada de PyInstaller.
3. Abrir una terminal en esta carpeta y ejecutar:

```bat
py -m tkinter
py app.py
```

El primer comando comprueba que Tcl/Tk abre una ventana. El segundo inicia el
programa. No se necesitan paquetes externos para ejecutar el código fuente.
También puede usar `iniciar_windows.cmd`.

## Crear el ejecutable Windows

En un equipo Windows, ejecutar `crear_exe_windows.cmd`. Este archivo crea un
entorno virtual `.venv_build`, instala PyInstaller, ejecuta las pruebas y genera:

```text
dist/TKD_Entrenador.exe
```

La instalación inicial de PyInstaller necesita internet; el programa terminado
funciona sin internet. El comando equivalente, dentro de un entorno de
desarrollo preparado, es:

```bat
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TKD_Entrenador app.py
```

El entrenador recibe ese `.exe` y no necesita instalar Python. Puede guardarlo
en una carpeta de su portátil y crear un acceso directo. Es un ejecutable
portable, no un instalador con asistente. Las actualizaciones del ejecutable
conservan la base de datos porque se almacena fuera del programa.

PyInstaller empaqueta Python y sus dependencias; no transforma la aplicación
en un dispositivo médico ni valida la metodología de entrenamiento. Para crear
el `.exe` Windows debe ejecutarse en Windows. Aquí no se ha generado ese binario.

## Flujo de trabajo del entrenador

### 1. Ficha individual

Crear el deportista, indicando nombre, nacimiento, sexo y experiencia. La edad
se calcula a partir de la fecha de nacimiento. En menores, registrar de manera
breve la autorización y el acudiente según el procedimiento de su organización.
No introducir diagnósticos innecesarios en observaciones.

### 2. Mediciones

Registrar peso, talla, FC basal, FC de reposo, FC durante el esfuerzo o FC de
recuperación. Cada registro incluye fecha, valor, método y observaciones.
Se pueden introducir varios registros por día; anotar hora/protocolo en notas.
El programa no borra las mediciones anteriores cuando se registra una nueva.

Para este proyecto se adoptan definiciones operativas:

- **Basal:** al despertar y antes de levantarse, siguiendo condiciones estables.
- **Reposo:** tras un periodo tranquilo, indicando postura y condiciones.
- **Durante:** lectura efectivamente obtenida durante el esfuerzo.
- **Recuperación:** lectura posterior al esfuerzo, con los segundos transcurridos.

No intercambiar basal y reposo automáticamente. La calculadora adulta pide
explícitamente un pulso de reposo; no selecciona una medición por su cuenta.

El pulsioxímetro estima pulso y saturación. Leer **PR/bpm** para pulso; **SpO2/%**
no es la frecuencia cardíaca. Seguir las instrucciones del dispositivo,
mantener el dedo quieto y esperar una señal estable. Si es necesario detener
el entrenamiento para medir, registrar recuperación y demora. No considerar
esa lectura equivalente al pulso durante el movimiento.

La conversión de un conteo manual es:

`FC (lpm) = latidos contados × 60 / segundos de observación`

Con seis segundos, un latido de diferencia equivale a diez lpm. La calculadora
solo convierte la observación; no corrige sus errores ni estima el pulso que
había antes de detenerse.

### 3. Referencias semanales

Cada deportista tiene su propio catálogo de ejercicios y referencias. El 100 %
es una referencia de planificación que decide el entrenador, no una prueba al
máximo, un límite seguro ni una meta obligatoria.

Las unidades aclaradas por Justo son:

| Ejercicio | Referencia histórica semanal |
|---|---:|
| Cross | 90 minutos |
| Escalera | 70 minutos |
| Patadas | 200 repeticiones |
| Combate condicionado | 16 asaltos × 3 minutos = 48 minutos activos |
| Combate libre | 12 asaltos × 3 minutos = 36 minutos activos |

El botón de referencias históricas está disponible solo para adultos y requiere
confirmación. No reemplaza referencias existentes. Patadas debe añadirse
manualmente porque falta definir su duración activa. Los 60 segundos de pausa
que ofrece el formulario son un valor inicial editable de la interfaz, no un
dato aportado por Justo ni una regla reglamentaria. Revisarlos siempre.
Los asaltos de tres minutos son la referencia histórica, no una afirmación
sobre duración reglamentaria vigente o adecuada para todas las edades.

Saco y canilleras se pueden añadir con la unidad que corresponda. No se ha
supuesto qué significaban 150 y 120 en el archivo antiguo. También se pueden
añadir movilidad, juegos, técnica, fuerza o desplazamientos: el entrenador
asigna la categoría según su función en el plan.

Para repeticiones, introducir además los minutos activos previstos para el
100 %. Este dato debe estimarse o medirse con el protocolo del ejercicio.
La app supone proporcionalidad tiempo/cantidad solo al construir el borrador;
se puede corregir el tiempo de cada actividad posteriormente.

### 4. Microciclo semanal

Indicar un lunes, fase, días de trabajo, porcentaje de cada referencia y objetivo.
La semana contiene siete días reales, puede cruzar meses y años, y no depende
de los bloques antiguos de cuatro semanas por mes.

Ejemplo **puramente aritmético**, no una recomendación de carga:

- Referencia cross 90 min; porcentaje elegido 50 %: 45 min semanales.
- Referencia patadas 200; 50 %: 100 patadas semanales.
- Referencia combate 16 asaltos; 50 %: ocho asaltos semanales.

Los porcentajes General/Especial/Competitiva NO tienen que sumar 100: cada uno
escala su propia referencia. Para medir la composición del microciclo se usa:

`proporción de categoría = minutos activos de categoría / minutos activos totales × 100`

Esas proporciones sí suman 100 cuando hay actividad. No se suman directamente
repeticiones, asaltos y minutos. Las pausas quedan excluidas de esta composición;
el entrenador debe considerar también el tiempo total disponible.

El primer reparto es uniforme y constituye un borrador. Las repeticiones y
asaltos se redondean una vez por semana al entero más próximo, con mitades
hacia arriba; los minutos se reparten a resolución de 0,1. Se conserva el total
redondeado. Es necesario revisar cantidades pequeñas y actividades que queden
sin asignar por redondeo. No se crean actividades de cantidad cero.

Editar cada fila permite cambiar día, cantidad, tiempo de repeticiones, pausa,
RPE objetivo opcional e indicaciones (series, técnica, ritmo, descansos).
En minutos, el tiempo coincide con la cantidad; en asaltos, con cantidad por
duración de asalto. La duración del asalto se define antes en Referencias.
Retirar una fila elimina solo esa actividad del borrador y deja auditoría.

La app no inventa una alternancia de días fuertes y suaves ni incrementos
semanales. El entrenador debe revisar descanso, experiencia, crecimiento,
calendario escolar y otras actividades deportivas. Para adolescentes no se
aplica automáticamente una reducción del 25 % ni un porcentaje de Matveyev.

Al marcar Revisado, el plan queda congelado. Esto significa revisión del
entrenador, no aptitud médica. Para cambiarlo se crea un nuevo plan: los
anteriores permanecen. Las referencias posteriores no recalculan el pasado.

### 5. Sesión realizada

Registrar fecha, duración total, RPE del deportista, RPE previsto opcional,
momento de recogida de RPE, minutos activos de cada categoría, trabajo realizado
y observaciones sobre sueño, cansancio y dolor. Los minutos activos no pueden
superar el tiempo total. La parte restante puede incluir descansos y explicaciones.

Enseñar primero la escala 0–10, con anclajes y ejemplos apropiados para la edad.
El RPE de sesión pregunta por el conjunto de la sesión. Registrar siempre un
procedimiento consistente. El formulario propone preguntar a los 30 minutos,
pero permite registrar el intervalo realmente utilizado. No se debe asumir
que todos los niños interpretan una escala adulta de la misma manera.

`carga de sesión (UA) = duración total en minutos × RPE de sesión`

Ejemplo aritmético: 60 min × 5 = 300 unidades arbitrarias. No son calorías,
capacidad física ni un umbral clínico. El RPE objetivo de un ejercicio y el
RPE global de una sesión son observaciones diferentes: no se promedian
automáticamente para reemplazarse entre sí.

Una sesión puede vincularse a un plan revisado del mismo deportista y semana.
Si hay varios planes alternativos, vincular al que realmente se utilizó.
Las cantidades realizadas se describen en texto; esta versión compara por
categoría usando minutos, no calcula cumplimiento automático de cada patada.

### 6. Progreso e informes

El informe individual incluye mediciones y sesiones. El informe del plan
añade actividades, composición general/especial/competitiva y gráfico de
minutos activos planificados frente a los registrados en sesiones vinculadas.
Un valor sin registro no prueba que hubo descanso o incumplimiento.

Se grafica la carga por semana usando las últimas doce semanas con registros.
No se rellenan semanas sin datos ni se declara que una carga alta sea mejor.
La app no predice lesiones ni recomienda aumentos automáticamente.

El HTML se abre en el navegador local y contiene todo lo necesario para verse
sin internet. Usar **Ctrl+P → Guardar como PDF** para imprimir o entregar.
CSV exporta las sesiones no anuladas. Conservar los informes como información
personal: contienen nombres y datos del deportista.

### 7. Correcciones y copias

Las mediciones y sesiones erróneas se anulan con motivo y se vuelven a registrar.
Se excluyen de los informes; no desaparecen de la auditoría local.

En Windows la base está en:

```text
%LOCALAPPDATA%\TKD_Entrenador\entrenamiento.sqlite3
```

La interfaz muestra la ruta exacta. Crear copias periódicas mediante el botón
correspondiente y conservar otra en un medio protegido. La restauración valida
integridad y estructura y crea una copia previa antes de reemplazar los datos.
No usar la base activa directamente en una carpeta compartida entre equipos.

Esta versión no implementa autenticación ni cifrado. La protección depende
de la cuenta y el disco del sistema operativo y del manejo de copias. No afirmar
que la base SQLite está cifrada. Tampoco hay nube, sincronización o transmisión
de datos. En un portátil compartido se necesitan controles adicionales antes
de introducir información identificable de menores.

## Fundamento y límites del modelo

Las curvas originales se conservan en `historical.py`, extraídas de las
columnas de semana, volumen e intensidad del Excel. Son 48 valores por hoja.
El botón «Ver curvas históricas» genera tablas y gráficos de barras. No se
aplican a la FC ni se corrigen silenciosamente los porcentajes originales.

Se mantiene la distinción general/especial/competitiva y las fases del proceso.
No se afirma haber reconstruido los libros del convenio colombo-alemán ni sus
proporciones originales. Sin la edición y el texto fuente no puede atribuirse
una tabla nueva a esos autores. El programa es una herramienta para organizar
y documentar decisiones, no una recuperación exacta de la teoría perdida.

La calculadora adulta utiliza:

`FCmáx estimada = 208 − 0,7 × edad` (Tanaka)

`FCobjetivo = FCreposo + intensidad/100 × (FCmáx − FCreposo)` (Karvonen)

Admite una FC máxima evaluada aportada por el usuario. No usar un pico casual
del pulsioxímetro como si fuera una evaluación máxima. El cálculo es opcional,
no se guarda como medición y no alimenta los planes. La fórmula de Tanaka
procede de adultos sanos y tiene incertidumbre individual. No se utiliza
`226 − edad` para mujeres ni se crean zonas automáticas para menores.

La planificación en menores requiere valoración apropiada del contexto del
deportista. La consulta a ciencias del deporte o medicina del deporte es
especialmente relevante para definir pruebas, objetivos fisiológicos o adaptar
el programa ante enfermedad, lesiones o síntomas. La aplicación no sustituye
esa evaluación.

## Organización del código

| Archivo | Función |
|---|---|
| `app.py` | Interfaz Tkinter/ttk, formularios, tablas, ayudas y exportación. |
| `core.py` | Validación, cálculos, SQLite, auditoría, copias e informes HTML/SVG. |
| `historical.py` | Valores del Excel original, sin dependencia de Excel. |
| `test_core.py` | Pruebas unitarias y de integración con bases temporales. |
| `iniciar_windows.cmd` | Inicio desde el código fuente. |
| `crear_exe_windows.cmd` | Preparación del ejecutable en Windows. |
| `MANUAL.html` | Este manual para abrir y leer en navegador. |
| `EJEMPLO_INFORME.html` | Informe de datos ficticios para revisar la salida. |

SQLite separa deportistas, mediciones, referencias, planes, actividades,
sesiones y auditoría. Se utilizan claves foráneas y transacciones. Las consultas
que reciben datos utilizan parámetros SQL. Las tablas usadas en operaciones
dinámicas se limitan a una lista permitida. Los textos se escapan en los informes
y se neutralizan prefijos de fórmulas en textos exportados a CSV.

## Comprobaciones y prueba piloto

```bat
py -m unittest -v test_core.py
```

Las 23 pruebas verifican cálculo de edad, conteo manual, Karvonen/Tanaka,
rechazo de cálculos adultos en menores, entradas inválidas, conservación de
totales, mezcla correcta de unidades, referencias históricas, planes congelados,
aislamiento de deportistas, carga de sesión, validación de recuperación,
copias/restauración y escape de informes.

Falta ejecutar en Windows la prueba de interfaz y distribución:

1. Crear un deportista ficticio adulto y otro menor.
2. Añadir referencias propias, generar y editar un microciclo.
3. Registrar mediciones y una sesión; comprobar tablas e informe impreso.
4. Cerrar y abrir para comprobar persistencia.
5. Crear y restaurar una copia con datos ficticios.
6. Empaquetar y abrir el `.exe` en un equipo sin Python.
7. Revisar tamaños de letra, fechas, decimales y comodidad de uso con el entrenador.

No se incluye una base con personas reales. El informe de ejemplo es una
demostración de software, no una propuesta de entrenamiento.

## Fuentes consultadas

Consulta: 26 de octubre de 2026. Fuentes científicas orientan los límites del
modelo; no validan automáticamente este programa ni sus decisiones de interfaz.

- Tanaka, Monahan y Seals (2001). *Age-predicted maximal heart rate revisited*.
  https://pubmed.ncbi.nlm.nih.gov/11153730/
- Machado y Denadai (2011). *Validity of maximum heart rate prediction equations
  for children and adolescents*. https://pubmed.ncbi.nlm.nih.gov/21739069/
- Bergeron et al. (2015). *IOC consensus statement on youth athletic development*.
  https://pubmed.ncbi.nlm.nih.gov/26084524/
- Albuquerque et al. (2026). *Training load monitoring in taekwondo:
  athlete-reported and coach-planned ratings of perceived exertion and the role
  of session duration*. https://doi.org/10.1007/s11332-026-01881-9
- FDA. *Pulse Oximeter Basics*.
  https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics
- MedlinePlus. *Pulsioximetría*.
  https://medlineplus.gov/spanish/pruebas-de-laboratorio/pulsioximetria/
- Documentación oficial Python: https://docs.python.org/3/library/tkinter.html
  y https://docs.python.org/3/library/sqlite3.html
- Documentación oficial PyInstaller:
  https://pyinstaller.org/en/stable/operating-mode.html

Las referencias y unidades históricas proceden del libro de Excel aportado por
Justo y de sus aclaraciones en esta conversación. Los valores no se atribuyen
a una edición específica de Matveyev sin disponer de esa fuente.
