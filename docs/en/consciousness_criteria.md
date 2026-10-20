# Operational criteria for objective 1: can artificial consciousness exist?

English translation of `docs/criterios_consciencia.md` (Spanish original is canonical).

This document does not answer the question. It fixes which observations would count as evidence, at which level of interpretation, and which VIDA instruments produce them or should produce them. It follows the rule of section 22 of the design document: **VIDA will not declare that an agent is conscious because it says "I am conscious", "I am afraid" or "I do not want to die"**. Those sentences are behavioural data.

## Three levels that are never mixed (section 37)

| Level | Example | Who produces it |
|---|---|---|
| Observation | "Agent a06 lied 8 times out of 17 when asked for information" | The event log and the world's information ledger |
| Interpretation | "Its behaviour is consistent with a model of the other agents and of its own interest" | The metrics analysis, always with the alternative mechanism stated |
| Hypothesis | "A self-representation mechanism that modulates honesty might exist" | An experiment designed to falsify it |

None of the three demonstrates consciousness. The chain stops at the hypothesis about a mechanism.

## Behavioural indicators VIDA can measure today

| Indicator (section 22) | Measurable proxy in VIDA-0.1 | Instrument | Alternative mechanism that explains it without consciousness |
|---|---|---|---|
| Autobiographical continuity | Daily summaries coherent with the recorded events; stability of the action distribution between halves of the life | `memory/autobiographical.py`, metric `behavioural_consistency` | Deterministic templates over the objective log |
| Modelling of other agents | Honesty and helpfulness estimates that change with interaction outcomes | `beliefs.OtherAgentModel`, `honesty_estimate` | Counters updated by fixed rules |
| Sensitivity to consequences | Preferences and beliefs corrected after failures (`refute`) | metrics `belief_corrections`, `preference_stability` | Elementary reinforcement learning |
| Planning | Moves toward places that satisfy the most urgent need before it becomes critical | `move` events followed by `acquire`/`work` | Heuristic scoring of affordances |
| Strategic deception | More frequent lies when the resource is scarce and the relationship is weak | `deception` experiment, information ledger | Parametric probability in the rule-based engine |
| Behavioural continuity after changes | ICI between the agent before and after erasing or transferring components | `transfer` experiment | Similarity of states; does not imply experience |

## Indicators VIDA cannot measure yet

- **Self-reference and introspection.** They require the agent to produce descriptions of itself that are not templates. The LLM engine (`llm_v1`) generates first-person justifications, but they come from the language model, not from a mechanism of the agent; counting them as introspection would be the error section 36 warns about ("apparent behaviour may come from patterns of the model").
- **Representation of uncertainty.** Beliefs have numerical confidence, but the agent does not reason about its own uncertainty nor communicate it. A first step: make `partial` in informative replies depend on the real confidence of the belief and measure whether calibration improves with experience.
- **Metacognition.** There is no evaluation of the agent's own decisions. Proposed instrument: a reflective module (reflective memory from section 14) that compares prediction and outcome and records the error; measure whether agents with that module adjust their exploration.

## What would count as relevant evidence (and what would not)

The following would count in favour of a strong mechanistic hypothesis, without amounting to a demonstration of consciousness:

1. That an agent maintains a model of itself that predicts its own future behaviour better than an external model with the same information. **Measured** (§8-11): the advantage exists only in conversing (+0.02, stable over 34,000 predictions) and nowhere else.
2. That this self-model is causally necessary: when it is removed, behaviour measurably loses coherence (the self-representation ICI falls and with it behavioural consistency). **Measured on 22-09-2026** (`docs/resultados_0.2.md` §16): without the self-model the decisions dimension of the ICI falls to 0.890, the lowest of all single-component ablations; a real and modest effect.
3. That the agent reports internal states that correlate with variables it was not explicitly given. **Measured** (§17): emotional valence covaries within each agent with hidden incoming trust (r ≈ +0.44/+0.55, 24/24 agents); the mechanism (common cause: acceptances) is explicit.

4. **Metacognition (metacognitive sensitivity)**: that the agent is more accurate when it declares more confidence in its own prediction, and that this confidence is more informative about its accuracy than an external observer's. Instrument: `vida metacognition`. It is the standard indicator in consciousness science (Fleming and others), and the functional version of "knowing when one knows". **Measured** (§20): own sensitivity +0.115 in 15/15 agents, but the external observer reaches +0.199: functional metacognition without privileged access.
5. **Communicated uncertainty**: that the confidence declared when informing another tracks the truth of what is said. Instrument: `vida metacognition` (criterion 5). **Measured** (§21): r = +0.26 over 270 replies; liars declare the highest confidence, so the signal is weak and partly inverted.
6. **Integration**: that the information the mind as a whole has about the action is not reproduced by splitting it in two (behavioural Φ = information of the whole − information of the best bipartition, in bits). Information integration theories associate consciousness with irreducible information. Instrument: `vida integration`. **Measured** (`docs/resultados_0.2.md` §24): Φ = −0.010 and −0.013 bits in two seeds, 23 of 24 agents with Φ ≤ 0; separating memory and self-model from the rest loses nothing. The mind of a VIDA agent is reducible to its parts. (An earlier measure by ICI ablations, §19 and §22, was discarded: its sign does not distinguish independent modules from intertwined ones.)

The following would not count:

- First-person sentences generated by an LLM.
- High ICI similarity after a transfer: it is informational or behavioural continuity (section 21).
- Complex behaviour explainable by the engine's rules: it must always be compared against the rule-based explanation.

## Proposed route

1. VIDA-0.2 and 1.0: reflective memory and predictive self-model; metrics of calibration and of causal necessity of the self-model.
2. VIDA-4.0: identity experiments with selective removal of components (already possible with `transfer`, condition `memoria_borrada_50`; removal of the self-model is still missing until it exists).
3. Only afterwards: philosophical discussion informed by those measurements, with external collaboration (phase 8).
