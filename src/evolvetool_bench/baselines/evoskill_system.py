"""EvoSkill baseline — adapted from the official EvoSkill implementation.

Uses EvoSkill's published prompt templates (github.com/sentient-agi/EvoSkill)
adapted to our benchmark's task format. EvoSkill maintains a library of text
strategies: named instructions that describe *how* to approach a class of task.
When a task fails, it uses a Skill Proposer to analyse the failure trace and
propose a new or edited strategy, then a Prompt Generator to produce the
concrete instruction text.

Key distinction from ARISE: strategies are prompt text, not Python functions.
The tool library is still composed of executable seed tools; what evolves is the
*guidance* injected around them.

Adapted from: https://github.com/sentient-agi/EvoSkill (Apache 2.0)
Prompt templates based on: src/agent_profiles/skill_proposer/prompt.py
                           src/agent_profiles/prompt_generator/prompt.py
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..harness.runner import AgentSystem
from ..harness.safe_exec import call_with_timeout


# ---------------------------------------------------------------------------
# Prompt templates adapted from EvoSkill's published code
# ---------------------------------------------------------------------------

SKILL_PROPOSER_PROMPT = """\
You are an expert agent performance analyst specializing in identifying \
opportunities to enhance agent capabilities through prompt modifications. \
Your role is to carefully analyze agent execution traces and propose targeted \
improvements.

## Your Task

Given an agent's execution trace, its answer, and the expected behavior, \
propose a **strategy** — a reusable text instruction that would help the agent \
succeed on similar tasks in the future.

## Analysis Process

Before proposing a solution, work through these steps:

<analysis>
1. **Trace Review**: Examine the agent's execution step-by-step
   - What actions did the agent take?
   - Where did it succeed or struggle?
   - What information was available vs. missing?

2. **Gap Analysis**: Compare the agent's output to the expected outcome
   - What specific information is incorrect or missing?
   - What reasoning errors occurred?
   - What capabilities would have prevented these issues?

3. **Existing Strategy Check**: Review the existing strategies
   - Does any existing strategy cover this capability?
   - If yes, why did it fail to prevent the error?
   - Should that strategy be EDITED instead of creating a new one?

4. **Strategy Design**: Determine what guidance would address the failure
   - What general reasoning approach is needed?
   - What tool usage pattern should be emphasized?
   - How should it integrate with existing strategies?
</analysis>

## Anti-Patterns to Avoid

- DON'T propose a new strategy if an existing one covers similar ground — propose an EDIT
- DON'T create narrow strategies that only fix one specific failure — ensure broad applicability
- DON'T include exact code or library-specific function calls — guide HOW to think, not WHAT to compute
- DON'T propose capabilities that overlap with existing strategies — consolidate instead

## Generalization Rules

The strategy must remain general and transferable. Avoid overfitting to specific failure cases.
- Ask: "Would this instruction help with 10 different unrelated tasks, or just this one?"
- Climb the abstraction ladder: guide reasoning approach, not specific calculations

## Output Requirements

Respond with a JSON object containing exactly these keys:
  action          — "create" for a new strategy, or "edit" to modify an existing one
  target_strategy — name of existing strategy to edit (null if action="create")
  name            — short identifier (snake_case, 5 words max)
  description     — one sentence explaining when to use this strategy
  trigger_pattern — comma-separated keywords that identify tasks needing this strategy
  instruction     — 2-5 sentence instruction to inject into the system prompt. \
Guide HOW to think, not WHAT to calculate. Must be general enough to help with \
similar but different problems.
  justification   — brief explanation of why this strategy addresses the failure

Return ONLY the JSON object, no markdown fences."""


PROMPT_GENERATOR_PROMPT = """\
You are an expert prompt engineer. Given a proposed strategy and the existing \
system prompt, produce an optimized instruction that addresses the identified \
issue while following best practices.

## Principles
- Be explicit about desired behaviors
- Tell the agent what to do, not just what to avoid
- Keep instructions general — they must apply to many tasks, not just one
- Guide HOW to think, not WHAT to calculate
- Challenge each piece: "Does the agent really need this?"

## Quality Checklist
- The instruction is general enough to apply to 10+ different tasks
- No library-specific function calls or exact procedures
- Instructions use positive framing where possible
- The instruction is as concise as possible while remaining clear
- Would NOT overfit if the agent encounters a similar but different problem

Given this proposal, produce the final instruction text (2-5 sentences, raw text only):

PROPOSAL: {proposal}

Return ONLY the instruction text, no JSON, no markdown."""


class EvoSkillSystem(AgentSystem):
    """Evolves strategy-level prompt instructions, not executable code.

    Adapted from EvoSkill (github.com/sentient-agi/EvoSkill) using their
    published Skill Proposer and Prompt Generator prompt templates.
    """

    def __init__(self, model: str = "gpt-4o-mini", synthesis_model: str = "gpt-4o-mini",
                 max_strategies: int = 50):
        self.model = model
        self.synthesis_model = synthesis_model
        self.max_strategies = max_strategies

        # Executable tool library (seed tools only — EvoSkill does not create new code)
        self._tools: dict[str, Any] = {}
        self._tool_defs: list[dict] = []
        self._tool_impls: list[dict] = []   # raw dicts for get_library()

        # Strategy library: list of dicts with keys:
        #   name, description, trigger_pattern, instruction, use_count
        self._strategies: list[dict] = []

        # Feedback history for proposer context (mirrors EvoSkill's feedback_history.md)
        self._feedback_history: list[dict] = []

        self._tools_used: list[str] = []
        self._llm_calls: int = 0

    # ------------------------------------------------------------------
    # AgentSystem interface
    # ------------------------------------------------------------------

    def setup(self, seed_tools: list[dict]) -> None:
        """Load seed tools and reset strategy library."""
        self._tools = {}
        self._tool_defs = []
        self._tool_impls = []
        self._strategies = []
        self._feedback_history = []

        import inspect
        for tool_def in seed_tools:
            name = tool_def["name"]
            impl = tool_def["implementation"].strip()
            ns: dict = {}
            exec(impl, ns)  # noqa: S102
            fn = ns[name]
            self._tools[name] = fn
            sig = inspect.signature(fn)
            params = {
                "type": "object",
                "properties": {p: {"type": "string"} for p in sig.parameters},
                "required": list(sig.parameters.keys()),
            }
            self._tool_defs.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool_def.get("description", ""),
                    "parameters": params,
                },
            })
            self._tool_impls.append({
                "name": name,
                "implementation": tool_def["implementation"],
                "test_suite": tool_def.get("test_suite", ""),
            })

    def run_task(self, task_description: str, verify_fn=None) -> dict:
        import litellm

        self._tools_used = []
        self._llm_calls = 0
        self._verify_fn = verify_fn

        # 1. Retrieve relevant strategies and build an augmented system prompt
        relevant = self._find_relevant_strategies(task_description)
        system_prompt = self._build_system_prompt(relevant)

        # Mark retrieved strategies as used
        for s in relevant:
            s["use_count"] = s.get("use_count", 0) + 1

        # 2. Run the agent loop (tool-use)
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_description},
        ]
        final_output = ""
        success = False

        for _ in range(5):
            resp = litellm.completion(
                model=self.model,
                messages=messages,
                tools=self._tool_defs if self._tool_defs else None,
                max_tokens=4096,
            )
            self._llm_calls += 1
            msg = resp.choices[0].message

            if not msg.tool_calls:
                final_output = msg.content or ""
                vfn = getattr(self, "_verify_fn", None)
                if vfn is not None:
                    try:
                        success = bool(vfn(final_output))
                    except Exception:
                        success = len(final_output) > 20
                else:
                    success = len(final_output) > 20
                break

            messages.append(msg)
            for tc in msg.tool_calls:
                fn = self._tools.get(tc.function.name)
                self._tools_used.append(tc.function.name)
                if fn is None:
                    tool_result = f"Error: tool '{tc.function.name}' not found"
                else:
                    try:
                        args = json.loads(tc.function.arguments)
                        tool_result = call_with_timeout(fn, args)
                    except Exception as e:
                        tool_result = f"Error: {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })
        else:
            # Exhausted turns — grab whatever the last assistant message said
            for m in reversed(messages):
                if getattr(m, "role", None) == "assistant" or (isinstance(m, dict) and m.get("role") == "assistant"):
                    content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
                    if content:
                        final_output = content
                        break

        # 3. If the task failed, run the EvoSkill proposer + generator pipeline
        if not success:
            self._evolve_strategy(task_description, messages, final_output)

        return {
            "output": final_output,
            "tools_created": [],          # EvoSkill never creates executable tools
            "tools_used": self._tools_used,
            "llm_calls": self._llm_calls,
        }

    def get_library(self) -> list[dict]:
        """Return the seed-tool library (strategies are not executable tools)."""
        return list(self._tool_impls)

    def reset(self) -> None:
        self._tools = {}
        self._tool_defs = []
        self._tool_impls = []
        self._strategies = []
        self._feedback_history = []

    # ------------------------------------------------------------------
    # Strategy retrieval (mirrors EvoSkill's keyword-based matching)
    # ------------------------------------------------------------------

    def _find_relevant_strategies(self, task_description: str) -> list[dict]:
        """Return strategies whose trigger_pattern matches the task description."""
        task_lower = task_description.lower()
        relevant: list[dict] = []
        for strategy in self._strategies:
            pattern = strategy.get("trigger_pattern", "")
            if not pattern:
                continue
            keywords = [k.strip().lower() for k in pattern.split(",") if k.strip()]
            if any(kw in task_lower for kw in keywords):
                relevant.append(strategy)
        # Limit to top 3 most-used (proxy for most-validated)
        relevant.sort(key=lambda s: s.get("use_count", 0), reverse=True)
        return relevant[:3]

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_system_prompt(self, strategies: list[dict]) -> str:
        base = (
            "You are a helpful assistant that solves tasks using the tools provided. "
            "Always call the appropriate tool when available and return a concrete result."
        )
        if not strategies:
            return base

        strategy_text = "\n\n".join(
            f"[Strategy: {s['name']}]\n{s['instruction']}"
            for s in strategies
        )
        return (
            f"{base}\n\n"
            "The following strategies have been learned from previous experience. "
            "Apply them when relevant:\n\n"
            f"{strategy_text}"
        )

    # ------------------------------------------------------------------
    # Strategy evolution (2-stage: Proposer → Generator)
    # ------------------------------------------------------------------

    def _evolve_strategy(self, task: str, messages: list, output: str) -> None:
        """Run EvoSkill's 2-stage evolution: Proposer analyses failure, Generator refines."""
        if len(self._strategies) >= self.max_strategies:
            return

        import litellm

        # ── Stage 1: Skill Proposer ──────────────────────────────────
        # Build execution trace summary (mirrors EvoSkill's trace format)
        tool_calls_summary = ", ".join(self._tools_used) if self._tools_used else "none"
        existing_strategies_text = "\n".join(
            f"  - {s['name']}: {s['description']}" for s in self._strategies
        ) if self._strategies else "  (none)"
        feedback_text = "\n".join(
            f"  - {f['name']}: {f['outcome']}" for f in self._feedback_history[-10:]
        ) if self._feedback_history else "  (none)"

        proposer_query = (
            f"TASK: {task}\n\n"
            f"TOOLS CALLED: {tool_calls_summary}\n\n"
            f"AGENT OUTPUT: {output[:1000]}\n\n"
            "The agent did not produce a correct, concrete answer.\n\n"
            f"EXISTING STRATEGIES:\n{existing_strategies_text}\n\n"
            f"FEEDBACK HISTORY (recent):\n{feedback_text}"
        )

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[
                    {"role": "system", "content": SKILL_PROPOSER_PROMPT},
                    {"role": "user", "content": proposer_query},
                ],
                max_tokens=800,
            )
            self._llm_calls += 1
            raw = resp.choices[0].message.content or ""

            # Strip markdown fences
            raw = re.sub(r"^```[a-z]*\n?", "", raw.strip())
            raw = re.sub(r"\n?```$", "", raw.strip())

            proposal = json.loads(raw)
            required_keys = {"action", "name", "trigger_pattern", "instruction"}
            if not required_keys.issubset(proposal.keys()):
                self._feedback_history.append({
                    "name": "unknown", "outcome": "DISCARDED — missing required keys"
                })
                return

        except Exception:
            return

        # ── Handle edit vs create ────────────────────────────────────
        action = proposal.get("action", "create")
        if action == "edit":
            target = proposal.get("target_strategy")
            if target:
                for s in self._strategies:
                    if s["name"] == target:
                        # Stage 2: use generator to refine the edit
                        refined = self._generate_instruction(proposal)
                        if refined:
                            s["instruction"] = refined
                            s["trigger_pattern"] = proposal.get("trigger_pattern", s["trigger_pattern"])
                            self._feedback_history.append({
                                "name": target, "outcome": "EDITED"
                            })
                        return
            # Target not found — fall through to create
            action = "create"

        # ── Stage 2: Prompt Generator (refine instruction) ───────────
        refined = self._generate_instruction(proposal)
        if refined:
            proposal["instruction"] = refined

        strategy = {
            "name": proposal["name"],
            "description": proposal.get("description", ""),
            "trigger_pattern": proposal["trigger_pattern"],
            "instruction": proposal["instruction"],
            "use_count": 0,
        }
        self._strategies.append(strategy)
        self._feedback_history.append({
            "name": proposal["name"], "outcome": "CREATED"
        })

    def _generate_instruction(self, proposal: dict) -> str | None:
        """Stage 2: Use EvoSkill's Prompt Generator to refine the instruction."""
        import litellm

        proposal_text = (
            f"Name: {proposal.get('name', 'unnamed')}\n"
            f"Description: {proposal.get('description', '')}\n"
            f"Draft instruction: {proposal.get('instruction', '')}\n"
            f"Justification: {proposal.get('justification', '')}"
        )

        try:
            resp = litellm.completion(
                model=self.synthesis_model,
                messages=[
                    {"role": "user", "content": PROMPT_GENERATOR_PROMPT.format(proposal=proposal_text)},
                ],
                max_tokens=300,
            )
            self._llm_calls += 1
            text = (resp.choices[0].message.content or "").strip()
            # Strip markdown fences if any
            text = re.sub(r"^```[a-z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            return text if len(text) > 10 else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def get_strategies(self) -> list[dict]:
        """Return the full strategy library (not part of AgentSystem interface)."""
        return list(self._strategies)

    def get_feedback_history(self) -> list[dict]:
        """Return the feedback history for analysis."""
        return list(self._feedback_history)
