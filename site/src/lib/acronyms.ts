// Short reading aids. Keep concept definitions aligned with content/glossary.json.
export const acronyms: Record<string, [string, string]> = {
  AI: ['Artificial intelligence', 'Software that performs tasks such as understanding language, recognizing patterns, and making predictions.'],
  LLM: ['Large language model', 'A model trained on large amounts of text that generates and interprets language.'],
  DUT: ['Device under test', 'The device or product a test project is designed to measure and validate.'],
  SCPI: ['Standard Commands for Programmable Instruments', 'A standardized command language used to control test and measurement instruments.'],
  API: ['Application programming interface', 'A defined way for software components to request functions or exchange data.'],
  SDK: ['Software development kit', 'Libraries and tools for building software with a particular platform.'],
  CSV: ['Comma-separated values', 'A plain-text format for tabular data, with fields separated by commas.'],
  JSON: ['JavaScript Object Notation', 'A text format for structured data using objects, arrays, and values.'],
  YAML: ["YAML Ain’t Markup Language", 'A text format commonly used for configuration, with indentation expressing structure.'],
  GraphRAG: ['Graph-based retrieval-augmented generation', 'Use entities and their relationships in a knowledge graph to retrieve connected information for a model to answer from.'],
  RAG: ['Retrieval-augmented generation', 'Retrieve relevant information and supply it to a model to help it answer.'],
  MCP: ['Model Context Protocol', 'A protocol for connecting AI applications to tools and data sources.'],
  GPU: ['Graphics processing unit', 'A processor that runs many calculations in parallel, often used for AI workloads.'],
  CPU: ['Central processing unit', 'The general-purpose processor that executes a computer’s instructions.'],
  UI: ['User interface', 'The controls and displays through which a person interacts with software.'],
  CLI: ['Command-line interface', 'A way to operate software by typing commands in a terminal.'],
  SQL: ['Structured Query Language', 'A language for querying and modifying data in relational databases.'],
  HTTP: ['Hypertext Transfer Protocol', 'The request-and-response protocol used to exchange web resources.'],
  URL: ['Uniform Resource Locator', 'An address identifying where a resource can be accessed.'],
  PDF: ['Portable Document Format', 'A document format designed to preserve page layout across devices.'],
  OCR: ['Optical character recognition', 'Converting text in an image or scan into machine-readable text.'],
  PII: ['Personally identifiable information', 'Information that can identify a person, alone or combined with other data.'],
  LoRA: ['Low-rank adaptation', 'A fine-tuning method that trains small added parameter matrices while keeping base model weights fixed.'],
  VLA: ['Vision-language-action', 'A model that connects visual and language inputs to actions, such as robot movements.'],
  TTS: ['Text to speech', 'Converting written text into spoken audio.'],
  ASR: ['Automatic speech recognition', 'Converting spoken audio into text.'],
};

const readingTerms: Record<string, [string, string]> = {
  "agent loop": [
    "Agent loop",
    "The repeating cycle behind every agent: the model proposes one action from what it currently sees, your code carries it out, and the result goes back to the model, until the model itself decides to stop."
  ],
  "agentic RAG": [
    "Agentic retrieval-augmented generation",
    "Retrieval where the model, not your code, decides how many times to search, what to search for next, and when it has read enough to answer, instead of searching once and answering once."
  ],
  "checkpoint": [
    "Checkpoint",
    "A saved snapshot of a workflow's shared state, written after a step, so a crashed or interrupted run can resume from that point instead of starting over from the beginning."
  ],
  "context engineering": [
    "Context engineering",
    "Deciding what goes into a model's request (which instructions, examples, documents and history) and in what order, since the model only knows what it was trained on and what the request contains."
  ],
  "context window": [
    "Context window",
    "The amount of text a model can read in one request; material that does not comfortably fit has to be trimmed, retrieved, or summarized before the model ever sees the question."
  ],
  "distillation": [
    "Distillation",
    "Training a smaller model to imitate a larger model's outputs on a given task, so the smaller one can stand in for the larger one on that same narrow job."
  ],
  "embedding": [
    "Embedding",
    "A list of floating-point numbers standing in for a piece of text's meaning, positioned so texts with similar meaning get vectors that point in similar directions."
  ],
  "fine-tuning": [
    "Fine-tuning",
    "Training a model further on your own examples so its behavior on that kind of task becomes more consistent, without repeating the same instructions in every request."
  ],
  "guardrail": [
    "Guardrail",
    "A check on what goes into a model or what comes out: an input filter, an output validator, a separate classifier trained to judge safety, a schema check. It is probabilistic and can be wrong in both directions, so it is never the control that holds; a code check that tests a specific fact is."
  ],
  "hallucination": [
    "Hallucination",
    "A fluent, confident answer that is not actually true or not supported by any real source; research argues this happens because training and grading reward a plausible guess over admitting uncertainty."
  ],
  "knowledge graph": [
    "Knowledge graph",
    "Facts stored as entities and the relationships between them, so a chain of hops can join facts across documents instead of needing one passage to state the whole answer."
  ],
  "observability": [
    "Observability",
    "Recording what each run did in enough detail that a bad result can be traced back to the step that caused it: which passages a retrieval step picked, which tool the model called and with what arguments, which branch a workflow took, and what each step spent."
  ],
  "prompt injection": [
    "Prompt injection",
    "Text written to look like an instruction, hidden in the user's message or in retrieved or tool-returned content, that tries to redirect what the model does instead of answering the actual question."
  ],
  "quantization": [
    "Quantization",
    "Storing a model's weights at lower precision so a large model fits smaller hardware and may run faster. llama.cpp's own documentation says it shrinks the model and can speed up inference, and that it may cost some accuracy. Name the exact level you ran, not just \"4-bit\"."
  ],
  "retrieval": [
    "Retrieval",
    "Searching an index of document chunks for the ones closest to a question, and keeping a fixed number of the best matches to hand to the model."
  ],
  "sandbox": [
    "Sandbox",
    "An isolated environment with no network access and fixed resource limits, where code the model wrote is actually run, so what the model produces is data your code hands to an interpreter, never code it trusts directly."
  ],
  "schema": [
    "Schema",
    "A fixed shape for a reply (named fields with defined types) that a model's output is constrained to match, so downstream code can parse it without guessing at its structure."
  ],
  "token": [
    "Token",
    "The unit a model's input and output are measured and billed in; every cost strip on this site counts tokens in and tokens out for the run it illustrates."
  ]
};
readingTerms['retrieval-augmented generation'] = acronyms.RAG;
Object.assign(acronyms, readingTerms);
const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const acronymPattern = new RegExp(`\\b(${Object.keys(acronyms).filter(k => !readingTerms[k]).map(escape).join('|')})(s)?\\b`, 'g');
const termPattern = new RegExp(`\\b(${Object.keys(readingTerms).sort((a,b) => b.length-a.length).map(escape).join('|')})(s)?\\b`, 'gi');
export function acronymMatches(text: string) {
  const terms = Array.from(text.matchAll(termPattern), m => ({ index: m.index!, text: m[0], key: Object.keys(readingTerms).find(k => k.toLowerCase() === m[1].toLowerCase())! }));
  const short = Array.from(text.matchAll(acronymPattern), m => ({ index: m.index!, text: m[0], key: m[1] }))
    .filter(m => !terms.some(t => m.index >= t.index && m.index < t.index + t.text.length));
  return [...terms, ...short].sort((a,b) => a.index-b.index);
}
