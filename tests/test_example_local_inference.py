"""Tests for examples/local_inference: a memory estimate (weights + KV cache) checked against
numbers computed by hand, not against any real model."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.local_inference.run import (  # noqa: E402
    LEVEL,
    SHAPES,
    estimate_memory,
    kv_cache_bytes,
    run,
    weights_bytes,
)


class WeightsBytesTests(unittest.TestCase):
    def test_16_bit_weights_is_two_bytes_per_parameter(self) -> None:
        # 1,000,000 params * 16 bits / 8 = 2,000,000 bytes, by hand
        self.assertEqual(weights_bytes(1_000_000, 16.0), 2_000_000)

    def test_4_bit_weights_is_half_a_byte_per_parameter(self) -> None:
        # 1,000,000 params * 4 bits / 8 = 500,000 bytes, by hand
        self.assertEqual(weights_bytes(1_000_000, 4.0), 500_000)

    def test_a_realistic_8b_model_at_fp16_is_16_gigabytes(self) -> None:
        # 8,000,000,000 * 16 / 8 = 16,000,000,000 bytes exactly, by hand
        self.assertEqual(weights_bytes(8_000_000_000, 16.0), 16_000_000_000)


class KvCacheBytesTests(unittest.TestCase):
    def test_a_small_hand_computed_shape(self) -> None:
        # 2 (K and V) * 2 layers * 10 context * 2 kv heads * 4 head_dim * 2 bytes/value
        # = 2*2*10*2*4*2 = 640 bytes, by hand
        got = kv_cache_bytes(context_length=10, num_layers=2, num_kv_heads=2, head_dim=4, bytes_per_value=2)
        self.assertEqual(got, 640)

    def test_a_realistic_shape_comes_to_exactly_one_gibibyte(self) -> None:
        # 2 * 32 layers * 8192 context * 8 kv heads * 128 head_dim * 2 bytes/value
        # = 1,073,741,824 bytes = exactly 2**30, by hand
        got = kv_cache_bytes(context_length=8192, num_layers=32, num_kv_heads=8, head_dim=128, bytes_per_value=2)
        self.assertEqual(got, 1_073_741_824)
        self.assertEqual(got, 2**30)

    def test_num_sequences_multiplies_the_cache_linearly(self) -> None:
        one = kv_cache_bytes(context_length=10, num_layers=2, num_kv_heads=2, head_dim=4, num_sequences=1)
        eight = kv_cache_bytes(context_length=10, num_layers=2, num_kv_heads=2, head_dim=4, num_sequences=8)
        self.assertEqual(eight, one * 8)

    def test_doubling_context_length_doubles_the_cache(self) -> None:
        short = kv_cache_bytes(context_length=1000, num_layers=4, num_kv_heads=2, head_dim=8)
        long = kv_cache_bytes(context_length=2000, num_layers=4, num_kv_heads=2, head_dim=8)
        self.assertEqual(long, short * 2)


class EstimateMemoryTests(unittest.TestCase):
    def test_total_is_the_sum_of_weights_and_kv_cache(self) -> None:
        est = estimate_memory(
            params=1_000_000, bits_per_weight=16.0, context_length=10, num_layers=2, num_kv_heads=2, head_dim=4
        )
        self.assertEqual(est.weights_bytes, 2_000_000)
        self.assertEqual(est.kv_cache_bytes, 640)
        self.assertEqual(est.total_bytes, 2_000_640)

    def test_total_gib_matches_total_bytes_divided_by_2_to_the_30(self) -> None:
        est = estimate_memory(
            params=8_000_000_000, bits_per_weight=16.0, context_length=8192, num_layers=32, num_kv_heads=8, head_dim=128
        )
        self.assertAlmostEqual(est.total_gib, est.total_bytes / 1024**3)

    def test_a_smaller_bits_per_weight_never_increases_the_estimate(self) -> None:
        kwargs = dict(params=8_000_000_000, context_length=8192, num_layers=32, num_kv_heads=8, head_dim=128)
        fp16 = estimate_memory(bits_per_weight=16.0, **kwargs)
        q4 = estimate_memory(bits_per_weight=4.0, **kwargs)
        self.assertLess(q4.total_bytes, fp16.total_bytes)
        # only the weights term should move; the KV cache term is independent of bits_per_weight
        self.assertEqual(q4.kv_cache_bytes, fp16.kv_cache_bytes)


class RecordableRunWrapperTests(unittest.TestCase):
    """`run(text, model, tracer)` is the entry point `record_trace.py` calls: arithmetic over
    the first illustrative shape in `SHAPES`, ignoring `text` and calling no model."""

    def test_declares_its_level(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))

    def test_run_estimates_the_first_shape_and_records_only_code_steps(self) -> None:
        tracer = Tracer(example="local_inference", level=LEVEL, model_id="stub-1")
        answer = run("anything", StubModel([]), tracer)
        label = SHAPES[0][0]
        self.assertIn(label, answer.text)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertGreaterEqual(len(tracer.steps), 3)

    def test_record_trace_now_classifies_local_inference_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("local_inference")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
