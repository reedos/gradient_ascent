"""Level 3: draft an instrument control script from its programming manual, check every command
against the documented command set, and feed back what the simulated instrument's error queue
finds for another pass.

The model drafts the Tarnley TRN-2400 electronic load's script for one production test step
(load the board, read it back, unload it) from an excerpt of the load's own manual. Code never
takes the draft on trust: each attempt is sent to a scratch, unwired TRN-2400 -- no board, safe
to try anything -- and `SYST:ERR?` is read after every command. A drafter that leans on the
Maridun supply's conventions (a long-form keyword, the words `ON`/`OFF`) gets exactly what a real
Tarnley instrument would answer: `-113,"Undefined header"` or `-224,"Illegal parameter value"`.
Those errors go back to the model as the only feedback it gets, and it drafts again, capped at
`MAX_REVISIONS` attempts.

Only once a draft runs clean does code execute it against the board for real, and then through
`GuardedLoad` rather than through the load itself. Two of its commands are not the model's to send
outright: `CURR` is a set point, checked against `SafetyEnvelope` first, and `INP 1` puts current
through the board, which needs a person's `Approval` naming the rail and the current -- see
`_enable_load`. Both gates raise `SafetyRefusal`, which stops the run rather than returning a code
a caller could ignore.

Nothing here has ever been run against a real TRN-2400. `docs/THE-BENCH.md` is the simulation
this trades against, and `examples/common/bench.py` is what a command is checked against.
"""
from __future__ import annotations

import re

from evals.bench import load_bench_sections
from examples.common.bench import (
    NO_ERROR,
    Approval,
    Bench,
    ElectronicLoad,
    GuardedLoad,
    GuardedSupply,
    SafetyEnvelope,
    SafetyRefusal,
)
from examples.common.model import Message, Model
from examples.common.trace import Tracer
from dataclasses import dataclass, field

LEVEL = 3
MAX_REVISIONS = 2

#: The default task this example illustrates: production test step 3's load side, in the TRN-2400
#: manual's own words (`evals/bench/corpus/trn2400-programming-manual.md` section 5).
TASK = (
    "Set the TRN-2400 electronic load to 1.000 A constant current, enable it, read the board's "
    "terminal voltage and the actual current, then disable it."
)

DRAFT_SYSTEM = (
    "You draft a SCPI command script for a Tarnley TRN-2400 electronic load, from the manual "
    "excerpt you are given. Use only what the excerpt documents. One command per line, nothing "
    "else: no numbering, no commentary."
)
REVISE_SYSTEM = (
    "The simulated TRN-2400 rejected some of your commands; you are given the exact SYST:ERR? "
    "text for each one. Revise the script using only what the manual excerpt documents. One "
    "command per line, nothing else."
)

_UNIT_SUFFIX_RE = re.compile(r"[A-Za-z]+$")


def parse_reading(reply: str) -> float:
    """Parse one numeric reply, Maridun's bare or Tarnley's suffixed (`"1.0000A"` -> `1.0000`).

    `float()` is tried first, which is the correct parse for a Maridun reply and the good failure
    for a Tarnley one: it raises rather than silently returning a wrong number, which is what
    slicing a fixed number of characters off the reply would do instead.
    """
    try:
        return float(reply)
    except ValueError:
        return float(_UNIT_SUFFIX_RE.sub("", reply))


@dataclass(frozen=True)
class CheckedAttempt:
    """One drafted script and what the scratch instrument's error queue said about it."""

    commands: list[str]
    errors: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ScriptResult:
    task: str
    attempts: list[CheckedAttempt]
    final_commands: list[str]
    readings: dict[str, float] = field(default_factory=dict)
    approver: str = ""


def _manual_excerpt() -> str:
    sections = load_bench_sections()
    cites = (
        "trn2400-programming-manual#2",  # the three dialect differences
        "trn2400-programming-manual#3",  # the command table
        "trn2400-programming-manual#5",  # the fixed order of a load step
    )
    return "\n\n".join(sections[c].text for c in cites if c in sections)


def _parse_commands(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _draft(model: Model, tracer: Tracer, task: str, manual: str) -> list[str]:
    prompt = f"Manual excerpt:\n{manual}\n\nTask: {task}"
    completion = model.complete(
        [Message(role="system", content=DRAFT_SYSTEM), Message(role="user", content=prompt)],
        max_tokens=150,
    )
    tracer.record(
        kind="model", decided_by="code", title="Draft commands from the manual",
        detail=completion.text, tokens_in=completion.tokens_in, tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return _parse_commands(completion.text)


def _revise(
    model: Model, tracer: Tracer, task: str, manual: str, previous: list[str],
    errors: list[tuple[str, str]],
) -> list[str]:
    found = "\n".join(f"{command} -> {error}" for command, error in errors)
    prompt = (
        f"Manual excerpt:\n{manual}\n\nTask: {task}\n\nPrevious script:\n"
        + "\n".join(previous)
        + f"\n\nSYST:ERR? found:\n{found}"
    )
    completion = model.complete(
        [Message(role="system", content=REVISE_SYSTEM), Message(role="user", content=prompt)],
        max_tokens=150,
    )
    tracer.record(
        kind="model", decided_by="code", title="Revise using SYST:ERR? feedback",
        detail=completion.text, tokens_in=completion.tokens_in, tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    return _parse_commands(completion.text)


def _check_against_manual(commands: list[str], tracer: Tracer) -> list[tuple[str, str]]:
    """Try a draft against a scratch TRN-2400: unwired, no board, safe to send anything.

    This is the documented command set for the instrument, not a copy of it: `ElectronicLoad`
    accepts exactly what `trn2400-programming-manual.md` documents and rejects everything else,
    so a command the manual does not support fails here the same way it would on the real load.
    """
    scratch = ElectronicLoad()
    errors: list[tuple[str, str]] = []
    for command in commands:
        scratch.send(command)
        error = scratch.send("SYST:ERR?")
        if error != NO_ERROR:
            errors.append((command, error))
    detail = "clean" if not errors else "; ".join(f"{c!r} -> {e}" for c, e in errors)
    tracer.record(
        kind="code", decided_by="code",
        title="Check commands against the documented command set", detail=detail,
    )
    return errors


def _enable_load(load: GuardedLoad, approval: Approval) -> None:
    """Enable the TRN-2400's input: the one command in this script that puts current through the
    board, and so the one command a person has to have approved.

    The gate itself is `GuardedLoad.input_on` in `examples/common/bench.py`, next to the identical
    one `GuardedSupply.output_on` puts in front of `OUTP ON`. It refuses an enable with no
    `Approval`, one that names a rail or a current the bench is not actually at, and one that has
    already been spent, and it re-checks the load's own set point against `SafetyEnvelope` on the
    way through. This recipe adds nothing of its own to that; it names the step, because a reader
    following the drafted script needs to see where the model's line stops being the model's.
    """
    load.input_on(approval)


def _execute(
    commands: list[str], bench: Bench, load: GuardedLoad, approval: Approval,
) -> dict[str, float]:
    """Replay a checked, clean script against the board. `CURR` goes through the envelope; `INP 1`
    goes through `_enable_load`; everything else is a read or a plain set the manual documents."""
    readings: dict[str, float] = {}
    for command in commands:
        header, _, argument = command.partition(" ")
        header, argument = header.upper(), argument.strip()
        if header == "CURR" and argument:
            load.set_current(argument)
        elif header == "INP" and argument == "1":
            _enable_load(load, approval)
        else:
            reply = bench.load.send(command)
            if header == "MEAS:VOLT?":
                readings["vout_v"] = parse_reading(reply)
            elif header == "MEAS:CURR?":
                readings["iout_a"] = parse_reading(reply)
        error = bench.load.send("SYST:ERR?")
        if error != NO_ERROR:
            raise SafetyRefusal(f"a checked script still failed on the bench: {command!r} -> {error}")
    return readings


def run(
    task: str,
    model: Model,
    tracer: Tracer,
    *,
    max_revisions: int = MAX_REVISIONS,
    envelope: SafetyEnvelope | None = None,
    approval_supply: Approval | None = None,
    approval_load: Approval | None = None,
) -> ScriptResult:
    envelope = envelope if envelope is not None else SafetyEnvelope()
    approval_supply = approval_supply or Approval("the test engineer", 24.0, 4.000, reason=task)
    approval_load = approval_load or Approval("the test engineer", 24.0, 1.000, reason=task)

    manual = _manual_excerpt()
    tracer.record(
        kind="code", decided_by="code", title="Read the TRN-2400 manual",
        detail="trn2400-programming-manual #2, #3, #5",
    )

    commands = _draft(model, tracer, task, manual)
    errors = _check_against_manual(commands, tracer)
    attempts = [CheckedAttempt(commands=commands, errors=errors)]
    revisions = 0
    while errors and revisions < max_revisions:
        commands = _revise(model, tracer, task, manual, commands, errors)
        errors = _check_against_manual(commands, tracer)
        attempts.append(CheckedAttempt(commands=commands, errors=errors))
        revisions += 1
    if errors:
        tracer.record(
            kind="code", decided_by="code", title="Stop: revision cap reached",
            detail=f"still rejected after {revisions} revision(s); no person sees a script that "
            f"has not run clean on the simulator",
        )
        return ScriptResult(task=task, attempts=attempts, final_commands=commands)

    bench = Bench()
    supply = GuardedSupply(bench, envelope)
    load = GuardedLoad(bench, envelope)
    supply.set_voltage(24.0)
    supply.set_current_limit(4.000)
    supply.output_on(approval_supply)
    tracer.record(
        kind="code", decided_by="code", title="Power the board",
        detail="24.000 V, 4.000 A supply current limit, approved by the test engineer",
    )

    readings = _execute(commands, bench, load, approval_load)
    tracer.record(
        kind="code", decided_by="code", title="Run the checked script on the bench",
        detail=f"vout={readings.get('vout_v')} V, iout={readings.get('iout_a')} A",
    )

    supply.output_off()
    tracer.record(
        kind="code", decided_by="code", title="Disable the load and the supply", detail="",
    )

    return ScriptResult(
        task=task, attempts=attempts, final_commands=commands, readings=readings,
        approver=approval_load.approver,
    )
