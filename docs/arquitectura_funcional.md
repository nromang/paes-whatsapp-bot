# Arquitectura funcional final

## 1. Objetivo del sistema
Implementar un chatbot de estudio PAES por WhatsApp que permita practicar, simular ensayo, corregir con clave oficial, y devolver un reporte claro y confiable para estudiante y apoderado.

## 2. Principios de diseño
- **Confiabilidad académica**: se separa el contenido de la lógica de corrección.
- **Transparencia**: el sistema distingue entre puntaje exacto y puntaje proyectado.
- **Escalabilidad**: el contenido se puede ampliar por CSV o por extracción estructurada.
- **Operación simple**: la alumna interactúa con comandos cortos y respuestas A-E.
- **Compatibilidad WhatsApp**: todas las decisiones del MVP son compatibles con Cloud API.

## 3. Capas
### 3.1 Canal
WhatsApp Cloud API:
- webhook para recibir mensajes,
- endpoint `/messages` para responder,
- mensajes de texto e interactive list.

### 3.2 Backend
FastAPI:
- validación del webhook,
- lógica conversacional,
- corrección,
- cálculo de puntaje,
- endpoints de administración.

### 3.3 Persistencia
SQLite:
- usuarios,
- sesiones,
- detalle de preguntas por sesión.

### 3.4 Contenido
Archivos JSON:
- `official_exam_config.json`
- `question_bank.json`
- `contexts.json`

## 4. Modos de uso
### 4.1 Práctica
Entrega una cantidad acotada de preguntas.
- rápida,
- útil para estudio diario,
- devuelve **proyección PAES** si no es la forma completa.

### 4.2 Ensayo
Intenta usar la forma completa disponible en el banco.
- si el banco contiene toda la forma, devuelve **puntaje PAES exacto**;
- si el banco aún es parcial, devuelve **proyección PAES**.

## 5. Flujo de sesión
1. Usuario escribe comando.
2. El sistema identifica materia y modo.
3. Selecciona preguntas activas.
4. Crea sesión.
5. Envía contexto si corresponde.
6. Envía pregunta.
7. Registra respuesta.
8. Avanza hasta cerrar.
9. Calcula resultado.
10. Entrega reporte final.

## 6. Materias y tracks
- Competencia Lectora
- Competencia Matemática 1
- Competencia Matemática 2
- Historia y Ciencias Sociales
- Ciencias:
  - Biología
  - Física
  - Química
  - Técnico Profesional

## 7. Regla pedagógica clave
El reporte final no solo dice si estuvo bien o mal:
- muestra la alternativa correcta,
- explica si el puntaje es exacto o estimado,
- separa avance y porcentaje válido.

## 8. Diseño de experiencia
### Inicio
- `MENU`
- `PRACTICA ...`
- `ENSAYO ...`

### Durante la prueba
- respuesta simple A-E,
- `OMITIR`,
- `TEXTO`,
- `RESULTADO`,
- `SALIR`.

### Cierre
Un reporte corto, claro y usable en celular.

## 9. Fase 2 sugerida
- dashboard web del apoderado,
- cron diario,
- templates aprobados,
- envío de imágenes,
- analítica por eje/habilidad,
- ranking de errores recurrentes,
- recomendación automática de siguiente práctica.
