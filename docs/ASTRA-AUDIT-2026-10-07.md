# Gradient Ascent audit, 10/07/2026

Status: incomplete primary-source recertification. Implementation and mechanical checks are described separately below. This document does not certify every external claim.

## Changes and verified claims

| Claim or defect | Status | Evidence and scope |
|---|---|---|
| Cobalt/navy palette and multicolor level ramp | Fixed | Shared IF ground, surface, raised surface, text, muted, amber and font families ported from its stylesheet; compared with the live IF landing page. Level labels and numbers still distinguish levels. |
| One measured model represents its whole model class | Fixed | Only one model appears in the committed measurement entries. HTML, Markdown and RAG introductions now restrict the result to that run/configuration/question set. |
| Correct answer totals | Confirmed | New test counts individual question verdicts independently of aggregate scores, for both measured techniques and every question kind. |
| Token totals, wall time, coverage and cap counts | Confirmed | Python test reconciles displayed aggregates against individual result rows. Millisecond tolerance is tied to the saved timestamp precision. No live model was called. |
| Same-sized evaluations necessarily use the same questions | Fixed | Comparisons now require matching question IDs and kinds; synthetic replacement-ID case fails before the change. Existing IDs do not prove unchanged question wording across different revisions; the current two runs share the same repository commit. |
| A complete-result flag suffices without checking rows | Fixed | Build rejects truncated, duplicate, ungraded and inconsistent records. Six mutation cases live in evals/measurement-integrity.json; row reordering remains valid. |
| RAG combines external retrieval with generation; original paper date 05/22/2020 | Confirmed | [Original paper](https://arxiv.org/abs/2005.11401), abstract and submission history. The one-pass implementation remains explicitly an example. |
| Agentic research uses iterative search and an orchestrator with workers | Confirmed | [Anthropic engineering account](https://www.anthropic.com/engineering/multi-agent-research-system), architecture section. This supports the example architecture, not universal performance. |
| Muse Glimmer model size and local model identity | Confirmed in published registry | [Ollama model page](https://ollama.com/library/muse-glimmer) describes 30B and Meta. Local quantization/configuration comes from the committed run metadata, not that page. |
| Claude cache reads universally cost 0.1 times input | Fixed | [Prompt caching documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), pricing table and footnotes checked 10/07/2026. Added 0.025 and 0.05 model exceptions, kept 1.25 and 2 write multipliers with durations. |
| Prompt caching means omitting the prefix from requests | Fixed | Same primary documentation, request examples and cache behavior. Wording now describes reuse of prefix computation. |
| Three cheap attempts always cost more than one expensive attempt | Fixed | The sum must exceed the alternative cost. Removed the unconditional assertion and the claim that batching cannot help low-volume work. |
| All numbers on the cost page are vendor rates | Fixed | The page also contains a synthetic worked price table. It now distinguishes those example prices from vendor discounts. |
| GraphRAG indexing costs 1,000 times vector retrieval generally | Footnoted | [Microsoft comparison](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) reports 0.1%; the inverse is scoped to that comparison, not a general price or a local measurement. |
| LLM judge agreement exceeds 80%; paper date 06/09/2023 | Confirmed as reported | [MT-Bench paper](https://arxiv.org/abs/2306.05685), abstract and submission history. The page already attributes the study and lists judge biases. |
| ECI combines benchmark scores | Confirmed definition only | [Epoch ECI](https://epoch.ai/eci) supports the definition. Individual values remain the dated 09/18/2026 snapshot; this pass did not replace it or independently recertify each historical score. |
| Phi is a Microsoft small-model family; Milvus is a vector database | Confirmed identity only | [Phi](https://azure.microsoft.com/en-us/products/phi) and [Milvus](https://milvus.io/) read successfully with the web reader after transport failures in the batch. |

## Source access and outstanding claim work

The source register contains 451 distinct URLs collected from all MDX frontmatter plus the timeline, landscape, frontier and capability data. The initial pass retrieved 413, received 9 access denials, skipped 25 later URLs on denied hosts, and had 4 transport failures. Two transport failures were resolved by a web-reader check; two failed both approaches. No denied request was retried through a different tool or path.

[Full access register](ASTRA-SOURCE-ACCESS-2026-10-07.json) includes every source and each referring page/data item. It records availability only. A reachable page is not evidence that a paraphrase, benchmark or date is correct. The confirmed/fixed/footnoted claims above are the claims actually rechecked in this pass. Other external claims remain unrecertified; the prior source dates were not bulk advanced.

Full source recertification cannot be completed under the no-retry rule for the following references. They need an approved accessible source copy or manual verification. The brief must remain BLOCKED rather than DONE.

| Reference | Access result | Affected content |
|---|---|---|
| https://www.perplexity.ai/help-center/en/articles/10352895-how-does-perplexity-work | denied 403 | site/src/content/teardowns/answer-engine.mdx |
| https://www.perplexity.ai/help-center/en/articles/10354917-what-is-an-answer-engine-and-how-does-perplexity-work-as-one | not attempted Host previously denied access; no retry or alternate path | site/src/content/teardowns/answer-engine.mdx; landscape.json perplexity |
| https://www.perplexity.ai/help-center/en/articles/10352901-what-is-perplexity-pro | not attempted Host previously denied access; no retry or alternate path | site/src/content/teardowns/answer-engine.mdx |
| https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research | not attempted Host previously denied access; no retry or alternate path | site/src/content/teardowns/deep-research-mode.mdx; landscape.json perplexity-deep-research |
| https://openai.com/policies/business-terms/ | denied 403 | site/src/content/techniques/distillation.mdx |
| https://www.pi.website/blog/pi0 | denied 429 | site/src/content/techniques/embodied.mdx; timeline.json milestone pi0-2024; landscape.json pi0 |
| https://www.pi.website/blog/pi07 | not attempted Host previously denied access; no retry or alternate path | site/src/content/techniques/embodied.mdx; timeline.json milestone pi0-7-2026; landscape.json pi0-7 |
| https://web.archive.org/web/20260915180415id_/https://ai.google.dev/gemini-api/docs/function-calling | unavailable TimeoutError | site/src/content/techniques/function-calling.mdx |
| https://genai.owasp.org/2025/01/22/announcing-the-owasp-gen-ai-red-teaming-guide/ | denied 403 | site/src/content/techniques/red-teaming.mdx |
| https://openai.com/index/better-language-models/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone gpt-2-post-2019 |
| https://openai.com/index/openai-api/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone gpt-3-api-2020 |
| https://openai.com/index/chatgpt/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone chatgpt-launch |
| https://openai.com/index/learning-to-reason-with-llms/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone o1-reasoning-models |
| https://openai.com/index/introducing-text-and-code-embeddings/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone openai-embeddings-2022 |
| https://neeva.com/blog/introducing-neevaai | unavailable URLError | timeline.json milestone neeva-ai-2023 |
| https://openai.com/index/memory-and-new-controls-for-chatgpt/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone chatgpt-memory-2024 |
| https://openai.com/index/chatgpt-plugins/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone chatgpt-plugins-2023 |
| https://help.openai.com/en/articles/6825453-chatgpt-release-notes | denied 403 | timeline.json milestone chatgpt-plugins-beta-2023 |
| https://openai.com/index/function-calling-and-other-api-updates/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone openai-function-calling-2023 |
| https://openai.com/index/introducing-operator/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone operator-2025 |
| https://openai.com/index/introducing-chatgpt-agent/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone chatgpt-agent-2025 |
| https://openai.com/chatgpt-work/ | not attempted Host previously denied access; no retry or alternate path | timeline.json milestone chatgpt-work-2026; landscape.json chatgpt-work |
| https://openai.com/index/gpt-6-astra/ | not attempted Host previously denied access; no retry or alternate path | landscape.json gpt-6-astra |
| https://openai.com/index/gpt-5-6/ | not attempted Host previously denied access; no retry or alternate path | landscape.json gpt-5.6-sol; landscape.json gpt-5.6-terra; landscape.json gpt-5.6-luna |
| https://openai.com/index/introducing-gpt-oss/ | not attempted Host previously denied access; no retry or alternate path | landscape.json gpt-oss |
| https://help.openai.com/en/articles/9260256-chatgpt-capabilities-overview | not attempted Host previously denied access; no retry or alternate path | landscape.json chatgpt |
| https://www.midjourney.com/ | denied 403 | landscape.json midjourney |
| https://help.openai.com/en/articles/10169521-projects-in-chatgpt | not attempted Host previously denied access; no retry or alternate path | landscape.json chatgpt-projects |
| https://help.openai.com/en/articles/8590148-memory-faq | not attempted Host previously denied access; no retry or alternate path | landscape.json chatgpt-memory |
| https://www.make.com | denied 403 | landscape.json make |
| https://help.openai.com/en/articles/8437071-data-analysis-with-chatgpt | not attempted Host previously denied access; no retry or alternate path | landscape.json chatgpt-data-analysis |
| https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq | not attempted Host previously denied access; no retry or alternate path | landscape.json custom-gpts |
| https://help.openai.com/en/articles/20001274 | not attempted Host previously denied access; no retry or alternate path | landscape.json chatgpt-voice |
| https://www.sec.gov/Archives/edgar/data/1318605/000162828026003952/tsla-20251231.htm | denied 403 | landscape.json optimus |
| https://www.iso.org/standard/76583.html | denied 403 | landscape.json sql |
| https://genai.owasp.org/llmrisk/llm062025-excessive-agency/ | not attempted Host previously denied access; no retry or alternate path | frontier.json level 4 sandbox-is-a-choice |

## Verification

- `python scripts/validate.py`: PASS.
- `cd site; npx astro check`: PASS, 0 errors, 0 warnings, 47 existing deprecation hints.
- `cd site; npm run build`: PASS, 139 built routes (136 swept routes plus three legacy pilot redirects).
- `cd site; npm test`: PASS, 271 tests.
- `python -m unittest discover -s tests`: PASS, 1,868 tests.
- `python -m unittest tests.test_no_owner_name tests.test_house_style tests.test_measurements`: PASS, 24 tests after staging the added files.
- `node scripts/astra_phone_sweep.cjs` with `ASTRA_URL=http://127.0.0.1:49803/gradient_ascent/` and `ASTRA_PLAYWRIGHT` set to an existing Playwright installation: PASS, 136 routes at 360, 390, 430 and 1440 px (544 checks). No page overflow, local asset failures, uncaught page errors or missing amber token. The runner follows the timed `/learn/` redirect before measuring.
- Initial run: the harness incorrectly inspected redirect notices; one home-page capture also lacked CSS. That capture was flaky. Home and four relevant pages passed three independent repeat runs, then the full corrected sweep passed. No permanent site defect was inferred from the transient capture.
- Mobile menu open/Escape-close and the search no-results state: PASS at 360 px.
- Prohibited hostname/IP scan: PASS against the staged branch, values not printed. New secret-shaped text scan: PASS. `git diff --cached --check`: PASS.

[Sweep evidence](astra-screens/sweep.json), [three-repeat evidence](astra-screens/repeat-checks.json), [interaction evidence](astra-screens/interaction-checks.json).

Screenshots were visually inspected: [360](astra-screens/home-360.png), [390](astra-screens/home-390.png), [430](astra-screens/home-430.png), [desktop](astra-screens/home-1440.png), [measured technique](astra-screens/techniques-agentic-rag--360.png), [timeline](astra-screens/timeline--430.png), [menu](astra-screens/menu-360.png), [no results](astra-screens/search-empty-360.png). The site has one dark theme; no light-theme coverage is claimed.

## Review scope

No prompt, live model, live dataset, deployment, service configuration, or main checkout was changed. The only external requests read public sources. Screenshots use the isolated preview on port 49803.
