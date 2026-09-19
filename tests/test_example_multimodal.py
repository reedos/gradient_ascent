"""The multimodal example, and the content-parts interface it is built on.

Two things are checked here that nothing else checks. First the example: a picture and words go
into one request, in that order, and the reply either parses into the two fields asked for or is
reported as not having them -- it is never filled in. Second the interface: `Message.content`
still takes a plain string everywhere it used to, the stub reads a parts list deterministically,
and the two real backends either translate a part into their documented shape or raise a
`NotImplementedError` that says what to do instead. No test here calls an API.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common import model as model_mod  # noqa: E402
from examples.common.model import (  # noqa: E402
    AudioPart,
    ImagePart,
    Message,
    StubModel,
    StubResponse,
    TextPart,
    content_payload,
    content_text,
)
from examples.common.trace import Tracer  # noqa: E402
from examples.multimodal.run import LEVEL, build_request, run  # noqa: E402

QUESTION = "Read the model number and the serial number off this rating plate."
PLATE = ImagePart(media_type="image/jpeg", data="ZmFrZQ==", label="rating-plate.jpg")


def _tracer() -> Tracer:
    return Tracer(example="multimodal", level=LEVEL, model_id="stub-1", stub=True)


class MultimodalExampleTests(unittest.TestCase):
    def test_a_readable_plate_parses_into_the_two_fields(self) -> None:
        model = StubModel([StubResponse(text="MODEL: DW-480\nSERIAL: HLV480-22719")])
        answer = run(QUESTION, model, _tracer(), image=PLATE)
        self.assertIn("DW-480", answer.text)
        self.assertIn("HLV480-22719", answer.text)
        self.assertEqual(answer.citations, ["rating-plate.jpg"])

    def test_an_unreadable_plate_is_reported_not_invented(self) -> None:
        model = StubModel([StubResponse(text="MODEL: UNREADABLE\nSERIAL: UNREADABLE")])
        answer = run(QUESTION, model, _tracer(), image=PLATE)
        self.assertNotIn("DW-", answer.text)
        self.assertEqual(answer.citations, [])

    def test_the_picture_comes_before_the_words(self) -> None:
        # Anthropic's vision guide recommends an image-then-text structure, and both backends
        # send the parts in the order they are given
        messages = build_request(PLATE, "it is the one in the utility room", QUESTION)
        parts = messages[-1].content
        self.assertIsInstance(parts, list)
        self.assertIsInstance(parts[0], ImagePart)
        self.assertTrue(all(isinstance(p, TextPart) for p in parts[1:]))

    def test_a_transcript_travels_as_text_beside_the_picture(self) -> None:
        with_note = content_text(build_request(PLATE, "utility room", QUESTION)[-1].content)
        without = content_text(build_request(PLATE, "", QUESTION)[-1].content)
        self.assertIn("utility room", with_note)
        self.assertNotIn("utility room", without)

    def test_every_step_is_decided_by_code(self) -> None:
        tracer = _tracer()
        run(QUESTION, StubModel([StubResponse(text="MODEL: DR-210\nSERIAL: A1B2C3D4")]), tracer, image=PLATE)
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)
        self.assertEqual(LEVEL, 1)

    def test_image_now_has_a_default_so_one_question_is_a_complete_call(self) -> None:
        # `image` used to be required with no default, which record_trace.py's shared
        # (text, model, tracer) convention cannot fill in from --question alone. The default is
        # a label-only stand-in, the same way this repo stands in for a photo everywhere else.
        model = StubModel([StubResponse(text="MODEL: UNREADABLE\nSERIAL: UNREADABLE")])
        answer = run(QUESTION, model, _tracer())
        self.assertEqual(answer.citations, [])

    def test_record_trace_now_classifies_multimodal_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("multimodal")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


class ContentPartsTests(unittest.TestCase):
    def test_a_plain_string_still_works_everywhere(self) -> None:
        message = Message(role="user", content="just text")
        self.assertEqual(content_text(message.content), "just text")
        self.assertEqual(content_payload(message.content), "just text")
        self.assertEqual(model_mod._ollama_message(message), {"role": "user", "content": "just text"})
        self.assertEqual(model_mod._anthropic_content(message.content), "just text")

    def test_content_text_names_the_part_without_inventing_a_token_cost(self) -> None:
        text = content_text([TextPart(text="what is this?"), PLATE, AudioPart(media_type="audio/wav", label="note.wav")])
        self.assertIn("what is this?", text)
        self.assertIn("[image image/jpeg: rating-plate.jpg]", text)
        self.assertIn("[audio audio/wav: note.wav]", text)
        self.assertNotIn("ZmFrZQ==", text, "base64 bytes must not be counted as prompt text")

    def test_the_stub_reads_a_parts_list_deterministically(self) -> None:
        seen: list[str] = []

        def responder(messages, tools):
            del tools
            seen.append(content_text(messages[-1].content))
            return StubResponse(text="MODEL: DW-300\nSERIAL: X1")

        model = StubModel(responder, model_id="stub-parts")
        message = Message(role="user", content=[PLATE, TextPart(text=QUESTION)])
        first = model.complete([message], max_tokens=50)
        second = model.complete([message], max_tokens=50)
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(first.tokens_in, second.tokens_in, "token counting must be deterministic")
        self.assertGreater(first.tokens_in, 0)

    def test_ollama_sends_images_as_base64_in_the_images_array(self) -> None:
        payload = model_mod._ollama_message(Message(role="user", content=[PLATE, TextPart(text=QUESTION)]))
        self.assertEqual(payload["images"], ["ZmFrZQ=="])
        self.assertEqual(payload["content"], QUESTION)

    def test_ollama_refuses_a_url_image_rather_than_dropping_it(self) -> None:
        by_url = ImagePart(media_type="image/png", url="https://example.invalid/a.png")
        with self.assertRaises(NotImplementedError) as caught:
            model_mod._ollama_message(Message(role="user", content=[by_url]))
        self.assertIn("base64", str(caught.exception))

    def test_ollama_refuses_audio_and_says_what_to_do_instead(self) -> None:
        with self.assertRaises(NotImplementedError) as caught:
            model_mod._ollama_message(Message(role="user", content=[AudioPart(media_type="audio/wav")]))
        self.assertIn("Transcribe", str(caught.exception))

    def test_anthropic_builds_the_documented_image_block(self) -> None:
        blocks = model_mod._anthropic_content([PLATE, TextPart(text=QUESTION)])
        self.assertEqual(
            blocks[0],
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "ZmFrZQ=="}},
        )
        self.assertEqual(blocks[1], {"type": "text", "text": QUESTION})

    def test_anthropic_builds_the_documented_url_source(self) -> None:
        blocks = model_mod._anthropic_content([ImagePart(media_type="image/png", url="https://example.invalid/a.png")])
        self.assertEqual(blocks[0]["source"], {"type": "url", "url": "https://example.invalid/a.png"})

    def test_anthropic_refuses_audio_and_says_what_to_do_instead(self) -> None:
        with self.assertRaises(NotImplementedError) as caught:
            model_mod._anthropic_content([AudioPart(media_type="audio/mp3")])
        self.assertIn("Transcribe", str(caught.exception))

    def test_a_parts_message_survives_the_turn_joining_rule(self) -> None:
        # the API alternates turns, so two user messages in a row are joined; a string and a
        # block list cannot be concatenated, so both become blocks
        payload = model_mod.ClaudeModel("claude-sonnet-5", api_key="test-key-not-real").build_payload(
            [
                Message(role="user", content="first, as text"),
                Message(role="user", content=[PLATE, TextPart(text="second, with a picture")]),
            ]
        )
        self.assertEqual(len(payload["messages"]), 1)
        blocks = payload["messages"][0]["content"]
        self.assertEqual([b["type"] for b in blocks], ["text", "image", "text"])

    def test_an_image_in_a_system_message_is_refused(self) -> None:
        model = model_mod.ClaudeModel("claude-sonnet-5", api_key="test-key-not-real")
        with self.assertRaises(ValueError):
            model.build_payload([Message(role="system", content=[PLATE])])

    def test_content_payload_keeps_the_parts_apart_for_a_cache_key(self) -> None:
        one = content_payload([ImagePart(media_type="image/png", data="AAAA")])
        two = content_payload([ImagePart(media_type="image/png", data="BBBB")])
        self.assertNotEqual(one, two, "two different images must not share a cache entry")


if __name__ == "__main__":
    unittest.main()
