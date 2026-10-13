# Sistema de gestión de fallas biomédicas

> Documentación oficial del proyecto

Aplicación web para registrar fallas de equipos biomédicos, identificar equipos con marcadores ArUco y organizar el trabajo del ingeniero clínico desde la recepción del reporte hasta la liberación del equipo.

El backend está desarrollado en Python con Flask. PostgreSQL conserva los equipos, reportes y el historial; OpenCV detecta y genera marcadores ArUco. Las páginas se renderizan con Jinja2 y usan HTML, CSS, Bootstrap y JavaScript nativo.

## Funcionalidades

- Estación de registro en `/station`: usa la cámara del navegador para capturar una imagen fija, identifica el marcador en Flask y permite registrar el reporte.
- Registro de equipos en `/registro`: formulario protegido para ingenieros. El sistema asigna automáticamente el siguiente ID ArUco consecutivo disponible y permite descargar el marcador PNG correspondiente.
- Aplicación del ingeniero: cola separada por etapas, detalle de caso, diagnóstico, estimaciones, ampliación de plazo, informe de mantenimiento, liberación e historial.
- Historial por equipo: permite consultar reportes actuales y cerrados desde el tablero mediante el serial.
- Clasificación de prioridad basada en impacto, criticidad clínica, respaldos operativos, uso y reincidencias.
- Despliegue en Docker Compose con Flask/Gunicorn y PostgreSQL.

## Tecnologías

| Tecnología | Uso |
| --- | --- |
| Python 3.12 | Lenguaje del servidor y reglas del sistema |
| Flask | Aplicación web, rutas y sesiones |
| Flask-SQLAlchemy / SQLAlchemy | Modelos y consultas a la base de datos |
| Flask-Migrate / Alembic | Migraciones de esquema |
| Flask-WTF | Protección CSRF de formularios |
| PostgreSQL + psycopg | Persistencia en Docker |
| OpenCV contrib headless + NumPy | Detección y generación ArUco en el servidor |
| Jinja2, HTML, CSS, Bootstrap | Interfaces web |
| JavaScript nativo | Vista previa y captura puntual de la cámara |
| Gunicorn | Servidor HTTP del contenedor |
| pytest | Pruebas automatizadas |

No hay frontend Node.js ni transmisión de video continuo. El navegador envía una imagen fija al servidor cuando el usuario solicita identificar el equipo.

## Requisitos

- Docker Desktop con Docker Compose, recomendado para ejecutar la aplicación completa.
- Para ejecución local sin contenedores: Python 3.12 y las dependencias de `requirements.txt`.
- Para usar cámara en un navegador, abrir el sitio desde `localhost` o desde un dominio servido por HTTPS y aceptar el permiso de cámara.

## Puesta en marcha con Docker

1. Copiar `.env.example` a `.env`.
2. Cambiar las contraseñas y la clave secreta para cualquier uso que no sea una demostración local.
3. En la carpeta del proyecto, ejecutar:

   ```sh
   docker compose up --build
   ```

4. Abrir las páginas siguientes:

   | Página | Dirección |
   | --- | --- |
   | Estación para reportar una falla | `http://localhost:8000/station` |
   | Ingreso del ingeniero | `http://localhost:8000/engineer/login` |
   | Tablero del ingeniero (requiere sesión) | `http://localhost:8000/engineer` |
   | Registro de equipo y marcador (requiere sesión) | `http://localhost:8000/registro` |
   | Estado del servicio y conexión a base de datos | `http://localhost:8000/health` |

Compose inicia PostgreSQL y espera a que su comprobación de salud pase antes de iniciar la aplicación. Al iniciar, el contenedor aplica migraciones, crea los datos de demostración que falten y ejecuta Gunicorn. El volumen `postgres_data` mantiene la base de datos entre reinicios y reconstrucciones normales.

### Ejecutar la imagen publicada (sin construir el código)

La versión publicada es `jorgepertuz23/biomed-mantenimiento:1.0.0` en Docker Hub. Para que otra persona la ejecute, debe recibir los archivos `compose.public.yaml` y `.env.example` de este proyecto, instalarlos en una carpeta y crear su propio `.env` a partir de la plantilla. Desde esa carpeta:

```sh
docker compose -f compose.public.yaml pull
docker compose -f compose.public.yaml up -d
```

Este flujo descarga la imagen publicada de la aplicación y la imagen oficial de PostgreSQL; no necesita Python ni el código fuente. Cada instalación crea su propio volumen `postgres_data`, por lo que sus equipos, reportes y usuarios no se mezclan con los de otras personas. Para ver el arranque, usar `docker compose -f compose.public.yaml logs -f`; para detenerlo sin borrar datos, usar `docker compose -f compose.public.yaml down`.

No se debe compartir el archivo `.env` real: cada persona copia `.env.example` como `.env` y cambia al menos `POSTGRES_PASSWORD`, `SECRET_KEY` e `INITIAL_ENGINEER_PASSWORD` antes de iniciar. La etiqueta `1.0.0` identifica esta entrega concreta; `latest` apunta a la versión más reciente publicada.

### Cuenta demostrativa

Los valores de `.env.example` permiten entrar al ingeniero con:

- Correo: `ingeniero@demo.local`
- Contraseña: `cambiar-para-demo`

Estos datos son únicamente para desarrollo y demostración. Deben cambiarse antes de cualquier despliegue compartido o de producción. El sistema guarda el hash de la contraseña, no la contraseña en texto plano.

### Variables de entorno

| Variable | Propósito | Valor de ejemplo |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | Contraseña del usuario de PostgreSQL que crea Compose | `maintenance_demo` |
| `SECRET_KEY` | Firma de las sesiones Flask y formularios | `change-this-in-production` |
| `INITIAL_ENGINEER_EMAIL` | Correo de la cuenta inicial creada por la semilla | `ingeniero@demo.local` |
| `INITIAL_ENGINEER_PASSWORD` | Contraseña inicial, almacenada como hash | `cambiar-para-demo` |
| `DATABASE_URL` | Conexión que usa Flask; Compose la construye para el servicio `db` | La define `compose.yaml` |

La configuración local también acepta `DATABASE_URL`. Si no se configura, Flask usa SQLite en `instance/maintenance.db`, apropiado para desarrollo simple. Docker utiliza PostgreSQL.

## Ejecución local sin Docker

Desde PowerShell o una terminal abierta en la carpeta del proyecto:

```sh
python -m venv .venv
```

Activar el entorno virtual según el sistema operativo y luego ejecutar:

```sh
python -m pip install -r requirements.txt
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

La aplicación local queda en `http://localhost:5000`. `DATABASE_URL` puede apuntar a PostgreSQL si se quiere usar esa base en lugar de SQLite.

## Flujo de trabajo clínico

```text
Registro de falla
       ↓
reportado → en_revision → en_mantenimiento → reparado → cerrado
                                     ↑           │
                                     └───────────┘
                                  si vuelve a requerir intervención
```

1. En `/station`, el reportante identifica un equipo mediante su marcador y envía persona, descripción e impacto operativo.
2. El caso aparece en “Pendientes de revisión”. “Iniciar revisión” solo registra que el ingeniero recibió el caso.
3. En revisión se guardan el diagnóstico inicial y los días estimados de indisponibilidad. Esos datos son requisito para iniciar mantenimiento.
4. En mantenimiento se conservan los datos iniciales. Se puede ampliar el plazo dejando una observación y, al finalizar, guardar el reporte final de mantenimiento.
5. Un caso reparado queda en “Reparados por verificar”. El ingeniero registra un reporte de liberación para cerrarlo o escribe el motivo para devolverlo a mantenimiento.
6. El equipo vuelve a estado operativo únicamente cuando se cierra el caso con un reporte de liberación.

Los respaldos forman parte de la fotografía de prioridad y se muestran como información operativa. Su ausencia no impide revisar, reparar o liberar un equipo.

En cada bandeja, la cola coloca primero los casos con validación de respaldo pendiente; luego ordena por prioridad crítica, alta, media y baja, puntaje descendente y antigüedad ascendente. El plazo estimado se muestra como información operativa y no cambia ese orden.

## Prioridad

Al registrar una falla, `calcular_prioridad()` suma cinco factores. Los días estimados no afectan el puntaje.

| Factor | Valores y puntos |
| --- | --- |
| Impacto | `detiene_servicio`: 35; `degradado`: 20; `sin_impacto`: 5 |
| Criticidad clínica del equipo | `soporte_vital`: 25; `diagnostico_terapia`: 15; `apoyo`: 8 |
| Respaldos compatibles disponibles | Ninguno: 15; uno: 6; dos o más: 0 |
| Nivel de uso | `alto`: 10; `medio`: 5; `bajo`: 2 |
| Reportes anteriores del mismo equipo en 90 días | Cero: 0; uno o dos: 5; tres o más: 15 |

La puntuación es la suma de esos factores, con máximo de 100. Si el impacto es `detiene_servicio` y hay cero respaldos, la prioridad se marca `critica` incluso si la suma es menor de 70; el puntaje no se altera.

| Puntaje | Prioridad |
| ---: | --- |
| 70–100 | Crítica |
| 50–69 | Alta |
| 30–49 | Media |
| 0–29 | Baja |

Los respaldos se cuentan en el momento de crear el reporte: deben compartir el mismo `grupo_respaldo`, estar operativos y no tener un reporte abierto. Si el grupo compatible del equipo no está definido, el sistema conserva la falla con prioridad pendiente para que un ingeniero confirme ese grupo. No interpreta un grupo desconocido como cero respaldos.

## Datos principales

### Equipo

Cada equipo tiene nombre, tipo, serial único, ID ArUco único entre 0 y 249, grupo de respaldo opcional, criticidad clínica, nivel de uso y estado operativo. El ID ArUco no se ingresa manualmente: al registrar, el servidor toma el siguiente número después del ID más alto ya asignado (comienza en 0 si no hay equipos) y comprueba que esté disponible. Si se agotaron los 250 IDs del diccionario, el registro se rechaza. La base de datos también impone unicidad para protegerse de registros simultáneos. La compatibilidad no se deduce del tipo: solo se cuentan equipos con el mismo grupo de respaldo explícitamente configurado.

### Usuario

Tiene nombre, correo único, hash de contraseña y rol. El acceso al panel y a `/registro` está limitado al rol `ingeniero`. El nombre de la persona que reporta una falla se guarda directamente en el reporte; no necesita una cuenta.

### Reporte de falla

Conserva el equipo asociado, quién reportó, descripción, impacto (`detiene_servicio`, `degradado`, `sin_impacto`), puntaje/prioridad (`critica`, `alta`, `media`, `baja`), cantidad de respaldos y reincidencias usados al calcular, estado (`reportado`, `en_revision`, `en_mantenimiento`, `reparado`, `cerrado`), diagnóstico, días iniciales y vigentes, reportes finales de mantenimiento/liberación, marcas de tiempo y banderas históricas de compatibilidad.

### Historial

Cada acontecimiento se añade como entrada persistente con reporte, usuario responsable cuando corresponde, estado previo/nuevo, tipo de evento, observación, detalles y fecha. Incluye registro original, cambios de estado, diagnóstico/estimación, extensiones de plazo, informe de mantenimiento, liberación y devoluciones a mantenimiento.

## Rutas web y API

| Método | Ruta | Acceso | Función |
| --- | --- | --- | --- |
| `GET` | `/station` | Público | Pantalla para identificar equipo y reportar falla |
| `POST` | `/api/identify` | Público | Recibe una imagen JPEG/PNG y devuelve el marcador/equipo detectado |
| `POST` | `/api/reports` | Público | Crea reporte para un `equipo_id` existente |
| `GET`, `POST` | `/engineer/login` | Público | Inicio de sesión del ingeniero |
| `POST` | `/engineer/logout` | Ingeniero | Cierra la sesión |
| `GET` | `/engineer` | Ingeniero | Tablero de casos abiertos agrupados por estado |
| `GET`, `POST` | `/registro` | Ingeniero | Formulario de registro de equipo; muestra el PNG generado después de guardar |
| `GET` | `/engineer/reports/<id>` | Ingeniero | Detalle, formularios de la etapa actual e historial del reporte |
| `POST` | `/engineer/reports/<id>/transition` | Ingeniero | Ejecuta una transición válida de estado |
| `POST` | `/engineer/reports/<id>/review` | Ingeniero | Guarda diagnóstico y días durante la revisión |
| `POST` | `/engineer/reports/<id>/extend-days` | Ingeniero | Añade días al plazo durante mantenimiento |
| `POST` | `/engineer/reports/<id>/confirm-backup-group` | Ingeniero | Confirma grupo y completa un cálculo de prioridad pendiente |
| `GET` | `/engineer/equipment/<id>/history` | Ingeniero | Historial de todos los reportes del equipo, incluso cerrados |
| `GET` | `/engineer/history?serial=<serial>` | Ingeniero | Busca historial por serial |
| `GET` | `/health` | Público | Comprueba que Flask puede consultar la base de datos |

`/api/identify` distingue `marker_not_found`, `multiple_markers`, `equipment_not_found`, `equipment_identified` e `invalid_image`. El endpoint de reportes no asocia un equipo por defecto: exige un ID que exista en la base de datos.

## ArUco y cámara

El detector y el generador usan el diccionario `DICT_6X6_250`. OpenCV procesa la imagen en Python; el navegador solo abre la cámara, presenta la vista previa y envía una captura puntual. Las imágenes de identificación se procesan en memoria y no se almacenan.

Los marcadores de demostración se generan desde la raíz del proyecto con:

```sh
python scripts/generate_markers.py
```

El script guarda en `markers/` los PNG con IDs 42, 43 y 44. La semilla registra equipos de demostración con IDs 42 a 46; por eso, en una base inicializada con esos datos, el primer equipo agregado desde `/registro` recibe el ID 47. Si la base está vacía, el primer ID es 0. El marcador se puede imprimir desde la página de confirmación del registro.

## Estructura del proyecto

```text
app/                    Aplicación Flask
  __init__.py           Fábrica Flask y comando de semilla
  config.py             Configuración por variables de entorno
  extensions.py         SQLAlchemy, migraciones y CSRF compartidos
  models.py             Entidades Equipo, Usuario, ReporteFalla e HistorialReporte
  routes.py             Páginas, API, autenticación y validación HTTP
  services.py           Prioridad, respaldos, reportes y reglas de estados
  vision.py             Detección y generación de ArUco
  templates/            Vistas Jinja2
  static/                CSS y JavaScript de cámara
migrations/              Historial de cambios del esquema de la base de datos
scripts/                  Herramientas pequeñas, como el generador de marcadores
tests/                    Pruebas de visión, prioridad y flujo de trabajo
compose.yaml              Servicios app y db
Dockerfile                Imagen Python 3.12 y arranque con Gunicorn
requirements.txt          Dependencias Python fijadas
run.py                    Punto de entrada de Flask/Gunicorn
GUIA_DEL_CODIGO.md         Guía no oficial, explicada paso a paso
```

## Migraciones, semilla y pruebas

Las migraciones están en `migrations/versions/`. El contenedor aplica `flask --app run.py db upgrade` al iniciar. Para crear una migración durante desarrollo después de cambiar los modelos:

```sh
flask --app run.py db migrate -m "descripcion del cambio"
flask --app run.py db upgrade
```

La semilla se puede repetir: no duplica el ingeniero inicial ni los equipos de demostración. Ejecutarla manualmente:

```sh
flask --app run.py seed
```

Ejecutar las pruebas con:

```sh
python -m pytest -q
```

Las pruebas usan una base SQLite aislada, imágenes ArUco generadas y el test client de Flask. No requieren cámara física ni PostgreSQL para la suite automatizada.

## Consideraciones de despliegue

- Sustituir todos los valores de demostración y usar una `SECRET_KEY` aleatoria y privada.
- Para una cámara desde otro dispositivo se requiere HTTPS; `localhost` funciona para desarrollo local.
- PostgreSQL no publica su puerto al host en la configuración Compose actual; solo la aplicación tiene el puerto web 8000 publicado.
- El diseño actual incluye un usuario inicial configurable por entorno y una pantalla de registro protegida para ingenieros. No incluye gestión de roles, recuperación de contraseña ni administración avanzada de inventario.
