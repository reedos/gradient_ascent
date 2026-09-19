"""Level 5: bring-up debug assistant. The model gets three tools, and every one of them only
reads: `test_log(serial)` reads a logged production result, `read_doc(cite)` reads one section of
the bench documents, and `measure(instrument, command)` sends one command to a bench instrument.
Nothing here lets the model set a voltage, a current limit, or an output, because
`examples.common.bench.is_read_only` is checked before `measure` ever calls an instrument's own
`send`: a command that is not read-only never reaches the instrument at all, whatever the model
asked for. See `docs/THE-BENCH.md`'s three-class table, reproduced on the page this example backs:
read only runs unattended, a command that sets state needs code checking it against
`SafetyEnvelope`, and enabling an output needs that plus a person's `Approval` naming the set
point. Only the first class is reachable through this file.

The board is already energized when the agent starts. `_bring_up` is a technician's own checked
sequence, through `GuardedSupply`, `GuardedLoad`, `SafetyEnvelope` and two `Approval`s, one for
each command that energizes the board, the same steps `tests/test_bench.py`'s `test_step_three`
runs. It is the one place in this file where a command sets anything, and the agent's own loop
never calls it and has no tool that could.

`decided_by` follows the one rule every level-5 example on this site follows
(`examples/common/trace.py`): the model's own output chooses which tool to call, with what
arguments, or chooses to stop, so every one of those is `decided_by: "model"`. Running the tool,
refusing it, and handing the result back are the program's decision every time, so they are
`decided_by: "code"` even when what the program decided was to refuse.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from evals.bench import BENCH_CORPUS_DIR, PRODUCTION_CSV
from evals.corpus import Section, load_sections
from examples.common.agent_loop import force_final
from examples.common.bench import Approval, Bench, GuardedLoad, GuardedSupply, SafetyEnvelope, is_read_only
from examples.common.model import Message, Model, ToolCall
from examples.common.tools import read_section
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 5
MAX_STEPS = 8
MAX_TOKENS = 5000

#: The set point a technician already brought the board up at, before the agent is given the
#: bench: 24.0 V in, 1.000 A out, the SRB-5030 test spec's own VOUT condition (`srb5030-test-spec#5`).
BOARD_VIN_V = 24.0
BOARD_IOUT_A = 1.0
#: A representative fixture-channel offset, illustrated: `docs/THE-BENCH.md` story 2 measures
#: FIX-03 reading about 30 mV low. The default bench this example builds carries that offset on
#: its DMM path so the `measure` tool has something real to find; a caller may pass a different
#: `Bench` (a clean one, or a different offset) to illustrate a different cause.
FIXTURE_DMM_OFFSET_V = -0.030

SYSTEM_PROMPT = (
    "A board failed the VOUT step in production. You have three read-only tools: "
    "test_log(serial) reads the logged production result for that serial, every step; "
    "read_doc(cite) reads one section of the bench documents (the datasheet, the test spec, the "
    "calibration procedure, the bring-up notebook, the ECN, the failure-analysis guide), cited as "
    "file#section; measure(instrument, command) sends one SCPI command to \"supply\", \"dmm\", "
    "\"load\", or \"scope\" and returns its response. Any command that would set a value or "
    "enable an output is refused before it reaches the instrument, so only ever send a command "
    "that queries. Decide what to check next from what the last call actually returned, not a "
    "fixed order. Call no tools, in your final turn, once you can name a cause and the next "
    "measurement a person should take."
)

TEST_LOG_TOOL = {
    "name": "test_log",
    "description": "Read the logged production test result for one serial, every step.",
    "parameters": {"type": "object", "properties": {"serial": {"type": "string"}}, "required": ["serial"]},
}
READ_DOC_TOOL = {
    "name": "read_doc",
    "description": "Read one section of the bench documents by citation, e.g. calibration-procedure#6.",
    "parameters": {"type": "object", "properties": {"cite": {"type": "string"}}, "required": ["cite"]},
}
MEASURE_TOOL = {
    "name": "measure",
    "description": (
        'Send one command to a bench instrument ("supply", "dmm", "load", or "scope") and return '
        "its response. A command that is not read-only is refused; it never reaches the instrument."
    ),
    "parameters": {
        "type": "object",
        "properties": {"instrument": {"type": "string"}, "command": {"type": "string"}},
        "required": ["instrument", "command"],
    },
}
TOOLS = [TEST_LOG_TOOL, READ_DOC_TOOL, MEASURE_TOOL]

ToolResult = tuple[str, list[str]]


def _bring_up(dmm_offset_v: float) -> Bench:
    """Everything a technician did before the agent gets the bench, through the checked,
    approved sequence: set the voltage and the current limit, get an `Approval` that names them,
    enable the supply, set the load, and get a second `Approval` for the enable that actually
    puts current through the board. Both commands `docs/THE-BENCH.md` classes as energizing a
    board are here, and each one needed a person. This is the only place in this file that sets
    anything; the agent's own tool cannot reach any of it."""
    bench = Bench(dmm_offset_v=dmm_offset_v)
    envelope = SafetyEnvelope()
    supply = GuardedSupply(bench, envelope)
    load = GuardedLoad(bench, envelope)
    supply.set_voltage(BOARD_VIN_V)
    supply.set_current_limit(4.0)
    supply.output_on(Approval("the test engineer", BOARD_VIN_V, 4.0, reason="VOUT bring-up confirmation"))
    load.set_current(BOARD_IOUT_A)
    load.input_on(
        Approval("the test engineer", BOARD_VIN_V, BOARD_IOUT_A, reason="VOUT bring-up confirmation")
    )
    return bench


def _test_log(serial: str, log_path: Path) -> ToolResult:
    with log_path.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["serial"] == serial]
    if not rows:
        return f"no rows logged for {serial}", []
    lines = [
        f"step {row['step']} {row['measurement']}={row['value']}{row['unit']} "
        f"(limits {row['lower_limit'] or '-'}..{row['upper_limit'] or '-'}) {row['result']}"
        + (f" note: {row['notes']}" if row["notes"] else "")
        for row in rows
    ]
    return "\n".join(lines), []


def _measure(instrument_name: str, command: str, bench: Bench) -> ToolResult:
    """Send one command, if and only if `is_read_only` says it only reads.

    `is_read_only` is the whole check, deliberately: the line between a query and a state change
    is written down once in `examples/common/bench.py` for every example on this site, and a
    second copy of it here would be a second copy to keep in step. It already covers the case
    that looks like a query and is not. `MEAS:VOLT:DC? 0.1` has a read-only header, but the
    multimeter uses that argument to set its DC range before it reads, and the range stays set
    for every later query with nothing in the error queue to say so, so an argument is read-only
    on exactly one header: the oscilloscope's `MEAS:VPP? CHAN1`, whose argument only says which
    channel to report.
    """
    instruments = {"supply": bench.supply, "dmm": bench.dmm, "load": bench.load, "scope": bench.scope}
    instrument = instruments.get(instrument_name)
    if instrument is None:
        return f"unknown instrument: {instrument_name!r}", []
    if not is_read_only(command):
        # The check that matters most: nothing past this line runs when it fails.
        # `instrument.send` is never called, so a command that would set state or enable an
        # output cannot reach the instrument through this tool no matter what the model asked
        # for.
        return (
            f"refused: {command!r} is not a read-only command; this tool can only query "
            f"{instrument_name}, never set it"
        ), []
    return instrument.send(command), []


def _run_tool(call: ToolCall, log_path: Path, sections: dict[str, Section], bench: Bench) -> ToolResult:
    if call.name == "test_log":
        return _test_log(str(call.arguments.get("serial", "")), log_path)
    if call.name == "read_doc":
        return read_section(sections, str(call.arguments.get("cite", "")))
    if call.name == "measure":
        args = call.arguments
        return _measure(str(args.get("instrument", "")), str(args.get("command", "")), bench)
    return f"unknown tool: {call.name}", []


def run(
    symptom: str,
    model: Model,
    tracer: Tracer,
    *,
    corpus_dir: Path = BENCH_CORPUS_DIR,
    log_path: Path = PRODUCTION_CSV,
    bench: Bench | None = None,
    max_steps: int = MAX_STEPS,
    max_tokens: int = MAX_TOKENS,
) -> Answer:
    sections = load_sections(corpus_dir)
    bench = bench if bench is not None else _bring_up(FIXTURE_DMM_OFFSET_V)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Board already energized under an approved set point",
        detail=f"{BOARD_VIN_V} V in, {BOARD_IOUT_A} A out; the agent's tools cannot reach this step",
    )
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=symptom)]

    citations: list[str] = []
    tokens_used = 0
    for _ in range(max_steps):
        completion = model.complete(messages, tools=TOOLS, max_tokens=400)
        tokens_used += completion.tokens_in + completion.tokens_out

        if not completion.tool_calls:
            tracer.record(
                kind="model",
                decided_by="model",
                title="Model states a cause and the next measurement",
                detail=completion.text[:200],
                tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out,
                ms=completion.ms,
            )
            return Answer(text=completion.text, citations=sorted(set(citations)))

        calls_desc = ", ".join(f"{c.name}({json.dumps(c.arguments, sort_keys=True)})" for c in completion.tool_calls)
        tracer.record(
            kind="model",
            decided_by="model",
            title="Model calls a tool",
            detail=calls_desc,
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        messages.append(Message(role="assistant", content=f"[called {calls_desc}]"))
        for call in completion.tool_calls:
            result_text, cites = _run_tool(call, log_path, sections, bench)
            citations.extend(cites)
            refused = result_text.startswith("refused:")
            title = "Refuse a command that sets state" if refused else f"Run tool: {call.name}"
            tracer.record(kind="code", decided_by="code", title=title, detail=result_text[:200])
            messages.append(Message(role="user", content=f"Result of {call.name}: {result_text}"))

        if tokens_used >= max_tokens:
            final = force_final(
                messages, model, tracer, reason=f"token budget reached: {tokens_used} >= {max_tokens}", max_tokens=400
            )
            return Answer(text=final.text, citations=sorted(set(citations)))

    final = force_final(messages, model, tracer, reason=f"step cap reached: {max_steps} steps", max_tokens=400)
    return Answer(text=final.text, citations=sorted(set(citations)))
