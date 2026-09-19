"""Run the multimodal example from the command line.

    python -m examples.multimodal --model stub
    python -m examples.multimodal --model stub --transcript "it's the one in the utility room"
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import interactive_stub
from examples.common.model import ImagePart, build_model
from examples.common.trace import Tracer
from examples.multimodal.run import LEVEL, run

DEFAULT_QUESTION = "Read the model number and the serial number off this rating plate."
# A reference, not bytes: nothing in this repo ships a real photograph. A real caller reads the
# file and passes base64 in `data`, which is what both documented backends take.
SAMPLE_IMAGE = ImagePart(media_type="image/jpeg", url="file://rating-plate.jpg", label="rating-plate.jpg")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Level 1: a picture and words in one request.")
    parser.add_argument("--model", default="stub", help="stub | ollama:<tag> | claude:<id>")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--transcript", default="", help="a voice note, already transcribed")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="multimodal", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer, image=SAMPLE_IMAGE, transcript=args.transcript)
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
