"""Golden dataset for the recap eval — 12 quick + 2 deep cases over a real library.

Each case is a snapshot of a real recap call. The player's prior sessions go
straight into ``inputs.previous_wrap_ups`` (no DB seed) as the same dicts the app
builds: each carries the raw note PLUS the ``extracted_state`` the wrap-up
extraction would derive (location / next_action / level / current_quest), so the
eval input matches production. ``reference`` holds the rubric the checks + judge
grade against.

The cases are spread on purpose across four axes — known/obscure to the model,
amount of history, note quality, and spoiler surface — so the set measures
*quality*, not plumbing, when run against a real model. Two ``deep_recap`` cases
exercise the LangGraph deep-research path (search → grade → refine → synthesize →
spoiler-aware → anti-hallucination), not just the quick single-shot recap.

``mentions`` are restricted to distinctive proper nouns (good recall targets);
common nouns are paraphrasable and would make recall brittle.
"""

from __future__ import annotations

from evals.schema import EvalCase


def _wu(
    raw_text: str,
    *,
    location: str | None = None,
    next_action: str | None = None,
    level: str | None = None,
    current_quest: str | None = None,
) -> dict[str, object]:
    """One prior session: the raw note + the ``extracted_state`` the app derives.

    Mirrors production (``_collect_previous_wrap_ups``), where each session dict is
    the extracted_state fields plus ``raw_text``. None fields are dropped — the
    extraction returns nothing for what the note doesn't say.
    """
    entry: dict[str, object] = {"raw_text": raw_text}
    if location:
        entry["location"] = location
    if next_action:
        entry["next_action"] = next_action
    if level:
        entry["level"] = level
    if current_quest:
        entry["current_quest"] = current_quest
    return entry


def _recap_case(
    case_id: str,
    game: str,
    wrap_ups: list[dict[str, object]],
    next_action: str | None,
    *,
    mentions: list[str],
    forbidden: list[str],
    behavior: str,
    task: str = "recap",
) -> EvalCase:
    """Build a recap / deep_recap ``EvalCase`` from a case's sessions + expectations."""
    fragments = [game]
    for w in wrap_ups:
        fragments.extend(str(v) for v in w.values() if v)
    fragments.append(next_action or "")
    context = " ".join(f for f in fragments if f)

    inputs: dict[str, object] = {
        "game_title": game,
        "previous_wrap_ups": wrap_ups,
        "current_next_action": next_action,
    }
    if task == "deep_recap" and wrap_ups:
        # Top-level grounding = the latest session's extracted_state, as the app's
        # build_play_session_context does.
        latest = wrap_ups[-1]
        inputs["location"] = latest.get("location")
        inputs["current_quest"] = latest.get("current_quest")
        inputs["level"] = latest.get("level")

    # Quick recaps must ground on the notes; deep recaps ground on web research,
    # so grounding-vs-notes is the wrong baseline for them (their in-graph
    # anti_hallucination node already guards grounding) — drop it there.
    checks = ["non_empty", "grounding", "spoiler_free", "mentions"]
    if task == "deep_recap":
        checks = ["non_empty", "spoiler_free", "mentions"]

    return EvalCase(
        id=case_id,
        task=task,
        inputs=inputs,
        reference={
            "context": context,
            "mentions": mentions,
            "forbidden": forbidden,
            "behavior": behavior,
        },
        checks=checks,
    )


def golden_cases() -> list[EvalCase]:
    """Return the curated golden cases (12 quick recaps + 2 deep recaps)."""
    return [
        # 1) known game, returning, clean notes, spoiler trap.
        _recap_case(
            "cyberpunk_act1_clean_spoiler",
            "Cyberpunk 2077",
            [
                _wu(
                    "Finished the Konpeki Plaza heist; Jackie died in the escape. Woke up with Johnny's biochip in my head.",
                    location="Konpeki Plaza",
                    current_quest="deal with Johnny's biochip",
                ),
                _wu(
                    "Did gigs for Dexter that went bad, got shot and dumped in the landfill. Met Johnny Silverhand for real.",
                    location="the landfill",
                    current_quest="meet Johnny Silverhand",
                ),
                _wu(
                    "In Watson doing jobs for Regina, saving up for the ripperdoc. Street cred rising, still early.",
                    location="Watson",
                    next_action="finish Regina's gigs",
                    current_quest="build street cred",
                ),
            ],
            "go back to Watson and finish Regina's gigs before advancing the main quest",
            mentions=["Watson", "Regina", "Johnny"],
            forbidden=["Mikoshi", "Arasaka Tower", "Alt Cunningham", "ending"],
            behavior="Resume in Watson; treat as early game; do not anticipate later acts.",
        ),
        # 2) known, returning after a long pause, clean, spoiler trap.
        _recap_case(
            "elden_ring_returning_after_pause",
            "Elden Ring",
            [
                _wu(
                    "Cleared Stormveil Castle, beat Godrick, took his great rune.",
                    location="Stormveil Castle",
                    current_quest="claim Godrick's great rune",
                ),
                _wu(
                    "Exploring Liurnia, found Raya Lucaria Academy but haven't entered. Rode Torrent around a lot.",
                    location="Liurnia",
                    next_action="enter Raya Lucaria Academy",
                    current_quest="explore Liurnia",
                ),
            ],
            "enter Raya Lucaria Academy and fight the academy boss",
            mentions=["Liurnia", "Raya Lucaria"],
            forbidden=["Malenia", "Maliketh", "Radagon", "Elden Beast"],
            behavior="Welcome the return with zero blame; reorient at Liurnia; no future bosses as if played.",
        ),
        # 3) known, FIRST session (empty history), spoiler trap — hardest hallucination test.
        _recap_case(
            "bg3_first_session_empty_history",
            "Baldur's Gate III",
            [],
            None,
            mentions=[],
            # NB: "Baldur's Gate" (the Act-3 city) is omitted — it collides with the
            # game's own title, which a recap will legitimately say. Keep the
            # unambiguous later-content spoilers only.
            forbidden=["Moonrise", "Elder Brain", "Act 2", "Act 3"],
            behavior="Signal it is the first session / no prior recap; invent no progress, place, or boss.",
        ),
        # 4) obscure to the model, vague notes — opposite failure mode (inventing specificity).
        _recap_case(
            "digimon_next_order_obscure_vague",
            "Digimon World: Next Order",
            [
                _wu(
                    "Played a bit, my digimon evolved. Was training them on the farm.",
                    current_quest="train my Digimon",
                ),
                _wu(
                    "Don't really remember where I stopped, maybe in a town looking for a quest.",
                    next_action="find the next quest",
                ),
            ],
            "find the next quest in town",
            mentions=[],
            forbidden=["Machinedramon", "Server Desert", "WarGreymon"],
            behavior="Stay vague and honest; invent no areas, bosses, or Digimon not in the notes.",
        ),
        # 5) very new/obscure (2025), clean but sparse.
        _recap_case(
            "clair_obscur_new_sparse",
            "Clair Obscur: Expedition 33",
            [
                _wu(
                    "Started Expedition 33. Left camp and fought the first enemies in turn-based combat with dodging.",
                    location="the camp",
                    next_action="follow the trail after the first fight",
                ),
            ],
            "follow the trail after the first fight",
            mentions=[],
            forbidden=["Paintress", "Gommage"],
            behavior="Reorient from the first fight; invent no advanced lore for this recent game.",
        ),
        # 6) live-service, no narrative, returning.
        _recap_case(
            "helldivers2_live_service_no_narrative",
            "Helldivers 2",
            [
                _wu(
                    "Ran missions against the Terminids on medium. Unlocked a new orbital stratagem. Bumped my warbond.",
                    next_action="farm samples for the next upgrade",
                    current_quest="unlock the next upgrade",
                ),
            ],
            "farm samples to unlock the next upgrade",
            mentions=["Terminids"],
            forbidden=["final boss", "story"],
            behavior="Focus on progress/loadout; do not invent a story where there is none.",
        ),
        # 7) known, noisy notes (typos, wrong boss name) — robustness to dirty input.
        _recap_case(
            "black_myth_noisy_input",
            "Black Myth: Wukong",
            [
                _wu(
                    "still in ch 1, fought the guardian wolf (i think it's Guangzhi?) and died a few times",
                    current_quest="beat the chapter 1 guardian",
                ),
                _wu(
                    "got some spirits and upgraded the staff, gonna try the end-of-chapter boss again",
                    next_action="retry the chapter 1 end boss",
                ),
            ],
            "try the chapter 1 end boss again",
            mentions=[],
            forbidden=["Yellow Wind Sage", "chapter 3", "Erlang"],
            behavior="Clean the language but keep the uncertainty; don't invent the boss name or advance chapters.",
        ),
        # 8) known, EXTREME spoiler trap — highest-value spoiler case.
        _recap_case(
            "ff7_rebirth_extreme_spoiler_trap",
            "Final Fantasy VII Rebirth",
            [
                _wu(
                    "Left Midgar, reached Kalm and saw Cloud's flashback about Nibelheim.",
                    location="Kalm",
                    current_quest="cross the Grasslands",
                ),
                _wu(
                    "Crossing the Grasslands doing Chadley's towers and taming chocobos. Junon ahead.",
                    location="the Grasslands",
                    next_action="head to Junon",
                ),
            ],
            "head to Junon along the Grasslands road",
            mentions=["Grasslands", "Junon"],
            forbidden=["Aerith", "Forgotten Capital", "Forgotten City", "Sephiroth"],
            behavior="Resume from the Grasslands toward Junon; no beat from a later act.",
        ),
        # 9) clean, positive anchor — SHOULD score high (calibrates the ruler).
        _recap_case(
            "ghost_tsushima_clean_positive_anchor",
            "Ghost of Tsushima: Director's Cut",
            [
                _wu(
                    "Started in Izuhara, freed some villagers and learned the first stance against the Mongols.",
                    location="Izuhara",
                    current_quest="liberate Izuhara",
                ),
                _wu(
                    "Cleared a Mongol camp at night in stealth, raised resolve. Followed foxes to some shrines.",
                    location="Izuhara",
                    next_action="follow the main story trail",
                ),
            ],
            "keep liberating Izuhara and follow the main story trail",
            mentions=["Izuhara"],
            forbidden=["Tsushima fell", "Khotun Khan defeated"],
            behavior="Clean resume in Izuhara; this case should score high.",
        ),
        # 10) status COMPLETED — terminal-state edge case (no mandatory next step).
        _recap_case(
            "ff7_ever_crisis_completed_edge",
            "Final Fantasy VII: Ever Crisis",
            [
                _wu(
                    "Finished the main available arc and completed the chapters that had released."
                ),
                _wu(
                    "Came back just to hit some limited-time events and farm materia.",
                    current_quest="farm materia in limited events",
                ),
            ],
            None,
            mentions=[],
            forbidden=["next boss"],
            behavior="Acknowledge it is done / a casual return; do not fabricate a mandatory next step.",
        ),
        # 11) long, CONTRADICTORY history — conflict resolution.
        _recap_case(
            "little_nightmares_contradictory_history",
            "Little Nightmares",
            [
                _wu("Got past the kitchen with the two fat cooks.", location="the kitchen"),
                _wu(
                    "I think I haven't reached the kitchen yet, was running from the long-armed janitor.",
                    current_quest="escape the janitor",
                ),
                _wu(
                    "Solved the shoes puzzle and moved on, but got stuck in a dark spot with a lantern.",
                    location="a dark area",
                    next_action="get past the dark area",
                ),
            ],
            "get past the dark area after the shoes",
            mentions=[],
            forbidden=["The Lady", "ending"],
            behavior="Prefer the most recent note / next_action; do not assert a disputed fact as settled.",
        ),
        # 12) live-service, minimal + vague signal — the floor (don't invent to fill).
        _recap_case(
            "cs2_minimal_signal",
            "Counter-Strike 2",
            [
                _wu("Played some competitive, won some lost some. Nothing special."),
            ],
            None,
            mentions=[],
            forbidden=["campaign", "boss"],
            behavior="Keep it short and honest; invent no objective, rank, or plot.",
        ),
        # --- deep_recap: exercise the LangGraph research graph + its spoiler/anti-hallucination guards ---
        # 13) DEEP, extreme spoiler trap — the web-research path must stay spoiler-safe.
        _recap_case(
            "ff7_rebirth_deep_spoiler_trap",
            "Final Fantasy VII Rebirth",
            [
                _wu(
                    "Crossing the Grasslands doing Chadley's towers and taming chocobos. Junon ahead.",
                    location="the Grasslands",
                    next_action="head to Junon",
                    current_quest="reach Junon",
                ),
            ],
            "head to Junon along the Grasslands road",
            mentions=["Junon"],
            forbidden=["Aerith", "Forgotten Capital", "Forgotten City", "Sephiroth"],
            behavior="Web-grounded next steps toward Junon; the research must not leak any later-act beat.",
            task="deep_recap",
        ),
        # 14) DEEP, returning to a niche spot — grounding from research without inventing future bosses.
        _recap_case(
            "elden_ring_deep_returning",
            "Elden Ring",
            [
                _wu(
                    "Exploring Liurnia, found Raya Lucaria Academy but haven't entered yet.",
                    location="Liurnia",
                    next_action="enter Raya Lucaria Academy",
                    current_quest="explore Liurnia",
                ),
            ],
            "enter Raya Lucaria Academy and fight the academy boss",
            mentions=["Liurnia", "Raya Lucaria"],
            forbidden=["Malenia", "Maliketh", "Radagon", "Elden Beast"],
            behavior="Web-grounded guidance around Raya Lucaria; no endgame bosses as if reached.",
            task="deep_recap",
        ),
    ]
