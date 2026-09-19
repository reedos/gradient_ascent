"""Track: running models locally. Estimates how much memory a model needs to run: the weights
(parameters times bits per weight) plus a KV cache (grows with context length and the number of
requests served at once).

This is an estimate, not a measurement of any real runtime. It counts the two costs every
runtime documents in some form -- weights and a KV cache -- and nothing else: not activation
memory, not a framework's own overhead, not the small extra a quantization method's higher-
precision tensors add on top of its nominal bits-per-weight figure. Real usage runs higher than
this number, never lower.

Both formulas are first principles, not a runtime's reported number:

    weights   = parameters * bits_per_weight / 8
    kv cache  = 2 * layers * kv_heads * head_dim * context * bytes_per_value * sequences

The 2 is the key tensor and the value tensor. `kv_heads` is the count of key/value heads, which
grouped-query attention makes smaller than the number of attention heads -- passing the attention
head count instead is the one mistake that silently inflates every number here, and a model's own
config is where the right figure comes from. A server that pages or shares cache blocks will use
less than `sequences` times one sequence; this counts the ceiling such a scheme avoids paying.
"""
from __future__ import annotations

from dataclasses import dataclass

from examples.common.model import Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 1  # local_inference is a track technique, not a rung on the ladder; see content/taxonomy.json

BYTES_PER_GIB = 1024**3


@dataclass(frozen=True)
class MemoryEstimate:
    weights_bytes: int
    kv_cache_bytes: int
    total_bytes: int

    @property
    def total_gib(self) -> float:
        return self.total_bytes / BYTES_PER_GIB


def weights_bytes(params: int, bits_per_weight: float) -> int:
    """Parameter count times bits per weight, converted to bytes. `bits_per_weight` is the
    caller's own average figure: 16 for fp16, roughly 4 for a 4-bit quantization such as Q4_K_M.
    A real quantized file usually averages a little above the bit width in its name, because not
    every tensor is quantized the same way (llama.cpp's quantize tool can leave the output tensor
    unquantized, for instance). This function models none of that; it takes the average given."""
    return round(params * bits_per_weight / 8)


def kv_cache_bytes(
    *, context_length: int, num_layers: int, num_kv_heads: int, head_dim: int, bytes_per_value: int = 2, num_sequences: int = 1
) -> int:
    """The key/value cache: two tensors (key and value) per layer, each sized
    context_length x num_kv_heads x head_dim at bytes_per_value bytes, times how many sequences
    are served at once. `num_kv_heads` is the key/value head count from the model's own config,
    which grouped-query attention makes smaller than the attention head count."""
    per_sequence = 2 * num_layers * context_length * num_kv_heads * head_dim * bytes_per_value
    return per_sequence * num_sequences


def estimate_memory(
    *,
    params: int,
    bits_per_weight: float,
    context_length: int,
    num_layers: int,
    num_kv_heads: int,
    head_dim: int,
    bytes_per_value: int = 2,
    num_sequences: int = 1,
) -> MemoryEstimate:
    w = weights_bytes(params, bits_per_weight)
    kv = kv_cache_bytes(
        context_length=context_length,
        num_layers=num_layers,
        num_kv_heads=num_kv_heads,
        head_dim=head_dim,
        bytes_per_value=bytes_per_value,
        num_sequences=num_sequences,
    )
    return MemoryEstimate(weights_bytes=w, kv_cache_bytes=kv, total_bytes=w + kv)


# (label, params, bits_per_weight, context_length, num_layers, num_kv_heads, head_dim, num_sequences)
# Round numbers chosen to be readable, shared by `python -m examples.local_inference --demo` and
# by `run` below. None is read off a particular model's published configuration.
SHAPES = [
    ("8B model, fp16, 8K context, 1 user", 8_000_000_000, 16.0, 8192, 32, 8, 128, 1),
    ("8B model, ~4-bit quantized, 8K context, 1 user", 8_000_000_000, 4.5, 8192, 32, 8, 128, 1),
    ("8B model, ~4-bit quantized, 32K context, 1 user", 8_000_000_000, 4.5, 32768, 32, 8, 128, 1),
    ("8B model, ~4-bit quantized, 8K context, 8 users", 8_000_000_000, 4.5, 8192, 32, 8, 128, 8),
]


def run(question: str, model: Model, tracer: Tracer) -> Answer:
    """Recordable entry point for `record_trace.py`. Ignores `question` and calls no model: this
    technique is arithmetic over numbers a caller supplies, not a question a model answers.
    Estimates the first of the illustrative shapes in `SHAPES` and records each formula's inputs
    and the total as `code` steps."""
    del question, model
    label, params, bits, ctx, layers, kv_heads, head_dim, seqs = SHAPES[0]
    w = weights_bytes(params, bits)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Estimate weights: parameters * bits_per_weight / 8",
        detail=f"{label}: {w / BYTES_PER_GIB:.2f} GiB",
    )
    kv = kv_cache_bytes(context_length=ctx, num_layers=layers, num_kv_heads=kv_heads, head_dim=head_dim, num_sequences=seqs)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Estimate KV cache: 2 * layers * kv_heads * head_dim * context * bytes_per_value * sequences",
        detail=f"{kv / BYTES_PER_GIB:.2f} GiB",
    )
    est = estimate_memory(
        params=params, bits_per_weight=bits, context_length=ctx, num_layers=layers,
        num_kv_heads=kv_heads, head_dim=head_dim, num_sequences=seqs,
    )
    tracer.record(kind="code", decided_by="code", title="Report total", detail=f"{est.total_gib:.2f} GiB")
    return Answer(text=f"{label}: {est.total_gib:.2f} GiB (weights and KV cache only; real usage runs higher)", citations=[])
