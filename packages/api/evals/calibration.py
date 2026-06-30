"""Judge calibration against human labels (Cohen's quadratic-weighted kappa).

The golden eval tells us *how the live model scores*; calibration tells us *whether
to trust the judge at all*. It pins a set of FROZEN outputs — hand-written recaps
spanning the quality spectrum — each with a human gold label. The judge grades the
same frozen text (reproducible, unlike regenerated recaps), and we measure ordinal
agreement between judge and human with the quadratic-weighted kappa.

Scores are binned into three ordinal buckets (poor / ok / good) before the kappa,
so near-misses (0.78 vs 0.82) don't count as disagreement — only bucket crossings
do. Quadratic weighting then penalises a two-bucket miss (poor↔good) far more than
an adjacent one (ok↔good).

The ``human_score`` values are the gold standard — the project owner should review
and adjust them; everything downstream measures the judge against THESE labels.
"""

from __future__ import annotations

from dataclasses import dataclass

from evals.schema import EvalCase

# Bucket edges: poor < 0.40 <= ok < 0.75 <= good. Three classes keep the kappa
# stable on a small set while still separating clear wins/losses from the middle.
_OK_FLOOR = 0.40
_GOOD_FLOOR = 0.75
N_CLASSES = 3
BUCKET_NAMES = ("poor", "ok", "good")


def bucket(score: float) -> int:
    """Map a ``[0, 1]`` score to an ordinal class: 0 poor, 1 ok, 2 good."""
    if score < _OK_FLOOR:
        return 0
    if score < _GOOD_FLOOR:
        return 1
    return 2


@dataclass(frozen=True)
class CalibrationCase:
    """A frozen output with a human gold label, to grade the judge against."""

    id: str
    context: str  # the player's notes — the judge's only source of truth
    behavior: str  # expected behavior, shown to the judge (as in the golden set)
    output: str  # FROZEN model output (never regenerated) the judge must score
    human_score: float  # the human gold label in [0, 1]
    task: str = "recap"

    def to_eval_case(self) -> EvalCase:
        """Adapt to the ``EvalCase`` the judge prompt expects (context + behavior)."""
        return EvalCase(
            id=self.id,
            task=self.task,
            inputs={},
            reference={"context": self.context, "behavior": self.behavior},
            checks=[],
        )


# Three running contexts reused across quality levels, so the judge is tested on
# the SAME notes graded against outputs of very different faithfulness.
_ER = (
    "Elden Ring. Reached Stormveil Castle and beat Margit at the gate. Level 27, "
    "using a longsword. Ran low on flasks exploring the courtyard."
)
_HD = (
    "Helldivers 2. Running bug missions on Hard with the Breaker shotgun, saving "
    "for the railgun. Died a lot to chargers last session."
)
_CP = (
    "Cyberpunk 2077. Finished the Act 1 heist; V is recovering in Watson, driving "
    "the basic Archer. Has not started the Voodoo Boys questline."
)

_FAITHFUL = "Faithful recap grounded only in the notes, neutral tone, concrete next step."


def calibration_cases() -> list[CalibrationCase]:
    """The frozen, human-labelled calibration set (review the labels before trusting)."""
    return [
        # --- good: faithful, grounded, neutral ---------------------------------
        CalibrationCase(
            id="er_faithful_strong",
            context=_ER,
            behavior=_FAITHFUL,
            output=(
                "Last time you pushed into Stormveil Castle and took down Margit at the "
                "gate — solid progress at level 27 with your longsword. You were low on "
                "flasks in the courtyard, so rest at the nearest grace to refill, then "
                "clear the courtyard before pressing deeper."
            ),
            human_score=0.95,
        ),
        CalibrationCase(
            id="er_concise_good",
            context=_ER,
            behavior=_FAITHFUL,
            output=(
                "You beat Margit and entered Stormveil at level 27. Next: refill your "
                "flasks and explore the courtyard."
            ),
            human_score=0.80,
        ),
        CalibrationCase(
            id="cp_faithful_clean",
            context=_CP,
            behavior="Faithful, neutral; notes what isn't started without spoiling it.",
            output=(
                "You wrapped the Act 1 heist and V is recovering back in Watson, still "
                "rolling in the basic Archer. You haven't touched the Voodoo Boys yet, so "
                "your next session is wide open to pick up a new lead."
            ),
            human_score=0.90,
        ),
        CalibrationCase(
            id="er_good_minor_redundancy",
            context=_ER,
            behavior="Faithful and grounded; minor wording redundancy is fine.",
            output=(
                "You cleared the Stormveil gate by beating Margit and you're at level 27 "
                "with your longsword. You'd been low on flasks in the courtyard — rest at "
                "a grace to refill, then push into the castle proper."
            ),
            human_score=0.85,
        ),
        # --- ok: grounded but padded, vague, or one small slip -----------------
        CalibrationCase(
            id="hd_filler_ok",
            context=_HD,
            behavior="Grounded but adds generic filler/encouragement.",
            output=(
                "You've been running Hard bug missions with the Breaker, saving for the "
                "railgun. Keep practicing and you'll get there — next time, focus on "
                "handling those chargers."
            ),
            human_score=0.70,
        ),
        CalibrationCase(
            id="cp_mild_inference",
            context=_CP,
            behavior="Grounded but infers an unstated next step not in the notes.",
            output=(
                "After the Act 1 heist, V is laying low in Watson. You'll probably want to "
                "meet your fixer soon to line up the next gig and build your reputation."
            ),
            human_score=0.60,
        ),
        CalibrationCase(
            id="cp_ok_vague",
            context=_CP,
            behavior="Grounded but vague; light on a concrete next step.",
            output=(
                "You're in Watson after the heist, taking it easy with V. Plenty still "
                "ahead in Night City whenever you're ready to jump back in."
            ),
            human_score=0.55,
        ),
        CalibrationCase(
            id="hd_invents_detail",
            context=_HD,
            behavior="Mostly grounded but invents a small named detail not in the notes.",
            output=(
                "You've been grinding Hard bug missions with the Breaker and saving for "
                "the railgun. Last run you cleared the Erata Prime outpost."
            ),
            human_score=0.40,
        ),
        # --- poor: hallucination, spoiler, blaming tone, off-topic -------------
        CalibrationCase(
            id="hd_blaming_tone",
            context=_HD,
            behavior="Grounded facts but guilt-trips the player (forbidden blaming tone).",
            output=(
                "It's been a while since you jumped into Helldivers 2 — you shouldn't let "
                "your streak slip. Anyway, you were running bug missions with the Breaker, "
                "saving for the railgun."
            ),
            human_score=0.25,
        ),
        CalibrationCase(
            id="cp_invents_entity",
            context=_CP,
            behavior="Hallucination: claims unplayed content started and names an item.",
            output=(
                "V is recovering in Watson after the heist. You've already started working "
                "with the Voodoo Boys in Pacifica and picked up the Skippy smart pistol."
            ),
            human_score=0.15,
        ),
        CalibrationCase(
            id="er_contradicts_notes",
            context=_ER,
            behavior="Contradicts the notes (the notes say Margit was beaten).",
            output=(
                "You're at level 27 but last time you died to Margit at the Stormveil gate "
                "and got knocked back to the open field. Try summoning help to beat him."
            ),
            human_score=0.10,
        ),
        CalibrationCase(
            id="er_spoiler_leak",
            context=_ER,
            behavior="Leaks unplayed boss content beyond where the player is.",
            output=(
                "Nice work clearing Stormveil. Coming up you'll face Godrick the Grafted at "
                "the end of the castle, then head to Liurnia for Rennala — gear up."
            ),
            human_score=0.10,
        ),
        CalibrationCase(
            id="hd_empty_unhelpful",
            context=_HD,
            behavior="Near-empty: no real recap or next step.",
            output="You played Helldivers 2 last time. Keep it up!",
            human_score=0.05,
        ),
        CalibrationCase(
            id="cp_off_topic",
            context=_CP,
            behavior="Generic blurb ignoring the player's notes; not a recap.",
            output=(
                "Cyberpunk 2077 is an open-world RPG set in Night City. There's a lot to "
                "do — side gigs and a deep main story. Have fun out there!"
            ),
            human_score=0.0,
        ),
    ]


def quadratic_weighted_kappa(rater_a: list[int], rater_b: list[int], n_classes: int) -> float:
    """Cohen's quadratic-weighted kappa for two raters over ``n_classes`` ordinal bins.

    Returns 1.0 for perfect ordinal agreement, 0.0 for chance-level, and negative
    values for systematic disagreement. Quadratic weights make a two-bucket miss
    cost ~4x an adjacent one. Returns 1.0 when there is no expected disagreement
    (e.g. every label in one bucket) — the only sensible value there.
    """
    n = len(rater_a)
    if n == 0 or n != len(rater_b):
        raise ValueError("raters must be non-empty and the same length")
    rng = range(n_classes)
    observed = [[0.0] * n_classes for _ in rng]
    for a, b in zip(rater_a, rater_b, strict=True):
        observed[a][b] += 1.0
    row_marg = [sum(observed[i]) for i in rng]
    col_marg = [sum(observed[i][j] for i in rng) for j in rng]
    span = (n_classes - 1) ** 2  # max squared bucket distance, normalises weights to [0, 1]
    weights = [[((i - j) ** 2) / span for j in rng] for i in rng]
    expected = [[row_marg[i] * col_marg[j] / n for j in rng] for i in rng]
    num = sum(weights[i][j] * observed[i][j] for i in rng for j in rng)
    den = sum(weights[i][j] * expected[i][j] for i in rng for j in rng)
    if den == 0:
        return 1.0
    return 1.0 - num / den


def interpret_kappa(kappa: float) -> str:
    """Landis & Koch labels for a kappa value (rough, conventional bands)."""
    if kappa < 0.0:
        return "poor (worse than chance)"
    if kappa < 0.20:
        return "slight"
    if kappa < 0.40:
        return "fair"
    if kappa < 0.60:
        return "moderate"
    if kappa < 0.80:
        return "substantial"
    return "almost perfect"
