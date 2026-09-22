# Resultados de VIDA-0.2 (22 de septiembre de 2026)

Registro de lo observado con los instrumentos de 0.2: memoria reflexiva, acoplamiento memoria→decisión, automodelo predictivo y experimentos con tamaños de efecto. Todo en el nivel de **observación** o **interpretación**; ninguna conclusión sobre consciencia.

Configuración base: `config/default.yaml`, motor por reglas, 10 agentes, semillas 1-3. Resultados crudos en `data/experiments/` (no versionados; reproducibles con el manifiesto).

## 1. Corrida de aceptación (30 días, semilla 42)

- Los 10 agentes sobreviven. Una primera versión del acoplamiento mató a tres: el factor que premiaba acciones siempre exitosas hizo que un agente con hambre crítica siguiera trabajando, y otra murió preguntando 14 veces por pan sin moverse. Se corrigió: el éxito propio sólo penaliza, hay límite de preguntas y una necesidad crítica multiplica por 3 las acciones que la atienden.
- **Automodelo**: calibración entre 0.84 y 0.89 en los diez agentes; **ventaja frente al modelo poblacional entre −0.01 y −0.03 en todos**. Un observador que sólo conoce la tasa de éxito de cada acción en la población predice el éxito del agente ligeramente mejor que el propio agente con su memoria. Interpretación: la memoria propia es una muestra pequeña y sesgada por el olvido; el criterio 1 ("el automodelo predice mejor que un modelo externo") **no se cumple** en 0.2.

## 2. Experimento de memoria (15 días, 4 variantes, 3 semillas)

Tamaños de efecto (d de Cohen) entre `completa` y `ausente`:

| Métrica | ausente | completa | d |
|---|---|---|---|
| Intercambios de información | 19.4 | 2.0 | −1.57 |
| Entropía de decisiones | 2.87 | 2.66 | −1.59 |
| Elecciones distintas | 34.7 | 26.5 | −1.59 |
| Confianza media en otros | 0.63 | 0.69 | +1.59 |
| Familiaridad media | 0.53 | 0.67 | +1.49 |
| Calibración del automodelo | 0.77 | 0.86 | +1.92 |
| Ventaja del automodelo | −0.155 | −0.032 | +1.96 |

Observación: sin memoria, los agentes preguntan diez veces más, deciden con más dispersión (menos hábito), forman vínculos más débiles y se predicen peor. Con memoria, aparece rutina.

Lo que **no** cambió: consistencia conductual entre mitades de la vida (0.97-0.98 en todas), estabilidad de preferencias, fracasos de compra (0 en todas: el mundo por defecto es benigno) y supervivencia. La versión 0.1 de este experimento salió nula porque medía justo estas últimas métricas; el análisis de tamaños de efecto sobre todas las métricas (`--effects completa:ausente`) fue lo que reveló dónde actúa la memoria.

## 3. Experimento de transferencia (corte al día 10, horizonte 5 días, 3 semillas, agente a01)

Orden del ICI frente a la continuación sin intervención, estable entre 0.1 y 0.2:

| Condición | ICI (0.2, tipos de acción) |
|---|---|
| completa | 1.000 |
| memoria borrada 50 % | 0.801 |
| parcial (memoria + conocimientos + preferencias) | 0.757 |
| sólo memoria | 0.702 |
| sólo conocimientos | 0.628 |
| sólo personalidad | 0.611 |
| ninguna | 0.591 |

Observación: la memoria es el componente con más peso en la continuidad medida; personalidad o conocimientos por sí solos no distinguen al agente de una mente nueva en el mismo cuerpo. La dimensión "decisiones" medida por tipos de acción dio ≈0.98 en todas las condiciones: el tipo de acción lo impone el mundo. Se cambió a comparar **elecciones concretas** (con quién, a dónde, qué); resultados con esa medida en la sección 4.

## 4. Transferencia con la dimensión de decisiones por elecciones concretas

| Condición | ICI vs referencia | ICI vs previo | memoria | preferencias | relaciones | decisiones | autorrepresentación |
|---|---|---|---|---|---|---|---|
| completa | 1.000 | 0.834 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| memoria borrada 50 % | 0.787 | 0.784 | 0.512 | 0.943 | 0.938 | 0.875 | 0.798 |
| parcial | 0.746 | 0.778 | 0.627 | 0.928 | 0.790 | 0.894 | 0.509 |
| sólo memoria | 0.691 | 0.741 | 0.632 | 0.890 | 0.788 | 0.888 | 0.495 |
| sólo conocimientos | 0.608 | 0.624 | 0.281 | 0.808 | 0.770 | 0.823 | 0.543 |
| sólo personalidad | 0.598 | 0.610 | 0.220 | 0.809 | 0.775 | 0.880 | 0.567 |
| ninguna | 0.578 | 0.601 | 0.235 | 0.857 | 0.795 | 0.863 | 0.520 |

Observaciones:

- Medida por elecciones concretas, la dimensión de decisiones baja de ≈0.98 a 0.82-0.89 y empieza a distinguir condiciones: la memoria transferida conserva mejor las elecciones (0.888) que los conocimientos solos (0.823). Sigue alta en todas porque cinco días en un pueblo de 12 lugares dejan poco margen de elección.
- Borrar la mitad de la memoria daña menos que trasplantar la memoria completa a una mente nueva (0.787 frente a 0.691): las relaciones propias, las preferencias y la identidad, que se pierden en el trasplante, pesan más de lo que la memoria por sí sola recupera.
- La autorrepresentación es la dimensión más frágil (≈0.5 en todas las transferencias parciales) y la más ruidosa (sd hasta 0.14): las etiquetas de identidad se recalculan a diario a partir de contadores que la mente nueva empieza de cero.
- Frente al agente previo al corte, incluso la continuación sin intervención cae a 0.834: cinco días de vida cambian al agente casi tanto como una transferencia parcial. Cualquier medida de continuidad debe compararse con esa deriva natural, no con la identidad perfecta.

## 6. Automodelo en contexto y ventaja emparejada (30 días, dos mundos)

Se sustituyó la tasa de éxito simple por una tabla de contexto (acción, objetivo, franja del día, hambre, energía) con retroceso jerárquico, y se dio al modelo externo la misma tabla con datos de toda la población. Además se añadió la **ventaja emparejada**: sólo en las predicciones donde el agente ya tenía evidencia suficiente en el contexto más específico, para descontar la ventaja que el modelo poblacional obtiene por ver diez veces más datos.

| Mundo | Calibración media | Ventaja | Ventaja emparejada | Agentes con ventaja > 0 |
|---|---|---|---|---|
| village_small | 0.856 | −0.029 | −0.031 | 0 de 10 |
| town | 0.850 | −0.026 | −0.032 | 0 de 10 |

Observación: incluso en igualdad de especificidad, la historia individual no aporta información predictiva por encima de la población. Interpretación: en el motor por reglas, el éxito de una acción depende del mundo (stock, horarios, aceptación ajena) y apenas de rasgos individuales; por tanto no hay información "propia" que un automodelo pueda capturar. El criterio 1 sigue sin cumplirse, y ahora sabemos que no es por falta de contexto en el modelo, sino porque el mundo no diferencia a los individuos en sus resultados. Para que el automodelo tenga algo propio que aprender, las consecuencias deben depender de la persona: habilidad, reputación y relaciones tienen que cambiar la probabilidad de éxito.

## 7. Transferencia en el pueblo grande (`town`, 3 semillas)

| Condición | ICI vs referencia (town) | ICI vs referencia (village_small) | decisiones (town) |
|---|---|---|---|
| completa | 1.000 | 1.000 | 1.000 |
| memoria borrada 50 % | 0.772 | 0.787 | 0.843 |
| parcial | 0.737 | 0.746 | 0.811 |
| sólo memoria | 0.688 | 0.691 | 0.808 |
| sólo conocimientos | 0.574 | 0.608 | 0.766 |
| sólo personalidad | 0.574 | 0.598 | 0.813 |
| ninguna | 0.537 | 0.578 | 0.754 |

Observación: con alternativas reales (dos mercados, tres trabajos), una mente nueva en el mismo cuerpo se aleja más de la original (0.537 frente a 0.578) y la dimensión de decisiones discrimina más (0.75-0.84). El orden de las condiciones se mantiene en los dos mundos, lo que sugiere que el instrumento es estable. La deriva natural en cinco días sigue en 0.834.

## 8. Consecuencias dependientes del individuo y ventaja por evidencia

Se hizo que trabajar y estudiar puedan fallar según habilidad, energía y apertura, y que la aceptación de una conversación dependa de la confianza, la reputación y la afinidad de personalidad. Los 10 agentes sobreviven en ambos mundos. La ventaja emparejada media siguió negativa (−0.028 y −0.03), así que se reanalizaron los eventos por **cantidad de evidencia propia** en el contexto exacto (`python -m vida selfmodel --run <id>`):

| Intentos propios | n (village) | ventaja | n (town) | ventaja |
|---|---|---|---|---|
| 0-2 | 2667 | −0.021 | 2953 | −0.020 |
| 3-5 | 1287 | −0.051 | 1365 | −0.052 |
| 6-10 | 1219 | −0.033 | 1078 | −0.033 |
| 11-20 | 1186 | −0.015 | 918 | −0.014 |
| 21-50 | 840 | −0.004 | 845 | −0.002 |
| 51+ | 1 | — | 41 | **+0.033** |

Por acción, con al menos 6 intentos propios:

| Acción | ventaja (village) | ventaja (town) |
|---|---|---|
| conversar | **+0.027** | **+0.020** |
| trabajar | −0.008 | +0.010 |
| descansar, comer, comprar, moverse | −0.03 a −0.045 | −0.03 a −0.044 |

Observaciones:

- La desventaja media es un efecto de muestra: con pocos intentos el estimador propio es ruidoso y el poblacional no. Al crecer la evidencia la diferencia converge a cero y, con más de 50 intentos, se vuelve positiva.
- En **conversar**, la única acción cuyo resultado depende de la relación entre dos individuos concretos, la historia propia predice mejor que la población con el mismo contexto. En las acciones deterministas la población gana porque aprende antes que "siempre sale bien".
- Interpretación: el criterio 1 se cumple **de forma estrecha y localizada**: existe información individual predictiva exactamente donde el mundo la genera (relaciones), y en ningún otro sitio. No es evidencia de autorrepresentación; es la demostración de que el instrumento detecta señal individual cuando la hay.
- Métrica nueva por agente: `self_model_advantage_social` (ventaja emparejada restringida a conversar).

## 5. Lo que estos resultados dicen sobre los objetivos

- **Objetivo 2 (identidad y continuidad)**: en este mundo, "quién es" el agente vive sobre todo en su memoria y sus relaciones; la personalidad fija pesa poco porque las reglas de decisión la usan débilmente. Un mundo con más opciones y menos rutina forzada haría más visibles las diferencias.
- **Objetivo 3 (cambio de soporte)**: el experimento de transferencia ya es reproducible y ordena las condiciones de forma estable. Es el instrumento; los números aún describen un mundo pequeño.
- **Objetivo 1 (consciencia)**: el primer criterio operativo (automodelo con ventaja predictiva) se midió con y sin contexto, y con comparación emparejada: negativo en todos los casos. Con consecuencias dependientes del individuo y análisis por evidencia (sección 8), la ventaja aparece sólo en conversar y con mucha experiencia: el instrumento detecta señal individual donde el mundo la genera. Siguiente paso: vidas más largas (VIDA-1.0) para acumular evidencia, y un automodelo que use también rasgos propios (habilidad, reputación) en lugar de sólo conteos.
