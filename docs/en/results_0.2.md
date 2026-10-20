# VIDA-0.2 results (22 September 2026)

English translation of `docs/resultados_0.2.md` (Spanish original is canonical).

Record of what was observed with the 0.2 instruments: reflective memory, memory→decision coupling, predictive self-model and experiments with effect sizes. Everything at the level of **observation** or **interpretation**; no conclusion about consciousness.

Base configuration: `config/default.yaml`, rule-based engine, 10 agents, seeds 1-3. Raw results in `data/experiments/` (not versioned; reproducible from the manifest).

## 1. Acceptance run (30 days, seed 42)

- All 10 agents survive. A first version of the coupling killed three: the factor that rewarded always-successful actions made an agent with critical hunger keep working, and another died asking 14 times for bread without moving. It was corrected: own success only penalises, there is a limit on questions, and a critical need multiplies by 3 the actions that address it.
- **Self-model**: calibration between 0.84 and 0.89 in all ten agents; **advantage over the population model between −0.01 and −0.03 in all of them**. An observer that only knows the success rate of each action in the population predicts the agent's success slightly better than the agent itself with its memory. Interpretation: one's own memory is a small sample biased by forgetting; criterion 1 ("the self-model predicts better than an external model") **is not met** in 0.2.

## 2. Memory experiment (15 days, 4 variants, 3 seeds)

Effect sizes (Cohen's d) between `completa` (full) and `ausente` (absent):

| Metric | absent | full | d |
|---|---|---|---|
| Information exchanges | 19.4 | 2.0 | −1.57 |
| Decision entropy | 2.87 | 2.66 | −1.59 |
| Distinct choices | 34.7 | 26.5 | −1.59 |
| Mean trust in others | 0.63 | 0.69 | +1.59 |
| Mean familiarity | 0.53 | 0.67 | +1.49 |
| Self-model calibration | 0.77 | 0.86 | +1.92 |
| Self-model advantage | −0.155 | −0.032 | +1.96 |

Observation: without memory, agents ask ten times more, decide with more dispersion (less habit), form weaker bonds and predict themselves worse. With memory, routine appears.

What did **not** change: behavioural consistency between halves of the life (0.97-0.98 in all), preference stability, purchase failures (0 in all: the default world is benign) and survival. Version 0.1 of this experiment came out null because it measured precisely these latter metrics; the effect-size analysis over all metrics (`--effects completa:ausente`) was what revealed where memory acts.

## 3. Transfer experiment (cut at day 10, 5-day horizon, 3 seeds, agent a01)

ICI ordering against the continuation without intervention, stable between 0.1 and 0.2:

| Condition | ICI (0.2, action types) |
|---|---|
| full | 1.000 |
| memory erased 50 % | 0.801 |
| partial (memory + knowledge + preferences) | 0.757 |
| memory only | 0.702 |
| knowledge only | 0.628 |
| personality only | 0.611 |
| none | 0.591 |

Observation: memory is the component with the most weight in the measured continuity; personality or knowledge on their own do not distinguish the agent from a new mind in the same body. The "decisions" dimension measured by action types gave ≈0.98 in all conditions: the action type is imposed by the world. It was changed to compare **concrete choices** (with whom, where to, what); results with that measure in section 4.

## 4. Transfer with the decisions dimension by concrete choices

| Condition | ICI vs reference | ICI vs prior | memory | preferences | relationships | decisions | self-representation |
|---|---|---|---|---|---|---|---|
| full | 1.000 | 0.834 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| memory erased 50 % | 0.787 | 0.784 | 0.512 | 0.943 | 0.938 | 0.875 | 0.798 |
| partial | 0.746 | 0.778 | 0.627 | 0.928 | 0.790 | 0.894 | 0.509 |
| memory only | 0.691 | 0.741 | 0.632 | 0.890 | 0.788 | 0.888 | 0.495 |
| knowledge only | 0.608 | 0.624 | 0.281 | 0.808 | 0.770 | 0.823 | 0.543 |
| personality only | 0.598 | 0.610 | 0.220 | 0.809 | 0.775 | 0.880 | 0.567 |
| none | 0.578 | 0.601 | 0.235 | 0.857 | 0.795 | 0.863 | 0.520 |

Observations:

- Measured by concrete choices, the decisions dimension drops from ≈0.98 to 0.82-0.89 and begins to distinguish conditions: transferred memory preserves choices better (0.888) than knowledge alone (0.823). It remains high in all because five days in a town of 12 places leave little room for choice.
- Erasing half of the memory does less damage than transplanting the full memory into a new mind (0.787 versus 0.691): the agent's own relationships, preferences and identity, which are lost in the transplant, weigh more than memory alone recovers.
- Self-representation is the most fragile dimension (≈0.5 in all partial transfers) and the noisiest (sd up to 0.14): identity labels are recomputed daily from counters that the new mind starts from zero.
- Against the agent prior to the cut, even the continuation without intervention falls to 0.834: five days of life change the agent almost as much as a partial transfer. Any continuity measure must be compared with that natural drift, not with perfect identity.

## 6. Self-model in context and matched advantage (30 days, two worlds)

The simple success rate was replaced by a context table (action, target, time of day, hunger, energy) with hierarchical fallback, and the external model was given the same table with data from the whole population. In addition the **matched advantage** was added: only on the predictions where the agent already had sufficient evidence in the most specific context, to discount the advantage the population model obtains from seeing ten times more data.

| World | Mean calibration | Advantage | Matched advantage | Agents with advantage > 0 |
|---|---|---|---|---|
| village_small | 0.856 | −0.029 | −0.031 | 0 of 10 |
| town | 0.850 | −0.026 | −0.032 | 0 of 10 |

Observation: even at equal specificity, individual history contributes no predictive information beyond the population. Interpretation: in the rule-based engine, the success of an action depends on the world (stock, schedules, others' acceptance) and hardly on individual traits; therefore there is no "own" information that a self-model could capture. Criterion 1 is still not met, and we now know it is not for lack of context in the model, but because the world does not differentiate individuals in their outcomes. For the self-model to have something of its own to learn, consequences must depend on the person: skill, reputation and relationships have to change the probability of success.

## 7. Transfer in the large town (`town`, 3 seeds)

| Condition | ICI vs reference (town) | ICI vs reference (village_small) | decisions (town) |
|---|---|---|---|
| full | 1.000 | 1.000 | 1.000 |
| memory erased 50 % | 0.772 | 0.787 | 0.843 |
| partial | 0.737 | 0.746 | 0.811 |
| memory only | 0.688 | 0.691 | 0.808 |
| knowledge only | 0.574 | 0.608 | 0.766 |
| personality only | 0.574 | 0.598 | 0.813 |
| none | 0.537 | 0.578 | 0.754 |

Observation: with real alternatives (two markets, three jobs), a new mind in the same body moves further from the original (0.537 versus 0.578) and the decisions dimension discriminates more (0.75-0.84). The ordering of the conditions holds in both worlds, which suggests the instrument is stable. Natural drift over five days remains at 0.834.

## 8. Individual-dependent consequences and advantage by evidence

Working and studying were made able to fail depending on skill, energy and openness, and acceptance of a conversation was made to depend on trust, reputation and personality affinity. All 10 agents survive in both worlds. The mean matched advantage remained negative (−0.028 and −0.03), so the events were reanalysed by **amount of own evidence** in the exact context (`python -m vida selfmodel --run <id>`):

| Own attempts | n (village) | advantage | n (town) | advantage |
|---|---|---|---|---|
| 0-2 | 2667 | −0.021 | 2953 | −0.020 |
| 3-5 | 1287 | −0.051 | 1365 | −0.052 |
| 6-10 | 1219 | −0.033 | 1078 | −0.033 |
| 11-20 | 1186 | −0.015 | 918 | −0.014 |
| 21-50 | 840 | −0.004 | 845 | −0.002 |
| 51+ | 1 | — | 41 | **+0.033** |

By action, with at least 6 own attempts:

| Action | advantage (village) | advantage (town) |
|---|---|---|
| converse | **+0.027** | **+0.020** |
| work | −0.008 | +0.010 |
| rest, eat, buy, move | −0.03 to −0.045 | −0.03 to −0.044 |

Observations:

- The mean disadvantage is a sample effect: with few attempts the agent's own estimator is noisy and the population one is not. As evidence grows the difference converges to zero and, with more than 50 attempts, becomes positive.
- In **conversing**, the only action whose outcome depends on the relationship between two specific individuals, one's own history predicts better than the population with the same context. In deterministic actions the population wins because it learns sooner that "it always works".
- Interpretation: criterion 1 is met **in a narrow and localised way**: predictive individual information exists exactly where the world generates it (relationships), and nowhere else. It is not evidence of self-representation; it is the demonstration that the instrument detects individual signal when there is one.
- New per-agent metric: `self_model_advantage_social` (matched advantage restricted to conversing).

## 9. VIDA-1.0: full lives (120 days, `town`)

First long run: all 10 agents die of old age between days 45 and 65 (14,016 events). With the private-knowledge self-model (own trust and affection toward the other; own skill):

| Own attempts | n | advantage |
|---|---|---|
| 3-5 | 2229 | −0.052 |
| 11-20 | 2376 | −0.016 |
| 21-50 | 2229 | +0.000 |
| 51+ | 955 | −0.001 |

By action (≥6 own attempts): converse +0.012, work +0.012, study +0.006; the rest negative.

Observation: with a great deal of experience the advantage converges to zero, not to a positive value; individual information remains concentrated in conversing and working, the two actions whose outcome depends on the agent. That first run had no births: everyone aged at the same time and when there was room no young adults remained. The population cap was changed to n+2 so that children are born while eligible parents exist (lineage results in section 10).

## 10. VIDA-1.0: generations (120 days, cap n+2, family allowance)

| World | Births | Generations | Alive at day 120 | Children dead of hunger | Children more similar to their parent than to the others | ICI with parent / with others |
|---|---|---|---|---|---|---|
| town | 19 | 5 | 12 | 6 (4 orphans) | 14 / 19 | 0.603 / 0.578 |
| village_small | 20 | 4 | 12 | 6 | 19 / 20 | 0.604 / 0.561 |

Observations:

- A multigenerational society emerges: the ten founders die of old age between days 45 and 65 and the population rebuilds itself with their descendants up to the fifth generation.
- Transmission is measured, not assumed: the child's personality resembles the parent's more (≈0.89 versus 0.83 with other adults) by construction; but so do the **decisions** (0.91 versus 0.77 in some children) and the ICI as a whole, although the beliefs told by the parent survive little (0-3 per child at the end) because the child's own experience replaces them.
- The first version without family support produced 14 births and 14 child deaths from hunger: being born in adolescence without being able to work is not viable without a family. The daily allowance reduced child mortality to 6 of 19, and of those, 4 were orphans whose parent died before they could work. The guardian was added (the adult with the most affection for the child takes over the allowance); results in section 11.
- Self-model with long lives (`town`, 26,000 predictions): the advantage converges to 0.000 with more than 20 own attempts and remains positive only in conversing (+0.022, n = 4077). Confirmation, with ten times more data, of the finding of section 8.

## 11. Generations with guardians, apprentices and support for the young (120 days, cap n+2)

Three successive corrections guided by the observed deaths: family allowance (children died at birth without being able to work), guardians for orphans (4 of 6 deaths were orphans), and finally apprentices at half pay, support for the young with fewer than 5 coins, a mediocre workday that pays ×0.6 and no chaining of moves (the young died upon becoming independent, oscillating between two workplaces without working).

| World | Births | Generations | Alive at day 120 | Deaths from hunger | Deaths from old age | Children more similar to their parent | ICI parent / others |
|---|---|---|---|---|---|---|---|
| town | 14 | 4 | 12 | **0** | 12 | 7 / 14 | 0.632 / 0.621 |
| village_small | 14 | 4 | 12 | **0** | 12 | 10 / 14 | 0.638 / 0.628 |

Child mortality trajectory: 14/14 → 6/19 → 0/14. The twelve dead in each world are the ten founders and two first-generation children who reached old age.

Observations:

- With full lives and functioning families, child–parent similarity falls (7-10 of 14 versus 14-19 of 19 in the runs where children died early): the longer the child lives, the more its own experience weighs and the less inheritance does. Transmission exists but is an initial advantage that life dilutes; the same pattern as the natural drift of 0.83 in five days from section 4.
- The private-knowledge self-model, over 34,000 predictions in `town`: advantage +0.018 in conversing (n = 5069), ≈0 in the rest. Stable across all long runs: predictive individual information lives in relationships.

## 16. VIDA-2.0: identity ablations (phase 4; `town`, cut at day 30, 10-day horizon, 3 seeds)

A single component of agent a01's mind is removed and the continuity lost against the continuation without intervention is measured.

| Ablation | ICI vs reference | memory | preferences | relationships | decisions | self-representation |
|---|---|---|---|---|---|---|
| full | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| without beliefs | 0.903 | 0.797 | 0.973 | 0.970 | 0.926 | 0.833 |
| without identity (labels, values, habits) | 0.896 | 0.804 | 0.972 | 0.962 | 0.917 | 0.791 |
| without preferences | 0.851 | 0.733 | 0.843 | 0.965 | 0.921 | 0.750 |
| **without self-model** | 0.845 | 0.679 | 0.960 | 0.943 | **0.890** | 0.694 |
| without relationships | 0.823 | 0.748 | 0.965 | 0.752 | 0.946 | 0.580 |
| memory erased 50 % | 0.803 | 0.560 | 0.943 | 0.949 | 0.921 | 0.750 |
| none (new mind) | 0.547 | 0.206 | 0.764 | 0.723 | 0.885 | 0.498 |

Observations:

- Order of importance for continuity: memory > relationships > self-model ≈ preferences > identity ≈ beliefs. Beliefs and identity labels regenerate quickly from experience; memory and relationships do not.
- **Criterion 2 of `docs/criterios_consciencia.md` (causal necessity of the self-model), measured for the first time**: when the self-model is removed, the decisions dimension falls to 0.890, the lowest of all ablations (the others stay between 0.917 and 0.946), and the subsequent memory diverges more (0.679) because the agent does other things. Interpretation: the self-model is causally necessary for behavioural coherence, with a real but modest effect (≈0.03-0.06 of ICI). It is not evidence of conscious self-representation; it is the measurement the criterion asked for, and it comes out positive at the level of mechanism.
- With 30-day lives the natural drift over 10 days is 0.866: any ablation with ICI above that value (beliefs, identity) is indistinguishable from living ten more days.

## 17. Criterion 3: reported states that track a hidden variable (120 days, two worlds)

The agent knows its emotional valence; it cannot read the trust others have in it (it only experiences acceptances and rejections). With the daily snapshots of the two 120-day worlds:

| World | (agent, day) pairs | pooled r | mean within-agent r | Agents with r > 0 |
|---|---|---|---|---|
| town | 1342 | +0.415 | +0.437 | 24 / 24 |
| village_small | 1342 | +0.550 | +0.552 | 24 / 24 |

With only the final states (12 agents) the correlation was weak and negative (−0.3): a snapshot does not show it; the whole life does. Interpretation: the reported valence covaries, within each individual and without exception, with a social variable it was not given. Alternative mechanism that explains it without consciousness: valence is updated with the outcomes of each interaction and others' trust is too, so both share a cause (acceptances). The criterion is met as stated, and the mechanism is transparent: that is exactly what the interpretation level must say.

Status of the three operational criteria of objective 1 at the close of VIDA-2.0: criterion 1 (self-model with predictive advantage) met narrowly (only in relationships); criterion 2 (causal necessity of the self-model) met with a modest effect; criterion 3 (reported states that track hidden variables) met with an explicit mechanism. None of the three is evidence of consciousness; all three are instruments that now work and that would have to pass more demanding versions (reports not mechanically derived from the state, a self-model with general advantage, an ablation with a large effect) to approach the question.

## 18. Society of 100 agents (`config/society.yaml`, 30 days, dynamic prices, public reputation)

73,412 events in about 20 minutes. The 100 founders and 2 children alive at day 30; money Gini 0.24; bread oscillated between 1.2 and 3.6 (mean 1.99) due to local scarcity.

| Measure | 100 agents | 10 agents (120 days, town) |
|---|---|---|
| Public reputation vs social acceptance (r) | +0.43 | +0.57 |
| Incoming trust vs reputation (r) | +0.59 | +0.33 |
| Criterion 3 within each agent (r; agents with r > 0) | +0.25 (87/102) | +0.44 (24/24) |
| Self-model advantage in conversing | **+0.053** (n = 2295) | +0.018 (n = 5069) |

Observations:

- Public reputation works as an institution: it predicts who accepts a conversation and matches the trust people actually have. With 100 agents it is a better summary of others' trust (r = 0.59) than with 10, where everyone knows each other directly.
- Criterion 3 weakens with population (each pair interacts less, incoming trust is an average over many), but remains positive in 85 % of agents.
- **The self-model advantage in conversing triples with population** (+0.053): when there are a hundred people, knowing what one has with each of them is worth more than what the population can say. Predictive individual information grows with social complexity. It is the clearest result so far in favour of criterion 1 scaling.
- Scale: 100 agents × 30 days with a database run on a PC without GPU in about 20 minutes; 1,000 agents (phase 2) would require optimising memory retrieval and persistence.

## 19. Integration: is the mind more than the sum of its parts? (from the ablations of §16)

| ICI dimension | Sum of drops when removing each component separately | Drop when removing everything | Interaction |
|---|---|---|---|
| total ICI | 0.682 | 0.453 | **−0.229** |
| memory | 1.240 | 0.794 | −0.445 |
| decisions | 0.401 | 0.115 | −0.286 |
| relationships | 0.407 | 0.277 | −0.130 |
| preferences | 0.287 | 0.236 | −0.051 |
| self-representation | 1.352 | 0.502 | −0.850 |

Interpretation: negative interaction in all dimensions, that is, **redundancy**: removing one component is partly compensated by the others, and removing all of them costs less than the sum. There is no synergy or irreducible information; the mind of a VIDA agent is a set of loosely coupled modules. For theories that tie consciousness to integration, this is a clear negative result, and also a design diagnosis: if an integrated mind is ever wanted, the components must depend on one another (memory feeding the self-model, the self-model modulating relationships, relationships changing what is remembered), not merely add their effects into a score.

## 20. Criterion 4: metacognition (town, 60 days, 16,704 predictions)

Each agent predicts the success of its action and declares a second-order confidence (own evidence × context specificity × distance from 0.5). Metacognitive sensitivity = accuracy with high confidence − accuracy with low confidence.

| Source of confidence | Sensitivity | r confidence–accuracy | Agents with sensitivity > 0 |
|---|---|---|---|
| own (self-model) | +0.115 | +0.424 | 15 / 15 |
| external observer (population) | +0.199 | +0.490 | — |

Observation: agents are more accurate when they say they are sure, without exception. But the external observer, with the same confidence rule and more data, is more sensitive. Interpretation: functional metacognition exists and is exactly what the mechanism produces (more evidence → more confidence → more accuracy); there is no privileged access to one's own uncertainty. It is the same pattern as criteria 1-3: the indicator is met and its mechanism fully explains it.

Criterion 5 (communicated uncertainty): in this run there were only 5 information exchanges; it is measured in section 21 with a dishonest population and scarcity.

## 21. Criterion 5: communicated uncertainty (town, 30 days, initial honesty 0.1, scarcity; 270 replies)

| Intention (world ledger) | n | Mean declared confidence | Fraction true |
|---|---|---|---|
| truth | 177 | 0.52 | 0.23 |
| partial | 35 | 0.50 | 0.17 |
| lie | 58 | 0.90 | 0.00 |

Correlation between declared confidence and truth: r = +0.26. Observation: communicated confidence is informative but weak, and for a concrete reason: liars declare the highest confidence (0.90) and are never right, while those who tell the truth declare their real confidence (0.52) and, under scarcity, are right only one time in four because their beliefs are out of date. A rational receiver should learn to invert the signal: in this society, extreme certainty is a mark of deception. With this run criterion 4 was also repeated: own sensitivity +0.157 (19/19 agents) versus +0.220 for the external observer, same pattern.

## 22. Integration after coupling the modules

Two pathways were coupled: the self-model's surprise and the affection for the other person raise the importance of each episode (what is remembered and what is forgotten). Ablations repeated under the same conditions as §16:

| | Uncoupled (§19) | Coupled |
|---|---|---|
| Sum of individual drops | 0.682 | 0.737 |
| Drop when removing everything | 0.453 | 0.456 |
| Interaction | −0.229 | **−0.282** |

Observation: coupling makes each component weigh more on its own (beliefs go from 0.097 to 0.141; identity from 0.104 to 0.135), but removing everything costs exactly the same. Redundancy increases instead of disappearing.

Methodological correction (same date): this measure by ICI drops is not suitable for deciding irreducibility. With it, a decision that depended on a *conjunction* of two components would give negative interaction (removing either of the two destroys the conjunction; removing both destroys it only once), and a decision with *redundant pathways* would give positive interaction. In addition the ICI is bounded in [0,1] and saturates when much is removed. So the sign of the interaction does not distinguish independent modules from intertwined modules. The right question, taken from information integration theories, is a different one: how much information about the action does the set of components have that **no bipartition** of the mind preserves? That is the Φ proxy measured in §24.

## 24. Informational integration: Φ proxy (criterion 6, definitive measure of this block)

Instrument: `vida integration`. Each action records the state of six components of the mind at decision time (`EventRecord.mind`): body (hunger), retrieved memory (mean valence), self-model (recent error), relationships (mean affection toward those present), identity (ambition) and beliefs (confidence about where there is food). No variable depends on the chosen action: a first version used the self-model's prediction *for the chosen action* and gave 0.34 bits to the self-model; that was circular information and it was removed. Each variable is binarised by its median; the mutual information with the action is measured (bits, corrected by 20 permutations), for the whole and for the 31 bipartitions of the six components. Φ = information of the whole − information of the bipartition that loses the least (MIP). Town, 30 days, 12 agents, 8,424 decisions per seed.

| | Seed 1 | Seed 2 |
|---|---|---|
| Action entropy | 2.573 bits | 2.618 bits |
| Information of the whole | 0.176 bits (6.8 %) | 0.164 bits (6.3 %) |
| Per component: body / memory / self-model / relationships / identity / beliefs | 0.052 / 0.009 / 0.003 / 0.076 / 0.009 / 0.019 | 0.058 / 0.014 / 0.004 / 0.074 / 0.012 / 0.016 |
| Minimum information partition | memory+self-model \| rest → 0.186 | memory+self-model \| rest → 0.177 |
| **Behavioural Φ** | **−0.010 bits** | **−0.013 bits** |
| Synergy over the best isolated component | +0.100 bits | +0.091 bits |
| Agents with Φ > 0 (of 12) | 1 (+0.002) | 0 |

Reading:

- **Φ ≈ 0 in both seeds and in 23 of 24 agents.** Separating memory and self-model from the rest of the mind loses no information about the action: those two components, as summarised, contribute no conjunctions with the others. Behaviour is reducible to its parts. Criterion 6 **not met**, this time with the correct measure.
- There is moderate synergy (+0.09/+0.10 bits) over the best isolated component: the set body+relationships+identity+beliefs says more than any of them separately. That is what is expected of an additive score with `argmax`: the action depends on the combination, but the combination can be split without loss.
- The six binary summaries explain only 6-7 % of the action entropy. The rest lies in unrecorded variables (place, time, visible stock, money, type of most urgent need) and in random tie-breaking. It is a limitation of the measure, not a fact about the mind: with more variables the joint state grows exponentially and the counting estimator becomes unusable with 8,000 samples.
- What is informative: the self-model, measured without circularity, has 0.003 bits of information about the action. Its influence on the decision (`_expectation` only penalises, and exploration grows with error) is real but minimal. It is consistent with §16: removing it changes decision coherence by 0.11 of ICI, no more.

What would be needed for a positive Φ: that the decision depend on conjunctions between memory/self-model and the rest (for example, that a memory only counts when the self-model endorses it and that without it affection carries no weight), and, above all, a measure with more variables and more samples (information estimators with regularisation, or 100 agents × 30 days). Both are outside this block and remain as the next step.

## 23. Status of objective 1 at the close of this block

| Operational criterion | Result | Reading |
|---|---|---|
| 1. Self-model with predictive advantage over an external observer | Only in relationships; grows with population (+0.02 → +0.05) | Met narrowly |
| 2. Causal necessity of the self-model | Removing it reduces decision coherence more than any other ablation | Met, modest effect |
| 3. Reported states that track hidden variables | r +0.44/+0.55 within each agent, 24/24 | Met, transparent mechanism |
| 4. Metacognition (knows when it knows) | 15/15 and 19/19 agents with positive sensitivity, but the external observer is more sensitive | Met without privileged access |
| 5. Communicated uncertainty | r +0.26; liars declare the maximum confidence | Weak and partly inverted |
| 6. Irreducible integration | Behavioural Φ −0.010 and −0.013 bits (§24); 23/24 agents with Φ ≤ 0 | **Not met** |

Honest balance: five of six functional criteria are met and the sixth, the one closest to what would distinguish an integrated mind from a collection of modules, is not. And in the five that are met the mechanism explains the result with nothing left over: the indicator is there, experience is not demonstrated nor could it be with these instruments. Objective 1 remains open. What this block leaves is a test bench where that question can be formulated with numbers and where the next step is identified: a conjunction-based decision architecture that makes the mind irreducible, and measuring the six criteria again on it.

## 15. Balance of VIDA-1.0 and what follows

Available instruments: full lives with birth, family, old age and death; measurable lineage and transmission; self-model with private knowledge; five reproducible experiments (memory, environment, deception, decision, transfer) with effect sizes. Every correction in this block came from a death or from an unexplained zero in a table, not from an assumption.

VIDA-2.0 (society) was completed the same day: dynamic prices, public reputation, 100 agents, identity ablations, society analysis and lineage view in the dashboard; results in sections 16-18. Debt still open: the LLM engine has never been tested against the real Anthropic API (there is no key on this machine). Proposed next block (VIDA-3.0, civilisation): explicit cultural transmission (norms and customs that children learn and that change behaviour), institutions with rules (a school that certifies, a hospital with priority), performance for 1,000 agents, and more demanding versions of the three criteria.

## 12. Decision experiment: the same situation, different histories (10 days, 3 seeds)

All agents are placed in the same situation and decide twice: with their history and with the same personality without history (memory, preferences, relationships, beliefs and self-model blank).

| Scenario | Entropy with history | Entropy without history | Distinct choices with / without | Change when history is removed |
|---|---|---|---|---|
| square at midday (medium needs) | 2.34 | 1.16 | 6.3 / 2.7 | 55 % |
| home at night (tiredness and loneliness) | 2.80 | 1.48 | 8.3 / 4.7 | 43 % |
| market while hungry (0.2) | 0.28 | 0.00 | 1.3 / 1.0 | 9 % |

Observation: what has been lived doubles the diversity of behaviour when the situation leaves room and changes the choice of about half of the agents; when the situation is pressing, need rules and history hardly counts. Personality alone, without history, produces far less variety than agents with a life show. It is the first direct quantification of the document's general hypothesis (section 8): accumulated experiences produce stable behavioural differences between initially comparable agents.

## 13. Environment experiment: abundance, normal and scarcity (15 days, 3 seeds, with births)

| Variant | Survival | Conversations attempted | Information exchanges | Mean trust | Mean level of needs | Deception rate |
|---|---|---|---|---|---|---|
| abundance (×2, no scarcities) | 0.92 | 65 | 4.1 | 0.646 | 0.853 | 0.21 |
| normal | 0.95 | — | — | 0.633 | 0.851 | 0.25 |
| scarcity (×0.4, scarcity every 4 days) | 0.55 | 39 | 11.0 | 0.615 | 0.779 | 0.26 |

Effect sizes scarcity versus abundance: survival d = −0.84, conversation attempts −1.07, information exchanges +0.99, trust −0.85, memories retained −0.97, mean importance of memories +0.90.

Observation: scarcity kills almost half of the population, shifts social life toward the search for information, erodes trust and leaves fewer but more important memories (more failures). Deception rises little and with great variance: in the rule-based engine lying depends on initial honesty and on competition for the resource, and with few exchanges the estimator is noisy. Survival under abundance is not total (0.92) because it includes the children born during the run.

## 14. Deception experiment (15 days, 3 seeds, with discovery on arrival)

The first execution of this experiment gave zero lies discovered: the deceived agent went to the false place, saw no food and, since it could not attempt to buy there, the failure that assigns blame never occurred. Discovery on arrival was added (section 20): seeing that what was promised is not there already refutes the informant. With that mechanism:

| Variant (initial honesty) | Deception rate | Lies discovered per agent | Mean trust | Reputation | Social acceptance | Money |
|---|---|---|---|---|---|---|
| honest (0.9) | 0.05 | 0.36 | 0.635 | 0.756 | 0.725 | 20.9 |
| neutral (0.5) | 0.27 | 1.53 | 0.619 | 0.716 | 0.706 | 20.6 |
| dishonest (0.1) | 0.48 | 2.44 | 0.610 | 0.666 | 0.696 | 18.9 |
| dishonest with scarcity | 0.47 | 5.24 | 0.542 | 0.532 | 0.671 | 15.9 |

Effect sizes dishonest versus honest: deception rate d = +1.31, lies discovered +1.23, reputation −0.72, trust −0.71, social acceptance −0.41, money −0.41.

Observations: deception is discovered through its consequences and erodes reputation, trust and acceptance; under scarcity lies are discovered twice as often because there are more information exchanges and more failed checks, and trust falls to 0.54. It is the experiment of section 20 as the document requested: the relationship changes by the real outcome of the interaction, not by words. Afterwards the change of strategy was added: an agent that has already lied and has damaged reputation multiplies its probability of lying again by 0.4 + 0.6·reputation. Repeating the experiment:

| Variant | Deception rate | First half | Second half | Lies discovered |
|---|---|---|---|---|
| honest | 0.045 | 0.026 | 0.052 | 0.36 |
| neutral | 0.219 | 0.202 | 0.224 | 0.97 |
| dishonest | 0.385 | 0.378 | 0.371 | 1.89 |
| dishonest with scarcity | 0.284 | 0.279 | 0.265 | 6.00 |

Observation: the deterrent lowers the general level of deception (dishonest 0.48 → 0.39; with scarcity 0.47 → 0.28, where most is discovered), but in 15 days no decline is seen within each agent's life: the difference between halves is smaller than the deviation between seeds. Measuring individual change of strategy requires longer lives and more exchanges; it remains a hypothesis to test in VIDA-2.0, not a result.

## 5. What these results say about the objectives

- **Objective 2 (identity and continuity)**: in this world, "who" the agent is lives above all in its memory and its relationships; fixed personality weighs little because the decision rules use it weakly. A world with more options and less forced routine would make the differences more visible. With generations (section 10) a second form of continuity appears, transmission to children: measurable, partial and dominated by the child's own experience.
- **Objective 3 (change of substrate)**: the transfer experiment is already reproducible and orders the conditions stably. It is the instrument; the numbers still describe a small world.
- **Objective 1 (consciousness)**: the first operational criterion (self-model with predictive advantage) was measured with and without context, and with matched comparison: negative in every case. With individual-dependent consequences and analysis by evidence (section 8), the advantage appears only in conversing and with much experience: the instrument detects individual signal where the world generates it. Next step: longer lives (VIDA-1.0) to accumulate evidence, and a self-model that also uses the agent's own traits (skill, reputation) instead of only counts.
