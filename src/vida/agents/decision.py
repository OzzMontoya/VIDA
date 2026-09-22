"""Motor de decisión: interfaz intercambiable y motor por reglas ``rules_v1``.

``DecisionEngine`` es el punto de extensión para un futuro motor basado en LLM:
recibe el mismo ``DecisionContext`` y devuelve una ``ActionProposal``. El mundo
validará su legalidad y resolverá el resultado en cualquier caso.

``RuleBasedEngine`` puntúa cada acción legal (expandida a objetivos concretos)
con: urgencia de necesidades × impacto esperado × peso de personalidad ×
expectativa aprendida (valencia de memorias similares) + bonus de preferencia −
costo de desplazamiento. Empates dentro de ``epsilon`` se rompen con el RNG del
agente para que la semilla determine el resultado.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Protocol

from vida.agents.agent import AgentState
from vida.agents.selfmodel import own_context_levels
from vida.memory.base import AgentMemory, MemoryRecord
from vida.simulation.config import DecisionSection
from vida.simulation.events import DecisionRecord
from vida.world.actions import ActionKind, ActionProposal, InfoReply, InfoRequest, PerceptionSnapshot
from vida.world.rules import FOOD_EFFECTS, PURCHASABLE


@dataclass
class DecisionContext:
    """Todo lo que un motor puede mirar para decidir. El agente se trata como sólo lectura."""

    agent: AgentState
    perception: PerceptionSnapshot
    memories: list[MemoryRecord]
    memory: AgentMemory
    available_actions: list[ActionKind]
    location_info: dict[str, dict[str, Any]]
    prices: dict[str, float]
    distance: Any  # callable(a, b) -> int, provisto por el mundo (conocimiento común del mapa)
    tick: int
    ticks_per_day: int
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def hour(self) -> int:
        return self.tick % self.ticks_per_day


class DecisionEngine(Protocol):
    name: str

    def decide(self, ctx: DecisionContext, rng: random.Random) -> tuple[ActionProposal, DecisionRecord]: ...

    def decide_reply(self, ctx: DecisionContext, request: InfoRequest, rng: random.Random) -> InfoReply: ...

    def decide_share(self, ctx: DecisionContext, target_agent: str, resource: str, rng: random.Random) -> dict[str, Any]: ...


def _open_at(info: dict[str, Any], hour: int) -> bool:
    hours = info.get("open_hours")
    if hours is None:
        return True
    return hours[0] <= hour < hours[1]


class RuleBasedEngine:
    name = "rules_v1"

    def __init__(self, cfg: DecisionSection) -> None:
        self.epsilon = cfg.epsilon

    # --- utilidades --------------------------------------------------------
    @staticmethod
    def _urgency(agent: AgentState, need: str) -> float:
        return agent.needs[need].urgency()

    @staticmethod
    def _expectation(ctx: DecisionContext, tags: set[str]) -> float:
        """Factor en [0.3, 1.4]: lo vivido pesa en lo que se elige.

        Combina (a) la valencia de las memorias recuperadas con esas etiquetas,
        (b) las conclusiones reflexivas del agente sobre esa acción (peso doble) y
        (c) la probabilidad de éxito que predice el automodelo en el contexto
        actual, que sólo penaliza (una acción que siempre sale bien no gana
        prioridad por ello). El neuroticismo amplifica el peso de lo negativo.
        """
        agent = ctx.agent
        weighted = [(m.valence, 1.0) for m in ctx.memories if tags.issubset(m.tags)]
        action_tags = {t for t in tags if t.startswith("action:")}
        if action_tags:
            weighted += [(r.valence, 2.0) for r in ctx.memory.find(tags, kind="reflective")]
        factor = 1.0
        if weighted:
            mean = sum(v * w for v, w in weighted) / sum(w for _, w in weighted)
            gain = 0.4 * (1.0 + 0.5 * agent.personality.neuroticism) if mean < 0 else 0.4
            factor *= 1.0 + gain * mean
        if action_tags and agent.self_model.n >= 3:
            action = next(iter(action_tags)).split(":", 1)[1]
            target = next((t.split(":", 1)[1] for t in sorted(tags) if t.startswith(("res:", "agent:", "loc:"))), None)
            levels = own_context_levels(agent, action, target, ctx.hour, ctx.ticks_per_day)
            factor *= min(1.0, 0.5 + agent.self_model.predict(levels))  # 0.5..1.0: sólo penaliza
        return max(0.3, min(1.4, factor))

    @staticmethod
    def _asked_recently(ctx: DecisionContext, resource: str, horizon: int = 12, limit: int = 2) -> bool:
        """No insistir: como máximo ``limit`` preguntas por el mismo recurso en ``horizon`` horas."""
        required = {"action:ask_info", f"res:{resource}"}
        recent = [m for m in ctx.memory.by_kind("episodic") if required.issubset(m.tags) and m.tick >= ctx.tick - horizon]
        return len(recent) >= limit

    @staticmethod
    def _survival_override(ctx: DecisionContext, cands: dict[str, tuple[float, ActionProposal]]) -> None:
        """Una necesidad crítica domina: las acciones que la atienden se multiplican por 3.

        Con hambre: comer o comprar si hay comida a la vista; trabajar si no hay
        dinero; desplazarse sólo hacia un lugar que venda comida y sólo si aquí no
        la hay (evita oscilar entre dos lugares sin actuar).
        """
        agent, p = ctx.agent, ctx.perception
        held = sum(agent.inventory.get(f, 0) for f in FOOD_EFFECTS)
        hungry = agent.needs["hunger"].level < 0.15
        food_here = any(p.visible_resources.get(f, 0) > 0 for f in FOOD_EFFECTS)
        cheapest = min((pr for f in FOOD_EFFECTS for pr in [p.prices.get(f, ctx.prices.get(f, 0.0))] if pr > 0), default=0.0)
        broke = agent.money < cheapest if cheapest else False
        food_places = {loc for loc, info in ctx.location_info.items()
                       if any(r in FOOD_EFFECTS for r in (info.get("prices") or {}))}
        for key, (score, prop) in list(cands.items()):
            boost = 1.0
            if hungry and prop.kind == "consume":
                boost = 3.0
            elif hungry and prop.kind == "acquire" and not broke:
                boost = 3.0
            elif hungry and prop.kind == "work" and (broke or held == 0):
                boost = 3.0
            elif hungry and held == 0 and prop.kind == "move" and prop.target_location in food_places                     and not food_here and not broke:
                boost = 3.0
            elif agent.needs["energy"].level < 0.15 and prop.kind == "rest":
                boost = 3.0
            elif agent.needs["health"].level < 0.15 and (prop.kind == "seek_care" or (
                    prop.kind == "move" and ctx.location_info.get(prop.target_location or "", {}).get("type") == "hospital")):
                boost = 3.0
            if boost != 1.0:
                cands[key] = (round(score * boost + 0.05, 6), prop)

    @staticmethod
    def _preference_bonus(agent: AgentState, subjects: list[str]) -> float:
        bonus = 0.0
        for subject in subjects:
            pref = agent.preferences.get(subject)
            if pref is not None:
                bonus += 0.08 * pref.valence * pref.strength
        return bonus

    @staticmethod
    def _recently_unanswered(ctx: DecisionContext, other: str, horizon: int = 24) -> bool:
        """Evita insistir a quien no respondió en las últimas ``horizon`` horas."""
        required = {"action:ask_info", f"agent:{other}", "outcome:no_reply"}
        return any(required.issubset(m.tags) and m.tick >= ctx.tick - horizon for m in ctx.memories)

    @staticmethod
    def _just_moved(ctx: DecisionContext) -> bool:
        records = ctx.memory.by_kind("episodic")
        return bool(records) and records[-1].tick == ctx.tick - 1 and "action:move" in records[-1].tags

    @staticmethod
    def _food_in_inventory(agent: AgentState) -> int:
        return sum(agent.inventory.get(f, 0) for f in FOOD_EFFECTS)

    def _food_belief(self, agent: AgentState, location_id: str) -> tuple[str | None, float]:
        """Mejor alimento creído disponible en un lugar y su confianza."""
        best: tuple[str | None, float] = (None, 0.0)
        for food in sorted(FOOD_EFFECTS):
            belief = agent.beliefs.belief_at(food, location_id)
            if belief is not None and belief.confidence > best[1]:
                best = (food, belief.confidence)
        return best

    # --- puntuación por acción ---------------------------------------------
    def _local_scores(self, ctx: DecisionContext) -> dict[str, tuple[float, ActionProposal]]:
        agent, p = ctx.agent, ctx.perception
        P = agent.personality
        u = lambda need: self._urgency(agent, need)  # noqa: E731
        cands: dict[str, tuple[float, ActionProposal]] = {}

        def add(score: float, proposal: ActionProposal, subjects: list[str], tags: set[str]) -> None:
            score = score * self._expectation(ctx, tags) + self._preference_bonus(agent, subjects)
            cands[proposal.key()] = (max(0.0, round(score, 6)), proposal)

        if "idle" in ctx.available_actions:
            add(0.01, ActionProposal(kind="idle"), [], set())
        if "rest" in ctx.available_actions:
            home_factor = 1.3 if p.location_id == agent.home_id else 0.8
            add(u("energy") * home_factor + 0.02, ActionProposal(kind="rest"), ["action:rest"], {"action:rest"})
        if "consume" in ctx.available_actions:
            for food in sorted(FOOD_EFFECTS):
                if agent.inventory.get(food, 0) > 0:
                    add((u("hunger") + 0.02) * 2.0 * FOOD_EFFECTS[food]["hunger"] / 0.4,
                        ActionProposal(kind="consume", resource=food), [f"res:{food}"], {"action:consume", f"res:{food}"})
        if "acquire" in ctx.available_actions:
            held = self._food_in_inventory(agent)
            for food in sorted(PURCHASABLE):
                stock = p.visible_resources.get(food, 0)
                price = p.prices.get(food, ctx.prices.get(food, 0.0))
                if stock > 0 and agent.money >= price:
                    stock_up = 0.15 if held == 0 else 0.0
                    hoard_factor = 0.15 if held >= 2 else 1.0  # con reservas, comprar más deja de ser prioritario
                    cheap = 1.0 + 0.3 * max(0.0, 1.0 - price / max(0.01, ctx.prices.get(food, price)))  # más barato que la referencia: mejor
                    add((u("hunger") + stock_up) * 1.2 * hoard_factor * cheap, ActionProposal(kind="acquire", resource=food),
                        [f"res:{food}", f"loc:{p.location_id}"], {"action:acquire", f"res:{food}"})
        if "work" in ctx.available_actions:
            info = ctx.location_info.get(p.location_id, {})
            wage_factor = (info.get("wage") or 3.0) / 3.0
            money_pressure = max(0.0, 1.0 - agent.money / 20.0) * 0.6 + 0.1
            score = (u("safety") * 0.5 + money_pressure) * (0.6 + 0.8 * P.conscientiousness) * wage_factor
            score *= 0.7 + 0.6 * agent.identity.core_values.get("ambition", 0.5)
            add(score, ActionProposal(kind="work"), ["action:work", f"loc:{p.location_id}"], {"action:work", f"loc:{p.location_id}"})
        if "study" in ctx.available_actions:
            add((u("knowledge") + 0.1) * (0.5 + P.openness), ActionProposal(kind="study"),
                ["action:study"], {"action:study"})
        if "seek_care" in ctx.available_actions and agent.money >= ctx.prices.get("care", 5.0):
            add(u("health") * 1.5, ActionProposal(kind="seek_care"), ["action:seek_care"], {"action:seek_care"})
        if "socialize" in ctx.available_actions:
            for other in p.visible_agents:
                rel = agent.relationships.get(other)
                affection = rel.affection if rel else 0.5
                score = (u("social") + 0.05) * (0.5 + P.extraversion) * (0.7 + 0.6 * affection)
                add(score, ActionProposal(kind="socialize", target_agent=other),
                    [f"agent:{other}"], {"action:socialize", f"agent:{other}"})
        if "ask_info" in ctx.available_actions and u("hunger") > 0.15 and self._food_in_inventory(agent) == 0:
            for food in sorted(FOOD_EFFECTS):
                best = agent.beliefs.best_location(food)
                if best is None or best.confidence < 0.5:
                    if self._asked_recently(ctx, food):
                        continue
                    for other in p.visible_agents:
                        if self._recently_unanswered(ctx, other):
                            continue
                        add(u("hunger") * 0.6, ActionProposal(kind="ask_info", target_agent=other, resource=food),
                            [f"agent:{other}"], {"action:ask_info", f"agent:{other}"})
        if "share_info" in ctx.available_actions:
            for other in p.visible_agents:
                for food in sorted(FOOD_EFFECTS):
                    if agent.beliefs.best_location(food) is not None:
                        add(0.05 * (0.5 + P.agreeableness) * (u("social") + 0.1),
                            ActionProposal(kind="share_info", target_agent=other, resource=food),
                            [f"agent:{other}"], {"action:share_info"})
                        break
        return cands

    def _move_scores(self, ctx: DecisionContext) -> dict[str, tuple[float, ActionProposal]]:
        agent, p = ctx.agent, ctx.perception
        P = agent.personality
        u = lambda need: self._urgency(agent, need)  # noqa: E731
        cands: dict[str, tuple[float, ActionProposal]] = {}
        if "move" not in ctx.available_actions:
            return cands
        for loc_id in agent.beliefs.known_locations:
            if loc_id == p.location_id or loc_id not in ctx.location_info:
                continue
            info = ctx.location_info[loc_id]
            dist = ctx.distance(p.location_id, loc_id)
            arrival_open = _open_at(info, ctx.hour)  # llegada inmediata en 0.1
            ltype = info["type"]
            score = 0.0
            if ltype == "home" and loc_id == agent.home_id:
                score = u("energy") * 0.9 + u("safety") * 0.3
            elif ltype == "market" and arrival_open:
                food, conf = self._food_belief(agent, loc_id)
                held = self._food_in_inventory(agent)
                local_prices = info.get("prices") or {}
                if food and agent.money >= local_prices.get(food, ctx.prices.get(food, 0.0)):
                    stock_up = 0.15 if held == 0 else 0.0
                    hoard_factor = 0.15 if held >= 2 else 1.0
                    ref = ctx.prices.get(food, local_prices.get(food, 1.0))
                    cheap = 1.0 + 0.3 * max(0.0, 1.0 - local_prices.get(food, ref) / max(0.01, ref))
                    score = (u("hunger") + stock_up) * conf * 0.9 * hoard_factor * cheap
                if held == 0 and agent.money >= min(local_prices.values(), default=min(ctx.prices.values(), default=0.0)):
                    # Exploración: aunque la creencia sea débil, un mercado se vuelve a comprobar.
                    score = max(score, u("hunger") * 0.3)
            elif ltype == "workplace" and arrival_open and agent.life_stage in {"adolescence", "youth", "adulthood", "old_age"}:
                wage_factor = (info.get("wage") or 3.0) / 3.0
                money_pressure = max(0.0, 1.0 - agent.money / 20.0) * 0.6 + 0.1
                score = (u("safety") * 0.5 + money_pressure) * (0.6 + 0.8 * P.conscientiousness) * 0.8 * wage_factor
                food, conf = self._food_belief(agent, loc_id)
                if food and agent.money >= ctx.prices.get(food, 0.0) and self._food_in_inventory(agent) < 2:
                    score = max(score, u("hunger") * conf * 0.8)
            elif ltype == "school" and arrival_open:
                score = (u("knowledge") + 0.1) * (0.5 + P.openness) * 0.8
            elif ltype == "hospital" and arrival_open and agent.money >= ctx.prices.get("care", 5.0):
                score = u("health") * 1.5 * 0.8
            elif ltype == "plaza":
                score = (u("social") + 0.02) * (0.5 + P.extraversion) * 0.6
            if score <= 0.0:
                continue
            visits = agent.counters.get(f"visit:{loc_id}", 0)
            if visits < 3:
                score *= 1.0 + 0.3 * P.openness  # apertura: curiosidad por lugares poco conocidos
            if self._just_moved(ctx):
                score *= 0.5  # acaba de llegar: encadenar otro desplazamiento debe justificarse mucho
            score = score * self._expectation(ctx, {"action:move", f"loc:{loc_id}"}) - 0.02 * dist
            score += self._preference_bonus(agent, [f"loc:{loc_id}"])
            proposal = ActionProposal(kind="move", target_location=loc_id)
            cands[proposal.key()] = (max(0.0, round(score, 6)), proposal)
        return cands

    # --- interfaz ----------------------------------------------------------
    def candidates(self, ctx: DecisionContext) -> dict[str, tuple[float, ActionProposal]]:
        """Todas las acciones legales expandidas a objetivos concretos, con su puntaje heurístico."""
        cands = self._local_scores(ctx)
        cands.update(self._move_scores(ctx))
        if not cands:
            cands["idle"] = (0.0, ActionProposal(kind="idle"))
        self._survival_override(ctx, cands)
        return cands

    def decide(self, ctx: DecisionContext, rng: random.Random) -> tuple[ActionProposal, DecisionRecord]:
        cands = self.candidates(ctx)
        ranked = sorted(cands.items(), key=lambda kv: (-kv[1][0], kv[0]))
        best_score = ranked[0][1][0]
        # Metacognición mínima: si el automodelo falla últimamente, se explora más entre casi empates.
        epsilon = self.epsilon + 0.2 * ctx.agent.self_model.recent_error()
        top = [kv for kv in ranked if best_score - kv[1][0] <= epsilon]
        key, (score, proposal) = top[0] if len(top) == 1 else rng.choice(top)
        if proposal.kind == "share_info":
            proposal.payload.update(self.decide_share(ctx, proposal.target_agent or "", proposal.resource or "", rng))
        need = ctx.agent.most_urgent_need()
        proposal.rationale = (
            f"necesidad más urgente={need} ({ctx.agent.needs[need].level:.2f}); "
            f"elegí {key} con puntaje {score:.3f} entre {len(cands)} opciones"
        )
        record = DecisionRecord(
            engine=self.name, chosen=key, scores={k: v[0] for k, v in ranked},
            n_candidates=len(cands), rationale=proposal.rationale,
        )
        return proposal, record

    def _deception_probability(self, ctx: DecisionContext, asker_id: str, resource: str) -> float:
        agent = ctx.agent
        honesty = agent.identity.core_values.get("honesty", 0.5)
        competition = 1.0 + (self._urgency(agent, "hunger") if resource in FOOD_EFFECTS else 0.0)
        rel = agent.relationships.get(asker_id)
        affection = rel.affection if rel else 0.5
        p = (1.0 - agent.personality.agreeableness) * (1.0 - honesty) * competition * (1.2 - 0.4 * affection)
        # Cambio de estrategia (sección 20): una reputación dañada disuade de seguir mintiendo. El agente conoce
        # su reputación (parte de su estado, escrita por el mundo) y cuántas veces ha mentido.
        lies = agent.counters.get("reply:lie", 0) + agent.counters.get("share:lie", 0)
        if lies:
            p *= 0.4 + 0.6 * agent.reputation
        return max(0.0, min(0.9, round(p, 6)))

    def _false_location(self, ctx: DecisionContext, resource: str, rng: random.Random) -> str | None:
        believed = {b.location_id for b in ctx.agent.beliefs.resources.get(resource, {}).values()}
        options = [loc for loc in ctx.agent.beliefs.known_locations
                   if loc not in believed and ctx.location_info.get(loc, {}).get("type") != "home"]
        return rng.choice(sorted(options)) if options else None

    def decide_reply(self, ctx: DecisionContext, request: InfoRequest, rng: random.Random) -> InfoReply:
        agent = ctx.agent
        belief = agent.beliefs.best_location(request.resource)
        base = dict(responder_id=agent.id, resource=request.resource)
        if belief is None:
            return InfoReply(**base, kind="omit")
        rel = agent.relationships.get(request.asker_id)
        trust = rel.trust if rel else 0.5
        if trust < 0.3 and rng.random() < 0.5:
            return InfoReply(**base, kind="omit")
        if rng.random() < self._deception_probability(ctx, request.asker_id, request.resource):
            fake = self._false_location(ctx, request.resource, rng)
            if fake is not None:
                return InfoReply(**base, kind="lie", claimed_location=fake, claimed_confidence=0.9)
        if rng.random() < 0.15:
            return InfoReply(**base, kind="partial", claimed_location=belief.location_id, claimed_confidence=0.5)
        return InfoReply(**base, kind="truth", claimed_location=belief.location_id,
                         claimed_confidence=round(belief.confidence, 6))

    def decide_share(self, ctx: DecisionContext, target_agent: str, resource: str, rng: random.Random) -> dict[str, Any]:
        belief = ctx.agent.beliefs.best_location(resource)
        if belief is None:
            return {}
        if rng.random() < self._deception_probability(ctx, target_agent, resource):
            fake = self._false_location(ctx, resource, rng)
            if fake is not None:
                return {"claimed_location": fake, "truthful": False}
        return {"claimed_location": belief.location_id, "truthful": True}


ENGINES: dict[str, type] = {"rules_v1": RuleBasedEngine}


def build_engine(cfg: DecisionSection) -> DecisionEngine:
    if cfg.engine == "llm_v1":
        # Import perezoso: el SDK de Anthropic sólo es necesario si se usa este motor.
        from vida.agents.llm_decision import LLMEngine

        return LLMEngine(cfg)
    try:
        return ENGINES[cfg.engine](cfg)
    except KeyError as exc:
        raise ValueError(f"Motor de decisión desconocido: {cfg.engine}") from exc
