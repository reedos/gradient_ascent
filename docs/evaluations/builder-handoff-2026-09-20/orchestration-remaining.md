# Orchestration notes: remaining builder trials

- Date: 2026-09-20
- Coordinator task: `/root/remaining_trials`
- Actor model: `gpt-5.6-luna` for all simulators and builder receivers, fresh `fork_turns: none` sessions, inherited default reasoning settings.
- Reviewer model: `gpt-5.6-sol`, fresh `fork_turns: none` session.
- Mode: agent-operated actual live form. Each generator run used `node .local/eval-browser.cjs generate ID`; generated `artifact.md` and downloaded `download.md` were retained alongside `browser.json`.
- Cost, tokens, completion time, and latency were not measured.
- Shared filesystem isolation was instructional, not enforced. Every actor was told exactly which files it could read.

| Case | Simulator actor | Receiver actor | Question rounds | Notes and limitations |
| --- | --- | --- | ---: | --- |
| DD-1 | `/root/remaining_trials/sim_dd1` | `/root/remaining_trials/recv_dd1` | 0 | Receiver produced a direct provisional final. Manifest-listed attachment files were unavailable at the declared paths; receiver recorded this. |
| DD-2 | `/root/remaining_trials/sim_dd2` | `/root/remaining_trials/recv_dd2` | 1 | Simulator answered the first-response questions in `builder-answers-1.md`. Receiver had already produced a provisional final with unknowns marked; no post-answer rewrite was requested. Manifest-listed attachments were unavailable. |
| WA-1 | `/root/remaining_trials/sim_wa1` | `/root/remaining_trials/recv_wa1` | 1 | Simulator initially saved the four field answers without the required `{slug, values}` wrapper. The same actor corrected only the wrapper; answer text was unchanged. Questions were answered as unknown. Manifest-listed attachments were unavailable. |
| WA-2 | `/root/remaining_trials/sim_wa2` | `/root/remaining_trials/recv_wa2` | 0 builder | Simulator initially omitted the required wrapper and corrected only the wrapper without changing answer text. Builder receiver reported the three explicit synthetic attachments accessible. The same simulator was later reactivated by the root coordinator for a separate baseline question round. |
| TS-1 | `/root/remaining_trials/sim_ts1` | `/root/remaining_trials/recv_ts1` | 1 | Simulator answered two material questions while preserving unspecified decisions. Receiver produced a provisional final before those answers; no continuation rewrite was requested. |
| TS-2 | `/root/remaining_trials/sim_ts2` | `/root/remaining_trials/recv_ts2` | 0 | Receiver produced a direct provisional final. All manifest-listed attachment paths were unavailable and logged. |
| PH-1 | `/root/remaining_trials/sim_ph1` | `/root/remaining_trials/recv_ph1` | 1 | Simulator initially used the slug as the outer JSON key. The same actor corrected only the wrapper; answer text was unchanged. It later answered receiver questions, leaving the revision/branch unknown. Receiver had already produced a provisional final. Four named attachments were unavailable. |
| PB-1 | `/root/remaining_trials/sim_pb1` | `/root/remaining_trials/recv_pb1` | 1 | Simulator initially used the slug as the outer JSON key. The same actor corrected only the wrapper; answer text was unchanged. It later answered receiver questions with all unspecified decisions left unknown. Receiver had already produced a provisional final. |

WF-1 already had simulator entries from `/root/sim_wf1`. This coordinator ran those entries through the actual live generator and retained the resulting artifact/download/browser evidence. The root coordinator owns its receiving trial. AI-2 and PH-2 were likewise assigned back to the root coordinator for receiving work. The completed pilots AI-1 and WF-2 were not modified by this coordinator.

The direct-final and pre-answer provisional-final runs are disclosed protocol variations. They follow the instruction to avoid unnecessary interview rounds and to deliver a complete provisional artifact with unresolved unknowns marked. Where questions were asked, they were still routed to the original simulator and preserved even when the receiver had already finalized.
