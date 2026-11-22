---
title: "Informe detallado de entrega final — Tesis FIL-0015-YA"
subtitle: "Arnold Indigoyen Aguilar · FIM-UNI · 22 de noviembre de 2026"
---

# 1. Archivos finales

| Archivo | Descripción |
|---|---|
| Tesis_Indigoyen_FIM_UNI_v19.docx | Tesis final (v17 del autor + ajustes v18 y v19) |
| FIL-0015-YA_Respaldo_Tesis_v15.xlsx | Respaldo de cálculos (12 hojas, 1.398 fórmulas), sin cambios |
| FIL-0015-YA_Escenarios_frecuencia_MTTR.xlsx | Nuevo: escenarios separados de frecuencia y MTTR (fórmulas vivas) |
| FIL-0015-YA_calculos_confiabilidad.py | Script de cálculos (sin `--robustez`), sin cambios |
| resultados_confiabilidad_reproducido.json | Salida de la corrida completa del script en esta sesión |
| resultados_confiabilidad_referencia.json / _con_robustez.json | Referencias aportadas por el autor |

# 2. Cambios en la tesis

**v18 (desde v17):** la comparación de confiabilidad 2025–2026 ya no dice "mejoró"; se presenta como descriptiva (R(48 h): 30,8 % → 37,2 %) con las reservas: periodos de distinta duración, intervalos reconstruidos sin horómetro, tendencia de Laplace 2026 (p = 0,041) e independencia no demostrada. Dos pasajes: objetivo específico 2 y conclusión del Capítulo IV.

**v19 (auditoría v18):**

- H01: el rechazo de la lognormal es estable por Kolmogorov-Smirnov, no por Anderson-Darling (p = 0,049–0,071 cruza 0,05); no se afirma estabilidad conjunta.
- H05: "fueron revisadas con el personal de mantenimiento" pasó a "se proponen para validación… deberá quedar en acta" (2 pasajes).
- H08: "no se encontró desgaste" pasó a "no se encontró evidencia estadística suficiente de desviación de β = 1", sin afirmar ausencia de desgaste (2 pasajes).
- H11: "alternativa viable" pasó a "viabilidad prospectiva condicionada, de diseño y matemática".
- H12: ya conciliado en la v17 (1.868,1 HH × US$ 25 = US$ 46.702).

# 3. Verificaciones realizadas

1. **Reproducción de la estadística ordinaria.** Se ejecutó el script completo con el Excel v15. Se compararon 148 valores contra `resultados_confiabilidad_referencia.json`: **0 diferencias** (semillas declaradas). Esto no cubre el modo `--robustez`.
2. **Escenarios frecuencia × MTTR (H03).** Línea base 2026: 7.608 h, 116 fallas, 230,5 h de parada por falla, 194,0 h de otras paradas, MTTR 1,987 h. Meta 95 % → paradas totales ≤ 380,4 h → paradas por falla ≤ 186,4 h (hay que evitar 44,1 h). Reducir solo la frecuencia o solo el MTTR da las mismas horas; combinando 10 % + 10 % se llega a 95,00 %. Matriz completa en el Excel nuevo.
3. **Geisbush y Ariaratnam (H04).** Existe una revisión de literatura de ambos en *Journal of Quality in Maintenance Engineering* 29(2), 313–337. No se pudo acceder al texto completo, por lo que **no está verificado** que el 20–40 % sea reducción de horas de parada ni el año 2023.

# 4. Estado de los hallazgos de la auditoría v18

| N.º | Estado |
|---|---|
| H01 | Corregido en v19 |
| H02 | **Abierto:** el script entregado no incluye `--robustez`; se requiere el script v7 correcto |
| H03 | Calculado (Excel nuevo); **falta incorporarlo como tabla en el Capítulo III** y vincularlo a modos de falla y tareas |
| H04 | **Abierto:** cotejar el artículo primario; si no coincide, presentar 20–40 % como supuesto propio |
| H05 | Corregido en v19; la validación real con el personal sigue pendiente |
| H06 | **Abierto:** faltan cotizaciones y fuente operativa del costo US$ 2.647/h y de la reserva de repuestos (US$ 50.000) |
| H07 | Ya cubierto por la redacción v18 |
| H08 | Corregido en v19 |
| H09, H10 | **Abiertos:** metadatos de Rosita y Rada (2021) y enlace de Cybertesis de Antón Barrientos (2025) |
| H11 | Corregido en v19 |
| H12 | Resuelto en v17 |
| H13 | Parcial: reproducción ordinaria hecha; `--robustez` no ejecutado |
| H14 | **Abierto:** verificación celda por celda del Excel no realizada |

# 5. Límites declarados

- No se certifica la exactitud de las 1.398 fórmulas del Excel ni la revisión visual página por página.
- El flujo económico (VAN de US$ 41.710 a US$ 510.499) es una evaluación condicionada a supuestos no acreditados.
- El RCM no fue implementado: toda reducción de paradas es escenario, no efecto observado.
- En esta sesión se escribió "186,1 h" como tope de paradas por falla; el valor correcto es 186,4 h.

# 6. Para cerrar antes de entregar al asesor

Script v7 con `--robustez` (y su ejecución en bloques), cotejo de Geisbush y Ariaratnam, cotizaciones y fuente del costo por hora, acta de validación con mantenimiento, metadatos bibliográficos, tabla de escenarios frecuencia × MTTR en el Capítulo III y auditoría de fórmulas del Excel.
