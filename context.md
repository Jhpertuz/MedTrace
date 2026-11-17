# Contexto de continuidad — MedTrace

## 1. Propósito de este archivo

Este archivo conserva el contexto necesario para preparar una presentación académica de MedTrace sin depender de una conversación anterior. La fuente principal debe ser el repositorio público `Jhpertuz/MedTrace` y su documentación. No deben inventarse funcionalidades, resultados, validaciones con usuarios, métricas, certificaciones ni datos clínicos.

Cuando exista una diferencia entre una afirmación del repositorio y una nota del equipo, debe indicarse la procedencia. Las propuestas futuras deben presentarse como propuestas, no como capacidades actuales.

## 2. Identificación del proyecto

- **Nombre:** MedTrace.
- **Repositorio:** `https://github.com/Jhpertuz/MedTrace`
- **Rama de referencia consultada:** `main`.
- **Descripción documentada:** aplicación web para registrar fallas de equipos biomédicos, identificar equipos con marcadores ArUco y organizar el trabajo del ingeniero clínico desde la recepción del reporte hasta la liberación del equipo.
- **Objetivo de la presentación:** exposición académica de 12 minutos con 6 integrantes.
- **Rúbrica:** planteamiento y objetivos 10 %, diseño y arquitectura 15 %, funcionamiento e integración 20 %, interfaz y usabilidad 15 %, código y documentación técnica 15 %, pruebas y validación 10 %, sustentación y trabajo en equipo 15 %.

## 3. Fuentes documentales del repositorio

- `README.md`: documentación oficial, funcionalidades, tecnologías, ejecución, flujo clínico, prioridad, datos, rutas, ArUco, pruebas y despliegue.
- `GUIA_DEL_CODIGO.md`: guía no oficial de lectura; explica la arquitectura, carpetas, modelos, servicios, rutas, estados, prioridad y pruebas.
- Código relevante: `app/routes.py`, `app/services.py`, `app/models.py`, `app/vision.py`, plantillas, JavaScript, `tests/`, `compose.yaml`, `Dockerfile` y migraciones.
- `context.md`: este archivo de continuidad; no constituye evidencia independiente del comportamiento del sistema.

## 4. Hechos documentados en el repositorio

### 4.1 Funcionalidades actuales

- Reporte público de fallas desde `/station`.
- Identificación de equipos mediante cámara del navegador y marcador ArUco.
- La cámara toma una imagen fija; no existe transmisión continua de video.
- `POST /api/identify` procesa JPEG/PNG en el servidor y distingue marcador no encontrado, múltiples marcadores, equipo no encontrado, equipo identificado e imagen inválida.
- Registro protegido de equipos para usuarios con rol `ingeniero` en `/registro`.
- Generación del siguiente ID ArUco disponible del diccionario `DICT_6X6_250`, en el rango 0–249.
- Cálculo automático de prioridad cuando el grupo de respaldo está definido.
- Gestión de reportes por estados: `reportado`, `en_revision`, `en_mantenimiento`, `reparado` y `cerrado`.
- Diagnóstico inicial, estimación de indisponibilidad, ampliación de plazo, informe final de mantenimiento y reporte de liberación.
- Historial persistente de acontecimientos por reporte y consulta del historial de un equipo.
- Tablero del ingeniero con bandejas por etapa y ordenamiento por validación de respaldo pendiente, prioridad, puntaje y antigüedad.
- Pruebas automatizadas de prioridad, visión y flujo web.
- Despliegue con Docker Compose, Flask/Gunicorn y PostgreSQL.

### 4.2 Tecnologías

- Python 3.12 y Flask.
- PostgreSQL con `psycopg` en Docker; SQLite para desarrollo/pruebas aisladas.
- Flask-SQLAlchemy/SQLAlchemy y Flask-Migrate/Alembic.
- Flask-WTF para CSRF.
- OpenCV contrib headless y NumPy.
- Jinja2, HTML, CSS, Bootstrap y JavaScript nativo.
- Gunicorn, Docker Compose y pytest.
- No hay frontend Node.js.

### 4.3 Arquitectura

```text
Navegador
  ├─ formularios y captura fija
  ▼
app/routes.py       valida solicitudes, sesiones y respuestas HTTP
  ├─ app/vision.py  detecta/genera ArUco
  ├─ app/services.py aplica reglas de negocio
  └─ app/models.py  representa entidades y relaciones
        ▼
     PostgreSQL o SQLite
```

- `create_app()` configura Flask, extensiones y rutas.
- `routes.py` atiende páginas, API, autenticación y validación HTTP.
- `services.py` concentra prioridad, respaldos, reincidencias, registro de equipos, transiciones e historial.
- `vision.py` detecta marcadores y genera PNG.
- Las plantillas Jinja2 y los archivos estáticos forman la interfaz.
- Las migraciones versionan el esquema.

### 4.4 Modelo de datos

- `Equipo`: nombre, tipo, serial único, `aruco_id` único, grupo de respaldo opcional, criticidad clínica, nivel de uso y estado operativo.
- `Usuario`: nombre, correo único, hash de contraseña y rol.
- `ReporteFalla`: equipo, reportante, descripción, impacto, puntaje/prioridad, respaldos y reincidencias usados, estado, diagnóstico, días, informes, fechas y banderas de validación.
- `HistorialReporte`: eventos persistentes con usuario, estado anterior/nuevo, tipo, observación, detalles y fecha.
- El tipo del equipo no determina la compatibilidad; solo cuenta el mismo `grupo_respaldo` explícitamente configurado.

### 4.5 Prioridad

`calcular_prioridad()` suma:

| Factor | Valores documentados |
|---|---|
| Impacto | `detiene_servicio`: 35; `degradado`: 20; `sin_impacto`: 5 |
| Criticidad clínica | `soporte_vital`: 25; `diagnostico_terapia`: 15; `apoyo`: 8 |
| Respaldos operativos compatibles | ninguno: 15; uno: 6; dos o más: 0 |
| Nivel de uso | `alto`: 10; `medio`: 5; `bajo`: 2 |
| Reincidencias en 90 días | cero: 0; una o dos: 5; tres o más: 15 |

- Máximo documentado: 100 puntos.
- Rangos: 70–100 crítica, 50–69 alta, 30–49 media, 0–29 baja.
- Regla especial: `detiene_servicio` sin respaldos marca prioridad `critica` sin alterar el puntaje.
- Los días estimados no afectan el puntaje.
- Si no está definido el grupo compatible, la prioridad queda pendiente para confirmación del ingeniero; no se interpreta como cero respaldos.

### 4.6 Flujo clínico documentado

```text
reportado → en_revision → en_mantenimiento → reparado → cerrado
                                      ↑             │
                                      └─────────────┘
                                  retorno a mantenimiento
```

- La estación registra persona, descripción e impacto después de identificar el equipo.
- En revisión se guarda diagnóstico y días estimados; son requisito para iniciar mantenimiento.
- En mantenimiento se puede ampliar el plazo y registrar el informe final.
- En reparado se registra liberación para cerrar o una observación para volver a mantenimiento.
- El equipo vuelve a `operativo` únicamente al cerrar con reporte de liberación.
- Los respaldos son información operativa y su ausencia no impide revisar, reparar o liberar.

### 4.7 Pruebas, ejecución y despliegue

- Comando documentado: `python -m pytest -q`.
- Las pruebas usan SQLite aislado, imágenes ArUco generadas y Flask test client.
- No requieren cámara física ni PostgreSQL para la suite automatizada.
- Docker Compose inicia PostgreSQL y la aplicación; aplica migraciones, ejecuta la semilla y arranca Gunicorn.
- `/health` comprueba la conexión de Flask con la base de datos.
- El README documenta Docker, ejecución local, variables de entorno y la imagen publicada.
- Las credenciales de demostración son solo para desarrollo/demostración y deben cambiarse antes de despliegues compartidos.

## 5. Información proporcionada por el equipo

Estas notas no deben presentarse como resultados medidos por el repositorio:

- Calificaciones visibles previamente:
  - Planteamiento del problema y objetivos: 3.8.
  - Diseño y arquitectura: 4.5.
  - Funcionamiento e integración: 4.8.
  - Interfaz y usabilidad: 5.0.
  - Código y documentación técnica: sin dato visible.
  - Pruebas y validación: 5.0.
  - Sustentación y trabajo en equipo: 4.0.
- Distribución acordada: 12 diapositivas, 12 minutos, 6 personas, dos diapositivas por persona.
- La cámara captura una imagen fija; esta nota coincide con la documentación del repositorio.

## 6. Estructura acordada de la presentación

1. Portada.
2. Planteamiento del problema.
3. Objetivos y alcance.
4. Arquitectura del sistema.
5. Identificación mediante cámara y ArUco.
6. Modelo de datos.
7. Flujo de gestión de una falla.
8. Priorización automática.
9. Interfaz y usabilidad.
10. Pruebas y validación.
11. Docker y despliegue.
12. Resultados y conclusiones.

Reparto:

- Persona 1: diapositivas 1 y 2.
- Persona 2: diapositivas 3 y 4.
- Persona 3: diapositivas 5 y 6.
- Persona 4: diapositivas 7 y 8.
- Persona 5: diapositivas 9 y 10.
- Persona 6: diapositivas 11 y 12.

## 7. Reglas para preparar la presentación

- Separar explícitamente “documentado en el repositorio”, “aportado por el equipo” y “propuesta/futuro”.
- No afirmar validación con usuarios, impacto clínico real, reducción de tiempos, precisión de detección, cobertura, disponibilidad, certificaciones o resultados no presentes en las fuentes.
- Describir las pruebas como pruebas automatizadas existentes; no convertir su existencia en una validación clínica o de usuarios.
- Mostrar la cámara como captura puntual, no como video en vivo.
- Explicar que PostgreSQL es el almacenamiento de Docker y SQLite se usa en desarrollo/pruebas.
- Presentar el cálculo de prioridad con sus factores y la regla de respaldo desconocido.
- Distinguir `aruco_id` del `equipo.id`.
- Si se mencionan mejoras, etiquetarlas como propuestas futuras: por ejemplo, gestión avanzada de roles, recuperación de contraseña o administración avanzada de inventario, que el README declara fuera del alcance actual.

## 8. Entregables esperados en futuras sesiones

Con base en este archivo y en la documentación vigente, preparar:

1. Markdown completo de la guía oral/visual de la presentación.
2. Disposición visual de las 12 diapositivas.
3. Notas sugeridas para cada presentador.
4. Prompt final optimizado para Claude usando la habilidad Gamma.

Cada entregable debe conservar la separación de fuentes y debe evitar inventar datos.
