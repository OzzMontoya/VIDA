"""Estado completo de un agente (sección 13 del documento).

``AgentState`` es un contenedor de datos; la lógica de decisión, aprendizaje,
relaciones e identidad vive en módulos separados para mantener la separación
mundo / agente / memoria / decisión / evaluación.

Campos con dueño externo:
- ``reputation`` la escribe el mundo (``World.update_reputation``), no el agente.
- ``location_id`` es una caché de ``WorldState.agent_locations``; sólo
  ``apply_outcome`` la actualiza a partir del resultado objetivo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from vida.agents.beliefs import WorldModel
from vida.agents.goals import Goal, Preference
from vida.agents.needs import Need, clamp01
from vida.agents.personality import Personality
from vida.agents.selfmodel import SelfModelState
from vida.simulation.config import NeedName
from vida.world.actions import ActionOutcome

LifeStage = Literal["infancy", "adolescence", "youth", "adulthood", "old_age", "dead"]
STAGE_ORDER: tuple[LifeStage, ...] = ("infancy", "adolescence", "youth", "adulthood", "old_age", "dead")
WORKING_STAGES: frozenset[str] = frozenset({"youth", "adulthood", "old_age"})


class PhysicalState(BaseModel):
    alive: bool = True
    injuries: int = 0


class Relationship(BaseModel):
    trust: float = Field(0.5, ge=0.0, le=1.0)
    affection: float = Field(0.5, ge=0.0, le=1.0)
    familiarity: float = Field(0.0, ge=0.0, le=1.0)
    last_interaction_tick: int | None = None

    def adjust(self, *, trust: float = 0.0, affection: float = 0.0, familiarity: float = 0.0) -> dict[str, float]:
        """Aplica deltas acotados y devuelve los cambios reales."""
        before = (self.trust, self.affection, self.familiarity)
        self.trust = clamp01(self.trust + trust)
        self.affection = clamp01(self.affection + affection)
        self.familiarity = clamp01(self.familiarity + familiarity)
        deltas = {
            "trust": round(self.trust - before[0], 6),
            "affection": round(self.affection - before[1], 6),
            "familiarity": round(self.familiarity - before[2], 6),
        }
        return {k: v for k, v in deltas.items() if v != 0.0}


class EmotionalState(BaseModel):
    """Estado emocional *simulado*: dos dimensiones, sin pretensión de vivencia."""

    valence: float = Field(0.0, ge=-1.0, le=1.0)
    arousal: float = Field(0.0, ge=0.0, le=1.0)

    def nudge(self, valence: float, arousal: float = 0.0) -> None:
        self.valence = max(-1.0, min(1.0, self.valence * 0.9 + valence * 0.3))
        self.arousal = clamp01(self.arousal * 0.9 + arousal * 0.3)


class KnowledgeItem(BaseModel):
    level: float = Field(0.0, ge=0.0, le=1.0)
    source: str = "experience"
    tick: int = 0


class Identity(BaseModel):
    """Representación dinámica derivada de hábitos, valores y relaciones (sección 15)."""

    self_description_tags: list[str] = Field(default_factory=list)
    core_values: dict[str, float] = Field(
        default_factory=lambda: {"honesty": 0.5, "loyalty": 0.5, "ambition": 0.5}
    )


class AgentStateSummary(BaseModel):
    """Resumen compacto del estado, usado en eventos y en el contexto de decisión."""

    agent_id: str
    life_stage: LifeStage
    age_ticks: int
    location_id: str
    needs: dict[str, float]
    money: float
    inventory: dict[str, int]
    emotion_valence: float
    reputation: float
    top_goal: str | None = None


class AgentState(BaseModel):
    id: str
    name: str
    age_ticks: int = 0
    life_stage: LifeStage = "adulthood"
    personality: Personality = Field(default_factory=Personality)
    physical: PhysicalState = Field(default_factory=PhysicalState)
    needs: dict[NeedName, Need]
    goals: list[Goal] = Field(default_factory=list)
    preferences: dict[str, Preference] = Field(default_factory=dict)
    knowledge: dict[str, KnowledgeItem] = Field(default_factory=dict)
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    reputation: float = Field(0.5, ge=0.0, le=1.0)
    emotion: EmotionalState = Field(default_factory=EmotionalState)
    beliefs: WorldModel = Field(default_factory=WorldModel)
    identity: Identity = Field(default_factory=Identity)
    location_id: str
    home_id: str
    inventory: dict[str, int] = Field(default_factory=dict)
    money: float = 0.0
    decision_history: list[str] = Field(default_factory=list)
    critical_streak: int = 0
    counters: dict[str, int] = Field(default_factory=dict)
    self_model: SelfModelState = Field(default_factory=SelfModelState)
    parent_id: str | None = None
    guardian_id: str | None = None  # adulto que asume la asignación si el progenitor muere
    generation: int = 0
    birth_tick: int = 0

    # --- helpers de consulta ----------------------------------------------
    @property
    def alive(self) -> bool:
        return self.physical.alive

    def age_days(self, ticks_per_day: int) -> int:
        return self.age_ticks // ticks_per_day

    def relationship_with(self, other_id: str) -> Relationship:
        rel = self.relationships.get(other_id)
        if rel is None:
            rel = Relationship()
            self.relationships[other_id] = rel
        return rel

    def preference_for(self, subject: str) -> Preference:
        pref = self.preferences.get(subject)
        if pref is None:
            pref = Preference(subject=subject)
            self.preferences[subject] = pref
        return pref

    def knowledge_level(self, key: str) -> float:
        item = self.knowledge.get(key)
        return item.level if item is not None else 0.0

    def bump_counter(self, key: str, by: int = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + by

    def most_urgent_need(self) -> NeedName:
        return max(sorted(self.needs), key=lambda n: self.needs[n].urgency())

    def summary(self) -> AgentStateSummary:
        active = [g for g in self.goals if g.active]
        top = max(active, key=lambda g: (g.priority, g.id)).id if active else None
        return AgentStateSummary(
            agent_id=self.id,
            life_stage=self.life_stage,
            age_ticks=self.age_ticks,
            location_id=self.location_id,
            needs={name: round(self.needs[name].level, 4) for name in sorted(self.needs)},
            money=round(self.money, 4),
            inventory={k: v for k, v in sorted(self.inventory.items()) if v > 0},
            emotion_valence=round(self.emotion.valence, 4),
            reputation=round(self.reputation, 4),
            top_goal=top,
        )

    # --- mutaciones locales -----------------------------------------------
    def decay_needs(self, health_factor: float = 1.0) -> None:
        for name in sorted(self.needs):
            self.needs[name].decay(health_factor if name == "health" else 1.0)

    def apply_need_deltas(self, deltas: dict[str, float]) -> None:
        for name, delta in sorted(deltas.items()):
            if name in self.needs:
                self.needs[name].apply(delta)

    def add_inventory(self, deltas: dict[str, int]) -> None:
        for item, delta in sorted(deltas.items()):
            self.inventory[item] = max(0, self.inventory.get(item, 0) + delta)

    def apply_outcome(self, outcome: ActionOutcome) -> None:
        """Incorpora el resultado objetivo: necesidades, inventario, dinero, posición y emoción.

        Es el único punto donde ``location_id`` se actualiza, y siempre a partir
        de lo que el mundo resolvió (``outcome.new_location``).
        """
        self.apply_need_deltas(outcome.need_deltas)
        self.add_inventory(outcome.inventory_deltas)
        self.money = round(max(0.0, self.money + outcome.money_delta), 6)
        if outcome.new_location is not None:
            self.location_id = outcome.new_location
            self.bump_counter(f"visit:{outcome.new_location}")
        self.emotion.nudge(outcome.valence, arousal=abs(outcome.valence))
        self.bump_counter(f"action:{outcome.action}")
        if outcome.success:
            self.bump_counter(f"success:{outcome.action}")

