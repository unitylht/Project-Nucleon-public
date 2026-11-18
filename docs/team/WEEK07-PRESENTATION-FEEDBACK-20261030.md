# Week 7 — Group 9 Nucleon/CreditEase presentation and feedback

**Recorded:** 30 October 2026 · **Event:** INFS3605 Week 7 PoC presentations (Wednesday 28 October 2026; an earlier edit of this line said 21 October, which was wrong: the narrated video shown that day was made on 28 October).  
**Source:** user-provided 2h53m classroom recording transcribed by *Parakeet v3* and *Whisper Large v3 Turbo*, plus the presenter's own account of the audio setup. Quotation spelling/punctuation is normalised from imperfect ASR; speaker attribution and word-for-word accuracy are **not audio-verified**. Recording timecodes are approximate. This is not a grading report.

## Executive takeaway

The external Microsoft speaker, **Chitra**, responded strongly to Nucleon's problem selection and **delegated AI decision authority**. She positioned the design at the more autonomous/intelligent end of a three-stage AI maturity framing, rather than treating it as another chatbot or recommendation dashboard. Her recurring recommendation was to prove measurable owner/business impact.

The teaching team's specific question was **how an approval, Owner correction and eventual repayment outcome close the learning/decision loop**. They revisited the question in a brief conversation after the presentations because the loop was **not explicit in the demonstration**.

The class presentation had an audio-routing failure: the team was using Teams screen sharing to a seminar-room computer with remote Microsoft participation and was, per the presenter's recollection, the only group needing to play a narrated video. Feedback/echo disrupted the demo. The transcript shows at least two audio/demo interruptions. It cannot independently diagnose the exact feedback path.

## What happened (recording offsets)

| Offset | What happened |
| --- | --- |
| 2:08:25–2:09:02 | Group 9 opening; mic initially off and introduction restarted |
| 2:09:03–2:10:22 | Credit-exception bottleneck, tacit Owner judgement, approach and evidence |
| ~2:10:47–2:11:16 | Attempted narrated demonstration; sound/echo issue and change to spoken explanation |
| 2:11:16–2:12:55 | Agent workflow and build-stage explanation |
| ~2:13:00–2:16:18 | Narrated demo retried: Owner policy, Northside bounded internal approval, Harbourline escalation; Lakeside information-gathering case not fully shown |
| 2:16:41–2:18:20 | Chitra's substantive positive feedback and AI impact-report suggestion |
| 2:18:52–2:21:16 | Teaching-team Q&A: post-decision feedback and Owner reasoning |
| 2:38:03–2:40:56 | Post-presentation conversation: teacher asks to make the closing loop clear in final presentation |

## Positive feedback from Chitra

1. **Problem fit.** She called the selected credit-decision bottleneck one of the clearest Founder's Second Brain problems and distinguished it from simply automating an administrative task. Credit judgements are difficult for a time-poor owner to delegate.
2. **Genuine agentic delegation.** She described maturity progressing from chat to assistance to automation/intelligent decision-making and explicitly put Nucleon's approach in the third category.
3. **Meaningful human oversight.** Owner sets classes/limits of decisions that can be delegated. The Agent handles requests inside them and returns genuine exceptions to the Owner. This **does not** imply every request needs human approval, nor does it authorise approvals without a server-enforced delegation policy.
4. **Main improvement: AI impact reporting.** Show how delegated requests affect Owner workload and business value (before versus after). This was a recurring theme in her feedback to other groups too; praise is **not a numerical class ranking**.

Short ASR excerpts (approximate wording):
- “One of the best clear Founder Second Brain problems.” (~2:16:41)
- “I see you are in the third maturity…” (~2:17:07)
- “Make that as an AI impact report…” (~2:17:35)

## Teaching team's question: closing the loop

At ~2:18:52 the teacher asked how an Owner decision and eventual customer payment/default are **captured and fed back into future judgements**. In the group's answer, historical decisions, Owner rationale, behavioural questionnaires and accumulating examples were described.

In the follow-up (~2:38:03), the teacher said this **closing loop was not visible** and should be made explicit in the final presentation. That is a presentation and product-evidence gap, not a request to abandon delegated autonomy.

Show two different loops rather than blending them:
- **Decision-learning loop:** request + evidence + recommendation → Owner approves/overrides with *reason* → decision/provenance saved → reviewed cases can inform the next case. A one-off exception does not automatically become policy.
- **Commercial-outcome loop:** effective credit decision → observe later invoice/payment status → reconcile on-time/late/loss and evidence completeness → evaluate decision and future policy. The existence of a payment ledger is not proof that a historical exception was approved.

**Current-evidence caution:** the 27 Oct engineering handover reports partial decision-memory, feedback and fictional evaluation features. It does **not** establish a validated real-business repayment learning cycle or an automatic model-weight retraining pipeline. In class, the team verbally described “training the model”; the final presentation must differentiate retrieval/case memory, policy updates and actual ML retraining.

## Audio incident / demonstration quality

The Teams room/remote-audience setup made playing video sound difficult, with severe echo. The team switched to spoken explanation and retried. Presentation interruption is documented; the claim of being the only group with a narrated video is attributed to the presenter.

For the final demo: use one verified audio path, explicitly test narration on the **actual room + Teams configuration**, keep a labelled silent-captioned fallback, pre-authenticate scenes, and make the decisive backend decision card legible independently of audio. Do not claim the 3:58.842 edited Week 7 recording is a continuous live inference time.

## Additional accuracy caveats

- During Q&A the team stated it could run locally and keep data on-device. This is **deployment-specific**; a remote API, storage, telemetry or Teams sharing path changes the disclosure. Confirm the exact actual configuration before claiming “data never leaves the computer.”
- Demo cases, policy thresholds and reported 17/17 engineering browser checks use fictional data. They do **not** measure real NTK credit accuracy, owner time saved or financial outcomes.
- Chitra's feedback was strongly positive, but she also gave many groups praise and repeatedly encouraged impact reporting; no formal class rank is inferred.

## Implications

1. **Do not pivot away from delegated autonomy.** The core idea was understood and valued.
2. **Demonstrate** decision authority, evidence requests, escalating over-limit cases and the closing loop in one coherent story.
3. **Measure** whether Owner involvement genuinely falls, including new setup and review burden.
4. Prioritise **real Owner/Staff PoV**, product usability and reliable facts over speculative new prediction features.

See [product roadmap](../product/POV-ROADMAP-20261030.md) and [validation protocol](../research/POV-VALIDATION-PLAN-20261030.md).
