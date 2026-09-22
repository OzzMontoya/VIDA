"""Motor de decisión basado en un modelo de lenguaje (``engine: llm_v1``).

El LLM es un componente cognitivo dentro del estado del agente, no "la mente
completa" (sección 13). Sólo elige entre las acciones legales que el mundo
permite, con su estado, percepción, creencias y memorias como contexto; el
mundo sigue resolviendo el resultado objetivo. Si la respuesta es inválida,
la API falla o el modelo declina, se recurre al motor por reglas y se deja
constancia en ``DecisionRecord.engine``.

Reproducibilidad: cada respuesta se guarda en una caché SQLite por hash del
prompt. Repetir una corrida con la misma semilla reutiliza las respuestas y
no vuelve a llamar a la API; el hash de eventos coincide.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from vida.agents.decision import DecisionContext, RuleBasedEngine
from vida.simulation.config import DecisionSection, LLMSection
from vida.simulation.events import DecisionRecord
from vida.world.actions import ActionProposal, InfoReply, InfoRequest
from vida.world.rules import FOOD_EFFECTS

log = logging.getLogger("vida.llm")

# Precio en dólares por millón de tokens (entrada, salida), para estimar el costo de una corrida.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.0, 50.0), "claude-opus-5": (5.0, 25.0), "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0), "claude-sonnet-4-6": (3.0, 15.0), "claude-haiku-4-5": (1.0, 5.0),
}

SYSTEM_PROMPT = """Eres el módulo de decisión de un agente en VIDA, una simulación científica de vidas artificiales.
Recibes una ficha del agente (personalidad, valores, necesidades, dinero, inventario), lo que percibe ahora,
lo que cree sobre el mundo (puede ser falso), sus recuerdos más relevantes y la lista de acciones legales.

Reglas:
- Elige exactamente una acción de la lista de candidatas, copiando su clave tal cual.
- Actúa como actuaría ESTE agente según su personalidad, valores, necesidades y experiencia; no como un asistente.
- Las necesidades van de 1.0 (satisfecha) a 0.0 (crítica); por debajo de 0.1 el agente puede morir.
- Las creencias sobre dónde hay recursos pueden ser erróneas: el mundo decide qué ocurre realmente.
- Responde sólo con el JSON pedido. La justificación es breve (máximo 30 palabras) y en español.
- No afirmes tener conciencia ni sentimientos; describe motivos conductuales."""

ACTION_HELP = {
    "rest": "descansar (recupera energía; más en casa)", "consume": "comer del inventario",
    "acquire": "comprar aquí", "work": "trabajar (gana dinero, gasta energía)", "study": "estudiar",
    "seek_care": "recibir atención médica (cuesta dinero)", "socialize": "conversar con",
    "ask_info": "preguntar dónde conseguir", "share_info": "contarle dónde hay", "move": "ir a", "idle": "no hacer nada",
}


class DecisionChoice(BaseModel):
    choice: str = Field(description="clave de la acción elegida, copiada de la lista de candidatas")
    rationale: str = Field(default="", description="motivo breve en español")


class ReplyChoice(BaseModel):
    kind: Literal["truth", "lie", "omit", "partial"]
    claimed_location: str | None = None
    rationale: str = ""


class ShareChoice(BaseModel):
    truthful: bool = True
    claimed_location: str | None = None
    rationale: str = ""


class LLMCache:
    """Caché de respuestas por hash del prompt (SQLite). Permite repetir corridas sin llamar a la API."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.path))
        self.con.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, model TEXT, response TEXT)")
        self.con.commit()

    @staticmethod
    def key_for(model: str, system: str, prompt: str, schema: dict[str, Any]) -> str:
        material = json.dumps([model, system, prompt, schema], sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def get(self, key: str) -> str | None:
        row = self.con.execute("SELECT response FROM responses WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def put(self, key: str, model: str, response: str) -> None:
        self.con.execute("INSERT OR REPLACE INTO responses (key, model, response) VALUES (?, ?, ?)", (key, model, response))
        self.con.commit()

    def close(self) -> None:
        self.con.close()


class LLMEngine:
    name = "llm_v1"  # se especializa por proveedor en __init__: llm_v1:anthropic | llm_v1:ollama

    def __init__(self, cfg: DecisionSection, *, client: Any | None = None, cache: LLMCache | None = None) -> None:
        self.cfg: LLMSection = cfg.llm
        self.name = f"llm_v1:{self.cfg.provider}"
        self.rules = RuleBasedEngine(cfg)
        self._client = client
        self.cache = cache if cache is not None else (LLMCache(self.cfg.cache_path) if self.cfg.cache_path else None)
        self.llm_agents: set[str] | None = set(self.cfg.agents) if self.cfg.agents is not None else None
        self.stats: dict[str, float] = {
            "calls": 0, "cache_hits": 0, "fallbacks": 0, "refusals": 0, "invalid": 0,
            "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
        }

    # --- cliente -----------------------------------------------------------
    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic  # import perezoso: sólo si de verdad se llama a la API

            self._client = anthropic.Anthropic(timeout=self.cfg.timeout_seconds)
        return self._client

    def uses_llm(self, agent_id: str) -> bool:
        return self.llm_agents is None or agent_id in self.llm_agents

    def estimated_cost_usd(self) -> float:
        if self.cfg.provider == "ollama":
            return 0.0  # modelo local: sin costo por token
        price_in, price_out = PRICES_PER_MTOK.get(self.cfg.model, (5.0, 25.0))
        return round((self.stats["input_tokens"] * price_in + self.stats["output_tokens"] * price_out) / 1e6, 4)

    # --- llamada con caché, validación y degradación ------------------------
    def _ask(self, prompt: str, schema_model: type[BaseModel]) -> BaseModel | None:
        schema = schema_model.model_json_schema()
        schema["additionalProperties"] = False
        key = LLMCache.key_for(f"{self.cfg.provider}/{self.cfg.model}", SYSTEM_PROMPT, prompt, schema)
        text = self.cache.get(key) if self.cache else None
        from_cache = text is not None
        if from_cache:
            self.stats["cache_hits"] += 1
        else:
            text = self._call_api(prompt, schema)
            if text is None:
                return None
        try:
            parsed = schema_model.model_validate_json(text)
        except ValidationError as exc:
            log.warning("Respuesta del LLM inválida (%s): %s", exc.__class__.__name__, text[:200])
            self.stats["invalid"] += 1
            return None
        if self.cache and not from_cache:
            self.cache.put(key, self.cfg.model, text)  # sólo se cachean respuestas bien formadas
        return parsed

    def _call_api(self, prompt: str, schema: dict[str, Any]) -> str | None:
        if self.cfg.provider == "ollama":
            return self._call_ollama(prompt, schema)
        return self._call_anthropic(prompt, schema)

    # --- proveedor Ollama (local, gratuito) --------------------------------
    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON con urllib (sin dependencias). Se puede sustituir en tests."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.cfg.timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _call_ollama(self, prompt: str, schema: dict[str, Any]) -> str | None:
        base = (self.cfg.base_url or "http://localhost:11434").rstrip("/")
        seed = int.from_bytes(hashlib.sha256(prompt.encode("utf-8")).digest()[:4], "big")
        # Modo JSON simple en lugar de gramática por esquema: la gramática de llama.cpp falla con
        # claves como "move@market". El formato se describe en el prompt y se valida con pydantic.
        example = {name: f"<{name}>" for name in schema.get("properties", {})}
        user = f"{prompt}\n\nResponde SOLO con JSON exactamente así: {json.dumps(example, ensure_ascii=False)}"
        options: dict[str, Any] = {"temperature": 0, "seed": seed, "num_predict": self.cfg.max_tokens}
        if self.cfg.num_gpu is not None:
            options["num_gpu"] = self.cfg.num_gpu
        payload = {
            "model": self.cfg.model, "stream": False, "format": "json",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
            "options": options,
        }
        self.stats["calls"] += 1
        try:
            data = self._post_json(f"{base}/api/chat", payload)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:200] if exc.fp else ""
            log.warning("Ollama respondió HTTP %s: %s; se usa el motor por reglas", exc.code, body)
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log.warning("No se pudo contactar a Ollama en %s (%s); se usa el motor por reglas", base, exc)
            return None
        except ValueError as exc:
            log.warning("Respuesta de Ollama no es JSON (%s); se usa el motor por reglas", exc)
            return None
        self.stats["input_tokens"] += int(data.get("prompt_eval_count") or 0)
        self.stats["output_tokens"] += int(data.get("eval_count") or 0)
        return (data.get("message") or {}).get("content")

    # --- proveedor Anthropic -----------------------------------------------
    def _call_anthropic(self, prompt: str, schema: dict[str, Any]) -> str | None:
        import anthropic

        output_config: dict[str, Any] = {"format": {"type": "json_schema", "schema": schema}}
        if self.cfg.effort:
            output_config["effort"] = self.cfg.effort
        request: dict[str, Any] = dict(
            model=self.cfg.model, max_tokens=self.cfg.max_tokens,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
            output_config=output_config,
        )
        self.stats["calls"] += 1
        try:
            if self.cfg.server_fallbacks:
                response = self.client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request)
            else:
                response = self.client.messages.create(**request)
        except anthropic.RateLimitError as exc:
            log.warning("Límite de tasa de la API (%s); se usa el motor por reglas", exc.__class__.__name__)
            return None
        except anthropic.APIStatusError as exc:
            log.warning("Error de la API %s: %s; se usa el motor por reglas", exc.status_code, exc.message)
            return None
        except anthropic.APIConnectionError as exc:
            log.warning("Sin conexión con la API (%s); se usa el motor por reglas", exc.__class__.__name__)
            return None
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.stats["input_tokens"] += getattr(usage, "input_tokens", 0) or 0
            self.stats["output_tokens"] += getattr(usage, "output_tokens", 0) or 0
            self.stats["cache_read_tokens"] += getattr(usage, "cache_read_input_tokens", 0) or 0
        if getattr(response, "stop_reason", None) == "refusal":
            self.stats["refusals"] += 1
            return None
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
        return text

    # --- construcción de prompts -------------------------------------------
    @staticmethod
    def _agent_card(ctx: DecisionContext) -> str:
        a = ctx.agent
        P = a.personality
        traits = (f"apertura {P.openness:.2f}, responsabilidad {P.conscientiousness:.2f}, extraversión {P.extraversion:.2f}, "
                  f"amabilidad {P.agreeableness:.2f}, neuroticismo {P.neuroticism:.2f}")
        needs = ", ".join(f"{n} {a.needs[n].level:.2f}" for n in sorted(a.needs))
        inv = ", ".join(f"{k}×{v}" for k, v in sorted(a.inventory.items()) if v > 0) or "vacío"
        tags = ", ".join(a.identity.self_description_tags) or "sin rasgos aún"
        values = ", ".join(f"{k} {v:.2f}" for k, v in sorted(a.identity.core_values.items()))
        return (f"Agente {a.name} ({a.id}), etapa {a.life_stage}, día {ctx.tick // ctx.ticks_per_day}, hora {ctx.hour:02d}.\n"
                f"Personalidad: {traits}.\nValores: {values}. Identidad observada: {tags}.\n"
                f"Necesidades: {needs}.\nDinero: {a.money:.2f}. Inventario: {inv}. Casa: {a.home_id}.")

    @staticmethod
    def _perception_text(ctx: DecisionContext) -> str:
        p = ctx.perception
        a = ctx.agent
        people = []
        for other in p.visible_agents:
            rel = a.relationships.get(other)
            model = a.beliefs.others.get(other)
            desc = f"{other}"
            if rel:
                desc += f" (familiaridad {rel.familiarity:.2f}, confianza {rel.trust:.2f}, afecto {rel.affection:.2f})"
            if model:
                desc += f" honestidad estimada {model.honesty_estimate:.2f}"
            people.append(desc)
        res = ", ".join(f"{r}: {s} a {ctx.prices.get(r, 0):.1f}" for r, s in sorted(p.visible_resources.items())) or "nada"
        return (f"Está en {p.location_id} ({p.location_type}, {'abierto' if p.is_open else 'cerrado'}). "
                f"Recursos visibles: {res}. Personas presentes: {'; '.join(people) or 'nadie'}.")

    @staticmethod
    def _beliefs_text(ctx: DecisionContext) -> str:
        lines = []
        for food in sorted(FOOD_EFFECTS):
            for loc, b in sorted(ctx.agent.beliefs.resources.get(food, {}).items()):
                src = b.source if b.source != "told" else f"contado por {b.source_agent}"
                lines.append(f"{food} en {loc} (confianza {b.confidence:.2f}, {src})")
        return "; ".join(lines) or "no sabe dónde hay comida"

    def _memories_text(self, ctx: DecisionContext) -> str:
        mems = ctx.memories[: self.cfg.max_memories]
        return "\n".join(f"- [{m.kind}] {m.content}" for m in mems) or "- (sin recuerdos relevantes)"

    def _candidates_text(self, cands: dict[str, tuple[float, ActionProposal]]) -> str:
        lines = []
        for key, (score, prop) in sorted(cands.items(), key=lambda kv: (-kv[1][0], kv[0])):
            desc = ACTION_HELP.get(prop.kind, prop.kind)
            if prop.target_agent:
                desc += f" {prop.target_agent}"
            if prop.resource:
                desc += f" {prop.resource}"
            if prop.target_location:
                desc += f" {prop.target_location}"
            hint = f" (heurística {score:.2f})" if self.cfg.include_heuristic_scores else ""
            lines.append(f"- {key}: {desc}{hint}")
        return "\n".join(lines)

    # --- interfaz DecisionEngine ------------------------------------------
    def decide(self, ctx: DecisionContext, rng: random.Random) -> tuple[ActionProposal, DecisionRecord]:
        if not self.uses_llm(ctx.agent.id):
            return self.rules.decide(ctx, rng)
        cands = self.rules.candidates(ctx)
        prompt = (f"{self._agent_card(ctx)}\n\nPercepción: {self._perception_text(ctx)}\n"
                  f"Creencias sobre comida: {self._beliefs_text(ctx)}\n\nRecuerdos relevantes:\n{self._memories_text(ctx)}\n\n"
                  f"Acciones candidatas (elige una clave):\n{self._candidates_text(cands)}")
        result = self._ask(prompt, DecisionChoice)
        if result is None or result.choice not in cands:
            if result is not None:
                self.stats["invalid"] += 1
            if not self.cfg.fallback_to_rules:
                raise RuntimeError("El LLM no produjo una acción válida y fallback_to_rules=false")
            self.stats["fallbacks"] += 1
            proposal, record = self.rules.decide(ctx, rng)
            record.engine = f"{self.name}/fallback:{self.rules.name}"
            return proposal, record
        score, proposal = cands[result.choice]
        proposal = proposal.model_copy(deep=True)
        if proposal.kind == "share_info":
            proposal.payload.update(self.decide_share(ctx, proposal.target_agent or "", proposal.resource or "", rng))
        proposal.rationale = result.rationale.strip()
        record = DecisionRecord(
            engine=self.name, chosen=result.choice, scores={k: v[0] for k, v in sorted(cands.items())},
            n_candidates=len(cands), rationale=proposal.rationale,
        )
        return proposal, record

    def decide_reply(self, ctx: DecisionContext, request: InfoRequest, rng: random.Random) -> InfoReply:
        if not self.uses_llm(ctx.agent.id):
            return self.rules.decide_reply(ctx, request, rng)
        a = ctx.agent
        belief = a.beliefs.best_location(request.resource)
        rel = a.relationships.get(request.asker_id)
        rel_txt = (f"familiaridad {rel.familiarity:.2f}, confianza {rel.trust:.2f}, afecto {rel.affection:.2f}"
                   if rel else "no la conoce")
        known = ", ".join(a.beliefs.known_locations)
        prompt = (f"{self._agent_card(ctx)}\n\n{request.asker_id} le pregunta dónde conseguir {request.resource}. "
                  f"Relación con quien pregunta: {rel_txt}.\n"
                  f"Lo que el agente cree: {self._beliefs_text(ctx)}.\nLugares conocidos: {known}.\n\n"
                  "Decide cómo responde: 'truth' (dice el lugar que cree), 'partial' (lo dice con poca seguridad), "
                  "'omit' (no responde) o 'lie' (afirma un lugar distinto). Si eliges truth/partial/lie indica claimed_location.")
        result = self._ask(prompt, ReplyChoice)
        base = dict(responder_id=a.id, resource=request.resource)
        if result is None:
            self.stats["fallbacks"] += 1
            return self.rules.decide_reply(ctx, request, rng)
        if result.kind == "omit":
            return InfoReply(**base, kind="omit")
        loc = result.claimed_location
        if loc is None or loc not in a.beliefs.known_locations:
            if belief is None:
                return InfoReply(**base, kind="omit")
            loc = belief.location_id
        if result.kind == "lie" and belief is not None and loc == belief.location_id:
            result.kind = "truth"  # decir la verdad no es mentir, aunque el modelo lo etiquete así
        conf = 0.5 if result.kind == "partial" else (round(belief.confidence, 6) if belief and loc == belief.location_id else 0.9)
        return InfoReply(**base, kind=result.kind, claimed_location=loc, claimed_confidence=conf)

    def decide_share(self, ctx: DecisionContext, target_agent: str, resource: str, rng: random.Random) -> dict[str, Any]:
        if not self.uses_llm(ctx.agent.id):
            return self.rules.decide_share(ctx, target_agent, resource, rng)
        a = ctx.agent
        belief = a.beliefs.best_location(resource)
        if belief is None:
            return {}
        rel = a.relationships.get(target_agent)
        rel_txt = f"familiaridad {rel.familiarity:.2f}, confianza {rel.trust:.2f}" if rel else "no lo conoce"
        prompt = (f"{self._agent_card(ctx)}\n\nVa a contarle a {target_agent} dónde hay {resource}. Relación: {rel_txt}.\n"
                  f"Lo que cree: {self._beliefs_text(ctx)}. Lugares conocidos: {', '.join(a.beliefs.known_locations)}.\n\n"
                  "Decide si dice la verdad (truthful=true, claimed_location = lo que cree) o engaña (truthful=false, otro lugar).")
        result = self._ask(prompt, ShareChoice)
        if result is None:
            self.stats["fallbacks"] += 1
            return self.rules.decide_share(ctx, target_agent, resource, rng)
        loc = result.claimed_location if result.claimed_location in a.beliefs.known_locations else belief.location_id
        truthful = result.truthful or loc == belief.location_id
        return {"claimed_location": loc if not truthful else belief.location_id, "truthful": truthful}
