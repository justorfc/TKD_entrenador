# TKD Entrenador

**Versión piloto 0.1.0**

Aplicación de escritorio local, en español, para organizar el entrenamiento de
Taekwondo y registrar la evolución de cada deportista: ficha individual,
mediciones fisiológicas, referencias semanales por ejercicio, microciclos
planificados, sesiones realizadas, progreso e informes imprimibles.

> **Estado del proyecto:** los cálculos y la persistencia de datos están
> verificados con pruebas automatizadas. La interfaz gráfica y el ejecutable
> deben probarse con datos ficticios antes de usar información real de
> deportistas. El programa **no** sustituye valoración médica o deportiva
> profesional y no incluye validación clínica de las cargas de entrenamiento.

## Tabla de contenido

- [Qué hace la aplicación](#qué-hace-la-aplicación)
- [Requisitos](#requisitos)
- [Puesta en marcha rápida](#puesta-en-marcha-rápida)
- [Guía de uso paso a paso](#guía-de-uso-paso-a-paso)
  - [1. Deportista](#1-deportista)
  - [2. Mediciones](#2-mediciones)
  - [3. Referencias](#3-referencias)
  - [4. Microciclo](#4-microciclo)
  - [5. Sesiones](#5-sesiones)
  - [6. Progreso](#6-progreso)
  - [7. Ayuda y copias](#7-ayuda-y-copias)
- [Dónde quedan los datos y cómo respaldarlos](#dónde-quedan-los-datos-y-cómo-respaldarlos)
- [Crear el ejecutable para Windows](#crear-el-ejecutable-para-windows)
- [Pruebas automatizadas](#pruebas-automatizadas)
- [Organización del código](#organización-del-código)
- [Límites y fundamento del modelo](#límites-y-fundamento-del-modelo)
- [Licencia](#licencia)

## Qué hace la aplicación

- Registra una **ficha por deportista** (nombre, nacimiento, sexo, experiencia,
  acudiente en menores) y calcula la edad automáticamente.
- Guarda **mediciones** (peso, talla, frecuencia cardíaca basal/reposo/durante
  el esfuerzo/recuperación, presión arterial) con fecha, método y notas.
- Permite definir **referencias semanales** propias por ejercicio y categoría
  (General, Especial, Competitiva), incluidas las referencias históricas del
  convenio (cross, escalera, patadas, combate).
- Genera un **borrador de microciclo** (semana de 7 días) a partir de esas
  referencias y un porcentaje por categoría, editable fila por fila.
- Registra **sesiones realizadas**: duración, RPE del deportista, minutos
  activos por categoría y observaciones de sueño/cansancio/dolor.
- Calcula la **carga de sesión** (duración × RPE) y la **composición** del
  microciclo, y genera **informes HTML/SVG** imprimibles o en PDF, además de
  exportación a **CSV**.
- Incluye una **calculadora adulta** opcional (Tanaka/Karvonen) y una prueba
  **ortostática** orientativa, ambas separadas de los planes de entrenamiento.
- Guarda todo en una base **SQLite local** con auditoría, anulación de
  registros erróneos (no se borran) y **copia/restauración** de seguridad.
- No requiere internet para funcionar, no envía datos a ningún servidor y no
  implementa autenticación ni cifrado adicional al del equipo donde se ejecuta.

## Requisitos

- **Python 3.10 o superior**, instalado con Tcl/Tk y el lanzador `py` (incluido
  en el instalador oficial de Windows: https://www.python.org/downloads/).
- No se necesitan paquetes externos para ejecutar el código fuente: `app.py`,
  `core.py` e `historical.py` usan solo la biblioteca estándar (`tkinter`,
  `sqlite3`, `csv`, `html`, `json`, `math`, `os`, `pathlib`, `datetime`).
- `pyinstaller` (ver [requirements.txt](requirements.txt)) solo se necesita
  para **compilar** el ejecutable Windows, no para usar la aplicación desde
  el código fuente.

## Puesta en marcha rápida

1. Descargue o clone el repositorio completo; mantenga juntos `app.py`,
   `core.py` e `historical.py` (están en la misma carpeta).
2. Compruebe que Tcl/Tk funciona abriendo una terminal en la carpeta del
   proyecto y ejecutando:

   ```bat
   py -m tkinter
   ```

   Debe aparecer una pequeña ventana de prueba. Si falla, reinstale Python
   marcando la opción de Tcl/Tk.
3. Inicie la aplicación con cualquiera de estas opciones:

   ```bat
   py app.py
   ```

   o haciendo doble clic en [`iniciar_windows.cmd`](iniciar_windows.cmd), que
   ejecuta el mismo comando y muestra un mensaje de ayuda si Python no está
   disponible.
4. La primera vez que se crea un deportista, la aplicación crea también la
   base de datos SQLite en `%LOCALAPPDATA%\TKD_Entrenador\` (ver
   [Dónde quedan los datos](#dónde-quedan-los-datos-y-cómo-respaldarlos)).

Si prefiere un `.exe` que no requiera Python instalado, vea
[Crear el ejecutable para Windows](#crear-el-ejecutable-para-windows).

## Guía de uso paso a paso

La ventana principal muestra, arriba, el selector de deportista y los botones
**Nuevo** / **Editar ficha**; debajo, seis pestañas que corresponden al flujo
de trabajo habitual del entrenador.

### 1. Deportista

Pulse **Nuevo** para crear la ficha: nombre, fecha de nacimiento, sexo y
experiencia. La edad se calcula sola a partir de la fecha de nacimiento. Para
menores de edad, registre brevemente la autorización y el acudiente según el
procedimiento de su organización; evite anotar diagnósticos innecesarios en
observaciones. Use **Editar ficha** para corregir estos datos más adelante.
Seleccione siempre el deportista correcto en el desplegable antes de trabajar
en las demás pestañas: cada una filtra por el deportista activo.

### 2. Mediciones

Pestaña **Mediciones**: registre peso, talla, FC basal, FC de reposo, FC
durante el esfuerzo o FC de recuperación, y presión arterial. Cada registro
incluye fecha, valor, método/dispositivo y observaciones; puede introducir
varios registros por día. Los registros anteriores nunca se sobreescriben.

Definiciones operativas usadas por la app:

| Tipo | Momento de la medición |
|---|---|
| Basal | Al despertar, antes de levantarse, en condiciones estables |
| Reposo | Tras un periodo tranquilo, indicando postura y condiciones |
| Durante | Lectura obtenida efectivamente durante el esfuerzo |
| Recuperación | Lectura posterior al esfuerzo, con segundos transcurridos |

Con un pulsioxímetro, lea **PR/bpm** (pulso); **SpO2/%** es saturación, no
frecuencia cardíaca. Para un conteo manual de latidos:

`FC (lpm) = latidos contados × 60 / segundos de observación`

Con 6 segundos de conteo, un latido de diferencia equivale a 10 lpm. Esta
pestaña incluye también la **calculadora ortostática** (FC acostado vs. FC de
pie; una diferencia mayor a 15 lpm es un criterio orientativo, no diagnóstico).

### 3. Referencias

Cada deportista tiene su propio catálogo de referencias semanales por
ejercicio y categoría (General/Especial/Competitiva). El 100 % es una
referencia de planificación elegida por el entrenador, **no** una prueba al
máximo ni una meta obligatoria. El botón de referencias históricas (solo para
adultos, con confirmación) carga estos valores de partida sin reemplazar los
existentes:

| Ejercicio | Referencia histórica semanal |
|---|---:|
| Cross | 90 minutos |
| Escalera | 70 minutos |
| Patadas | 200 repeticiones |
| Combate condicionado | 16 asaltos × 3 min = 48 min activos |
| Combate libre | 12 asaltos × 3 min = 36 min activos |

Para ejercicios en repeticiones (patadas, etc.) indique además los minutos
activos previstos para el 100 %: la app no puede deducir el tiempo a partir
de la cantidad. Puede añadir también saco, canilleras, movilidad, juegos,
técnica, fuerza o desplazamientos con la unidad que corresponda.

### 4. Microciclo

Cree un borrador indicando el lunes de inicio, la fase, los días de trabajo y
el porcentaje de cada referencia. La semana tiene 7 días reales y puede
cruzar meses o años. Ejemplo puramente aritmético (no una recomendación de
carga): referencia de cross 90 min al 50 % → 45 min semanales.

El primer reparto entre los días elegidos es uniforme y es solo un punto de
partida: edite cada fila para cambiar día, cantidad, tiempo, pausa, RPE
objetivo opcional e indicaciones (series, técnica, ritmo, descansos), o
retire una actividad (queda en la auditoría, no se borra). Al pulsar
**Revisar/aprobar** con el nombre del entrenador, el plan queda congelado:
para cambiarlo se genera un nuevo plan y el anterior se conserva.

### 5. Sesiones

Registre lo realmente ejecutado: fecha, duración total, RPE del deportista
(escala 0–10, explicada primero con anclajes apropiados para la edad), minutos
activos por categoría y observaciones de sueño, cansancio, dolor o
participación. Los minutos activos no pueden superar la duración total. Puede
vincular la sesión a un plan revisado de la misma semana para comparar lo
planificado contra lo realizado en el informe.

`carga de sesión (UA) = duración total (min) × RPE de sesión`

Ejemplo: 60 min × 5 = 300 unidades arbitrarias. No son calorías ni un umbral
clínico.

### 6. Progreso

Genera el **informe individual** (mediciones y sesiones) o el **informe del
plan** (actividades, composición General/Especial/Competitiva y gráfico de
minutos activos planificados frente a registrados), y grafica la carga de las
últimas 12 semanas con registros. El informe HTML se abre en el navegador sin
necesidad de internet; use **Ctrl+P → Guardar como PDF** para imprimir o
entregar. El botón de exportación en CSV incluye las sesiones no anuladas.
Conserve los informes como información personal, ya que contienen datos del
deportista.

### 7. Ayuda y copias

Incluye la guía rápida dentro de la propia aplicación, el botón **Ver curvas
históricas** (datos de `historical.py`, no aplicables a la FC) y los botones
de **copia de seguridad** y **restauración** descritos a continuación.

## Dónde quedan los datos y cómo respaldarlos

En Windows, la base de datos vive en:

```text
%LOCALAPPDATA%\TKD_Entrenador\entrenamiento.sqlite3
```

La propia interfaz (pestaña **Ayuda y copias**) muestra la ruta exacta. Use el
botón de copia de seguridad periódicamente y conserve otra copia en un medio
distinto. La restauración valida la integridad y la estructura del archivo
elegido y crea automáticamente una copia de la base actual antes de
reemplazarla. Esta versión **no cifra** la base de datos ni implementa
autenticación: la protección depende de la cuenta y el disco del sistema
operativo. No hay sincronización en la nube ni transmisión de datos. En un
equipo compartido, aplique controles adicionales antes de introducir
información identificable de menores.

Los registros erróneos no se eliminan: se **anulan** con un motivo y quedan
excluidos de los informes mientras permanecen en la auditoría local.

## Crear el ejecutable para Windows

Si el entrenador no tiene Python instalado, genere un `.exe` portable en un
equipo Windows ejecutando:

```bat
crear_exe_windows.cmd
```

Este script crea un entorno virtual `.venv_build`, instala PyInstaller,
ejecuta las pruebas automatizadas y produce:

```text
dist\TKD_Entrenador.exe
```

La preparación inicial necesita internet (para instalar PyInstaller); el
programa compilado funciona sin conexión. El comando equivalente, dentro de un
entorno ya preparado, es:

```bat
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TKD_Entrenador app.py
```

El `.exe` es portable (no un instalador con asistente): puede copiarse a una
carpeta del portátil del entrenador y crear un acceso directo. Las
actualizaciones del ejecutable conservan la base de datos, porque esta se
guarda fuera del programa (ver sección anterior). PyInstaller empaqueta Python
y sus dependencias; no convierte la aplicación en un dispositivo médico ni
valida la metodología de entrenamiento.

## Pruebas automatizadas

```bat
py -m unittest -v test_core.py
```

Las pruebas cubren cálculo de edad, conteo manual de pulso, Karvonen/Tanaka,
rechazo de la calculadora adulta en menores, validación de entradas,
conservación de totales al redondear, mezcla de unidades, referencias
históricas, planes congelados, aislamiento entre deportistas, carga de
sesión, validación de recuperación, copia/restauración y escape de informes.

## Organización del código

| Archivo | Función |
|---|---|
| [`app.py`](app.py) | Interfaz Tkinter/ttk: formularios, tablas, ayuda y exportación. |
| [`core.py`](core.py) | Validación, cálculos, SQLite, auditoría, copias e informes HTML/SVG. |
| [`historical.py`](historical.py) | Valores del Excel original del convenio, sin dependencia de Excel. |
| [`test_core.py`](test_core.py) | Pruebas unitarias y de integración con bases temporales. |
| [`iniciar_windows.cmd`](iniciar_windows.cmd) | Inicio desde el código fuente. |
| [`crear_exe_windows.cmd`](crear_exe_windows.cmd) | Preparación del ejecutable en Windows. |
| [`MANUAL.html`](MANUAL.html) | Manual detallado para abrir y leer en el navegador. |
| [`EJEMPLO_INFORME.html`](EJEMPLO_INFORME.html) | Informe de ejemplo con datos ficticios. |
| [`LEAME.md`](LEAME.md) | Manual extendido en español (fuentes consultadas, detalle técnico, prueba piloto). |

Para la explicación más extensa de cada cálculo, de las fuentes científicas
consultadas y del protocolo de prueba piloto, consulte [LEAME.md](LEAME.md) y
[MANUAL.html](MANUAL.html).

## Límites y fundamento del modelo

- La calculadora adulta usa Tanaka (`FCmáx = 208 − 0,7 × edad`) y Karvonen
  (`FCobjetivo = FCreposo + intensidad/100 × (FCmáx − FCreposo)`); procede de
  estudios en adultos sanos y **no se aplica a menores**. Es opcional, no se
  guarda como medición y no alimenta los planes.
- Las referencias semanales "al 100 %" son decisiones de planificación del
  entrenador, no pruebas máximas ni límites seguros.
- La app no inventa alternancia de días fuertes/suaves, incrementos
  semanales automáticos, ni aplica reducciones porcentuales por edad.
- El RPE y la carga de sesión son herramientas de registro, no umbrales
  clínicos ni predicción de lesiones.
- La planificación con menores requiere valoración apropiada del contexto del
  deportista; ante síntomas relevantes, consulte ciencias del deporte o
  medicina deportiva. El programa no sustituye esa evaluación.

## Licencia

Distribuido bajo licencia [MIT](LICENSE).
