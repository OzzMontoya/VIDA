# Six operational criteria for machine consciousness, tested on a reproducible artificial-life simulator: five functional indicators hold, behavioural integration (Φ) is zero

**Oziel Atlahi Montoya Mares**¹

¹ Universidad Tecnológica Metropolitana de Aguascalientes (UTMA), Mexico

*Preprint draft, October 2026. Code, configurations and raw results: repository VIDA (MIT licence). Spanish originals of the result logs are canonical: `docs/resultados_0.2.md`, `docs/criterios_consciencia.md`.*

---

## Abstract

Claims about consciousness in artificial systems are usually made from the outside, by reading first-person text. We take the opposite route: a simulator in which the designer fixes, in advance, which observations would count as evidence for which mechanism, measures them, and states the mechanistic explanation alongside every positive result. VIDA (Artificial Life, Identity and Agent Development) is a deterministic, seed-reproducible multi-agent simulation in which agents with six kinds of memory, needs, personality, beliefs, relationships, a learned self-model and a dynamic identity live full lives (birth, work, deception, ageing, death, offspring) in a textual world that is the sole authority over outcomes. We define six operational criteria drawn from the consciousness-science literature (predictive self-model advantage, causal necessity of the self-model, reported states tracking hidden variables, metacognitive sensitivity, communicated uncertainty, and informational integration) and measure each with a dedicated instrument over 10 to 100 agents and up to 120 simulated days. Five criteria are met in their functional reading, each with a transparent mechanism that fully accounts for the result: the self-model predicts better than a population observer only where the world generates individual information (social interaction; advantage +0.018 with 10 agents, +0.053 with 100); ablating the self-model lowers decision coherence more than any other single ablation; reported emotional valence tracks hidden incoming trust within every agent (mean within-agent r = +0.44 and +0.55); agents are more accurate when they declare higher confidence (15/15 and 19/19 agents), but an external observer is more sensitive; declared confidence weakly tracks truth (r = +0.26) and is inverted by liars. The sixth criterion fails: a behavioural proxy of integrated information, computed as the mutual information between the state of six mind components and the chosen action minus the information retained by the minimum-information bipartition, is Φ = −0.010 and −0.013 bits over 8,424 decisions per seed, with 23 of 24 agents at Φ ≤ 0. The mind of a VIDA agent is reducible to its parts. We also report a measurement error we committed and corrected (an action-dependent feature inflated the self-model's information by two orders of magnitude) and a metric we discarded (an ablation-interaction index whose sign cannot distinguish independent from conjunctive modules). We argue that functional criteria of this kind can be satisfied by a system with no plausible claim to experience, that integration-type criteria are where such systems currently fail, and that both facts are useful: they turn a philosophical question into a list of measurements with known failure modes.

**Keywords:** artificial consciousness, operational criteria, integrated information, self-model, metacognition, artificial life, agent-based simulation, reproducibility.

---

## 1. Introduction

Whether an artificial system can be conscious is an open scientific and philosophical question. Most recent discussion concerns large language models and proceeds by interpreting their text. That route has a known defect: a system trained on human descriptions of experience will produce such descriptions whether or not anything corresponds to them, so the evidence is contaminated at the source.

This paper takes a different route, in the tradition of artificial life rather than natural-language AI. We build a simulator in which:

1. Nothing an agent says is treated as evidence. Agents produce no free text about themselves; their only outputs are actions and numerical reports (a valence, a confidence) whose generating mechanism is known.
2. The criteria are fixed before measurement, each with an instrument and with the alternative mechanistic explanation written down next to it.
3. Every run is reproducible from a seed, and every positive result is reported together with the mechanism that produces it.

The purpose is not to build a conscious machine. It is to find out how far a system that is certainly not conscious in any demanding sense can go in satisfying operational criteria that the literature proposes as indicators, and where exactly it stops. Both answers are informative for anyone who wants to use such criteria on systems where the mechanism is not known.

The contribution is threefold: (i) a reproducible platform, VIDA, with full life cycles, memory, self-model, deception and lineage; (ii) six operational criteria with instruments and results; (iii) a negative result on behavioural integration, together with two methodological lessons (a circular-feature leak and an uninterpretable interaction metric) that we expect to generalise.

## 2. The simulator

### 2.1 Design principles

VIDA follows five non-negotiable principles.

- **The world is the authority.** The objective world state is separate from each agent's world model (beliefs). Only the world's resolution function mutates the world.
- **The decision engine proposes; the world resolves.** An engine returns an action proposal; the world returns the objective outcome. A rule-based engine and an LLM-backed engine implement the same interface; the LLM may only choose among legal candidates and degrades to rules on error.
- **Relationships change through outcomes, not words.** Social and learning updates read only the outcome record, never the proposal's rationale text or world-private details.
- **Reproducibility.** All randomness flows from seeded named streams. Two runs with the same seed and configuration produce an identical SHA-256 digest of their event log, a property enforced by tests.
- **Scientific language.** Nothing in code, logs, memories or biographies asserts consciousness or feeling; observed behaviour is described.

### 2.2 Agents

Each agent has: Big Five personality; six needs (hunger, energy, health, social, safety, knowledge) that decay per tick; goals; preferences adjusted by consequences; knowledge/skills; relationships (trust, affection, familiarity) with other agents; a reputation written by the world; an emotional state (valence, arousal) updated by outcomes; a world model of beliefs about resources and other agents, with confidence and provenance (observed vs told, with source agent and source event); a dynamic identity (self-description tags and core values: honesty, loyalty, ambition) recomputed daily from behaviour counters; and a **self-model**.

Memory has six stores: episodic, semantic (resource@location facts with confirmations and refutations), social, autobiographical (daily summaries), procedural (skill gains) and reflective (daily conclusions about actions). Retrieval scores recency, importance and tag relevance. Forgetting removes low-importance old episodes; forgotten semantic facts weaken (never delete) the associated belief, so that places can be re-checked.

The **self-model** is a hierarchical context table that estimates the agent's own probability of success for an action in context (action, target, time band, hunger band, energy band), with back-off to more general contexts when evidence is thin, plus private levels not visible to any external observer (own trust and affection toward the target, own skill). Before acting, the agent predicts its success and declares a second-order confidence (evidence × context specificity × distance from 0.5). A **population model** with the same table structure but trained on all agents' public contexts serves as the external observer. Both predictions, both confidences and the actual outcome are logged per event.

### 2.3 World

A textual world of locations (homes, plaza, markets, workplaces, school, hospital) with opening hours, stock, restocking and scarcity events, dynamic prices (base × clamp(1 + 0.8·(1 − stock/restock), 0.6, 2.0)), wages per workplace and public reputation visible to all. Eleven actions: move, acquire, consume, work, rest, socialize, ask_info, share_info, study, seek_care, idle. Outcomes depend on the individual: work fails with probability 1 − (0.35 + 0.5·skill + 0.15·energy); study fails depending on openness; socialising is accepted with probability 0.15 + 0.45·trust + 0.25·reputation + 0.15·personality affinity.

Deception is a first-class mechanism. Information requests and shares carry a claimed location; the world compares it with the truth and records intent (truth, partial, lie, omit) in a ledger the agents cannot read. A deceived agent discovers the lie when it acts on the belief and fails, or when it arrives at the promised place and sees nothing; trust in the informant then drops and, if the ledger says lie, the informant's reputation falls.

Life cycle: infancy, adolescence, youth, adulthood, old age, death (health, critical hunger, age). Births occur when population is under a cap: offspring inherit part of the personality, start as adolescents in the parent's home, receive the parent's remembered beliefs as "told" beliefs, a daily allowance, and a guardian if orphaned.

### 2.4 Decision engine

The rule-based engine scores each legal action expanded to concrete targets: need urgency × expected impact × personality weights × a learned expectation factor in [0.3, 1.4] (valence of retrieved memories, reflective conclusions at double weight, and the self-model's predicted success, which only penalises) + preference bonus − travel cost, with a survival override (×3 for actions addressing a critical need) and tie-breaking by seeded RNG within ε. Exploration grows with the self-model's recent error (minimal metacognition). Coupling additions: self-model surprise and affection toward the interaction partner raise the importance of the stored episode.

### 2.5 Instruments

Per-run analyses are command-line tools over the event log: biography (what an agent lived, remembers, learned, prefers, knows, decided, and what changed it); identity continuity index (ICI, eight dimensions, used for transfer and ablation); self-model advantage by evidence and by action; lineage (child vs parent vs other adults); society (criterion 3, reputation structure, Gini, prices); metacognition (criteria 4 and 5); integration (criterion 6). Experiments (memory, environment, deception, decision, transfer/ablation) run in memory with Cohen's d effect sizes across seeds.

## 3. Six operational criteria

Each criterion is stated with its instrument and the alternative mechanism that would explain a positive result without experience. A positive result at the level of observation never licenses a claim at the level of experience; the chain stops at a hypothesis about mechanism.

| # | Criterion | Instrument | Mechanism that explains a positive result |
|---|---|---|---|
| 1 | The self-model predicts the agent's own success better than an external observer with the same context and population data | Matched self-model advantage (external error − own error), by evidence and by action | Private information (own relationships, skills) exists only where the world makes outcomes depend on the individual |
| 2 | The self-model is causally necessary: removing it degrades behavioural coherence measurably | Single-component ablations at a split point, ICI decision dimension over the following horizon | The expectation factor uses the self-model; without it, choices shift |
| 3 | Reported internal states correlate with variables the agent was never given | Within-agent correlation of reported valence with hidden incoming trust, daily snapshots | Common cause: acceptances update both valence and others' trust |
| 4 | Metacognitive sensitivity: accuracy is higher when declared confidence is higher, and own confidence is more informative than an observer's | Accuracy(high conf) − accuracy(low conf); r(confidence, accuracy); own vs population | Confidence is a monotone function of evidence; more evidence yields both confidence and accuracy |
| 5 | Communicated uncertainty tracks the truth of what is communicated | r(declared confidence, claim true) over information replies; by ledger intent | Honest agents report belief confidence; liars report a fixed high value |
| 6 | Integration: the whole mind carries information about action that no bipartition retains | Behavioural Φ: I(action; all components) − max over bipartitions [I(action; P1) + I(action; P2)], bias-corrected | Additive scoring with argmax is separable by construction |

## 4. Results

All runs use the rule-based engine (the LLM engine is excluded so that world cloning and determinism hold). Configurations: `village_small` (12 locations), `town` (two markets, three workplaces), `society` (100 agents). Seeds 1–3 unless stated. Full tables are in `docs/resultados_0.2.md`; section numbers below refer to it.

### 4.1 Preliminary: memory produces individuality (§2, §12)

Without memory, agents ask for information ten times more often (19.4 vs 2.0 exchanges; d = −1.57), decide with higher entropy (d = −1.59), form weaker bonds (trust 0.63 vs 0.69, d = +1.59) and predict themselves worse (calibration 0.77 vs 0.86, d = +1.92). Placed in the same situation with and without their history, agents change their choice in 55 % of cases in a mid-day plaza, 43 % at home at night, and 9 % when hungry at a market: history matters when the situation leaves room.

### 4.2 Criterion 1: self-model advantage is narrow and grows with society (§6, §8–11, §18)

Averaged over all predictions the self-model is slightly *worse* than the population observer (matched advantage −0.03 in both worlds). Stratifying by own evidence shows this is a sampling effect: the disadvantage shrinks with evidence and turns positive above 50 own attempts. Stratifying by action shows where individual information lives:

| Action | Advantage, village | Advantage, town |
|---|---|---|
| socialize | **+0.027** | **+0.020** |
| work | −0.008 | +0.010 |
| rest, consume, acquire, move | −0.03 to −0.045 | −0.03 to −0.044 |

Over 34,000 predictions in 120-day runs the socialising advantage is +0.018 (n = 5,069). With 100 agents it is **+0.053** (n = 2,295): when there are a hundred people, knowing one's own standing with each is worth more than the population can say. Criterion 1 holds exactly where the world generates individual information and nowhere else.

### 4.3 Criterion 2: the self-model is causally necessary, modestly (§16)

Ablating one component of agent a01 at day 30 and following 10 days (3 seeds):

| Ablation | ICI | Decision dimension |
|---|---|---|
| none (continuation) | 1.000 | 1.000 |
| without beliefs | 0.903 | 0.926 |
| without identity | 0.896 | 0.917 |
| without preferences | 0.851 | 0.921 |
| **without self-model** | 0.845 | **0.890** |
| without relationships | 0.823 | 0.946 |
| 50 % memory erased | 0.803 | 0.921 |
| fresh mind | 0.547 | 0.885 |

Removing the self-model lowers decision coherence more than any other single ablation. Natural drift over the same 10 days is 0.866, so ablations above that value (beliefs, identity) are indistinguishable from simply living longer.

### 4.4 Criterion 3: reported valence tracks hidden trust (§17, §18)

| World | (agent, day) pairs | pooled r | mean within-agent r | agents with r > 0 |
|---|---|---|---|---|
| town | 1,342 | +0.415 | +0.437 | 24 / 24 |
| village_small | 1,342 | +0.550 | +0.552 | 24 / 24 |
| society (100) | — | — | +0.25 | 87 / 102 |

A single end-of-run snapshot showed a weak negative correlation (−0.3); the whole life shows a positive one without exception. The mechanism is explicit: acceptances update both valence and the acceptor's trust.

### 4.5 Criterion 4: functional metacognition without privileged access (§20, §21)

| Confidence source | Sensitivity | r(confidence, accuracy) | agents with sensitivity > 0 |
|---|---|---|---|
| own self-model (60 days, 16,704 predictions) | +0.115 | +0.424 | 15 / 15 |
| external observer | +0.199 | +0.490 | — |
| own self-model (dishonest town, 30 days) | +0.157 | — | 19 / 19 |
| external observer | +0.220 | — | — |

Agents are more accurate when they say they are sure, always. But an observer applying the same confidence rule to more data is more sensitive. There is no privileged access to one's own uncertainty; there is a confidence rule that works.

### 4.6 Criterion 5: communicated uncertainty is weak and inverted by liars (§21)

In a town with initial honesty 0.1 and scarcity (270 replies):

| Intent (world ledger) | n | mean declared confidence | fraction true |
|---|---|---|---|
| truth | 177 | 0.52 | 0.23 |
| partial | 35 | 0.50 | 0.17 |
| lie | 58 | 0.90 | 0.00 |

r(declared confidence, truth) = +0.26. Honest agents declare their actual belief confidence and are often wrong because beliefs go stale under scarcity; liars declare the maximum. A rational receiver in this society should learn to invert the signal.

### 4.7 Criterion 6: behavioural integration is zero (§19, §22, §24)

**Discarded metric.** We first measured integration as the interaction between single ablations and the full ablation on ICI drops: −0.229 without coupling and −0.282 after coupling memory encoding to surprise and affection. We then showed that this metric cannot answer the question: a decision depending on a *conjunction* of two components yields negative interaction (removing either destroys the conjunction; removing both destroys it once), while *redundant pathways* yield positive interaction, and the bounded ICI saturates. The sign does not distinguish independent from entangled modules.

**Behavioural Φ.** Each action logs the state of six mind components at decision time: body (hunger), retrieved memory (mean valence), self-model (recent error), relationships (mean affection toward agents present), identity (ambition), beliefs (confidence in food location). Each is binarised at its median. We compute, bias-corrected by 20 permutations of the action labels, I(action; all six) and, for each of the 31 bipartitions, I(action; P1) + I(action; P2). Φ is the whole minus the bipartition that loses least. Town, 30 days, 12 agents, 8,424 decisions per seed:

| | Seed 1 | Seed 2 |
|---|---|---|
| Action entropy | 2.573 bits | 2.618 bits |
| Information of the whole | 0.176 bits (6.8 %) | 0.164 bits (6.3 %) |
| Per component (body / memory / self / relations / identity / beliefs) | .052 / .009 / .003 / .076 / .009 / .019 | .058 / .014 / .004 / .074 / .012 / .016 |
| Minimum-information partition | memory+self \| rest → 0.186 | memory+self \| rest → 0.177 |
| **Behavioural Φ** | **−0.010 bits** | **−0.013 bits** |
| Synergy over best single component | +0.100 | +0.091 |
| Agents with Φ > 0 (of 12) | 1 (+0.002) | 0 |

Separating memory and self-model from the rest loses no information about action. There is moderate synergy over any single component, as expected from an additive score followed by argmax, but the combination can be cut without loss. The mind is reducible.

**A leak we caught.** A first version logged the self-model's predicted success *for the chosen action*. That feature carried 0.336 bits about the action, two orders of magnitude more than any other component, and Φ was still ≈ 0. The feature was circular: it was computed after the choice and conditioned on it. Replacing it with action-independent summaries (recent error, experience count) reduced the self-model's information to 0.003 bits. Any feature computed downstream of the variable being predicted will inflate integration-like measures, and the check is cheap: no logged component may depend on the action.

### 4.8 Summary

| Criterion | Result | Reading |
|---|---|---|
| 1 Self-model advantage | Only in social interaction; +0.02 → +0.05 with population | Met, narrowly |
| 2 Causal necessity | Largest decision-coherence drop of all single ablations | Met, modest effect |
| 3 Hidden-variable tracking | within-agent r +0.44 / +0.55, 24/24 | Met, transparent mechanism |
| 4 Metacognition | 15/15, 19/19 positive; observer more sensitive | Met, no privileged access |
| 5 Communicated uncertainty | r +0.26; liars declare maximum | Weak, partly inverted |
| 6 Integration | Φ −0.010 / −0.013 bits; 23/24 agents ≤ 0 | **Not met** |

## 5. Discussion

**Functional criteria are cheap.** Five of six indicators that appear in discussions of machine consciousness are satisfied by a few thousand lines of deterministic rules, and in each case the mechanism accounts for the result with nothing left over. This does not show that the criteria are useless. It shows that, applied to a system whose mechanism is unknown, a positive result on any of them is compatible with a mechanism as simple as a context table and an additive score. Criteria of this kind are necessary-condition tests at best.

**Integration is where the system fails, and the failure is structural.** The decision is a sum of module contributions followed by a maximum. Any such architecture is separable: Φ ≈ 0 is not a tuning accident but a property of additive scoring. A positive Φ would require decisions that depend on conjunctions spanning every cut of the mind, which is a different architecture, not a parameter change. Integration-type criteria therefore do discriminating work that functional criteria do not, at least against this class of system.

**Individual information lives where the world puts it.** The self-model has predictive advantage exactly in social interaction, the only action whose outcome depends on a relationship between two specific individuals, and the advantage triples when society grows from 10 to 100 agents. A self-model has something to learn only where outcomes are individual. This suggests that tests of self-knowledge should be designed around outcomes that genuinely depend on the agent, not on world statistics.

**Two methodological lessons.** The ablation-interaction index looked like an integration measure and was not; its sign is uninterpretable. The circular feature looked like a strong self-model signal and was an artefact. Both would have passed a casual review. Reporting them is part of the result.

**What this does not show.** Nothing here bears on whether any artificial system has experience. The agents do not, in any sense the author would defend, and the measurements were never designed to detect experience. They were designed to detect mechanisms, and they did.

## 6. Limitations

- Six binary summaries explain only 6–7 % of action entropy; the rest is in unlogged variables (location, hour, visible stock, money) and seeded tie-breaking. With more variables the joint state grows exponentially and the plug-in estimator fails at 8,000 samples. Regularised estimators or 100-agent runs are needed before a positive Φ could be detected if it existed.
- The ICI and the component summaries are the author's choices. Different summaries could change the numbers, though not, we expect, the sign of Φ for an additive engine.
- All measurements use the rule-based engine. The LLM-backed engine has been exercised only against a local open-weights model, not against a frontier API.
- Single author, single lab, modest hardware. Every metric was designed and measured by the same person; the two caught errors suggest others may remain.

## 7. Future work

Conjunctive decision architectures (a memory that counts only when the self-model endorses it; affection that weighs only when remembered) to test whether Φ can be made positive and what it costs in survival; estimators for higher-dimensional integration; stricter versions of criteria 1–5 (self-reports not mechanically derived from state; self-model advantage beyond social action; large ablation effects); criteria for identity continuity under substrate change, which the transfer experiments already instrument; and external replication.

## Reproducibility

Python 3.12+, dependencies pinned in `pyproject.toml`. `python -m pytest` runs 114 tests including determinism (identical event digests for equal seeds). Each result section names its configuration file, seeds and command; experiment outputs carry a manifest with configuration hash and git SHA. Runs of 10 agents × 30 days take under a minute on a laptop CPU; 100 agents × 30 days about 20 minutes.

## Acknowledgements

Development was assisted by an AI coding system (Claude, Anthropic) operating under the author's direction; all design decisions, criteria and interpretations are the author's responsibility.

## References (to be completed)

Baars, B. J. (1988). *A Cognitive Theory of Consciousness*. Cambridge University Press.
Balduzzi, D., & Tononi, G. (2008). Integrated information in discrete dynamical systems. *PLoS Computational Biology*, 4(6).
Butlin, P., Long, R., et al. (2023). Consciousness in artificial intelligence: insights from the science of consciousness. arXiv:2308.08708.
Dehaene, S., Lau, H., & Kouider, S. (2017). What is consciousness, and could machines have it? *Science*, 358(6362).
Fleming, S. M., & Lau, H. C. (2014). How to measure metacognition. *Frontiers in Human Neuroscience*, 8:443.
Metzinger, T. (2003). *Being No One: The Self-Model Theory of Subjectivity*. MIT Press.
Oizumi, M., Albantakis, L., & Tononi, G. (2014). From the phenomenology to the mechanisms of consciousness: IIT 3.0. *PLoS Computational Biology*, 10(5).
Parfit, D. (1984). *Reasons and Persons*. Oxford University Press.
Seth, A. K., & Bayne, T. (2022). Theories of consciousness. *Nature Reviews Neuroscience*, 23.
Williams, P. L., & Beer, R. D. (2010). Nonnegative decomposition of multivariate information. arXiv:1004.2515.
