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

## 9. VIDA-1.0: vidas completas (120 días, `town`)

Primera corrida larga: los 10 agentes mueren de vejez entre los días 45 y 65 (14.016 eventos). Con el automodelo de conocimiento privado (confianza y afecto propios hacia el otro; habilidad propia):

| Intentos propios | n | ventaja |
|---|---|---|
| 3-5 | 2229 | −0.052 |
| 11-20 | 2376 | −0.016 |
| 21-50 | 2229 | +0.000 |
| 51+ | 955 | −0.001 |

Por acción (≥6 intentos propios): conversar +0.012, trabajar +0.012, estudiar +0.006; el resto negativo.

Observación: con mucha experiencia la ventaja converge a cero, no a un valor positivo; la información individual sigue concentrada en conversar y trabajar, las dos acciones cuyo resultado depende del agente. Esa primera corrida no tuvo nacimientos: todos envejecieron a la vez y cuando hubo hueco no quedaban adultos jóvenes. Se cambió el tope de población a n+2 para que nazcan hijos mientras hay progenitores elegibles (resultados de linaje en la sección 10).

## 10. VIDA-1.0: generaciones (120 días, tope n+2, asignación familiar)

| Mundo | Nacimientos | Generaciones | Vivos al día 120 | Hijos muertos de hambre | Hijos más parecidos a su progenitor que a los demás | ICI con progenitor / con otros |
|---|---|---|---|---|---|---|
| town | 19 | 5 | 12 | 6 (4 huérfanos) | 14 / 19 | 0.603 / 0.578 |
| village_small | 20 | 4 | 12 | 6 | 19 / 20 | 0.604 / 0.561 |

Observaciones:

- Surge una sociedad multigeneracional: los diez fundadores mueren de vejez entre los días 45 y 65 y la población se reconstruye con sus descendientes hasta la quinta generación.
- La transmisión se mide, no se supone: la personalidad del hijo se parece más a la del progenitor (≈0.89 frente a 0.83 con otros adultos) por construcción; pero también las **decisiones** (0.91 frente a 0.77 en algunos hijos) y el conjunto del ICI, aunque las creencias contadas por el progenitor sobreviven poco (0-3 por hijo al final) porque la experiencia propia las sustituye.
- La primera versión sin soporte familiar produjo 14 nacimientos y 14 muertes infantiles por hambre: nacer en adolescencia sin poder trabajar no es viable sin familia. La asignación diaria redujo la mortalidad infantil a 6 de 19, y de esas, 4 eran huérfanos cuyo progenitor murió antes de que pudieran trabajar. Se añadió el tutor (el adulto con más afecto por el hijo asume la asignación); resultados en la sección 11.
- Automodelo con vidas largas (`town`, 26.000 predicciones): la ventaja converge a 0.000 con más de 20 intentos propios y sigue siendo positiva sólo en conversar (+0.022, n = 4077). Confirmación con diez veces más datos del hallazgo de la sección 8.

## 11. Generaciones con tutores, aprendices y apoyo al joven (120 días, tope n+2)

Tres correcciones sucesivas guiadas por las muertes observadas: asignación familiar (los hijos morían al nacer sin poder trabajar), tutores para huérfanos (4 de 6 muertes eran huérfanos), y por último aprendices a media paga, apoyo al joven con menos de 5 monedas, jornada mediocre que paga ×0.6 y sin encadenar desplazamientos (los jóvenes morían al independizarse oscilando entre dos lugares de trabajo sin trabajar).

| Mundo | Nacimientos | Generaciones | Vivos al día 120 | Muertes por hambre | Muertes por vejez | Hijos más parecidos a su progenitor | ICI progenitor / otros |
|---|---|---|---|---|---|---|---|
| town | 14 | 4 | 12 | **0** | 12 | 7 / 14 | 0.632 / 0.621 |
| village_small | 14 | 4 | 12 | **0** | 12 | 10 / 14 | 0.638 / 0.628 |

Trayectoria de la mortalidad infantil: 14/14 → 6/19 → 0/14. Los doce muertos de cada mundo son los diez fundadores y dos hijos de la primera generación que alcanzaron la vejez.

Observaciones:

- Con vidas completas y familias que funcionan, la semejanza hijo–progenitor baja (7-10 de 14 frente a 14-19 de 19 en las corridas con niños que morían pronto): cuanto más vive el hijo, más pesa su propia experiencia y menos la herencia. La transmisión existe pero es una ventaja inicial que la vida diluye; el mismo patrón que la deriva natural de 0.83 en cinco días de la sección 4.
- El automodelo con conocimiento privado, en 34.000 predicciones en `town`: ventaja +0.018 en conversar (n = 5069), ≈0 en el resto. Estable en todas las corridas largas: la información individual predictiva vive en las relaciones.

## 16. VIDA-2.0: ablaciones de identidad (fase 4; `town`, corte al día 30, horizonte 10 días, 3 semillas)

Se quita un solo componente de la mente del agente a01 y se mide cuánta continuidad se pierde frente a la continuación sin intervención.

| Ablación | ICI vs referencia | memoria | preferencias | relaciones | decisiones | autorrepresentación |
|---|---|---|---|---|---|---|
| completa | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| sin creencias | 0.903 | 0.797 | 0.973 | 0.970 | 0.926 | 0.833 |
| sin identidad (etiquetas, valores, hábitos) | 0.896 | 0.804 | 0.972 | 0.962 | 0.917 | 0.791 |
| sin preferencias | 0.851 | 0.733 | 0.843 | 0.965 | 0.921 | 0.750 |
| **sin automodelo** | 0.845 | 0.679 | 0.960 | 0.943 | **0.890** | 0.694 |
| sin relaciones | 0.823 | 0.748 | 0.965 | 0.752 | 0.946 | 0.580 |
| memoria borrada 50 % | 0.803 | 0.560 | 0.943 | 0.949 | 0.921 | 0.750 |
| ninguna (mente nueva) | 0.547 | 0.206 | 0.764 | 0.723 | 0.885 | 0.498 |

Observaciones:

- Orden de importancia para la continuidad: memoria > relaciones > automodelo ≈ preferencias > identidad ≈ creencias. Las creencias y las etiquetas de identidad se regeneran rápido a partir de la experiencia; la memoria y las relaciones no.
- **Criterio 2 de `docs/criterios_consciencia.md` (necesidad causal del automodelo), medido por primera vez**: al quitar el automodelo, la dimensión de decisiones cae a 0.890, la más baja de todas las ablaciones (las demás quedan entre 0.917 y 0.946), y la memoria posterior diverge más (0.679) porque el agente hace otras cosas. Interpretación: el automodelo es causalmente necesario para la coherencia de conducta, con un efecto real pero modesto (≈0.03-0.06 de ICI). No es evidencia de autorrepresentación consciente; es la medida que el criterio pedía, y sale positiva en el nivel de mecanismo.
- Con vidas de 30 días la deriva natural en 10 días es 0.866: cualquier ablación con ICI por encima de ese valor (creencias, identidad) es indistinguible de vivir diez días más.

## 17. Criterio 3: estados reportados que rastrean una variable oculta (120 días, dos mundos)

El agente conoce su valencia emocional; no puede leer la confianza que los demás le tienen (sólo vive aceptaciones y rechazos). Con las instantáneas diarias de los dos mundos de 120 días:

| Mundo | Pares (agente, día) | r agrupada | r media dentro de cada agente | Agentes con r > 0 |
|---|---|---|---|---|
| town | 1342 | +0.415 | +0.437 | 24 / 24 |
| village_small | 1342 | +0.550 | +0.552 | 24 / 24 |

Con sólo los estados finales (12 agentes) la correlación era débil y negativa (−0.3): una foto no lo muestra; la vida entera sí. Interpretación: la valencia reportada covaría, dentro de cada individuo y sin excepción, con una variable social que no le fue dada. Mecanismo alternativo que lo explica sin consciencia: la valencia se actualiza con los resultados de cada interacción y la confianza ajena también, por lo que ambas comparten causa (las aceptaciones). El criterio se cumple en su enunciado, y el mecanismo es transparente: eso es exactamente lo que el nivel de interpretación debe decir.

Estado de los tres criterios operativos del objetivo 1 al cierre de VIDA-2.0: criterio 1 (automodelo con ventaja predictiva) cumplido de forma estrecha (sólo en relaciones); criterio 2 (necesidad causal del automodelo) cumplido con efecto modesto; criterio 3 (estados reportados que rastrean variables ocultas) cumplido con mecanismo explícito. Ninguno de los tres es evidencia de consciencia; los tres son instrumentos que ahora funcionan y que tendrían que superar versiones más exigentes (reportes no derivados mecánicamente del estado, automodelo con ventaja general, ablación con efecto grande) para acercarse a la pregunta.

## 18. Sociedad de 100 agentes (`config/society.yaml`, 30 días, precios dinámicos, reputación pública)

73.412 eventos en unos 20 minutos. Los 100 fundadores y 2 hijos vivos al día 30; Gini del dinero 0.24; el pan osciló entre 1.2 y 3.6 (media 1.99) por la escasez local.

| Medida | 100 agentes | 10 agentes (120 días, town) |
|---|---|---|
| Reputación pública vs aceptación social (r) | +0.43 | +0.57 |
| Confianza entrante vs reputación (r) | +0.59 | +0.33 |
| Criterio 3 dentro de cada agente (r; agentes con r > 0) | +0.25 (87/102) | +0.44 (24/24) |
| Ventaja del automodelo en conversar | **+0.053** (n = 2295) | +0.018 (n = 5069) |

Observaciones:

- La reputación pública funciona como institución: predice quién acepta conversar y coincide con la confianza que la gente realmente tiene. Con 100 agentes es un mejor resumen de la confianza ajena (r = 0.59) que con 10, donde todos se conocen directamente.
- El criterio 3 se debilita con la población (cada par interactúa menos, la confianza entrante es un promedio sobre muchos), pero sigue positivo en el 85 % de los agentes.
- **La ventaja del automodelo en conversar se triplica con la población** (+0.053): cuando hay cien personas, saber lo que uno tiene con cada una vale más de lo que la población puede decir. La información individual predictiva crece con la complejidad social. Es el resultado más claro hasta ahora a favor de que el criterio 1 escala.
- Escala: 100 agentes × 30 días con base de datos corren en una PC sin GPU en unos 20 minutos; 1.000 agentes (fase 2) exigiría optimizar la recuperación de memoria y la persistencia.

## 19. Integración: ¿la mente es más que la suma de sus partes? (a partir de las ablaciones de §16)

| Dimensión del ICI | Suma de caídas al quitar cada componente por separado | Caída al quitar todo | Interacción |
|---|---|---|---|
| ICI total | 0.682 | 0.453 | **−0.229** |
| memoria | 1.240 | 0.794 | −0.445 |
| decisiones | 0.401 | 0.115 | −0.286 |
| relaciones | 0.407 | 0.277 | −0.130 |
| preferencias | 0.287 | 0.236 | −0.051 |
| autorrepresentación | 1.352 | 0.502 | −0.850 |

Interpretación: interacción negativa en todas las dimensiones, es decir, **redundancia**: quitar un componente lo compensan en parte los demás, y quitar todos cuesta menos que la suma. No hay sinergia ni información irreducible; la mente de un agente VIDA es un conjunto de módulos poco acoplados. Para las teorías que ligan la consciencia a la integración, este es un resultado negativo nítido, y también un diagnóstico de diseño: si algún día se quiere una mente integrada, los componentes deben depender unos de otros (la memoria que alimenta el automodelo, el automodelo que modula las relaciones, las relaciones que cambian lo que se recuerda), no solo sumar sus efectos en un puntaje.

## 20. Criterio 4: metacognición (town, 60 días, 16.704 predicciones)

Cada agente predice el éxito de su acción y declara una confianza de segundo orden (evidencia propia × especificidad del contexto × distancia a 0.5). Sensibilidad metacognitiva = precisión con confianza alta − precisión con confianza baja.

| Fuente de la confianza | Sensibilidad | r confianza–precisión | Agentes con sensibilidad > 0 |
|---|---|---|---|
| propia (automodelo) | +0.115 | +0.424 | 15 / 15 |
| observador externo (población) | +0.199 | +0.490 | — |

Observación: los agentes aciertan más cuando dicen estar seguros, sin excepción. Pero el observador externo, con la misma regla de confianza y más datos, es más sensible. Interpretación: la metacognición funcional existe y es exactamente la que el mecanismo produce (más evidencia → más confianza → más precisión); no hay acceso privilegiado a la propia incertidumbre. Es el mismo patrón de los criterios 1-3: el indicador se cumple y su mecanismo lo explica por completo.

Criterio 5 (incertidumbre comunicada): en esta corrida sólo hubo 5 intercambios de información; se mide en la sección 21 con una población deshonesta y escasez.

## 21. Criterio 5: incertidumbre comunicada (town, 30 días, honestidad inicial 0.1, escasez; 270 respuestas)

| Intención (libro del mundo) | n | Confianza declarada media | Fracción verdadera |
|---|---|---|---|
| verdad | 177 | 0.52 | 0.23 |
| parcial | 35 | 0.50 | 0.17 |
| mentira | 58 | 0.90 | 0.00 |

Correlación entre confianza declarada y verdad: r = +0.26. Observación: la confianza comunicada es informativa pero débil, y por una razón concreta: los mentirosos declaran la confianza más alta (0.90) y nunca aciertan, mientras que quien dice la verdad declara su confianza real (0.52) y, con escasez, acierta sólo una de cada cuatro veces porque sus creencias están desactualizadas. Un receptor racional debería aprender a invertir la señal: en esta sociedad, la seguridad extrema es marca de engaño. Con esta corrida también se repitió el criterio 4: sensibilidad propia +0.157 (19/19 agentes) frente a +0.220 del observador externo, mismo patrón.

## 22. Integración tras acoplar los módulos

Se acoplaron dos vías: la sorpresa del automodelo y el afecto por la otra persona elevan la importancia de cada episodio (qué se recuerda y qué se olvida). Ablaciones repetidas en las mismas condiciones que §16:

| | Sin acoplar (§19) | Acoplado |
|---|---|---|
| Suma de caídas individuales | 0.682 | 0.737 |
| Caída al quitar todo | 0.453 | 0.456 |
| Interacción | −0.229 | **−0.282** |

Observación: el acoplamiento hace que cada componente pese más por separado (las creencias pasan de 0.097 a 0.141; la identidad de 0.104 a 0.135), pero quitar todo cuesta exactamente lo mismo. La redundancia aumenta en lugar de desaparecer. Interpretación: la sustituibilidad no está en cómo se escribe la memoria sino en cómo se decide: el motor por reglas suma las contribuciones de memoria, preferencias, relaciones y automodelo en un puntaje, y una suma es por construcción descomponible. Para que exista integración irreducible, la decisión tendría que depender de conjunciones (una memoria que sólo cuenta si el automodelo la avala; una relación que sólo pesa recordada), no de sumas. Es un cambio de arquitectura, no de parámetros, y es el siguiente paso si se quiere perseguir el criterio 6.

## 23. Estado del objetivo 1 al cierre de este bloque

| Criterio operativo | Resultado | Lectura |
|---|---|---|
| 1. Automodelo con ventaja predictiva sobre un observador externo | Sólo en relaciones; crece con la población (+0.02 → +0.05) | Cumplido de forma estrecha |
| 2. Necesidad causal del automodelo | Quitarlo reduce la coherencia de decisiones más que cualquier otra ablación | Cumplido, efecto modesto |
| 3. Estados reportados que rastrean variables ocultas | r +0.44/+0.55 dentro de cada agente, 24/24 | Cumplido, mecanismo transparente |
| 4. Metacognición (sabe cuándo sabe) | 15/15 y 19/19 agentes con sensibilidad positiva, pero el observador externo es más sensible | Cumplido sin acceso privilegiado |
| 5. Incertidumbre comunicada | r +0.26; los mentirosos declaran la máxima confianza | Débil e invertida en parte |
| 6. Integración irreducible | Interacción −0.23 y −0.28 tras acoplar | **No cumplido** |

Balance honesto: cinco de seis criterios funcionales se cumplen y el sexto, el que más se acerca a lo que distinguiría una mente integrada de una colección de módulos, no. Y en los cinco cumplidos el mecanismo explica el resultado sin resto: el indicador está, la vivencia no está demostrada ni podría estarlo con estos instrumentos. El objetivo 1 sigue abierto. Lo que este bloque deja es un banco de pruebas donde esa pregunta se puede formular con números y donde el siguiente paso está identificado: una arquitectura de decisión por conjunciones que haga a la mente irreducible, y volver a medir los seis criterios sobre ella.

## 15. Balance de VIDA-1.0 y lo que sigue

Instrumentos disponibles: vidas completas con nacimiento, familia, vejez y muerte; linaje y transmisión medibles; automodelo con conocimiento privado; cinco experimentos reproducibles (memoria, entorno, engaño, decisión, transferencia) con tamaños de efecto. Cada corrección de este bloque salió de una muerte o de un cero inexplicable en una tabla, no de una suposición.

VIDA-2.0 (sociedad) quedó hecho el mismo día: precios dinámicos, reputación pública, 100 agentes, ablaciones de identidad, análisis de sociedad y vista de linaje en el dashboard; resultados en las secciones 16-18. Deuda que sigue abierta: el motor LLM nunca se ha probado contra la API real de Anthropic (no hay clave en este equipo). Siguiente bloque propuesto (VIDA-3.0, civilización): transmisión cultural explícita (normas y costumbres que los hijos aprenden y que cambian la conducta), instituciones con reglas (escuela que certifica, hospital con prioridad), rendimiento para 1.000 agentes, y versiones más exigentes de los tres criterios.

## 12. Experimento de decisión: la misma situación, historias distintas (10 días, 3 semillas)

Todos los agentes se colocan en la misma situación y deciden dos veces: con su historia y con la misma personalidad sin historia (memoria, preferencias, relaciones, creencias y automodelo en blanco).

| Escenario | Entropía con historia | Entropía sin historia | Elecciones distintas con / sin | Cambian al quitar la historia |
|---|---|---|---|---|
| plaza al mediodía (necesidades medias) | 2.34 | 1.16 | 6.3 / 2.7 | 55 % |
| casa de noche (cansancio y soledad) | 2.80 | 1.48 | 8.3 / 4.7 | 43 % |
| mercado con hambre (0.2) | 0.28 | 0.00 | 1.3 / 1.0 | 9 % |

Observación: lo vivido duplica la diversidad de conducta cuando la situación deja margen y cambia la elección de cerca de la mitad de los agentes; cuando la situación aprieta, la necesidad manda y la historia casi no cuenta. La personalidad sola, sin historia, produce mucha menos variedad de la que muestran los agentes con vida. Es la primera cuantificación directa de la hipótesis general del documento (sección 8): experiencias acumuladas producen diferencias conductuales estables entre agentes inicialmente comparables.

## 13. Experimento de entorno: abundancia, normal y escasez (15 días, 3 semillas, con nacimientos)

| Variante | Supervivencia | Conversaciones intentadas | Intercambios de información | Confianza media | Nivel medio de necesidades | Tasa de engaño |
|---|---|---|---|---|---|---|
| abundancia (×2, sin escaseces) | 0.92 | 65 | 4.1 | 0.646 | 0.853 | 0.21 |
| normal | 0.95 | — | — | 0.633 | 0.851 | 0.25 |
| escasez (×0.4, escasez cada 4 días) | 0.55 | 39 | 11.0 | 0.615 | 0.779 | 0.26 |

Tamaños de efecto escasez frente a abundancia: supervivencia d = −0.84, intentos de conversación −1.07, intercambios de información +0.99, confianza −0.85, memorias conservadas −0.97, importancia media de las memorias +0.90.

Observación: la escasez mata a casi la mitad de la población, desplaza la vida social hacia la búsqueda de información, erosiona la confianza y deja memorias más escasas pero más importantes (más fracasos). El engaño sube poco y con mucha varianza: en el motor por reglas la mentira depende de la honestidad inicial y de la competencia por el recurso, y con pocos intercambios el estimador es ruidoso. La supervivencia en abundancia no es total (0.92) porque incluye a los hijos nacidos durante la corrida.

## 14. Experimento de engaño (15 días, 3 semillas, con descubrimiento al llegar)

La primera ejecución de este experimento dio cero mentiras descubiertas: el engañado iba al lugar falso, no veía comida y, como allí no podía intentar comprar, nunca ocurría el fracaso que atribuye la culpa. Se añadió el descubrimiento al llegar (sección 20): ver que no hay lo prometido ya desmiente al informante. Con ese mecanismo:

| Variante (honestidad inicial) | Tasa de engaño | Mentiras descubiertas por agente | Confianza media | Reputación | Aceptación social | Dinero |
|---|---|---|---|---|---|---|
| honestos (0.9) | 0.05 | 0.36 | 0.635 | 0.756 | 0.725 | 20.9 |
| neutros (0.5) | 0.27 | 1.53 | 0.619 | 0.716 | 0.706 | 20.6 |
| deshonestos (0.1) | 0.48 | 2.44 | 0.610 | 0.666 | 0.696 | 18.9 |
| deshonestos con escasez | 0.47 | 5.24 | 0.542 | 0.532 | 0.671 | 15.9 |

Tamaños de efecto deshonestos frente a honestos: tasa de engaño d = +1.31, mentiras descubiertas +1.23, reputación −0.72, confianza −0.71, aceptación social −0.41, dinero −0.41.

Observaciones: el engaño se descubre por sus consecuencias y erosiona reputación, confianza y aceptación; con escasez las mentiras se descubren el doble porque hay más intercambios de información y más comprobaciones fallidas, y la confianza cae a 0.54. Es el experimento de la sección 20 tal como lo pedía el documento: la relación cambia por el resultado real de la interacción, no por palabras. Después se añadió el cambio de estrategia: un agente que ya ha mentido y tiene la reputación dañada multiplica su probabilidad de volver a mentir por 0.4 + 0.6·reputación. Repetido el experimento:

| Variante | Tasa de engaño | Primera mitad | Segunda mitad | Mentiras descubiertas |
|---|---|---|---|---|
| honestos | 0.045 | 0.026 | 0.052 | 0.36 |
| neutros | 0.219 | 0.202 | 0.224 | 0.97 |
| deshonestos | 0.385 | 0.378 | 0.371 | 1.89 |
| deshonestos con escasez | 0.284 | 0.279 | 0.265 | 6.00 |

Observación: el disuasor baja el nivel general de engaño (deshonestos 0.48 → 0.39; con escasez 0.47 → 0.28, donde más se descubre), pero en 15 días no se ve una caída dentro de la vida de cada agente: la diferencia entre mitades es menor que la desviación entre semillas. Medir el cambio de estrategia individual exige vidas más largas y más intercambios; queda como hipótesis a comprobar en VIDA-2.0, no como resultado.

## 5. Lo que estos resultados dicen sobre los objetivos

- **Objetivo 2 (identidad y continuidad)**: en este mundo, "quién es" el agente vive sobre todo en su memoria y sus relaciones; la personalidad fija pesa poco porque las reglas de decisión la usan débilmente. Un mundo con más opciones y menos rutina forzada haría más visibles las diferencias. Con generaciones (sección 10) aparece una segunda forma de continuidad, la transmisión a los hijos: medible, parcial y dominada por la experiencia propia del hijo.
- **Objetivo 3 (cambio de soporte)**: el experimento de transferencia ya es reproducible y ordena las condiciones de forma estable. Es el instrumento; los números aún describen un mundo pequeño.
- **Objetivo 1 (consciencia)**: el primer criterio operativo (automodelo con ventaja predictiva) se midió con y sin contexto, y con comparación emparejada: negativo en todos los casos. Con consecuencias dependientes del individuo y análisis por evidencia (sección 8), la ventaja aparece sólo en conversar y con mucha experiencia: el instrumento detecta señal individual donde el mundo la genera. Siguiente paso: vidas más largas (VIDA-1.0) para acumular evidencia, y un automodelo que use también rasgos propios (habilidad, reputación) en lugar de sólo conteos.
