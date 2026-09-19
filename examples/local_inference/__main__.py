"""Print a memory estimate for a few illustrative model shapes.

    python -m examples.local_inference --demo

The shapes below are round numbers chosen to be readable and to make each variable's effect
visible on its own. None of them is read off a particular model's published configuration, and
none describes anybody's deployment: for a real estimate, take the layer count, key/value head
count and head dimension from the model's own config. This is an estimate either way -- it counts
weights and a KV cache only, and real usage runs higher, never lower.
"""
from __future__ import annotations

import argparse
import sys

from examples.local_inference.run import SHAPES, estimate_memory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo", action="store_true", help="print the illustrative shapes above (the only mode today)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.demo:
        parser.error("pass --demo")

    print("ESTIMATE -- weights and KV cache only, in GiB. Real usage runs higher, never lower:")
    print("activation memory and a runtime's own overhead are not counted. Shapes are made up.")
    print()
    print(f"{'shape':<46}{'weights':>10}{'kv cache':>10}{'total':>10}")
    for label, params, bits, ctx, layers, kv_heads, head_dim, seqs in SHAPES:
        est = estimate_memory(
            params=params,
            bits_per_weight=bits,
            context_length=ctx,
            num_layers=layers,
            num_kv_heads=kv_heads,
            head_dim=head_dim,
            num_sequences=seqs,
        )
        print(
            f"{label:<46}{est.weights_bytes / 1024**3:>9.2f} {est.kv_cache_bytes / 1024**3:>9.2f} "
            f"{est.total_gib:>9.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
