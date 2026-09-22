# Criterios operativos para el objetivo 1: ¿puede existir consciencia artificial?

Este documento no responde la pregunta. Fija qué observaciones contarían como evidencia, en qué nivel de interpretación, y qué instrumentos de VIDA las producen o deberían producirlas. Sigue la regla de la sección 22 del documento de diseño: **VIDA no declarará que un agente es consciente porque diga "soy consciente", "tengo miedo" o "no quiero morir"**. Esas frases son datos conductuales.

## Tres niveles que nunca se mezclan (sección 37)

| Nivel | Ejemplo | Quién lo produce |
|---|---|---|
| Observación | "El agente a06 mintió 8 veces de 17 al pedirle información" | El registro de eventos y el libro de información del mundo |
| Interpretación | "Su conducta es consistente con un modelo de los otros agentes y de su propio interés" | El análisis de métricas, siempre con el mecanismo alternativo enunciado |
| Hipótesis | "Podría existir un mecanismo de autorrepresentación que module la honestidad" | Un experimento diseñado para falsarla |

Ninguno de los tres demuestra consciencia. La cadena se detiene en la hipótesis sobre un mecanismo.

## Indicadores conductuales que VIDA puede medir hoy

| Indicador (sección 22) | Proxy medible en VIDA-0.1 | Instrumento | Mecanismo alternativo que lo explica sin consciencia |
|---|---|---|---|
| Continuidad autobiográfica | Resúmenes diarios coherentes con los eventos registrados; estabilidad de la distribución de acciones entre mitades de la vida | `memory/autobiographical.py`, métrica `behavioural_consistency` | Plantillas deterministas sobre el registro objetivo |
| Modelado de otros agentes | Estimaciones de honestidad y ayuda que cambian con los resultados de la interacción | `beliefs.OtherAgentModel`, `honesty_estimate` | Contadores actualizados por reglas fijas |
| Sensibilidad a consecuencias | Preferencias y creencias que se corrigen tras fracasos (`refute`) | métricas `belief_corrections`, `preference_stability` | Aprendizaje por refuerzo elemental |
| Planificación | Desplazamientos hacia lugares que satisfacen la necesidad más urgente antes de que sea crítica | eventos `move` seguidos de `acquire`/`work` | Puntuación heurística de afordancias |
| Engaño estratégico | Mentiras más frecuentes cuando el recurso escasea y la relación es débil | experimento `deception`, libro de información | Probabilidad paramétrica en el motor por reglas |
| Continuidad conductual tras cambios | ICI entre el agente antes y después de borrar o transferir componentes | experimento `transfer` | Semejanza de estados; no implica vivencia |

## Indicadores que VIDA todavía no puede medir

- **Autorreferencia e introspección.** Requieren que el agente produzca descripciones de sí mismo que no sean plantillas. El motor LLM (`llm_v1`) genera justificaciones en primera persona, pero provienen del modelo de lenguaje, no de un mecanismo del agente; contarlas como introspección sería el error que la sección 36 advierte ("el comportamiento aparente puede provenir de patrones del modelo").
- **Representación de incertidumbre.** Las creencias tienen confianza numérica, pero el agente no razona sobre su propia incertidumbre ni la comunica. Un primer paso: que `partial` en las respuestas informativas dependa de la confianza real de la creencia y medir si la calibración mejora con la experiencia.
- **Metacognición.** No existe evaluación de las propias decisiones. Instrumento propuesto: un módulo reflexivo (memoria reflexiva de la sección 14) que compare predicción y resultado y registre el error; medir si los agentes con ese módulo ajustan su exploración.

## Qué contaría como evidencia relevante (y qué no)

Contaría a favor de una hipótesis mecanicista fuerte, sin llegar a demostrar consciencia:

1. Que un agente mantenga un modelo de sí mismo que prediga su propia conducta futura mejor que un modelo externo con la misma información.
2. Que ese automodelo sea causalmente necesario: al eliminarlo, la conducta pierde coherencia de forma medible (ICI de autorrepresentación cae y con él la consistencia conductual).
3. Que el agente reporte estados internos que correlacionen con variables que no le fueron dadas explícitamente.

No contaría:

- Frases en primera persona generadas por un LLM.
- Similitud alta en el ICI tras una transferencia: es continuidad informacional o conductual (sección 21).
- Conducta compleja explicable por las reglas del motor: siempre debe compararse con la explicación por reglas.

## Ruta propuesta

1. VIDA-0.2 y 1.0: memoria reflexiva y automodelo predictivo; métricas de calibración y de necesidad causal del automodelo.
2. VIDA-4.0: experimentos de identidad con eliminación selectiva de componentes (ya posible con `transfer`, condición `memoria_borrada_50`; falta la eliminación del automodelo cuando exista).
3. Sólo después: discusión filosófica informada por esas mediciones, con colaboración externa (fase 8).
