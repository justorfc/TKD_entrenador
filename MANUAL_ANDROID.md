# Manual breve para entrenadores — TKD Entrenador (Android)

Guía rápida de uso en el teléfono. No sustituye valoración médica o deportiva
profesional; es una herramienta de registro y organización.

## Primeros pasos

1. Instale el APK que le entregue la persona responsable técnica (ver
   `BUILD_ANDROID.md`). No necesita conexión a internet para usarla.
2. Abra la app. En **Inicio** verá accesos directos a las secciones
   principales y un resumen del deportista seleccionado.
3. Vaya a **Deportistas** y pulse **Nuevo deportista** para crear la primera
   ficha (nombre, nacimiento, sexo, experiencia y, si es menor, el acudiente
   que autoriza el registro).
4. Toque el nombre de un deportista en la lista para seleccionarlo: su
   nombre y edad quedan fijos en la parte superior de cada pantalla mientras
   trabaja, para evitar registrar datos de la persona equivocada.

## Mediciones

- **Nueva medición**: fecha, tipo (peso, talla, pulso en sus variantes,
  presión arterial sistólica/diastólica, etc.), valor, método/dispositivo y
  postura. Puede escribir el valor con coma o con punto decimal.
- **Convertir conteo manual de pulso**: si cuenta latidos durante unos
  segundos, esta calculadora los convierte a latidos/min; no sustituye medir
  más tiempo si puede hacerlo.
- **Prueba ortostática (acostado/de pie)**: registra la diferencia entre la
  frecuencia cardíaca acostado (tras reposo) y de pie (inmediata). La
  diferencia **se calcula siempre**, pero la app solo la marca si usted ha
  activado un umbral personal de seguimiento para ese deportista (ver
  siguiente punto). Marcarla **no es un diagnóstico**: si ocurre, revise las
  condiciones de la medición y el contexto del deportista, no decida solo
  con este dato.
- **Umbral de seguimiento postural**: opcional, deportista por deportista.
  Si lo deja vacío, la prueba ortostática nunca se marca. El valor histórico
  de referencia usado antes era 15 lpm, pero es usted quien decide si lo usa
  y con qué valor.
- Registre también la presión arterial como una medición más (sistólica y
  diastólica por separado), nunca con un dispositivo de pulso en el dedo que
  no esté diseñado para medir presión.

## Referencias y planificación semanal

- **Añadir referencia semanal**: defina, por ejercicio y categoría (general,
  especial, competitiva), la cantidad de referencia al 100 % para una
  semana. El 100 % es una referencia de planificación suya, no un máximo
  obligatorio ni un valor universal para todos los deportistas.
- **Generar borrador de microciclo**: elige el lunes de inicio, la fase, los
  días de la semana y el porcentaje de cada categoría a aplicar sobre las
  referencias. El borrador reparte el trabajo por igual entre los días
  elegidos: ajuste cantidades, pausas y notas de cada actividad antes de
  revisarlo (en esta primera versión móvil, edite detalles finos desde la
  versión Windows si necesita mover actividades día a día; la versión móvil
  está pensada para crear, consultar y revisar microciclos en el gimnasio).
- **Revisar último borrador**: congela el plan con su nombre como
  responsable. Un plan revisado no puede editarse: genere otro borrador si
  necesita cambiarlo, y el historial de versiones anteriores se conserva.

## Sesiones

- **Registrar sesión realizada**: duración total, RPE del deportista (0 a
  10), minutos activos por categoría, trabajo realmente realizado, y
  observaciones de sueño/cansancio/dolor. La carga de sesión se calcula como
  duración × RPE. Puede vincular la sesión a un plan ya revisado.
- Si se equivoca al registrar, **no borre** el dato: anúlelo (desde la
  versión Windows, donde está disponible el botón de anulación con motivo) y
  registre el correcto. Así queda constancia en la auditoría.

## Progreso e informes

- Vea un resumen de sesiones y carga acumulada.
- **Generar y compartir informe (HTML)** y **Exportar y compartir sesiones
  (CSV)** usan el mecanismo de "Compartir" de Android para enviar el archivo
  a otra app (correo, almacenamiento, impresora, etc.).

## Ajustes y copias de seguridad

- Muestra dónde vive la base de datos (una carpeta privada de la app) y
  recuerda que **no hay cifrado ni cuentas**: la protección real es el
  bloqueo de pantalla de su teléfono.
- **Crear copia de seguridad**: genera y verifica una copia, y le deja
  elegir el destino (por ejemplo una carpeta de Google Drive sincronizada,
  una tarjeta SD, etc.) mediante el selector del propio Android.
- **Restaurar copia de seguridad**: reemplaza los datos activos por los de
  la copia elegida. Antes de nada, la app guarda automáticamente una copia
  de lo que había activo, y pide confirmación explícita.
- **Conserve siempre una copia fuera del teléfono antes de desinstalar la
  app o cambiar de equipo**: los datos privados de la app se borran al
  desinstalar.
- Actualizar la app (instalar una versión nueva del APK/AAB sin
  desinstalar la anterior) conserva los datos.

## Qué NO hace esta app

- No diagnostica, no clasifica aptitud ni sustituye valoración clínica.
- No calcula objetivos cardíacos automáticos para menores de edad.
- No aplica reducciones automáticas de carga por edad.
- No sincroniza entre dispositivos ni envía datos a ningún servidor: todo
  queda en el teléfono salvo que usted mismo exporte o comparta un archivo.
- No se conecta a sensores Bluetooth: todas las mediciones se introducen a
  mano.
