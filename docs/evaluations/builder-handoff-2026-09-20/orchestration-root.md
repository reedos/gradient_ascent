# Root orchestration record

Date: 2026-09-20. All first-pass simulators and receivers below used `gpt-5.6-luna`, fresh `fork_turns: none` sessions, with no reasoning-effort override. Access restrictions were provided in each initial task. Actual tool access and claims are recorded in each condition's access file.

| Case | Simulator | Builder receiver | Builder clarification |
| --- | --- | --- | --- |
| AI-1 | /root/sim_ai1 | /root/recv_ai1 | One round; answers delivered back before final |
| AI-2 | /root/sim_ai2 | /root/recv_ai2 | Direct provisional final, no questions |
| WF-1 | /root/sim_wf1 | /root/recv_wf1 | Direct provisional final, no questions |
| WF-2 | /root/sim_wf2 | /root/recv_wf2 | One round; answers delivered back before final |
| PH-2 | /root/sim_ph2 | /root/recv_ph2 | One round; answers delivered back before final |

Four baseline receivers used separate fresh sessions with the same model and permitted access, reading only baseline.md and attachments.json: /root/base_ai1, /root/base_wf2, /root/base_wa2, /root/base_ph2. Each asked questions, the original simulator answered from its case facts, and those answers were delivered before the final artifact. WA-2's simulator was /root/remaining_trials/sim_wa2. No receiving session saw another condition's output or private criteria in its supplied context.

AI-2 diagnostic replay: /root/strong_ai2, `gpt-5.6-sol`, fresh `fork_turns: none`, same artifact and attachments. It was not told about the path error or original result. One clarification round was answered by /root/sim_ai2 and delivered before stronger-final.md. This is a single diagnostic replay, not evidence of reliable model superiority or a matched repeated benchmark.

Independent reviewer /root/review_pilots used `gpt-5.6-sol` with fresh context for the first review. It reviewed AI-1/WF-2 builder and baseline, then continued to review AI-2, WF-1, PH-2, PH-2 baseline, and the AI-2 diagnostic replay. Reviews were grouped, a disclosed cost-saving departure from fresh reviewer sessions per case. Initial pilot review files were preserved before an evidence-based follow-up about a missed WF-2 completion contradiction. The reviewer issued a separate adjudication without changing scores.

Case preparation was delegated to /root/prepare_cases (`gpt-5.6-luna`), which did not read generator source. The coordinator normalized the tool slug identifiers before freezing cases. The scenario text and fixtures remained unchanged after freeze. Form snapshots were captured from the live site; the coordinator entered simulator-produced values using Playwright and saved actual browser-generated and downloaded text. No receiver was given generator source.

No website source changes, production deployments, original-task implementations, or external actions were made during these trials. Costs, tokens, and completion durations were not measured. The evidence was inspected and checksummed after collection.
