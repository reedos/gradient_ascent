// A JSON5-shaped reader for the `{...}` attribute literals the site's MDX writes:
//
//   <FailureModes modes={[{ name: 'Stale index', notice: "The answer is ...", test: `...` }]} />
//   <CostStrip stats={[{ label: 'Tokens in', value: '~1,850' }]} level={2} illustrative={false} />
//
// It replaces `new Function("return (" + raw + ")")`, which indexes.ts used to evaluate those
// attributes at build time. That call was only ever fed this repository's own content, but it
// gave a prop in a Markdown file the full run of the build process, and "the input is trusted"
// is a property of today's repository rather than of the code. This parser can only ever produce
// data: it accepts strings, numbers, booleans, null, arrays and plain objects, and throws on
// anything else -- an identifier, a call, a template substitution, an operator, a trailing
// character after the value. indexes.ts turns that throw into a build failure naming the file,
// so a page whose literal cannot be parsed stops the build instead of quietly losing its block.
//
// What it accepts beyond strict JSON, because MDX is JavaScript and its authors write it that
// way: single quotes and backticks (no `${}` substitution), unquoted object keys, trailing
// commas, `//` and block comments, `+`/`-` signs, hex and exponent numbers, and the standard
// escape sequences including \u and \x.

export class LiteralParseError extends Error {
  readonly index: number;
  constructor(message: string, index: number) {
    super(`${message} (at character ${index + 1})`);
    this.name = 'LiteralParseError';
    this.index = index;
  }
}

const WHITESPACE = new Set([' ', '\t', '\n', '\r', '\f', '\v', ' ', '﻿']);
const IDENT_START = /[A-Za-z_$]/;
const IDENT_PART = /[A-Za-z0-9_$]/;

class Reader {
  // Plain fields, not TypeScript parameter properties: `node --test` strips types rather than
  // compiling them, and a parameter property is syntax it cannot erase. site/tests runs this
  // file directly.
  src: string;
  i: number;

  constructor(src: string, i = 0) {
    this.src = src;
    this.i = i;
  }

  fail(message: string): never {
    throw new LiteralParseError(message, this.i);
  }

  atEnd(): boolean {
    return this.i >= this.src.length;
  }

  peek(): string {
    return this.src[this.i];
  }

  /** Skips whitespace and `//` / block comments. */
  skip(): void {
    for (;;) {
      while (!this.atEnd() && WHITESPACE.has(this.src[this.i])) this.i++;
      if (this.src[this.i] === '/' && this.src[this.i + 1] === '/') {
        while (!this.atEnd() && this.src[this.i] !== '\n') this.i++;
        continue;
      }
      if (this.src[this.i] === '/' && this.src[this.i + 1] === '*') {
        const end = this.src.indexOf('*/', this.i + 2);
        if (end === -1) this.fail('unterminated block comment');
        this.i = end + 2;
        continue;
      }
      return;
    }
  }

  expect(ch: string): void {
    if (this.src[this.i] !== ch) this.fail(`expected ${JSON.stringify(ch)}`);
    this.i++;
  }

  value(): unknown {
    this.skip();
    if (this.atEnd()) this.fail('unexpected end of input, expected a value');
    const ch = this.peek();
    if (ch === '{') return this.object();
    if (ch === '[') return this.array();
    if (ch === '"' || ch === "'" || ch === '`') return this.string(ch);
    if (ch === '-' || ch === '+' || (ch >= '0' && ch <= '9') || ch === '.') return this.number();
    if (IDENT_START.test(ch)) {
      const at = this.i;
      const word = this.identifier();
      if (word === 'true') return true;
      if (word === 'false') return false;
      if (word === 'null') return null;
      this.i = at; // point the error at the start of the identifier, not past its end
      this.fail(
        `only strings, numbers, true, false, null, arrays and objects are allowed here; found the identifier ${JSON.stringify(word)}`,
      );
    }
    this.fail(`unexpected character ${JSON.stringify(ch)}`);
  }

  identifier(): string {
    const start = this.i;
    this.i++;
    while (!this.atEnd() && IDENT_PART.test(this.src[this.i])) this.i++;
    return this.src.slice(start, this.i);
  }

  object(): Record<string, unknown> {
    this.expect('{');
    const out: Record<string, unknown> = {};
    this.skip();
    if (this.peek() === '}') {
      this.i++;
      return out;
    }
    for (;;) {
      this.skip();
      const ch = this.peek();
      let key: string;
      if (ch === '"' || ch === "'" || ch === '`') key = this.string(ch);
      else if (ch !== undefined && IDENT_START.test(ch)) key = this.identifier();
      else this.fail('expected a property name');
      this.skip();
      this.expect(':');
      out[key] = this.value();
      this.skip();
      if (this.peek() === ',') {
        this.i++;
        this.skip();
        if (this.peek() === '}') {
          this.i++;
          return out;
        }
        continue;
      }
      if (this.peek() === '}') {
        this.i++;
        return out;
      }
      this.fail('expected "," or "}" after a property');
    }
  }

  array(): unknown[] {
    this.expect('[');
    const out: unknown[] = [];
    this.skip();
    if (this.peek() === ']') {
      this.i++;
      return out;
    }
    for (;;) {
      out.push(this.value());
      this.skip();
      if (this.peek() === ',') {
        this.i++;
        this.skip();
        if (this.peek() === ']') {
          this.i++;
          return out;
        }
        continue;
      }
      if (this.peek() === ']') {
        this.i++;
        return out;
      }
      this.fail('expected "," or "]" after an array element');
    }
  }

  string(quote: string): string {
    this.i++; // opening quote
    let out = '';
    for (;;) {
      if (this.atEnd()) this.fail('unterminated string');
      const ch = this.src[this.i];
      if (ch === quote) {
        this.i++;
        return out;
      }
      if (ch === '\\') {
        this.i++;
        out += this.escape();
        continue;
      }
      // A backtick string is a template literal: `${...}` is code, not text, so it is refused
      // rather than silently pasted in as the characters "${" and "}".
      if (quote === '`' && ch === '$' && this.src[this.i + 1] === '{') {
        this.fail('a ${...} substitution is code, not a literal value');
      }
      out += ch;
      this.i++;
    }
  }

  escape(): string {
    if (this.atEnd()) this.fail('unterminated escape sequence');
    const ch = this.src[this.i];
    this.i++;
    switch (ch) {
      case 'n':
        return '\n';
      case 't':
        return '\t';
      case 'r':
        return '\r';
      case 'b':
        return '\b';
      case 'f':
        return '\f';
      case 'v':
        return '\v';
      case '0':
        // Only the lone NUL escape; \01 is a legacy octal escape and is not accepted.
        if (/[0-9]/.test(this.src[this.i] ?? '')) this.fail('octal escape sequences are not allowed');
        return '\0';
      case 'x':
        return this.codeUnit(2);
      case 'u': {
        if (this.src[this.i] === '{') {
          this.i++;
          const end = this.src.indexOf('}', this.i);
          if (end === -1) this.fail('unterminated \\u{...} escape');
          const hex = this.src.slice(this.i, end);
          if (!/^[0-9a-fA-F]{1,6}$/.test(hex)) this.fail('bad \\u{...} escape');
          const cp = parseInt(hex, 16);
          if (cp > 0x10ffff) this.fail('\\u{...} escape is out of range');
          this.i = end + 1;
          return String.fromCodePoint(cp);
        }
        return this.codeUnit(4);
      }
      case '\n':
        return ''; // a line continuation inside a string
      case '\r':
        if (this.src[this.i] === '\n') this.i++;
        return '';
      default:
        // \\ \' \" \` \/ and any other single character stand for themselves.
        return ch;
    }
  }

  codeUnit(digits: number): string {
    const hex = this.src.slice(this.i, this.i + digits);
    if (hex.length !== digits || !/^[0-9a-fA-F]+$/.test(hex)) this.fail(`bad \\${digits === 2 ? 'x' : 'u'} escape`);
    this.i += digits;
    return String.fromCharCode(parseInt(hex, 16));
  }

  number(): number {
    const start = this.i;
    if (this.src[this.i] === '+' || this.src[this.i] === '-') this.i++;
    if (this.src[this.i] === '0' && /[xX]/.test(this.src[this.i + 1] ?? '')) {
      this.i += 2;
      const hs = this.i;
      while (!this.atEnd() && /[0-9a-fA-F]/.test(this.src[this.i])) this.i++;
      if (this.i === hs) this.fail('bad hexadecimal number');
      const n = parseInt(this.src.slice(hs, this.i), 16);
      return this.src[start] === '-' ? -n : n;
    }
    while (!this.atEnd() && /[0-9]/.test(this.src[this.i])) this.i++;
    if (this.src[this.i] === '.') {
      this.i++;
      while (!this.atEnd() && /[0-9]/.test(this.src[this.i])) this.i++;
    }
    if (this.src[this.i] === 'e' || this.src[this.i] === 'E') {
      this.i++;
      if (this.src[this.i] === '+' || this.src[this.i] === '-') this.i++;
      const es = this.i;
      while (!this.atEnd() && /[0-9]/.test(this.src[this.i])) this.i++;
      if (this.i === es) this.fail('bad exponent');
    }
    const text = this.src.slice(start, this.i);
    if (!/[0-9]/.test(text)) this.fail('expected a number');
    const n = Number(text);
    if (Number.isNaN(n)) this.fail(`${JSON.stringify(text)} is not a number`);
    return n;
  }
}

/**
 * Parses one data literal and returns it. Throws `LiteralParseError` on anything that is not a
 * string, number, boolean, null, array or plain object -- an identifier, a call, an operator, a
 * template substitution, or trailing characters after the value.
 */
export function parseLiteral(raw: string): unknown {
  const r = new Reader(raw);
  const value = r.value();
  r.skip();
  if (!r.atEnd()) {
    r.fail(`unexpected trailing text ${JSON.stringify(r.src.slice(r.i, r.i + 24))}; only one literal value is allowed`);
  }
  return value;
}
