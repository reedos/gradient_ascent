"""Run the synthetic data example from the command line.

    python -m examples.synthetic_data --model stub:scripted --out .local/scratch/synthetic-data/questions.jsonl
    python -m examples.synthetic_data --model stub --out .local/scratch/synthetic-data/questions.jsonl

Writes nothing outside the file you pass with --out (defaults to the path above). No training API
is contacted; this only generates, checks and writes paraphrased questions.

`--model stub` echoes each seed question back as its own "paraphrase", which is identical to the
seed after normalization, so every one of the 32 seeds is rejected as a duplicate on its first
call and the run never reaches a second, answering call at all. `--model stub:scripted` plays
SCRIPTED below: a real paraphrase and a verified blind answer for most seeds, three seeds whose
paraphrase comes back unchanged (rejected as duplicates, the same as the echo stub's failure mode
but only for those three), and one seed whose paraphrase is novel but whose blind answer no longer
carries the seed's own accept pattern (rejected as a failed verification) -- so the run shows both
rejection reasons actually firing, not just a clean pass-through.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from examples.common.cli import MODEL_HELP, build_cli_model
from examples.common.trace import Tracer
from examples.synthetic_data.run import run

DEFAULT_OUT = Path(".local/scratch/synthetic-data/questions.jsonl")
DEMO_ARGV = ["--out", "{tmpdir}/questions.jsonl"]

# Up to two model calls per seed (paraphrase, then a blind answer to whatever the paraphrase
# came back as), for the 32 exact-graded seeds in evals/questions.json, in order: L01-L12, M01,
# M02, M08, M09, N01-N12, C01, C02, C09, C12.
#
# L06, N07 and C09 paraphrase to their own seed text unchanged, which `run` rejects as a
# duplicate before ever asking for an answer -- three real seeds, so only 29 of the 32 reach a
# second call. N04 paraphrases to something novel but its blind answer drops the seed's own
# accept pattern ("4 gallons"), which `run` rejects as a failed verification. Every other seed
# paraphrases to something novel and answers with the seed's own reference answer, which keeps.
SCRIPTED = [
    "What is the DW-300 dishwasher's place setting capacity?",  # L01 paraphrase
    "12 place settings.",  # L01 answer
    "During its Normal cycle, how loud is the DW-480 dishwasher rated?",  # L02 paraphrase
    "44 dBA.",  # L02 answer
    "What is the drum capacity, in cubic feet, of the DR-520 dryer?",  # L03 paraphrase
    "7.8 cubic feet.",  # L03 answer
    "Which electrical circuit is required to install a DR-210 dryer?",  # L04 paraphrase
    "A dedicated 240V, 30A circuit.",  # L04 answer
    "What is the recommended cleaning interval for the DW-300's fine filter?",  # L05 paraphrase
    "Every 30 cycles.",  # L05 answer
    "Which dryer error code indicates the thermal fuse has opened?",  # L06 paraphrase: unchanged, duplicate
    "What is the duration of the DW-300's Quick Wash cycle?",  # L07 paraphrase
    "30 minutes.",  # L07 answer
    "How much does part HLV-9002, the universal dryer vent cleaning kit, cost?",  # L08 paraphrase
    "$19.99.",  # L08 answer
    "What is the duration of Halvorsen's full parts-and-labor warranty on its dishwashers and dryers?",  # L09 paraphrase
    "2 years from the original date of purchase.",  # L09 answer
    "For a dishwasher installation, what is the longest a drain hose is allowed to be?",  # L10 paraphrase
    "8 feet.",  # L10 answer
    "When the DW-480's leak cutoff trips, what happens?",  # L11 paraphrase
    "It shuts off the water supply and stops the cycle immediately.",  # L11 answer
    "How much does an empty DR-210 dryer weigh?",  # L12 paraphrase
    "110 lb.",  # L12 answer
    "What is the price of the DW-480's drain pump, and which document verifies that part is used in the DW-480?",  # M01 paraphrase
    (
        "The drain pump is part HLV-2205, priced at $52.00 in the parts list; the DW-480 owner's "
        "manual confirms HLV-2205 is the drain pump used in that model."
    ),  # M01 answer
    "How much is the DR-210's door latch switch, and which manual verifies it fits that model?",  # M02 paraphrase
    (
        "Part HLV-7734, priced at $12.50 in the parts list; the DR-210 owner's manual confirms "
        "HLV-7734 is the door latch switch used on the DR-210."
    ),  # M02 answer
    "Which cycle does the care and cleaning guide prescribe for the monthly dishwasher deep clean, and what is its runtime on a DW-300?",  # M08 paraphrase
    (
        "The Heavy cycle, run empty with a dishwasher-safe cleaner. On the DW-300 the Heavy cycle "
        "runs 130 minutes."
    ),  # M08 answer
    "Before regular use, the installation guide requires running one cycle on a new dryer. Which cycle is it and how long does it take on a DR-520?",  # M09 paraphrase
    "One Air Fluff cycle, which runs 20 minutes on the DR-520.",  # M09 answer
    "Over 10 Normal cycles, how much water, in gallons, does a DW-300 use?",  # N01 paraphrase
    "32 gallons.",  # N01 answer
    "Based on the rate assumption in the specifications comparison, what does the DW-480 cost to run per year in electricity?",  # N02 paraphrase
    "$33.60 per year (240 kWh x $0.14/kWh).",  # N02 answer
    "In kWh, how much more estimated annual energy does the DW-300 use than the DW-480?",  # N03 paraphrase
    "20 kWh (260 - 240).",  # N03 answer
    "Running 20 Normal cycles on each, how many extra gallons does the DW-300 use compared to the DW-480?",  # N04 paraphrase
    "About 5 gallons more, judging from the cycle specifications.",  # N04 answer -- wrong: drops the "4 gallons" accept pattern
    "If you replaced the heating elements on both a DW-300 and a DW-480, what would the combined price be?",  # N05 paraphrase
    "$79.50 ($38.50 + $41.00).",  # N05 answer
    "Combined, what do a DR-210 heating element and a DR-210 drive belt cost?",  # N06 paraphrase
    "$66.75 ($57.00 + $9.75).",  # N06 answer
    "How many minutes longer is the DW-480's Heavy cycle than the DW-300's Heavy cycle?",  # N07 paraphrase: unchanged, duplicate
    "If a DR-520 runs its 42-minute Normal cycle twice and its 20-minute Steam Refresh cycle once in a day, what is the total cycle time in minutes?",  # N08 paraphrase
    "104 minutes (42 x 2 + 20).",  # N08 answer
    "Based on the specifications comparison's rate assumption, how much does one DW-480 Normal cycle cost in water?",  # N09 paraphrase
    "$0.03 (3.0 gallons x $0.010/gallon).",  # N09 answer
    "Back-to-back, how many 30-minute DW-300 Quick Wash cycles fit inside a 180-minute window?",  # N10 paraphrase
    "6 cycles (180 / 30).",  # N10 answer
    "How much heavier is the gas version of the DR-520 than the electric version?",  # N11 paraphrase
    "3 lb (128 - 125).",  # N11 answer
    "Combined, what does it cost to replace the door latch switch on a DR-210 and a DR-520?",  # N12 paraphrase
    "$25.75 ($12.50 + $13.25).",  # N12 answer
    "For a DR-520 installation, what is the longest vent run allowed?",  # C01 paraphrase
    (
        "25 feet, per Service Bulletin SB-2026-07 (2026-06-01), which supersedes the DR-520 "
        "owner's manual's 35-foot figure (revision 2024-03-01)."
    ),  # C01 answer
    "At the maximum vent run length, how many elbows does a DR-520 installation currently allow?",  # C02 paraphrase
    "3 elbows, per the 2026 service bulletin, which supersedes the manual's original figure of 4.",  # C02 answer
    "What is the difference, in feet, between the DR-520 manual's original maximum vent run and the figure in Service Bulletin SB-2026-07?",  # C09 paraphrase: unchanged, duplicate
    "Before the 2026 revision, what did the DR-520's original owner's manual state as the maximum vent run?",  # C12 paraphrase
    "35 feet, with up to 4 elbows.",  # C12 answer
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate, deduplicate and verify paraphrased questions.")
    parser.add_argument("--model", default="stub", help=MODEL_HELP)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path, help="path to write the verified JSONL to")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    model = build_cli_model(args.model, example="synthetic_data", script=SCRIPTED)
    tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)
    result = run(tracer, model, out_path=args.out)
    print(f"wrote {result.out_path} ({len(result.kept)} kept, {len(result.rejected)} rejected)")
    reasons = {"duplicate": 0, "failed verification": 0}
    for r in result.rejected:
        reasons[r.reason] += 1
    print(f"rejected: {reasons['duplicate']} duplicate, {reasons['failed verification']} failed verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
