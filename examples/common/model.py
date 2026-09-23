"""The thin model interface every example is built on.

One `Model` protocol with three backends (`StubModel` for tests and dry runs, `OllamaModel` and
`ClaudeModel` for live runs) and one `Embedder` protocol with two backends (`StubEmbedder`,
`OllamaEmbedder`). Examples and the eval runner depend only on these protocols, never on a
specific backend, so a trace or a result file records which backend ran without the example's
own code caring which one it was.

Both real backends are import-safe: constructing one does no network I/O, and neither is called
by the test suite. `OllamaModel` never pulls a model; `ClaudeModel` reads its key from
`.local/api-keys.json` (gitignored) and takes no default beyond `DEFAULT_MODEL`.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Protocol

DEFAULT_MODEL = "claude-sonnet-5"


@dataclass(frozen=True)
class TextPart:
    text: str


@dataclass(frozen=True)
class ImagePart:
    """A reference to an image: base64 bytes in `data`, or a `url` the provider fetches.

    `label` is what a text-only path writes in place of the image, so a run that never reaches a
    vision model still reads sensibly in a trace. No example in this repo carries real image
    bytes; `data` exists because both documented backends take base64.
    """

    media_type: str  # "image/png", "image/jpeg", "image/gif", "image/webp"
    data: str | None = None  # base64, no data: prefix
    url: str | None = None
    label: str = ""


@dataclass(frozen=True)
class AudioPart:
    """A reference to an audio clip. Neither backend here documents an audio input block, so
    both raise rather than guess a wire format; see `OllamaModel` and `ClaudeModel`. The working
    shape for audio today is to transcribe first and send the transcript as a `TextPart`."""

    media_type: str  # "audio/wav", "audio/mp3", ...
    data: str | None = None
    url: str | None = None
    label: str = ""


Part = TextPart | ImagePart | AudioPart
Content = str | list[Part]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict
    # Pairs a call with its result. The Messages API requires it; Ollama returns one on newer
    # servers. Backends fill it in when the provider does not, so a loop can always rely on it.
    id: str = ""


@dataclass(frozen=True)
class Message:
    """One turn. Two turn shapes exist for agent loops, and they are real turns in both wire
    formats rather than text a model could imitate:

    - an assistant turn that called tools: `role="assistant"`, `tool_calls` set, `content` the
      model's text alongside the calls (often empty);
    - a tool result: `role="tool"`, `tool_call_id` and `tool_name` naming the call it answers.
    """

    role: str  # "system" | "user" | "assistant" | "tool"
    content: Content  # plain text, or a list of parts for a multimodal request
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str = ""
    tool_name: str = ""


@dataclass(frozen=True)
class Completion:
    text: str
    tool_calls: list[ToolCall]
    tokens_in: int
    tokens_out: int
    ms: float
    model_id: str


class Model(Protocol):
    model_id: str

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[dict] | None = None,
        schema: dict | None = None,
        max_tokens: int = 1024,
    ) -> Completion: ...


class Embedder(Protocol):
    """Turns text into vectors. Every implementation returns **unit** vectors (length 1), so a
    dot product between two of them is their cosine similarity; `to_unit` is what enforces it.
    The examples rely on this to score retrieval with one multiply-and-add, and to keep the same
    ranking when a real embedding backend replaces the stub."""

    model_id: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def count_tokens(text: str) -> int:
    """A simple, deterministic token estimate: the larger of a whitespace-split word count and
    a 4-characters-per-token count. Used by the stub model and for `--dry` budgeting; a real
    backend reports the provider's own count instead, when the provider gives one."""
    if not text:
        return 0
    words = len(text.split())
    chars = max(1, round(len(text) / 4))
    return max(words, chars)


def content_text(content: Content) -> str:
    """The text of a message's content, with a short placeholder standing in for each image or
    audio part. Used for token counting, for the stub model, and anywhere a trace needs one
    readable string.

    The placeholder is what a text-only path would actually send, so counting it is honest for
    that path. It is not what an image costs on a vision model: Anthropic documents an image as
    costing ceil(width / 28) * ceil(height / 28) visual tokens, a number that depends on pixels
    this interface never sees. Nothing here estimates it, and `--dry` does not either.
    """
    if isinstance(content, str):
        return content
    pieces: list[str] = []
    for part in content:
        if isinstance(part, TextPart):
            pieces.append(part.text)
        else:
            kind = "image" if isinstance(part, ImagePart) else "audio"
            where = part.label or part.url or "inline data"
            pieces.append(f"[{kind} {part.media_type}: {where}]")
    return "\n".join(pieces)


def message_payload(message: Message) -> dict:
    """A JSON-safe rendering of a whole message, for cache keys. Tool-call fields appear only when
    set, so a plain message renders exactly as it did before they existed."""
    out: dict = {"role": message.role, "content": content_payload(message.content)}
    if message.tool_calls:
        out["tool_calls"] = [asdict(c) for c in message.tool_calls]
    if message.tool_call_id:
        out["tool_call_id"] = message.tool_call_id
    if message.tool_name:
        out["tool_name"] = message.tool_name
    return out


def with_ids(calls: list[ToolCall], prefix: str = "call") -> list[ToolCall]:
    """Give every call an id, keeping any the provider supplied."""
    return [c if c.id else ToolCall(name=c.name, arguments=c.arguments, id=f"{prefix}_{i}") for i, c in enumerate(calls)]


def content_payload(content: Content) -> str | list[dict]:
    """A JSON-safe rendering of message content, for cache keys and trace files. Neutral: this
    is this repo's own shape, not any provider's wire format."""
    if isinstance(content, str):
        return content
    return [{"part": type(p).__name__, **asdict(p)} for p in content]


def _messages_tokens(messages: list[Message]) -> int:
    """Tokens a model is sent: each message's text, plus the name and arguments of any tool call
    it carries, which a provider sends too."""
    return sum(
        count_tokens(content_text(m.content))
        + sum(count_tokens(c.name + " " + json.dumps(c.arguments, sort_keys=True)) for c in m.tool_calls)
        for m in messages
    )


@dataclass(frozen=True)
class StubResponse:
    """One canned response for `StubModel`: text, a tool call, or both."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


ResponseFn = Callable[[list[Message], "list[dict] | None"], StubResponse]


class StubModel:
    """A deterministic model for tests and dry runs. Makes no network call.

    Construct it with either a fixed list of `StubResponse` (consumed in order, one per
    `complete` call) or a function `(messages, tools) -> StubResponse` for a response that
    depends on what was asked. Token counts come from `count_tokens`, so they are the same
    every run.
    """

    def __init__(self, responses: list[StubResponse] | ResponseFn, *, model_id: str = "stub-1") -> None:
        self._responses = responses
        self._next = 0
        self.model_id = model_id

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[dict] | None = None,
        schema: dict | None = None,
        max_tokens: int = 1024,
    ) -> Completion:
        start = time.perf_counter()
        if callable(self._responses):
            response = self._responses(messages, tools)
        else:
            if self._next >= len(self._responses):
                raise IndexError(f"StubModel ran out of responses after {self._next} call(s)")
            response = self._responses[self._next]
            self._next += 1
        tokens_out = count_tokens(response.text) + sum(
            count_tokens(json.dumps(call.arguments, sort_keys=True)) for call in response.tool_calls
        )
        ms = (time.perf_counter() - start) * 1000
        return Completion(
            text=response.text,
            tool_calls=list(response.tool_calls),
            tokens_in=_messages_tokens(messages),
            tokens_out=tokens_out,
            ms=ms,
            model_id=self.model_id,
        )


def _ollama_message(message: Message) -> dict:
    """One message in Ollama's `/api/chat` shape.

    Ollama's API documentation gives a message as `role` plus `content`, with images attached as
    an `images` array of base64-encoded strings alongside the text. There is no documented audio
    field, so an `AudioPart` raises instead of being dropped or guessed at.
    """
    if message.role == "tool":
        # Ollama's documented tool-result turn: role "tool", the result as content, and the name
        # of the tool that produced it.
        return {"role": "tool", "content": content_text(message.content), "tool_name": message.tool_name}
    if message.tool_calls:
        return {
            "role": "assistant",
            "content": content_text(message.content),
            "tool_calls": [{"function": {"name": c.name, "arguments": c.arguments}} for c in message.tool_calls],
        }
    if isinstance(message.content, str):
        return {"role": message.role, "content": message.content}
    text: list[str] = []
    images: list[str] = []
    for part in message.content:
        if isinstance(part, TextPart):
            text.append(part.text)
        elif isinstance(part, ImagePart):
            if not part.data:
                raise NotImplementedError(
                    "Ollama's /api/chat takes images as base64 strings in the message's `images` "
                    "array; it does not fetch a URL. Read the image and pass base64 in "
                    "ImagePart.data."
                )
            images.append(part.data)
        else:
            raise NotImplementedError(
                "Ollama's /api/chat documents text content and a base64 `images` array, and no "
                "audio input. Transcribe the audio first and send the transcript as a TextPart."
            )
    payload = {"role": message.role, "content": "\n".join(text)}
    if images:
        payload["images"] = images
    return payload


DEFAULT_NUM_CTX = 8192

# Tokens a reasoning model may spend before its first visible one, on top of what the caller asked
# for. Ollama counts hidden reasoning against `num_predict`, so a caller's `max_tokens=500` can be
# used up entirely by reasoning: the reply comes back with `done_reason: length` and no text. The
# first live run lost 3 of 12 answers that way, and each was scored as a wrong answer.
DEFAULT_REASONING_ALLOWANCE = 4096


class OllamaModel:
    """Calls a local Ollama server's `/api/chat`. Never pulls a model automatically.

    `num_ctx` is always sent, and defaults to `DEFAULT_NUM_CTX` rather than to whatever the
    server would pick. Left unset, Ollama applies its own small default and silently drops the
    front of a long prompt: a RAG run would score badly because the model never saw the sources,
    and the chart would read that as the technique failing. Anything measured here must be
    measured at a context size the result file can state.

    `num_predict` is the caller's `max_tokens` plus `reasoning_allowance`, for the same reason: a
    reasoning model spends hidden tokens first, and a cap sized for the visible answer alone can
    leave nothing for it. `settings` records both numbers so a result file can state them.
    """

    def __init__(
        self,
        tag: str,
        *,
        host: str = "http://127.0.0.1:11434",
        num_ctx: int = DEFAULT_NUM_CTX,
        reasoning_allowance: int = DEFAULT_REASONING_ALLOWANCE,
    ) -> None:
        self.model_id = f"ollama:{tag}"
        self._tag = tag
        self._host = host.rstrip("/")
        self._num_ctx = num_ctx
        self._reasoning_allowance = reasoning_allowance
        self.settings = {"num_ctx": num_ctx, "reasoning_allowance": reasoning_allowance}

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[dict] | None = None,
        schema: dict | None = None,
        max_tokens: int = 1024,
    ) -> Completion:
        options: dict = {"num_predict": max_tokens + self._reasoning_allowance, "num_ctx": self._num_ctx}
        payload: dict = {
            "model": self._tag,
            "messages": [_ollama_message(m) for m in messages],
            "stream": False,
            "options": options,
        }
        if tools is not None:
            payload["tools"] = [{"type": "function", "function": tool} for tool in tools]
        if schema is not None:
            payload["format"] = schema
        data = _post_json(f"{self._host}/api/chat", payload, timeout=120)
        message = data.get("message", {})
        tool_calls = with_ids(
            [
                ToolCall(name=c["function"]["name"], arguments=c["function"].get("arguments", {}), id=str(c.get("id") or ""))
                for c in message.get("tool_calls", []) or []
            ],
            prefix=f"ollama_{len(messages)}",
        )
        text = message.get("content", "")
        return Completion(
            text=text,
            tool_calls=tool_calls,
            tokens_in=data.get("prompt_eval_count", _messages_tokens(messages)),
            tokens_out=data.get("eval_count", count_tokens(text)),
            ms=data.get("total_duration", 0) / 1_000_000,
            model_id=self.model_id,
        )


def to_unit(vector: list[float]) -> list[float]:
    """Scale a vector to length 1, or return it unchanged if it is all zeros.

    Every `Embedder` in this repository returns unit vectors, so a dot product between two of
    them is their cosine similarity and the examples can score with one multiply-and-add. A
    backend that returned raw vectors would break that quietly rather than loudly: the dot
    product would still be a number, just one that grows with the length of a passage, so a long
    chunk would outrank a short relevant one.
    """
    norm = sum(v * v for v in vector) ** 0.5
    return [v / norm for v in vector] if norm else list(vector)


class OllamaEmbedder:
    """Calls a local Ollama server's `/api/embeddings`, one text at a time, and returns unit
    vectors. `/api/embeddings` returns whatever the embedding model produced, unnormalized for
    some tags, so the scaling happens here: the `Embedder` interface promises unit vectors, and
    swapping this in for `StubEmbedder` must not change how the retrieval code has to score."""

    def __init__(self, tag: str, *, host: str = "http://127.0.0.1:11434") -> None:
        self.model_id = f"ollama:{tag}"
        self._tag = tag
        self._host = host.rstrip("/")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [
            to_unit(_post_json(f"{self._host}/api/embeddings", {"model": self._tag, "prompt": t})["embedding"])
            for t in texts
        ]


def _error_detail(exc: urllib.error.HTTPError) -> str:
    """The server's own message, which is where Ollama says which model tag is missing. Without
    it every failure reads as "is the server running", including the ones where it is."""
    try:
        return exc.read().decode("utf-8", "replace")[:400]
    except Exception:  # noqa: BLE001 - the body is best-effort context for an error we re-raise
        return ""


def _post_json(url: str, payload: dict, *, timeout: int = 60) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        # a 404 here usually means the tag is not pulled; nothing in this repo ever pulls one
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {_error_detail(exc)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach {url}. Is the local server running? ({exc})") from exc


def _load_api_key(name: str) -> str:
    path = Path(__file__).resolve().parents[2] / ".local" / "api-keys.json"
    if not path.exists():
        raise RuntimeError(f'No {path} found; add a JSON file with a "{name}" key, e.g. {{"anthropic": "sk-..."}}.')
    keys = json.loads(path.read_text(encoding="utf-8"))
    if name not in keys:
        raise RuntimeError(f'{path} has no "{name}" key.')
    return keys[name]


def _anthropic_messages(messages: list[Message]) -> list[dict]:
    """Turn this repo's message list into the Messages API's `messages` array.

    Two shape rules the API enforces and this interface does not: the only roles are `user` and
    `assistant` (`system` is a separate top-level parameter, and there is no `tool` role, since a
    tool result is content inside a user turn), and turns alternate. The agent loop appends one
    user message per tool result, so consecutive same-role messages are joined here rather than
    sent as separate turns.
    """
    out: list[dict] = []
    for message in messages:
        if message.role == "system":
            continue
        role = "assistant" if message.role == "assistant" else "user"
        if message.role == "tool":
            # A tool result is a `tool_result` block inside a user turn, paired by id with the
            # `tool_use` block of the assistant turn that asked for it.
            content: str | list[dict] = [
                {"type": "tool_result", "tool_use_id": message.tool_call_id, "content": content_text(message.content)}
            ]
        elif message.tool_calls:
            text = content_text(message.content)
            content = ([{"type": "text", "text": text}] if text else []) + [
                {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments} for c in message.tool_calls
            ]
        else:
            content = _anthropic_content(message.content)
        if out and out[-1]["role"] == role:
            out[-1]["content"] = _join_anthropic_content(out[-1]["content"], content)
        else:
            out.append({"role": role, "content": content})
    return out


def _anthropic_content(content: Content) -> str | list[dict]:
    """Plain text stays a string, which the Messages API accepts. A list of parts becomes the
    API's content blocks.

    The image block is `{"type": "image", "source": {...}}`, and the documented source types are
    base64 (with `media_type` and `data`), `url`, and a Files API `file_id`; the documented image
    media types are JPEG, PNG, GIF and WebP. The documented input blocks are text, image and
    document: there is no audio block, so an `AudioPart` raises rather than being guessed at.
    """
    if isinstance(content, str):
        return content
    blocks: list[dict] = []
    for part in content:
        if isinstance(part, TextPart):
            blocks.append({"type": "text", "text": part.text})
        elif isinstance(part, ImagePart):
            if part.data:
                source = {"type": "base64", "media_type": part.media_type, "data": part.data}
            elif part.url:
                source = {"type": "url", "url": part.url}
            else:
                raise ValueError("an ImagePart needs either base64 data or a url")
            blocks.append({"type": "image", "source": source})
        else:
            raise NotImplementedError(
                "The Messages API documents text, image and document content blocks, and no "
                "audio input block. Transcribe the audio first and send the transcript as a "
                "TextPart."
            )
    return blocks


def _join_anthropic_content(first: str | list[dict], second: str | list[dict]) -> str | list[dict]:
    """Merge two same-role turns. Two strings join as text, the way they did before parts
    existed; anything with blocks in it becomes one block list, since the API will not take a
    string and a list at once."""
    if isinstance(first, str) and isinstance(second, str):
        return first + "\n\n" + second
    as_blocks = lambda c: [{"type": "text", "text": c}] if isinstance(c, str) else list(c)  # noqa: E731
    return as_blocks(first) + as_blocks(second)


def _anthropic_schema(schema: dict) -> dict:
    """Copy a JSON schema and close object shapes as required by Claude JSON outputs.

    Explicit open dictionaries cannot be represented; refuse them instead of silently
    changing their contract. Other unsupported constraints are left for the API to reject,
    never stripped. Walk schema positions only, not data in enum/default values.
    """
    from copy import deepcopy

    result = deepcopy(schema)
    if result.get("type") == "object" or "properties" in result:
        if result.get("additionalProperties", False) is not False:
            raise ValueError("Claude structured outputs require additionalProperties: false for objects")
        result["additionalProperties"] = False
    for key in ("properties", "$defs", "definitions", "patternProperties"):
        if key in result:
            result[key] = {name: _anthropic_schema(child) for name, child in result[key].items()}
    for key in ("items", "not"):
        if isinstance(result.get(key), dict):
            result[key] = _anthropic_schema(result[key])
    for key in ("anyOf", "allOf", "oneOf", "prefixItems"):
        if key in result:
            result[key] = [_anthropic_schema(child) for child in result[key]]
    return result


def _anthropic_tools(tools: list[dict]) -> list[dict]:
    """The shared definitions use `parameters` (wrapped inside `function` for Ollama).
    The Messages API calls the same field `input_schema` and rejects the request without it."""
    converted = []
    for tool in tools:
        entry = {key: value for key, value in tool.items() if key != "parameters"}
        if "parameters" in tool:
            entry["input_schema"] = tool["parameters"]
        converted.append(entry)
    return converted


class ClaudeModel:
    """Calls the Anthropic Messages API. The key comes from `.local/api-keys.json` (`anthropic`),
    never from a hard-coded default; the model id is passed in, defaulting to `DEFAULT_MODEL`.

    Stdlib only, by the same rule as the rest of this repo, so the request is built by hand
    rather than by the official SDK. That makes the request shape this class's problem: see
    `_anthropic_messages` and `_anthropic_tools`, which convert from the interface's shape to the
    API's. One request per call, no retries: a retry here would multiply the cost of a metered
    run without saying so on the result file.
    """

    def __init__(self, model_id: str = DEFAULT_MODEL, *, api_key: str | None = None) -> None:
        self.model_id = model_id
        self._api_key = api_key or _load_api_key("anthropic")

    def build_payload(
        self,
        messages: list[Message],
        *,
        tools: list[dict] | None = None,
        schema: dict | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        """The request body, split out so it can be checked without calling the API."""
        system_messages = [m for m in messages if m.role == "system"]
        if any(not isinstance(m.content, str) and any(not isinstance(p, TextPart) for p in m.content) for m in system_messages):
            raise ValueError(
                "The Messages API takes `system` as text, separate from the messages array. Put "
                "an image or audio part in a user message instead."
            )
        system = "\n".join(content_text(m.content) for m in system_messages)
        payload: dict = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "messages": _anthropic_messages(messages),
        }
        if system:
            payload["system"] = system
        if tools is not None:
            payload["tools"] = _anthropic_tools(tools)
        if schema is not None:
            # structured output; dropping it silently would let a run score a free-text answer
            # against a question that asked for JSON
            payload["output_config"] = {"format": {"type": "json_schema", "schema": _anthropic_schema(schema)}}
        return payload

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[dict] | None = None,
        schema: dict | None = None,
        max_tokens: int = 1024,
    ) -> Completion:
        payload = self.build_payload(messages, tools=tools, schema=schema, max_tokens=max_tokens)
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Anthropic API returned HTTP {exc.code}: {_error_detail(exc)}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Anthropic API request failed: {exc}") from exc
        ms = (time.perf_counter() - start) * 1000
        text = "".join(block["text"] for block in data.get("content", []) if block.get("type") == "text")
        tool_calls = [
            ToolCall(name=block["name"], arguments=block.get("input", {}), id=block.get("id", ""))
            for block in data.get("content", [])
            if block.get("type") == "tool_use"
        ]
        usage = data.get("usage", {})
        return Completion(
            text=text,
            tool_calls=tool_calls,
            tokens_in=usage.get("input_tokens", _messages_tokens(messages)),
            tokens_out=usage.get("output_tokens", count_tokens(text)),
            ms=ms,
            model_id=self.model_id,
        )


def _bucket(word: str, dims: int) -> int:
    digest = hashlib.sha256(word.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % dims


# Words that appear in nearly every section and in nearly every question. Left in, they are most
# of the overlap between a question and a chunk, and the ranking becomes a measure of how long a
# chunk is. This is the stand-in for the inverse-document-frequency weighting a real embedding
# model gets from its training data, not a claim about how one works.
_STOPWORDS = frozenset(
    "a an and are as at be been but by can do does for from has have how i if in into is it its "
    "not of on or should that the their then there these they this to use used using was what "
    "when where which who will with would you your".split()
)
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def _tokens(text: str) -> list[str]:
    """Words of a text, for the stub embedder: lowercase, punctuation dropped, hyphenated model
    numbers kept whole (`dw-300` is one word, not two), a possessive `'s` stripped so that
    "the DW-300's rating" and "the DW-300 rating" share a word, and stopwords dropped."""
    words: list[str] = []
    for raw in _WORD_RE.findall(text.lower().replace("\u2019", "'").replace("'s ", " ")):
        word = raw.removesuffix("-")
        if word and word not in _STOPWORDS:
            words.append(word)
    return words


class StubEmbedder:
    """Deterministic hashing bag-of-words embedder. Makes no network call. The same text always
    hashes to the same vector, in this process and every other one, since it uses `sha256`
    rather than Python's randomized `hash()`.

    It is a stand-in, not a model: it knows nothing about meaning, so a question and a chunk that
    share no word share nothing, where a real embedder would still see that "water use" and
    "consumption" are close. What it does have to be is good enough that retrieval returns the
    section a reader can see is the right one, because an example whose retrieval misses teaches
    the opposite of what the page says. That needs enough dimensions to keep two different words
    apart (64 buckets collide constantly) and a tokenizer that does not let stopwords dominate.
    """

    def __init__(self, dims: int = 512, *, model_id: str = "stub-embed-1") -> None:
        self._dims = dims
        self.model_id = model_id

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dims
        for word in _tokens(text):
            vector[_bucket(word, self._dims)] += 1.0
        return to_unit(vector)


def build_model(spec: str, *, stub: Model | None = None) -> Model:
    """Build a model from a `--model` spec: `stub`, `ollama:<tag>`, or `claude:<id>`.

    `stub` must be supplied by the caller (each example scripts its own stub answers); the
    other two specs need no extra argument.
    """
    if spec == "stub":
        if stub is None:
            raise ValueError("model spec 'stub' needs a StubModel instance via build_model(..., stub=...)")
        return stub
    if spec.startswith("ollama:"):
        return OllamaModel(spec.split(":", 1)[1])
    if spec.startswith("claude:"):
        return ClaudeModel(spec.split(":", 1)[1])
    raise ValueError(f"Unknown model spec: {spec!r}. Use 'stub', 'ollama:<tag>', or 'claude:<id>'.")


def build_embedder(spec: str, *, stub: Embedder | None = None) -> Embedder:
    """Build an embedder from the same kind of spec `build_model` takes: `stub` or
    `ollama:<tag>`.

    There is no `claude:` branch, on purpose: Anthropic does not publish an embeddings endpoint,
    so a `claude:` spec has nothing this function could build. That is a real gap, not an
    oversight to paper over here -- an example whose `run()` takes an `embedder` cannot be
    recorded against a metered Claude chat model by passing `build_embedder(args.model, ...)`
    with the same spec used for the model, as `scripts/record_trace.py` and most example
    `__main__.py` files historically did. The fix lives at the call site, not in this function:
    let the embedder spec vary independently of the chat model spec (`record_trace.py` takes a
    separate `--embedder`, defaulting to `--model` so today's pairing still works when the two
    happen to agree), so a `claude:` chat model can be recorded against a `stub` or `ollama:<tag>`
    embedder instead of one this function cannot build.
    """
    if spec == "stub":
        return stub or StubEmbedder()
    if spec.startswith("ollama:"):
        return OllamaEmbedder(spec.split(":", 1)[1])
    raise ValueError(f"Unknown embedder spec: {spec!r}. Use 'stub' or 'ollama:<tag>'.")
