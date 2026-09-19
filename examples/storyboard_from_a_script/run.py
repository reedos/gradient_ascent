"""Level 3: prompt chaining. Three fixed steps over one script, in this order, every time: split
it into scenes, propose shots inside each scene, then check in code that every script line is
inside a shot and every shot is inside the script and its own scene.

The model is called twice (scenes, then shots), but the code always runs both calls, always in
this order, and always hands the result to the same coverage check regardless of what either call
returns. The model never picks which step runs next and never decides whether a line counts as
covered; that comparison is arithmetic on line numbers, which is why every step below is
`decided_by="code"`. Drawing the shots is a different job and nothing here does it: `on_screen` is
a sentence a camera operator reads, not a frame.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 3
MAX_RETRIES = 1
WORDS_PER_MINUTE = 150  # a plain, unhurried read; see estimate_read_seconds
OVER_BUDGET_FACTOR = 3

#: The invented product video this example storyboards. Line 14 describes two things happening at
#: once, which is the trap for a shot list that assigns it only one shot; line 15 is pure
#: voiceover with no visual named at all, which is the trap for a coverage check that only looks
#: at lines next to an action. No real product, company or person is named.
SCRIPT_LINES: tuple[str, ...] = (
    "Open on a cluttered desk at dusk; a single overhead bulb flickers over stacks of paper.",
    "A hand pulls a plain shipping box from a mailer and sets it on the desk.",
    "The box's lid lifts, revealing the Solace lamp nested in molded paper, its arm catching the light.",
    'MARA (to camera): "This is the part everyone skips: the manual."',
    "Mara sets the paper insert aside unopened and stands the lamp upright.",
    "She presses the lamp's base once; the head tilts up on its own and the light glows warm, then "
    "shifts to daylight white.",
    'MARA: "Warm for reading. Daylight for everything else."',
    "Close on the base: a thin ring around it glows soft blue under her finger.",
    "Mara taps the ring twice; the light dims by half. She taps once more; it returns to full "
    "brightness.",
    'MARA: "Dim it without waking anyone else in the house."',
    "Wide shot: the desk is organized now, the lamp centered, its arm angled over an open notebook.",
    "Mara opens a laptop beside the lamp and starts typing, the light steady over her hands.",
    'MARA (not looking up): "It just stays out of the way."',
    "The lamp's arm folds flat against its base while, in the same beat, Mara zips the empty "
    "shipping box shut and sets it by the door.",
    "It packs down to the size of a paperback.",
    "Cut to a nightstand: the folded lamp sits beside a glass of water and a paperback novel.",
    'MARA: "I travel with mine."',
    "Close-up on the cord: woven fabric, not plastic, coiled neatly beside the base.",
    'MARA: "The cord alone outlasts most lamps twice its price."',
    "Mara unfolds the lamp on the nightstand and switches it to warm light with one press.",
    'MARA (quieter): "That\'s it. That\'s the whole lamp."',
    "Slow push-in on the lamp; the light holds steady as the room dims around it.",
    "Final card: the product name on a plain background, the glow from the lamp still visible "
    "behind it.",
    "The glow fades to black behind the card.",
    'MARA (V.O.): "One light, wherever you put it."',
)

#: What a recorder should pass as `run`'s first argument: the whole script, numbered the way a
#: shooting script actually is, one line per script line. `parse_script` reads this back apart.
SAMPLE_INPUT = "\n".join(f"{i}. {line}" for i, line in enumerate(SCRIPT_LINES, start=1))

_LINE_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")

SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene": {"type": "integer"},
                    "heading": {"type": "string"},
                    "first_line": {"type": "integer"},
                    "last_line": {"type": "integer"},
                },
                "required": ["scene", "heading", "first_line", "last_line"],
            },
        },
    },
    "required": ["scenes"],
}
SHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "shots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene": {"type": "integer"},
                    "shot": {"type": "integer"},
                    "size": {"type": "string"},
                    "on_screen": {"type": "string"},
                    "seconds": {"type": "number"},
                    "first_line": {"type": "integer"},
                    "last_line": {"type": "integer"},
                },
                "required": ["scene", "shot", "size", "on_screen", "seconds", "first_line", "last_line"],
            },
        },
    },
    "required": ["shots"],
}
SCENE_SYSTEM = (
    "Split the numbered script below into scenes: a scene number, a short slugline heading, and "
    "the first and last script line number it covers. Every line from 1 to the script's last "
    "line must fall inside exactly one scene, in order, with no gap. Reply as JSON matching the "
    "schema and nothing else."
)
SHOT_SYSTEM = (
    "Propose shots for the scenes below, given the full numbered script and the scene list. Each "
    "shot names its scene, a shot number local to that scene, a shot size, what is on screen, an "
    "estimated duration in seconds, and the first and last script line it covers. Cover every "
    "line, including a line with no visual named of its own: pair it with the shot playing when it "
    "is read. A line describing two things happening at once needs two shots, not one. Reply as "
    "JSON matching the schema and nothing else."
)


def parse_script(text: str) -> dict[int, str]:
    """A numbered script's lines, keyed by line number. Lines that do not match `N. text` are
    skipped rather than guessed at; a script the reader hands in is text they wrote, not a format
    this code invents rules for."""
    lines: dict[int, str] = {}
    for raw in text.strip().splitlines():
        match = _LINE_RE.match(raw)
        if match:
            lines[int(match.group(1))] = match.group(2).strip()
    return lines


def estimate_read_seconds(script_lines: dict[int, str]) -> float:
    """A rough, stated estimate of how long the script takes to read aloud: total words over a
    plain, unhurried pace. This is not a measurement of the finished video; see `OVER_BUDGET_FACTOR`
    for what it is used to flag."""
    words = sum(len(text.split()) for text in script_lines.values())
    return (words / WORDS_PER_MINUTE) * 60.0


@dataclass(frozen=True)
class Scene:
    number: int
    heading: str
    first_line: int
    last_line: int


@dataclass(frozen=True)
class Shot:
    scene: int
    number: int
    size: str
    on_screen: str
    seconds: float
    first_line: int
    last_line: int


@dataclass(frozen=True)
class CoverageReport:
    scenes: tuple[Scene, ...]
    shots: tuple[Shot, ...]  # shots that land inside the script; a scene-escaping shot stays here
    dropped_shots: tuple[str, ...]  # shots whose range falls outside the script entirely
    scene_escapes: tuple[str, ...]  # shots inside the script but outside their own scene's range
    uncovered_lines: tuple[int, ...]
    seconds_by_scene: dict[int, float]
    estimated_read_seconds: float
    over_budget: bool

    @property
    def total_seconds(self) -> float:
        return sum(self.seconds_by_scene.values())

    @property
    def text(self) -> str:
        lines = [f"{len(self.scenes)} scene(s), {len(self.shots)} shot(s)"]
        for scene in self.scenes:
            secs = self.seconds_by_scene.get(scene.number, 0.0)
            lines.append(f"  scene {scene.number} {scene.heading} (lines {scene.first_line}-{scene.last_line}, {secs:.1f}s)")
            for shot in self.shots:
                if shot.scene == scene.number:
                    lines.append(f"    shot {shot.number} {shot.size}: {shot.on_screen} ({shot.seconds:.1f}s, lines {shot.first_line}-{shot.last_line})")
        lines.append(f"total {self.total_seconds:.1f}s, estimated read {self.estimated_read_seconds:.1f}s")
        if self.uncovered_lines:
            lines.append(f"uncovered lines: {', '.join(str(n) for n in self.uncovered_lines)}")
        for note in self.dropped_shots:
            lines.append(f"dropped: {note}")
        for note in self.scene_escapes:
            lines.append(f"escapes its scene: {note}")
        if self.over_budget:
            lines.append(f"shot list runs to more than {OVER_BUDGET_FACTOR}x the estimated read time: check it by hand")
        return "\n".join(lines)


def _ask_json(
    messages: list[Message],
    schema: dict,
    validate: Callable[[dict], tuple[list[dict], list[str]]],
    key: str,
    model: Model,
    tracer: Tracer,
    *,
    title: str,
    max_tokens: int,
) -> list[dict]:
    """Ask for one JSON reply matching `schema`, validate it, and retry once with the validation
    error appended if it fails. Every attempt is `decided_by="code"`: the code always makes this
    call and always retries the same way, whatever the model said last time."""
    items: list[dict] = []
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=schema, max_tokens=max_tokens)
        tracer.record(
            kind="model",
            decided_by="code",
            title=title if attempt == 0 else f"{title}, retry with the validation error",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            payload = json.loads(completion.text)
        except json.JSONDecodeError as exc:
            items, problems = [], [f"invalid JSON: {exc}"]
        else:
            items, problems = validate(payload)
        tracer.record(kind="code", decided_by="code", title=f"Validate the {key} JSON", detail="; ".join(problems) or "valid")
        if not problems:
            return items
        if attempt < MAX_RETRIES:
            messages.append(Message(role="user", content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only."))
    return []  # exhausted the retry and still invalid: nothing here is safe to build a Scene or Shot from


def _validate_scenes(payload: dict) -> tuple[list[dict], list[str]]:
    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return [], ["missing or empty 'scenes' list"]
    problems = []
    for s in scenes:
        missing = [f for f in ("scene", "heading", "first_line", "last_line") if f not in s]
        if missing:
            problems.append(f"scene entry missing field(s): {', '.join(missing)}")
            continue
        if not isinstance(s["scene"], int) or not isinstance(s["first_line"], int) or not isinstance(s["last_line"], int):
            problems.append(f"scene {s.get('scene')}: scene, first_line and last_line must be integers")
        elif s["first_line"] > s["last_line"]:
            problems.append(f"scene {s['scene']}: first_line after last_line")
    return scenes, problems


def _validate_shots(payload: dict) -> tuple[list[dict], list[str]]:
    shots = payload.get("shots")
    if not isinstance(shots, list) or not shots:
        return [], ["missing or empty 'shots' list"]
    required = ("scene", "shot", "size", "on_screen", "seconds", "first_line", "last_line")
    problems = []
    for s in shots:
        missing = [f for f in required if f not in s]
        if missing:
            problems.append(f"shot entry missing field(s): {', '.join(missing)}")
            continue
        ints_ok = all(isinstance(s[f], int) for f in ("scene", "shot", "first_line", "last_line"))
        if not ints_ok or not isinstance(s["seconds"], (int, float)) or not str(s["size"]).strip() or not str(s["on_screen"]).strip():
            problems.append(f"scene {s.get('scene')} shot {s.get('shot')}: a field has the wrong type or is empty")
        elif s["first_line"] > s["last_line"]:
            problems.append(f"scene {s['scene']} shot {s['shot']}: first_line after last_line")
    return shots, problems


def check_coverage(scenes: tuple[Scene, ...], shots: tuple[Shot, ...], script_lines: dict[int, str]) -> CoverageReport:
    """The whole check, in code: every script line inside a shot, every shot inside the script and
    inside its own scene. Nothing here reads what a shot describes; it compares line numbers."""
    numbers = sorted(script_lines)
    lo, hi = (numbers[0], numbers[-1]) if numbers else (1, 0)
    scene_by_number = {s.number: s for s in scenes}
    accepted: list[Shot] = []
    dropped: list[str] = []
    escapes: list[str] = []
    covered: set[int] = set()
    for shot in shots:
        if shot.first_line > shot.last_line or shot.first_line < lo or shot.last_line > hi:
            dropped.append(f"scene {shot.scene} shot {shot.number}: lines {shot.first_line}-{shot.last_line} fall outside the script (1-{hi})")
            continue
        accepted.append(shot)
        covered.update(range(shot.first_line, shot.last_line + 1))
        scene = scene_by_number.get(shot.scene)
        if scene is None or shot.first_line < scene.first_line or shot.last_line > scene.last_line:
            where = f"lines {scene.first_line}-{scene.last_line}" if scene else "a scene number the scene list does not have"
            escapes.append(f"scene {shot.scene} shot {shot.number}: lines {shot.first_line}-{shot.last_line} fall outside {where}")
    uncovered = tuple(n for n in numbers if n not in covered)
    seconds_by_scene: dict[int, float] = {}
    for shot in accepted:
        seconds_by_scene[shot.scene] = seconds_by_scene.get(shot.scene, 0.0) + shot.seconds
    read_seconds = estimate_read_seconds(script_lines)
    total = sum(seconds_by_scene.values())
    return CoverageReport(
        scenes=tuple(scenes),
        shots=tuple(accepted),
        dropped_shots=tuple(dropped),
        scene_escapes=tuple(escapes),
        uncovered_lines=uncovered,
        seconds_by_scene=seconds_by_scene,
        estimated_read_seconds=read_seconds,
        over_budget=total > OVER_BUDGET_FACTOR * read_seconds,
    )


def run(script: str, model: Model, tracer: Tracer) -> CoverageReport:
    script_lines = parse_script(script)
    tracer.record(kind="code", decided_by="code", title="Read the numbered script", detail=f"{len(script_lines)} line(s)")

    scene_messages = [Message(role="system", content=SCENE_SYSTEM), Message(role="user", content=script)]
    scene_dicts = _ask_json(scene_messages, SCENE_SCHEMA, _validate_scenes, "scene", model, tracer, title="Split into scenes", max_tokens=500)
    scenes = tuple(Scene(d["scene"], d["heading"], d["first_line"], d["last_line"]) for d in scene_dicts)
    tracer.record(kind="code", decided_by="code", title="Parse the scene list", detail=", ".join(f"{s.number} {s.heading}" for s in scenes) or "none")

    scene_lines = "\n".join(f"scene {s.number}: {s.heading}, lines {s.first_line}-{s.last_line}" for s in scenes)
    shot_messages = [Message(role="system", content=SHOT_SYSTEM), Message(role="user", content=f"{script}\n\nScenes:\n{scene_lines}")]
    shot_dicts = _ask_json(shot_messages, SHOT_SCHEMA, _validate_shots, "shot", model, tracer, title="Propose shots for all scenes", max_tokens=1500)
    shots = tuple(Shot(d["scene"], d["shot"], d["size"], d["on_screen"], float(d["seconds"]), d["first_line"], d["last_line"]) for d in shot_dicts)
    tracer.record(kind="code", decided_by="code", title="Parse the shot list", detail=f"{len(shots)} shot(s) proposed")

    report = check_coverage(scenes, shots, script_lines)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check coverage against the script",
        detail=(
            f"{len(report.uncovered_lines)} uncovered line(s), {len(report.dropped_shots)} shot(s) "
            f"dropped, {len(report.scene_escapes)} shot(s) escape their scene"
        ),
    )
    return report
