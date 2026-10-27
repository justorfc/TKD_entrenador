# Compilación y mantenimiento de la versión Android

Esta guía documenta cómo generar el APK/AAB de TKD Entrenador a partir del
mismo repositorio que la versión Windows, y cómo mantenerlo. La interfaz
Android vive en [`main.py`](main.py) y el paquete [`mobile/`](mobile); ambos
reutilizan [`core.py`](core.py) y [`historical.py`](historical.py) sin
duplicar ninguna fórmula ni regla de negocio.

> **Estado de esta guía (26-10-2026):** el código de la interfaz Android se
> probó funcionalmente en un PC con Kivy 2.3.1 sobre Python 3.12 (navegación
> completa entre pantallas, alta de deportistas, mediciones con coma
> decimal, configuración del umbral de seguimiento postural, referencias,
> microciclo con revisión, sesión, y copia de seguridad/restauración, todo
> mediante los mismos widgets que usará la app). **No se generó ni se probó
> un APK real** porque este entorno de trabajo es Windows sin WSL2 instalado
> (sin Subsistema de Windows para Linux, sin Android SDK/NDK). La sección
> [Bloqueo exacto en este entorno](#bloqueo-exacto-en-este-entorno) detalla
> qué falta y los comandos exactos que quedan pendientes de ejecutar.

## Requisitos (comprobados el 26-10-2026)

| Herramienta                       | Versión usada en esta guía                                                                  | Notas                                                       |
| --------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Kivy                              | 2.3.1 (última estable en PyPI)                                                               | [https://kivy.org/doc/stable/](https://kivy.org/doc/stable/) |
| Buildozer                         | 1.6.0 (última estable en PyPI)                                                               | Solo Linux/macOS; en Windows se usa vía WSL2               |
| python-for-android                | gestionado por Buildozer                                                                      | No fijar versión manualmente salvo que falle el build      |
| Python (máquina de compilación) | 3.11–3.12 recomendado                                                                        | Kivy 2.3.1 no publica ruedas para Python 3.14 (ver nota)    |
| Java JDK                          | el que instale Buildozer (OpenJDK 17 vía `sdkmanager`)                                     | Buildozer lo gestiona junto con el Android SDK              |
| Android SDK / NDK                 | gestionados automáticamente por Buildozer (NDK 28c, API 36, minAPI 24 en `buildozer.spec`) | Se descargan la primera vez, varios GB                      |

> **Nota sobre Python 3.14:** al preparar este encargo, el único Python
> disponible en el PC de desarrollo era 3.14, para el que Kivy 2.3.1 no
> publica paquetes binarios (`pip install kivy` falla intentando compilar
> desde la fuente). Para desarrollar/probar la interfaz en un PC, use Python
> 3.9–3.13. En Linux/WSL2, Buildozer administra su propio Python para el
> build de Android, por lo que esto solo afecta a las pruebas de la interfaz
> Kivy *en escritorio*, no a la compilación del APK en sí.



## 1. Preparar el entorno de compilación Linux (Fedora nativo o WSL2 en Windows)

Buildozer **no compila en Windows nativo**: funciona en Linux o macOS. Hay dos
rutas equivalentes; elija una:

- **Opción A — Fedora (Linux nativo, recomendado si ya tiene o puede instalar
  Fedora):** evita la capa de virtualización de WSL2 y los problemas de
  rutas/permisos al compilar; es el entorno más simple y más parecido a lo
  que usan la mayoría de guías de Buildozer.
- **Opción B — WSL2 sobre Windows:** útil si no quiere salir de Windows, pero
  requiere instalar/mantener el Subsistema de Windows para Linux y trabajar
  siempre dentro del sistema de archivos de Linux (ver advertencia abajo).

### Opción A: Fedora (Linux nativo)

```bash
sudo dnf install -y git zip unzip java-17-openjdk-devel python3-pip \
    gcc gcc-c++ make autoconf automake libtool pkgconf-pkg-config \
    libffi-devel openssl-devel ncurses-compat-libs zlib-devel cmake patch which
```

## 2. Compilar un APK de depuración

```bash
cd ~/tkd_entrenador
source .venv_build_android/bin/activate
buildozer android debug
```

La primera ejecución descarga el Android SDK/NDK y compila python-for-android
(puede tardar bastante y requiere varios GB de descarga y espacio en disco).
El resultado queda en `bin/tkdentrenador-0.1.0-arm64-v8a_armeabi-v7a-debug.apk`
(el nombre exacto depende de la versión y arquitecturas de `buildozer.spec`).

## 3. Instalar y depurar con ADB

Con el dispositivo conectado por USB y la depuración USB activada:

```bash
adb devices                       # confirma que el dispositivo aparece
buildozer android debug deploy run   # compila, instala y lanza la app
adb logcat | grep python           # ver la salida de Python/Kivy en vivo
```

Para instalar un APK ya compilado sin recompilar:

```bash
adb install -r bin/tkdentrenador-*-debug.apk
```

## 4. Firma y actualizaciones (release)

- `buildozer android debug` genera un APK firmado con una **clave de
  depuración genérica**: sirve para instalar y probar, **no** para distribuir
  ni para actualizar una instalación existente con otra clave.
- Para una versión de distribución: `buildozer android release` genera un
  **AAB** (ver `android.release_artifact = aab` en `buildozer.spec`), que debe
  firmarse con una clave propia (`keytool`/`jarsigner` o Play App Signing).
- **Conserve esa clave de firma de forma segura y por separado del
  repositorio.** `.gitignore` ya excluye `*.keystore` y `*.jks`: nunca la
  suba a Git. Si se pierde, no podrá publicar actualizaciones de la misma
  aplicación: tendría que publicarla como una app nueva y los usuarios
  perderían la continuidad de actualización (no los datos locales, que son
  independientes de la firma, pero sí la posibilidad de actualizar sin
  desinstalar).
- Para actualizar sin perder datos: instale el APK/AAB nuevo **sobre** el
  anterior (`adb install -r` o la propia tienda), sin desinstalar. Los datos
  SQLite están en el directorio privado de la app (`App.user_data_dir`) y
  sobreviven a una actualización in-place, pero se **borran si se
  desinstala** (ver Ajustes → copia de seguridad en la app).

## 5. Compilar desde macOS

Buildozer funciona de forma nativa en macOS (no necesita WSL2). Los pasos son
equivalentes a la sección 1 (instalar dependencias de compilación con
Homebrew en vez de `apt`) y 2.

## Bloqueo exacto en este entorno

Este encargo se ejecutó en un PC Windows sin WSL2 instalado
(`wsl --list --verbose` devuelve "El Subsistema de Windows para Linux no está
instalado") y sin acceso a un Android SDK/NDK ni a un dispositivo/emulador
Android. Por eso:

- **No se ejecutó** `buildozer android debug` ni ningún paso de la sección 1
  en adelante: quedan pendientes tal cual están documentados arriba.
- **No existe ningún APK/AAB generado** por este trabajo. No se afirma ni se
  simula la existencia de uno.
- Lo que **sí se hizo y se puede repetir** para verificar el estado del
  código antes de compilar: crear un entorno con Python 3.12 y Kivy 2.3.1 en
  Windows (ver abajo) y ejecutar `python main.py`, navegar por las ocho
  pantallas, crear un deportista de prueba, registrar una medición con coma
  decimal, configurar el umbral de seguimiento postural, crear una
  referencia y un microciclo, revisarlo, registrar una sesión, y hacer una
  copia de seguridad y restaurarla. Todo ello se verificó con pruebas
  automatizadas de UI (no interactivas) durante este trabajo.
- Lo que **no se pudo probar** por no tener Linux/WSL2 ni un dispositivo:
  - El proceso real de `buildozer android debug/release` (puede requerir
    ajustes menores en `buildozer.spec`, p. ej. permisos adicionales que
    pida la receta de `plyer` o `pyjnius` al compilar).
  - El selector de archivos SAF real en Android (`plyer.filechooser`) y la
    copia de flujos `content://` con `pyjnius`/`ContentResolver`
    (`mobile/paths.py`): el código sigue las APIs documentadas de Android y
    Kivy, pero no se ha ejercitado en un dispositivo real.
  - `plyer.share` para abrir/compartir el informe HTML y el CSV exportado.
  - El comportamiento exacto del botón Atrás físico/gesto de Android, el
    teclado numérico nativo y el guardado de borradores ante un cierre
    forzado real del proceso por el sistema operativo (se implementó según
    la documentación de ciclo de vida de `kivy.app.App`, pero el
    comportamiento final depende del fabricante/versión de Android).

### Reproducir las pruebas de escritorio de esta guía

```powershell
# Requiere un Python 3.9-3.13 (Kivy 2.3.1 no tiene ruedas para 3.14+ a fecha de hoy).
uv python install 3.12
uv venv --python 3.12 .venv_kivy
.venv_kivy\Scripts\python -m ensurepip --upgrade
.venv_kivy\Scripts\python -m pip install -r requirements-mobile.txt
.venv_kivy\Scripts\python main.py
```

## Estructura de archivos relevante para Android

```text
main.py              Punto de entrada Kivy (lo usa Buildozer como main.py)
mobile/
  __init__.py
  paths.py           Directorio de datos privado + SAF (content://) + compartir
  widgets.py          Formularios táctiles, borradores, confirmaciones
  screens.py          Las ocho pantallas (Inicio, Deportistas, Ficha, ...)
buildozer.spec        Configuración de empaquetado Android
requirements-mobile.txt  Dependencias SOLO para probar la interfaz en un PC
core.py, historical.py   Compartidos con la versión Windows, sin cambios de UI
```

## Limitaciones conocidas (pendientes, no implementadas)

- No hay Bluetooth ni lectura automática de sensores (tampoco la tenía la
  versión Windows): las mediciones se introducen manualmente, como pide el
  encargo.
- No hay cifrado de la base SQLite ni cuentas de usuario: la protección real
  es la del bloqueo del propio teléfono. Un PIN visual dentro de la app (no
  implementado) no equivaldría a cifrado; si se añadiera en el futuro, debe
  documentarse igual de explícitamente.
- El icono/presplash de la app no se ha diseñado (usa los valores por
  defecto de Buildozer); añadir `icon.filename`/`presplash.filename` en
  `buildozer.spec` cuando haya arte disponible.
- `android.permissions` se dejó vacío porque SAF no debería necesitar
  permisos de almacenamiento amplios en API 24+; verifique en el primer
  build si alguna receta (`plyer`, `pyjnius`) añade permisos automáticamente
  y ajuste la documentación si es necesario.
