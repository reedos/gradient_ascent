# Gradient Ascent audit, 10/07/2026

Status: partly recertified. The 10/08/2026 pass (WebFetch) checked 32 more claims against reachable primary sources: 30 verified as written, 2 footnoted, none wrong. Pages on 30 URLs still refuse automated access (see Needs owner review). This document does not certify every external claim.

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
| Claude cache reads universally cost 0.1 times input | Fixed | [Prompt caching documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), pricing table and footnotes checked 10/07/2026. Added 0.025 and 0.05 model exceptions. Follow-up 10/08/2026: the 0.05 exception omitted Sonnet 5.5; now names both. Source (WebFetch 10/08/2026): "Cache hits and refreshes on Claude Opus 5.5 and Claude Sonnet 5.5 are priced at 0.05x the base input price.", kept 1.25 and 2 write multipliers with durations. |
| Prompt caching means omitting the prefix from requests | Fixed | Same primary documentation, request examples and cache behavior. Wording now describes reuse of prefix computation. |
| Three cheap attempts always cost more than one expensive attempt | Fixed | The sum must exceed the alternative cost. Removed the unconditional assertion and the claim that batching cannot help low-volume work. |
| All numbers on the cost page are vendor rates | Fixed | The page also contains a synthetic worked price table. It now distinguishes those example prices from vendor discounts. |
| GraphRAG indexing costs 1,000 times vector retrieval generally | Footnoted | [Microsoft comparison](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) reports 0.1%; the inverse is scoped to that comparison, not a general price or a local measurement. |
| LLM judge agreement exceeds 80%; paper date 06/09/2023 | Confirmed as reported | [MT-Bench paper](https://arxiv.org/abs/2306.05685), abstract and submission history. The page already attributes the study and lists judge biases. |
| ECI combines benchmark scores | Confirmed definition only | [Epoch ECI](https://epoch.ai/eci) supports the definition. Individual values remain the dated 09/18/2026 snapshot; this pass did not replace it or independently recertify each historical score. |
| Phi is a Microsoft small-model family; Milvus is a vector database | Confirmed identity only | [Phi](https://azure.microsoft.com/en-us/products/phi) and [Milvus](https://milvus.io/) read successfully with the web reader after transport failures in the batch. |

## Recertification pass, 10/08/2026

Tool: WebFetch. Each claim was checked against the source text the tool returned, not against the fact that the page loaded. The tool answers through a small model, so the quotes below are what it reported as verbatim; where it said a phrase was absent or paraphrased, the row says so. Statuses: verified (source supports number, date and wording), footnoted, unreachable.

| Claim on the site | Status | Source sentence or number read |
|---|---|---|
| Transformer paper 06/12/2017, "dispensing with recurrence and convolutions" | Verified | arXiv 1706.03762: submitted 12 Jun 2017; "dispensing with recurrence and convolutions entirely" |
| XGBoost 03/09/2016 | Verified | arXiv 1603.02754: 9 Mar 2016; "used widely by data scientists to achieve state-of-the-art results" |
| GPT-3 05/28/2020, 175 billion parameters, no gradient updates | Verified | arXiv 2005.14165: 28 May 2020; "an autoregressive language model with 175 billion parameters"; "applied without any gradient updates or fine-tuning" |
| Chain of thought 01/28/2022 | Verified | arXiv 2201.11903: 28 Jan 2022; "significantly improves the ability of large language models to perform complex reasoning" |
| InstructGPT 03/04/2022, 1.3B preferred to 175B, 100x fewer parameters | Verified | arXiv 2203.02155: 4 Mar 2022; "outputs from the 1.3B parameter InstructGPT model are preferred to outputs from the 175B GPT-3, despite having 100x fewer parameters" |
| GPT-4 report 03/15/2023, multimodal, human-level on benchmarks | Verified | arXiv 2303.08774: 15 Mar 2023; "GPT-4 exhibits human-level performance on various professional and academic benchmarks" |
| DeepSeek-R1 01/22/2025, pure RL, self-reflection | Verified | arXiv 2501.12948: 22 Jan 2025; "incentivized through pure reinforcement learning (RL)", "obviating the need for human-labeled reasoning trajectories" |
| RAG paper 05/22/2020, Wikipedia dense index | Verified | arXiv 2005.11401: 22 May 2020; "the non-parametric memory is a dense vector index of Wikipedia" |
| AI Chains 10/04/2021 | Verified | arXiv 2110.01691: 4 Oct 2021; "Chaining LLM steps together, where the output of one step becomes the input for the next" |
| MRKL 05/01/2022 date | Verified | arXiv 2205.00445: 1 May 2022 |
| MRKL: quoted router sentence; router is a small neural network | Footnoted | Not in the abstract text the tool returned; the PDF could not be read as text. Note added to the timeline entry. |
| Toolformer 02/09/2023 | Verified | arXiv 2302.04761: 9 Feb 2023; "decide which APIs to call, when to call them, what arguments to pass, and how to best incorporate" |
| ReAct 10/06/2022 | Verified | arXiv 2210.03629: 6 Oct 2022; "reasoning traces help the model induce, track, and update action plans as well as handle exceptions" |
| CAMEL 03/31/2023 | Verified | arXiv 2303.17760: 31 Mar 2023; "a novel communicative agent framework named role-playing" |
| Multiagent debate 05/23/2023 | Verified | arXiv 2305.14325: 23 May 2023; "improves the factual validity of generated content, reducing fallacious answers and hallucinations" |
| Generative Agents 04/07/2023, 25 agents | Verified | arXiv 2304.03442: 7 Apr 2023; "a small town of twenty five agents using natural language" |
| LoRA 06/17/2021; 10,000 times fewer trainable parameters, 3 times less GPU memory vs GPT-3 175B with Adam | Verified | arXiv 2106.09685: "LoRA can reduce the number of trainable parameters by 10,000 times and the GPU memory requirement by 3 times." |
| Self-consistency 03/21/2022 | Verified | arXiv 2203.11171: 21 Mar 2022; GSM8K +17.9%, SVAMP +11.0%, AQuA +12.2%, StrategyQA +6.4%, ARC-challenge +3.9% |
| MetaGPT 08/01/2023; assembly line; SOPs; "more coherent solutions" | Verified | arXiv 2308.00352: "On collaborative software engineering benchmarks, MetaGPT generates more coherent solutions than previous chat-based multi-agent systems." |
| Hallucination cascade 06/06/2026: 500 cascades, 10 domains, 1,250 responses, 0.422 to 0.272, accuracy 0.789 to 0.769, three models | Verified | arXiv 2606.07937: "from 0.422 at the first agent to 0.272 at the final agent in 3-agent chains"; "a decline in factual accuracy from 0.789 to 0.769"; "500 cascade experiments across 10 knowledge domains", "1,250 evaluated responses"; GPT-5.3, DeepSeek-V3, LLaMA-3-70B-Instruct |
| DSPy paper 10/05/2023 | Verified | arXiv 2310.03714: 5 Oct 2023 |
| Why Language Models Hallucinate 09/04/2025 | Verified | arXiv 2509.04664: 4 Sep 2025; "the training and evaluation procedures reward guessing over acknowledging uncertainty" |
| pi0 date 10/31/2024; up to 50 per second for dexterous tasks | Verified | arXiv 2410.24164: submitted 31 Oct 2024; "up to 50 Hz for dexterous tasks such as laundry folding" |
| pi0 trained on "8 distinct robots" (quoted from the maker's blog) | Footnoted | The paper says "7 different robot configurations and 68 tasks" for its dexterous data. The blog was unreachable (429). Note added to the timeline entry. |
| Multi-agent research: agents use about 4x the tokens of chat, multi-agent about 15x | Verified | Anthropic engineering post: "agents typically use about 4x more tokens than chat interactions, and multi-agent systems use about 15x more tokens than chats" |
| LazyGraphRAG indexing identical to vector RAG, 0.1% of full GraphRAG | Verified | Microsoft Research post: "LazyGraphRAG data indexing costs are identical to vector RAG and 0.1% of the costs of full GraphRAG." Scope stays as footnoted on 10/07. |
| OWASP Gen AI Red Teaming Guide announced 01/22/2025; quoted "practical approach to evaluating LLM and Generative AI vulnerabilities" and "spans from model-level vulnerabilities (toxicity, bias) to system-level pitfalls (API misuse, data exposure)" | Verified | OWASP announcement: publication date January 22, 2025; on a targeted second read both quoted phrases were reported present with exact wording |
| OWASP LLM06: "an extension to run one specific shell command fails to properly prevent other shell commands from being executed" | Verified | LLM06:2025 page contains that sentence. Its mitigations also say to limit extension functionality and permissions and to validate downstream requests "rather than relying on the LLM itself". |
| Tesla Optimus: "applying our artificial intelligence learnings from self-driving technology to Bots, such as Optimus, a general purpose, autonomous humanoid robot in development" | Verified | Tesla 10-K for FY2025 on SEC.gov. The filing also says "we may experience delays in launching and ramping the production" of Bots. |
| Make is part of Celonis | Verified | make.com: "The visual AI automation platform"; "now part of Celonis" |
| Phi-4-mini and Phi-4-multimodal are the newest Phi models | Verified | Azure Phi page lists Phi-4-multimodal, Phi-4-mini, Phi-4, Phi-3.5 and Phi-3; "Phi is the Microsoft family of small language models (SLMs)" |
| Milvus is a vector database | Verified | milvus.io: "The High-Performance Vector Database Built for Scale" |

Counts for this pass: 30 claims verified, 2 footnoted (MRKL router sentence, pi0 robot count), 0 found wrong, no site prose changed. Claims verified on 10/07 (MT-Bench, RAG paper, prompt caching, GraphRAG scope, Muse Glimmer, ECI) stand as listed in the first table. Mechanical guard added: `tests/test_arxiv_dates.py` pins 23 arXiv v1 dates against every arXiv-sourced timeline milestone and technique-page source.

## Source access and outstanding claim work

Initial pass 10/07/2026: 451 URLs, 413 retrieved, 9 denied, 25 skipped on denied hosts, 4 transport failures. Second pass 10/08/2026 with WebFetch tried all 38 of those. Six were reached (OWASP red-teaming announcement, OWASP LLM06, SEC 10-K, Make, Phi, Milvus). Thirty were refused by the sites with HTTP 403 or 429; each got one retry where the first try failed, and no other tool or mirror was used. Two failed in transport: web.archive.org, which WebFetch declines to fetch, and the defunct Neeva site. The register now shows 419 retrieved, 30 denied, 2 unavailable. Beyond the claims in the tables, the retrieved sources were not rechecked claim by claim.

[Full access register](ASTRA-SOURCE-ACCESS-2026-10-07.json) records availability only; a reachable page is not evidence that a paraphrase, benchmark or date is correct. Unlisted external claims remain unrecertified, and prior source dates were not bulk advanced.

### Needs owner review

These URLs still refuse automated access. Each needs a copy the owner approves or a manual check. The claims they support stay unrecertified.

| Reference | Access result | Affected content |
|---|---|---|
| https://www.perplexity.ai/help-center/en/articles/10352895-how-does-perplexity-work | HTTP 403, 10/08 | site/src/content/teardowns/answer-engine.mdx |
| https://www.perplexity.ai/help-center/en/articles/10354917-what-is-an-answer-engine-and-how-does-perplexity-work-as-one | HTTP 403, 10/08 | site/src/content/teardowns/answer-engine.mdx; landscape.json perplexity |
| https://www.perplexity.ai/help-center/en/articles/10352901-what-is-perplexity-pro | HTTP 403, 10/08 | site/src/content/teardowns/answer-engine.mdx |
| https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research | HTTP 403, 10/08 | site/src/content/teardowns/deep-research-mode.mdx; landscape.json perplexity-deep-research |
| https://openai.com/policies/business-terms/ | HTTP 403, 10/08 | site/src/content/techniques/distillation.mdx |
| https://www.pi.website/blog/pi0 | HTTP 429 (twice), 10/08 | site/src/content/techniques/embodied.mdx; timeline.json milestone pi0-2024; landscape.json pi0 |
| https://www.pi.website/blog/pi07 | HTTP 429, 10/08 | site/src/content/techniques/embodied.mdx; timeline.json milestone pi0-7-2026; landscape.json pi0-7 |
| https://web.archive.org/web/20260915180415id_/https://ai.google.dev/gemini-api/docs/function-calling | domain refused by WebFetch, 10/08 | site/src/content/techniques/function-calling.mdx |
| https://openai.com/index/better-language-models/ | HTTP 403, 10/08 | timeline.json milestone gpt-2-post-2019 |
| https://openai.com/index/openai-api/ | HTTP 403, 10/08 | timeline.json milestone gpt-3-api-2020 |
| https://openai.com/index/chatgpt/ | HTTP 403, 10/08 | timeline.json milestone chatgpt-launch |
| https://openai.com/index/learning-to-reason-with-llms/ | HTTP 403, 10/08 | timeline.json milestone o1-reasoning-models |
| https://openai.com/index/introducing-text-and-code-embeddings/ | HTTP 403, 10/08 | timeline.json milestone openai-embeddings-2022 |
| https://neeva.com/blog/introducing-neevaai | transport failure (socket hang up), 10/08 | timeline.json milestone neeva-ai-2023 |
| https://openai.com/index/memory-and-new-controls-for-chatgpt/ | HTTP 403, 10/08 | timeline.json milestone chatgpt-memory-2024 |
| https://openai.com/index/chatgpt-plugins/ | HTTP 403, 10/08 | timeline.json milestone chatgpt-plugins-2023 |
| https://help.openai.com/en/articles/6825453-chatgpt-release-notes | HTTP 403, 10/08 | timeline.json milestone chatgpt-plugins-beta-2023 |
| https://openai.com/index/function-calling-and-other-api-updates/ | HTTP 403, 10/08 | timeline.json milestone openai-function-calling-2023 |
| https://openai.com/index/introducing-operator/ | HTTP 403, 10/08 | timeline.json milestone operator-2025 |
| https://openai.com/index/introducing-chatgpt-agent/ | HTTP 403, 10/08 | timeline.json milestone chatgpt-agent-2025 |
| https://openai.com/chatgpt-work/ | HTTP 403, 10/08 | timeline.json milestone chatgpt-work-2026; landscape.json chatgpt-work |
| https://openai.com/index/gpt-6-astra/ | HTTP 403, 10/08 | landscape.json gpt-6-astra |
| https://openai.com/index/gpt-5-6/ | HTTP 403, 10/08 | landscape.json gpt-5.6-sol; landscape.json gpt-5.6-terra; landscape.json gpt-5.6-luna |
| https://openai.com/index/introducing-gpt-oss/ | HTTP 403, 10/08 | landscape.json gpt-oss |
| https://help.openai.com/en/articles/9260256-chatgpt-capabilities-overview | HTTP 403, 10/08 | landscape.json chatgpt |
| https://www.midjourney.com/ | HTTP 403, 10/08 | landscape.json midjourney |
| https://help.openai.com/en/articles/10169521-projects-in-chatgpt | HTTP 403, 10/08 | landscape.json chatgpt-projects |
| https://help.openai.com/en/articles/8590148-memory-faq | HTTP 403, 10/08 | landscape.json chatgpt-memory |
| https://help.openai.com/en/articles/8437071-data-analysis-with-chatgpt | HTTP 403, 10/08 | landscape.json chatgpt-data-analysis |
| https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq | HTTP 403, 10/08 | landscape.json custom-gpts |
| https://help.openai.com/en/articles/20001274 | HTTP 403, 10/08 | landscape.json chatgpt-voice |
| https://www.iso.org/standard/76583.html | HTTP 403, 10/08 | landscape.json sql |

## Verification

- `python scripts/validate.py`: PASS.

- Rerun 10/08/2026 after the recertification edits: `python scripts/validate.py` PASS; `npx astro check` PASS (0 errors, 47 hints); `npm run build` PASS (139 routes); `npm test` PASS (271); `python -m unittest discover -s tests` PASS (1,871 tests, including 3 new in `tests/test_arxiv_dates.py`).
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
