# Modelo de datos y scoring

## 1. Tabla `users`
Guarda:
- teléfono,
- nombre,
- fecha de creación,
- último contacto.

## 2. Tabla `sessions`
Cabecera de la sesión:
- materia,
- modo,
- forma oficial,
- estado,
- puntaje válido,
- puntaje PAES exacto o estimado,
- fechas.

## 3. Tabla `session_questions`
Detalle operativo:
- secuencia,
- id de pregunta,
- número oficial,
- contexto asociado,
- si puntúa,
- si fue eliminada,
- respuesta del usuario,
- corrección.

## 4. Archivo `official_exam_config.json`
Contiene por materia:
- forma,
- total de preguntas,
- preguntas excluidas,
- preguntas eliminadas,
- claves oficiales,
- tabla de transformación P -> PAES.

## 5. Archivo `question_bank.json`
Cada pregunta contiene:
- id único,
- materia,
- forma,
- número oficial,
- stem,
- alternativas,
- correcta,
- contexto,
- flags operativas (`is_scored`, `is_deleted`, `active`, `delivery_mode`).

## 6. Lógica de corrección
### 6.1 Preguntas válidas
Solo cuentan:
- preguntas no excluidas,
- preguntas no eliminadas.

### 6.2 Puntaje P
Se calcula como la suma de respuestas correctas válidas.

### 6.3 Puntaje exacto
Se entrega cuando la sesión contiene la forma oficial completa.

### 6.4 Puntaje proyectado
Se usa cuando la sesión es parcial.
Fórmula:
1. porcentaje válido = correctas válidas / válidas de la sesión
2. proyección P = round(porcentaje válido * total válido oficial)
3. búsqueda del valor en la tabla PAES de la forma.

## 7. Caso especial M2
M2 tiene:
- 5 preguntas marcadas con `*` que no puntúan,
- 1 pregunta eliminada `**`.
Por eso la transformación oficial llega hasta **P = 49**.

## 8. Regla de honestidad del sistema
Nunca presentar como exacto un puntaje que fue extrapolado.
El sistema siempre debe rotular:
- `Puntaje PAES oficial exacto`
o
- `Puntaje PAES proyectado`
