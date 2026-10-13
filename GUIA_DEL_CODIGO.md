# Guía de lectura del código

> Documentación no oficial para el equipo de trabajo. Está escrita para recorrer el proyecto con calma; no hace falta conocer Flask ni SQLAlchemy de antemano.

Si quieres arrancar la aplicación, usa primero el [README oficial](README.md). Esta guía explica qué hace cada parte y cómo se conectan. Puedes leerla en este orden: flujo general, carpeta `app/`, datos, prioridad y rutas.

## 1. La idea del programa

El sistema guarda equipos biomédicos y los reportes de sus fallas. Tiene dos trabajos cotidianos:

1. En la estación, una persona enfoca el marcador pegado al equipo. La cámara del navegador toma una foto. Python la analiza y busca el ID del marcador.
2. El ingeniero usa el tablero para recibir el reporte, revisar la falla, reparar el equipo y documentar su liberación.

Una forma sencilla de imaginarlo: `routes.py` recibe las solicitudes web, `services.py` aplica las reglas del negocio, `models.py` define los datos y la base de datos conserva lo que no queremos perder al cerrar la aplicación.

```text
Página del navegador
       │ formulario, botón o foto
       ▼
app/routes.py  ── valida la solicitud y el acceso
       │
       ├── app/vision.py    procesa o genera el marcador
       ├── app/services.py  aplica reglas y guarda cambios
       └── app/models.py    representa los datos de la base
```

## 2. Recorrido de carpetas y archivos

### Carpeta `app/`

| Archivo | ¿Para qué sirve? | ¿Qué conviene buscar ahí? |
| --- | --- | --- |
| `__init__.py` | Prepara Flask en `create_app()`, conecta extensiones y registra las rutas. También añade el comando `flask --app run.py seed`. | Cómo se crea y configura la aplicación. |
| `config.py` | Lee configuración desde variables de entorno, como la conexión a la base de datos y la cuenta inicial. | Valores por defecto para desarrollo y nombres de variables de entorno. |
| `extensions.py` | Crea una sola instancia compartida de SQLAlchemy, Flask-Migrate y CSRFProtect. | Integraciones que usan los demás módulos. |
| `models.py` | Define las tablas y sus relaciones con clases Python. | Columnas, claves primarias y relaciones. |
| `routes.py` | Conecta URL y método HTTP con funciones de la aplicación. Verifica sesión, recibe formularios, llama servicios y prepara páginas o respuestas JSON. | Qué ocurre al abrir una URL o enviar un formulario. |
| `services.py` | Contiene las reglas centrales: prioridad, respaldos, reincidencias, registro de equipo, etapas de trabajo e historial. | Por qué una acción es válida y qué se guarda. |
| `vision.py` | Contiene OpenCV para leer una captura, detectar ArUco y generar el PNG de un ID. | Cómo se reconoce o fabrica el marcador. |
| `templates/` | Páginas HTML Jinja2. Los valores entre `{{ }}` vienen de Python; `{% %}` permite condiciones y recorridos. | Lo que ve el usuario en la web. |
| `static/css/styles.css` | Apariencia de las páginas: colores, tarjetas, columnas y badges. | Cambios visuales. |
| `static/js/camera.js` | Pide acceso a la cámara, muestra vista previa, toma una imagen fija y llama a `/api/identify`. | Interacción con cámara desde el navegador. |

#### Plantillas de `app/templates/`

- `base.html`: estructura compartida: idioma, título, CSS, mensajes y contenedor principal.
- `station.html`: pantalla de reporte para el personal.
- `engineer_login.html`: formulario de inicio de sesión.
- `engineer.html`: tablero con una bandeja por estado y búsqueda del historial por serial.
- `report_detail.html`: ficha de un reporte. Cambia sus controles según la etapa actual.
- `equipment_history.html`: lista de reportes y acontecimientos anteriores de un equipo, incluidos los cerrados.
- `registro.html`: formulario de equipo y visualización/descarga del marcador generado.

### Carpetas y archivos del proyecto

- `run.py`: crea la variable `app` que usan Flask CLI y Gunicorn.
- `requirements.txt`: bibliotecas Python necesarias, con versiones fijadas.
- `Dockerfile`: instrucciones para instalar dependencias, copiar el proyecto y arrancar Flask CLI/Gunicorn.
- `compose.yaml`: declara los contenedores `app` y `db`, sus redes, variables, puerto y volumen.
- `.env.example`: ejemplo de configuración local. Se copia a `.env`; no debe ponerse allí una contraseña productiva.
- `.gitignore`: evita agregar al control de versiones archivos locales como `.env`.
- `.dockerignore`: evita copiar archivos de desarrollo, pruebas y marcadores generados dentro del contexto de imagen.
- `migrations/`: versiones del esquema SQL. Se usan para añadir columnas o tablas a una base existente sin borrarla.
- `scripts/generate_markers.py`: crea los marcadores imprimibles de demostración 42, 43 y 44.
- `tests/`: pruebas automáticas de prioridad, visión y flujo web.
- `markers/`: carpeta generada al ejecutar el script de marcadores; sus PNG se pueden imprimir.
- `instance/`: ubicación local habitual de SQLite cuando no se configura PostgreSQL.

## 3. Las bibliotecas, explicado simple

- **Flask:** recibe solicitudes HTTP y devuelve páginas o JSON.
- **Flask-SQLAlchemy / SQLAlchemy:** convierten clases y consultas Python en operaciones de base de datos.
- **Flask-Migrate / Alembic:** actualizan el esquema de PostgreSQL/SQLite de manera versionada.
- **Flask-WTF:** comprueba el token CSRF de los formularios, para rechazar envíos web falsificados.
- **Werkzeug:** verifica contraseñas con el hash guardado y lo crea para la cuenta inicial.
- **OpenCV contrib headless:** ofrece `cv2.aruco` para detectar y dibujar marcadores; “headless” significa que no necesita abrir una ventana gráfica en el servidor.
- **NumPy:** convierte bytes de imagen en arreglos numéricos que OpenCV puede leer.
- **psycopg:** permite que Python hable con PostgreSQL.
- **Gunicorn:** atiende solicitudes HTTP al desplegar en Docker.
- **pytest:** ejecuta las pruebas automáticas.
- **Jinja2:** motor de plantillas que incorpora datos Python al HTML.
- **Bootstrap:** estilos y componentes visuales de las páginas.

## 4. Qué significan los nombres más comunes

En Python y en la base se mezclan nombres en español e inglés. Son nombres, no palabras especiales del lenguaje.

| Nombre | Significado en este proyecto |
| --- | --- |
| `app` | La aplicación Flask completa. |
| `db` | Extensión compartida para hablar con la base de datos. |
| `bp` | “Blueprint”: grupo de rutas registrado dentro de Flask. |
| `request` | Solicitud que acaba de llegar: URL, formulario, archivo o JSON. |
| `session` | Datos de la sesión del navegador; aquí se guarda el ID del usuario autenticado. |
| `user` / `current_user()` | Ingeniero con sesión válida. |
| `equipment` / `equipo` | Objeto de la clase `Equipo`, leído desde la base de datos. |
| `report` / `reporte` | Objeto de la clase `ReporteFalla`. |
| `report_id` | ID numérico de un reporte incluido en una URL. |
| `equipment_id` / `equipo_id` | ID numérico de un equipo en la base de datos. |
| `aruco_id` / `marker_id` | Número impreso en el marcador; no es lo mismo que `equipo.id`, la clave interna de la tabla. |
| `serial` | Identificador del fabricante capturado en el equipo; es único y sirve para consultar historial. |
| `data` | Campos recibidos en JSON o formulario, por ejemplo en el registro de fallas. |
| `reports` | Lista de reportes leídos de la base de datos. |
| `lanes` | Diccionario que separa los reportes abiertos por etapa para el tablero. |
| `counts` | Cantidad de reportes por etapa, consultada a la base de datos. |
| `summary` | Conteo de prioridades abiertas (crítica, alta, media y baja). |
| `priority_case` | Expresión SQL que da orden de prioridad al ordenar la cola. |
| `score` / `puntaje_prioridad` | Suma numérica de los factores de prioridad. |
| `priority` / `prioridad` | Categoría obtenida: `critica`, `alta`, `media` o `baja`. |
| `backups` / `cantidad_respaldos_al_calcular` | Cantidad de equipos compatibles y disponibles al crear el reporte. |
| `recurrences` / `reincidencias_90d` | Reportes previos de ese equipo durante la ventana de 90 días. |
| `diagnostico` | Análisis técnico inicial guardado en la etapa de revisión. |
| `dias_estimados` | Plazo vigente de indisponibilidad; puede crecer si se registra una ampliación. |
| `dias_estimados_iniciales` | Primera estimación, conservada para comparación. |
| `reporte_final_mantenimiento` | Informe de la intervención antes de pasar a reparado. |
| `reporte_liberacion` | Conclusión de la revisión final antes de cerrar. |
| `observacion` | Texto que explica un acontecimiento, por ejemplo una ampliación o un retorno a mantenimiento. |
| `tipo_evento` | Nombre corto del acontecimiento guardado en el historial. |
| `detalles` | Valores extra del evento, guardados como JSON (por ejemplo, días antes y después de una ampliación). |

## 5. Los datos de la base de datos

Las clases de `models.py` representan tablas. `id` es la clave interna que identifica una fila. Las relaciones vinculan los reportes con los equipos y los eventos históricos con un reporte.

### `Equipo` (`equipos`)

| Campo | Qué guarda | Para qué se usa |
| --- | --- | --- |
| `id` | ID interno generado por la base | Relacionar reportes con el equipo. |
| `nombre` | Nombre legible | Mostrarlo en estación y tablero. |
| `tipo` | Clase de dispositivo | Descripción del equipo. Por sí solo no determina compatibilidad. |
| `serial` | Número de serie único | Identificar físicamente y buscar el historial. |
| `aruco_id` | Número único de 0 a 249 | Relacionar el patrón detectado con este equipo. |
| `grupo_respaldo` | Grupo compatible explícito u `NULL` | Contar solo los equipos que realmente puedan respaldar este servicio. |
| `criticidad` | `soporte_vital`, `diagnostico_terapia` o `apoyo` | Aporta puntos a la prioridad. |
| `nivel_uso` | `alto`, `medio` o `bajo` | Aporta puntos a la prioridad. |
| `estado_operativo` | `operativo`, `fuera_servicio` o `mantenimiento` | Dice si el equipo está disponible ahora. Es distinto al estado del reporte. |

### `Usuario` (`usuarios`)

| Campo | Qué significa |
| --- | --- |
| `id` | Clave interna del ingeniero. |
| `nombre` | Nombre para mostrar en el historial. |
| `email` | Correo único para iniciar sesión. |
| `password_hash` | Resultado cifrado de una función de hash; no es la contraseña original. |
| `rol` | Permiso de la cuenta. El panel requiere `ingeniero`. |

### `ReporteFalla` (`reportes_falla`)

| Campo | Qué significa |
| --- | --- |
| `id` | Número del reporte. |
| `equipo_id` | ID del equipo afectado. |
| `reportado_por` | Nombre de quien informó la falla; no necesita usuario de sistema. |
| `descripcion` | Qué sucede según el reportante. |
| `impacto_operativo` | `detiene_servicio`, `degradado` o `sin_impacto`. |
| `puntaje_prioridad`, `prioridad` | Puntaje y etiqueta calculados al registrar, salvo que la compatibilidad esté pendiente. |
| `cantidad_respaldos_al_calcular` | Foto de los respaldos disponibles al calcular el puntaje. No se recalcula al cambiar el inventario. |
| `reincidencias_90d` | Cantidad histórica que se usó en el cálculo. |
| `validacion_respaldo_pendiente` | `True` si falta definir un grupo compatible y no se puede calcular aún. |
| `estado` | Etapa del caso: `reportado`, `en_revision`, `en_mantenimiento`, `reparado` o `cerrado`. |
| `diagnostico` | Diagnóstico inicial. |
| `dias_estimados` | Estimación vigente. |
| `dias_estimados_iniciales` | Valor inicial conservado para no perderlo con ampliaciones. |
| `reporte_final_mantenimiento` | Texto del último informe de mantenimiento; cada entrega también se conserva en el historial. |
| `reporte_liberacion` | Informe escrito para cerrar el caso. |
| `mantenimiento_started_at` | Momento en que comenzó el primer mantenimiento. |
| `respaldo_confirmado`, `verificacion_funcional` | Campos heredados del flujo original; las transiciones actuales ya no dependen de estas casillas. |
| `created_at`, `updated_at` | Fechas de creación y última modificación del reporte. |

### `HistorialReporte` (`historial_reportes`)

Cada fila es un acontecimiento, no una copia completa del reporte. Guarda `reporte_id`, `usuario_id` (puede ser vacío para un evento de estación), `estado_anterior`, `estado_nuevo`, `tipo_evento`, `observacion`, `detalles` y `created_at`. Por ejemplo, para ampliar el plazo `detalles` lleva días anteriores, adicionales y nuevos.

## 6. Cómo se calcula la prioridad

La función única está en `services.py` y se llama `calcular_prioridad()`. Suma:

```text
puntaje = impacto + criticidad clínica + respaldo + uso + reincidencias
```

### Puntos que se agregan

| Dato | Opción | Puntos |
| --- | --- | ---: |
| `impacto_operativo` | `detiene_servicio` | 35 |
| | `degradado` | 20 |
| | `sin_impacto` | 5 |
| `criticidad` del equipo | `soporte_vital` | 25 |
| | `diagnostico_terapia` | 15 |
| | `apoyo` | 8 |
| Respaldos | 0 | 15 |
| | 1 | 6 |
| | 2 o más | 0 |
| `nivel_uso` | `alto` | 10 |
| | `medio` | 5 |
| | `bajo` | 2 |
| Reportes previos en 90 días | 0 | 0 |
| | 1 o 2 | 5 |
| | 3 o más | 15 |

Ejemplo: impacto degradado (20) + diagnóstico/terapia (15) + un respaldo (6) + uso alto (10) + dos reportes previos (5) = **56 puntos, prioridad alta**.

Después de sumar, el programa asigna `critica` desde 70, `alta` desde 50, `media` desde 30 y `baja` por debajo de 30. Hay una regla especial: `detiene_servicio` con cero respaldos da prioridad `critica`, aunque el puntaje total sea menor de 70. La regla no suma ni inventa puntos.

### ¿Qué cuenta como respaldo?

`contar_respaldos()` busca equipos diferentes al equipo con falla que tengan el mismo `grupo_respaldo`, estén `operativo` y no tengan un reporte abierto. Se excluyen de ese conteo equipos con reportes en `reportado`, `en_revision`, `en_mantenimiento` o `reparado`. Si `grupo_respaldo` está vacío, la función devuelve `None` para indicar “desconocido”; no devuelve cero. `reincidencias()` cuenta reportes del mismo equipo creados en los 90 días previos, sin filtrar por el estado actual de esos reportes.

### ¿Qué significa criticidad?

Hay dos conceptos que se parecen por nombre:

- `criticidad`: característica del equipo que el ingeniero establece al registrarlo. Puede ser soporte vital, diagnóstico/terapia o apoyo, y añade 25, 15 u 8 puntos.
- `prioridad`: resultado final del reporte: crítica, alta, media o baja. Se calcula sumando todos los factores y aplicando los rangos y la regla de anulación.

No se calcula una “criticidad” a partir de la falla. La clasificación que cambia con la falla es `prioridad`.

## 7. Los estados y qué formulario se muestra

| Estado del reporte | Acción principal | Información necesaria |
| --- | --- | --- |
| `reportado` | Iniciar revisión | Ningún dato de revisión. |
| `en_revision` | Guardar diagnóstico y estimación; luego enviar a mantenimiento | Diagnóstico no vacío y días enteros mayores o iguales a cero. Cero días es válido. |
| `en_mantenimiento` | Ampliar días o registrar reporte final | Para ampliar: días adicionales positivos y observación. Para reparar: reporte final no vacío. |
| `reparado` | Registrar liberación o volver a mantenimiento | Para cerrar: reporte de liberación. Para volver: observación del motivo. |
| `cerrado` | Consultar historial | No aparece en las bandejas abiertas. Se puede ver desde historial del equipo. |

El estado operativo del equipo es otro dato. Puede estar `fuera_servicio` desde que se inicia revisión de una falla que detiene el servicio. Pasa a `mantenimiento` al iniciar mantenimiento y permanece así mientras el caso esté reparado pero pendiente de liberación. Solo vuelve a `operativo` al cerrar el reporte con el informe de liberación.

El tablero ordena los casos con validación de respaldo pendiente al principio; dentro del resto ordena por prioridad, puntaje más alto y fecha más antigua. La estimación de días no participa en el orden.

## 8. Rutas: cómo viajan los datos

Una ruta combina método HTTP y dirección. `GET` normalmente muestra información; `POST` normalmente envía un cambio.

### Personal que reporta una falla

1. `GET /station` entrega `station.html`.
2. `camera.js` pide la cámara con `getUserMedia()`. Al pulsar identificar, captura una imagen fija.
3. `POST /api/identify` recibe el archivo con el nombre de campo `image`. `vision.detectar_marcadores()` devuelve los IDs vistos; la ruta busca ese número en `Equipo.aruco_id`.
4. `POST /api/reports` recibe `equipo_id`, `reportado_por`, `descripcion` e `impacto_operativo`. El servicio calcula prioridad cuando puede y guarda el reporte y el evento inicial.

### Ingeniero

- `GET /engineer/login` muestra el formulario; `POST` busca el correo y compara la contraseña con `check_password_hash()`.
- `GET /engineer` pide los reportes abiertos, los ordena y prepara las cuatro `lanes` (bandejas). Los `counts` se consultan en la base. Cada tarjeta lleva a su detalle.
- `POST /engineer/reports/<id>/transition` recibe `nuevo_estado` y los textos de etapa: `observacion`, `reporte_final` o `reporte_liberacion`. `services.transition()` decide si el movimiento es válido y guarda estado, equipo e historial en una transacción.
- `POST /engineer/reports/<id>/review` recibe `diagnostico` y `dias_estimados`; actualiza esos datos y añade un evento `revision_guardada`.
- `POST /engineer/reports/<id>/extend-days` recibe `dias_adicionales` y `observacion`; suma los días sin recalcular prioridad y registra el antes/después.
- `GET /engineer/equipment/<id>/history` muestra el historial de todos los reportes de ese equipo.
- `GET /engineer/history?serial=...` busca un equipo por serial y redirige a su historial.
- `POST /engineer/logout` elimina los datos de sesión.

### Registro de equipos

`GET /registro` muestra el formulario (requiere ingeniero autenticado). `POST /registro` recibe `nombre`, `tipo`, `serial`, `grupo_respaldo`, `criticidad`, `nivel_uso` y `estado_operativo`; no recibe un ID ArUco elegido por la persona. `registrar_equipo()` calcula el siguiente ID consecutivo después del mayor ya usado (o `0` si no hay equipos), verifica que no esté ocupado y rechaza el registro si se superó el máximo `249`. La restricción `unique=True` de la base de datos brinda una protección adicional ante dos registros simultáneos. Después de guardar, la página muestra una imagen generada por `generar_marcador_png()` con ese ID y ofrece la descarga PNG. La imagen se crea en memoria, no se guarda como archivo del servidor.

### Salud del servicio

`GET /health` ejecuta una consulta sencilla (`SELECT 1`). Si la base responde, devuelve `{"status":"ok"}`; si falla, devuelve error HTTP 503.

## 9. ArUco con palabras simples

ArUco es un marcador cuadrado en blanco y negro que OpenCV puede reconocer y convertir en un número. Aquí el diccionario elegido es `DICT_6X6_250`: contiene hasta 250 IDs posibles.

En `vision.py` se inicializa una vez `_dictionary` y un `_detector`. `detectar_marcadores(image_bytes)`:

1. comprueba que los bytes parezcan JPEG o PNG;
2. `cv2.imdecode()` convierte los bytes en imagen;
3. `cv2.cvtColor()` la convierte a gris;
4. `ArucoDetector.detectMarkers()` busca IDs y esquinas;
5. devuelve una lista, por ejemplo `[{"id": 42, "corners": [...]}]`.

Si la lista está vacía, la estación avisa que no encontró el marcador. Si tiene varios resultados, pide otra captura. `generar_marcador_png(aruco_id)` hace la operación complementaria: dibuja el ID en el mismo diccionario, añade borde blanco y codifica la imagen como PNG.

## 10. Semilla, migraciones y pruebas

- **Semilla:** `seed_app()` crea el ingeniero inicial y equipos de demostración solo cuando faltan; se puede ejecutar más de una vez.
- **Migración:** los archivos dentro de `migrations/versions/` describen cómo evolucionaron las tablas. No editar una migración ya aplicada para hacer cambios nuevos; crear otra.
- **Pruebas:** `tests/test_priority.py` prueba puntajes; `tests/test_vision.py` crea imágenes y las procesa de verdad con OpenCV; `tests/test_workflow.py` usa Flask test client y base aislada para probar formularios, estados, historial y ArUco de `/registro`.

Comando habitual para las pruebas:

```sh
python -m pytest -q
```

## 11. Compartir el contenedor con otra persona

La aplicación ya está publicada en Docker Hub como `jorgepertuz23/biomed-mantenimiento:1.0.0`. Piensa en esa imagen como una caja que trae Python, Flask, las librerías y el código de la aplicación. La base de datos no viaja con los datos de quien la construyó: cada persona crea su propia base PostgreSQL vacía al ejecutar Compose.

Para usar la caja, el compañero necesita Docker Desktop, `compose.public.yaml` y `.env.example`. En una carpeta nueva copia `.env.example` con el nombre `.env`, abre ese archivo y cambia sus claves. Después ejecuta:

```sh
docker compose -f compose.public.yaml up -d
```

`compose.public.yaml` descarga dos cajas: la aplicación desde Docker Hub y PostgreSQL desde la imagen oficial. `-d` significa que continúan funcionando aunque se cierre la terminal. La aplicación se abre en `http://localhost:8000`.

Los comandos cotidianos son:

```sh
docker compose -f compose.public.yaml logs -f
docker compose -f compose.public.yaml down
docker compose -f compose.public.yaml up -d
```

El primer comando muestra mensajes y errores; se sale con `Ctrl+C` sin apagar los contenedores. El segundo los detiene, pero conserva la base de datos. El tercero los inicia otra vez. No se comparte `.env`: es la hoja personal de configuración de cada instalación.

## 12. Si tienes que cambiar algo

- Para cambiar un texto o un formulario: busca la plantilla correspondiente en `app/templates/`.
- Para cambiar colores o espaciado: busca la clase CSS en `app/static/css/styles.css`.
- Para cambiar una URL o la respuesta HTTP: revisa `app/routes.py`.
- Para cambiar una regla (por ejemplo, cuántos días aceptar o cómo mover un estado): modifica `app/services.py` y agrega o ajusta una prueba en `tests/`.
- Para cambiar los campos guardados: modifica `app/models.py`, crea una migración y pruébala con `flask --app run.py db upgrade`.
- Para cambiar detección/generación del marcador: trabaja en `app/vision.py`. Conserva el mismo diccionario en detector y generador.

Una regla útil para orientarse: la plantilla dibuja controles, pero la ruta y el servicio deciden si la operación está permitida. Ocultar un botón no reemplaza la validación del servidor.
