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

const pattern = new RegExp(`\\b(${Object.keys(acronyms).join('|')})(s)?\\b`, 'g');
export function acronymMatches(text: string) {
  return Array.from(text.matchAll(pattern), match => ({
    index: match.index!, text: match[0], key: match[1],
  }));
}
