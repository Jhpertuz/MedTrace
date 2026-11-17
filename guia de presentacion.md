Con 10 diapositivas, las personas que tenían pares contiguos quedan así: la 2 y la 5 absorben sus dos temas en una sola diapositiva, y las otras cuatro mantienen dos cada una. El total ronda los 11:30 min, con margen para el cambio de presentador.

| Persona | Diapositivas | Tiempo |
|---|---|---|
| 1 | 1 y 2 (portada, problema) | ~1:30 |
| 2 | 3 (objetivos, alcance y arquitectura) | ~1:45 |
| 3 | 4 y 5 (ArUco, modelo de datos) | ~2:00 |
| 4 | 6 y 7 (flujo, prioridad) | ~2:15 |
| 5 | 8 (interfaz, usabilidad y pruebas) | ~1:45 |
| 6 | 9 y 10 (Docker, conclusiones) | ~2:15 |

Cada guion está redactado para decirse en voz alta. Al final de cada bloque va una etiqueta interna para el equipo, que no se lee.

## Persona 1: diapositivas 1 y 2

**Diapositiva 1.** «Buenos días. Somos el equipo que les presenta MedTrace, una aplicación web para gestionar fallas de equipos biomédicos. La idea central es que un reporte de falla quede asociado al equipo correcto mediante un marcador ArUco y que después tenga un seguimiento ordenado hasta que el equipo se libera. En los próximos doce minutos vamos a recorrer el problema, la arquitectura, el funcionamiento y los límites de lo que hemos demostrado.»

**Diapositiva 2.** «El problema tiene tres partes. Primero, un reporte de falla tiene que apuntar sin ambigüedad a un equipo concreto. Segundo, quien reporta y quien atiende son personas distintas: una usa una estación pública y el otro un panel de ingeniería. Tercero, el caso pasa por varias etapas y hay que decidir cuál atender primero según el impacto, la criticidad clínica, los respaldos disponibles, el uso y las reincidencias. Aclaro algo importante: MedTrace organiza reportes y etapas de seguimiento; no diagnostica ni repara los equipos.»

*Etiqueta: planteamiento tomado del README; la formulación del problema es de presentación.*

## Persona 2: diapositiva 3

«Esta diapositiva reúne objetivos, alcance y arquitectura. El objetivo es registrar fallas, identificar equipos con marcadores ArUco y organizar el trabajo del ingeniero clínico. Según la documentación, el alcance incluye el reporte público, el registro protegido de equipos, un tablero por etapas, la prioridad automática, el historial por equipo y el despliegue con Docker Compose. Quedan fuera por ahora la gestión avanzada de roles, la recuperación de contraseña y la administración avanzada de inventario.

La arquitectura es en capas. El navegador envía formularios y una captura fija a Flask. El archivo de rutas valida solicitudes y sesiones, y delega en tres módulos: visión, que maneja ArUco con OpenCV; servicios, donde viven las reglas de negocio; y modelos, que representan los datos. Abajo está la base de datos: PostgreSQL en Docker y SQLite en desarrollo y pruebas aisladas. Separar así las responsabilidades nos permite cambiar una regla sin tocar la interfaz.»

*Etiqueta: hechos documentados (README y GUIA_DEL_CODIGO). La última frase es interpretación de presentación.*

## Persona 3: diapositivas 4 y 5

**Diapositiva 4.** «Para identificar un equipo, el navegador abre la cámara y muestra una vista previa. Cuando el usuario pulsa identificar, envía una imagen fija al servidor; insisto, no hay transmisión continua de video. OpenCV detecta el marcador del diccionario DICT_6X6_250, que ofrece IDs del 0 al 249. El servidor responde con uno de cinco resultados: marcador no encontrado, varios marcadores, equipo no encontrado, equipo identificado o imagen inválida. La imagen se procesa en memoria y no se guarda. Para usar la cámara desde otro dispositivo se necesita HTTPS.»

**Diapositiva 5.** «El modelo de datos tiene cuatro entidades. Equipo guarda nombre, tipo, serial único, el ID ArUco, un grupo de respaldo opcional, criticidad, nivel de uso y estado operativo. Usuario guarda el correo, el hash de la contraseña y el rol. ReporteFalla concentra la descripción, el impacto, la prioridad, el estado y los informes. Y HistorialReporte registra cada acontecimiento con su fecha. Dos aclaraciones: el ID del marcador no es la clave interna del equipo, y el tipo de equipo no define quién respalda a quién; solo cuenta el grupo de respaldo configurado explícitamente.»

*Etiqueta: hechos documentados.*

## Persona 4: diapositivas 6 y 7

**Diapositiva 6.** «Un caso recorre cinco estados: reportado, en revisión, en mantenimiento, reparado y cerrado. En revisión se guardan un diagnóstico inicial y los días estimados, y son requisito para pasar a mantenimiento. En mantenimiento se puede ampliar el plazo dejando una observación y, al terminar, registrar el informe final. Un caso reparado se cierra con un reporte de liberación o vuelve a mantenimiento si hace falta, explicando el motivo. El equipo solo vuelve a estado operativo cuando el caso se cierra con ese reporte de liberación.»

**Diapositiva 7.** «La prioridad se calcula con cinco factores que suman hasta 100 puntos: impacto, criticidad clínica del equipo, respaldos compatibles disponibles, nivel de uso y reportes previos en 90 días. Con la suma, el caso queda crítico desde 70, alto desde 50, medio desde 30 y bajo por debajo de 30. Hay una regla especial: si el equipo detiene el servicio y no hay respaldos, la prioridad es crítica aunque el puntaje sea menor. Y si el grupo de respaldo no está definido, el cálculo queda pendiente para que un ingeniero lo confirme; el sistema no lo trata como cero respaldos. Estos pesos son reglas implementadas en este proyecto, no una escala clínica universal.»

*Etiqueta: hechos documentados. Puntos y rangos tal como están en el README.*

## Persona 5: diapositiva 8

«Esta diapositiva junta interfaz y pruebas. Hay dos interfaces según el rol. La estación pública permite identificar el equipo y enviar quién reporta, la descripción y el impacto. El panel del ingeniero tiene una bandeja por etapa, un detalle que cambia sus formularios según el estado y una búsqueda de historial por serial. Además, la pantalla de registro asigna el siguiente ID ArUco y permite descargar el marcador en PNG.

En pruebas, el repositorio incluye tres archivos automatizados: uno para los puntajes de prioridad, otro que procesa imágenes ArUco generadas con OpenCV y otro que recorre formularios, estados e historial con el cliente de pruebas de Flask. Usan SQLite aislado y no necesitan cámara ni PostgreSQL. Dejo claro el límite: son pruebas automatizadas existentes, no una validación clínica ni con usuarios, y aquí no presentamos resultados de ejecución, cobertura ni precisión. Como propuesta futura, queda evaluar la usabilidad con usuarios reales.»

*Etiqueta: hechos documentados para la descripción; la evaluación de usabilidad es propuesta futura. Usar capturas reales del proyecto en esta diapositiva.*

## Persona 6: diapositivas 9 y 10

**Diapositiva 9.** «Para el despliegue usamos Docker Compose con dos servicios: la aplicación, con Flask y Gunicorn, y PostgreSQL con una comprobación de salud. Al iniciar, el contenedor aplica las migraciones, crea los datos de demostración que falten y arranca el servidor. Un volumen conserva la base entre reinicios, y la ruta de salud confirma que Flask llega a la base. También hay una imagen publicada en Docker Hub, de modo que otra persona puede ejecutarla sin el código fuente. Las credenciales de demostración son solo para desarrollo y deben cambiarse en cualquier despliegue compartido.»

**Diapositiva 10.** «Para cerrar, lo que está implementado y documentado en el repositorio es el reporte público, la identificación por captura fija con ArUco, el registro de equipos, la prioridad automática, la gestión por estados con historial, las pruebas automatizadas y el despliegue con Docker. Lo que no podemos afirmar es igual de importante: no aportamos métricas de impacto, precisión ni cobertura, no hay validación clínica ni con usuarios, y no decimos que el sistema reduzca tiempos, errores o costos. Como trabajo futuro proponemos evaluar la usabilidad, recolectar métricas de uso y avanzar en la gestión de roles. Gracias; quedamos atentos a sus preguntas.»

*Etiqueta: hechos documentados en la primera parte; los límites son aclaración del equipo y el trabajo futuro es propuesta.*

Si el tiempo de la exposición es estricto, la diapositiva 8 es la más densa. Si Persona 5 se pasa de los dos minutos, conviene que recorte la parte de interfaz y conserve el párrafo de límites de las pruebas.
