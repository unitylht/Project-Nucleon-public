# Module interfaces v0.1 / 模块接口

Date: 16 October 2026. Status: proposed contract, not implemented API.
Scope: [one-invoice payment-extension flow](MINIMUM-FLOW.md). Language/framework/database/model-neutral.
Implementation note (16 October): a subset now runs in prototype/ with a live local model; prototype/README.md lists the differences. This document remains the proposal.
JSON examples describe payloads; runtime validation is required when implemented.

## Module boundaries / 模块边界

| Module | Input → output | Owns / 职责 |
| --- | --- | --- |
| Intake / 接收 | message + optional identity hints → Request | Authenticated intake, deduplication, request.received event / 身份、去重、接收事件 |
| Evidence / 证据 | authorised customer/invoice IDs → EvidenceSnapshot | Lookup, original terms, balances, confirmed notes and provenance / 查询、原条款、余额、备注和来源 |
| Facts / 计算 | verified evidence + proposed date + asOfDate → ExtensionFacts | Money/date arithmetic and known/unknown fields; no LLM / 金额日期计算与未知项 |
| Agent runner / Agent 运行 | request version + permitted tools → AnalysisResult | Extraction, tool choice, clarification, brief and action trace / 提取、选工具、补充、简报与动作记录 |
| Workflow / 流程控制 | tool command + trusted actor/run context → task/state | Tool validation, permission/state/version checks, durable tasks / 工具校验、权限状态版本与持久任务 |
| Decision and history / 决定与历史 | owner command → Decision; committed Decision → ResponseDraft | Atomic decision, linked history, response validation / 原子决定、关联历史与回复校验 |

These are modules of one backend. UI uses workflow APIs. Only the backend calls the model. A replaceable model adapter receives minimised evidence and an allowlist of tools; it does not receive database credentials.

以上是单个后端内的模块。界面调用流程 API；模型仅由后端调用，可替换适配器接收必要证据与工具白名单，不取得数据库凭据。

## Common data conventions / 通用数据约定

- IDs are opaque strings. businessId and actor identity/role come from the authenticated server session, never from an untrusted request body or model output.
- Dates are validated calendar dates YYYY-MM-DD. Instants are UTC ISO timestamps. The business timezone is configuration; fictional fixtures may use Australia/Sydney, without assuming that is the real pilot timezone.
- Money: {minorUnits: "125000", currency: "AUD", scale: 2}. minorUnits is an integer string; parse as an integer, not a binary floating-point currency amount. Currency/scale are verified configuration, not inferred from names/account codes. This example is fictional.
- Unknown values are null plus a MissingField entry, never 0, false or an invented date.
- EvidenceRef = {recordType, recordId, version, origin, locator}. origin is fictional, owner_confirmed, staff_reported, ledger or derived. Derived facts retain their input refs; source-message claims are not promoted to verified ledger facts.
- Models output a concise decision explanation with sources, not private reasoning traces. Store tool names/arguments/results or result refs, model ID, prompt version, timestamps and failure status. Keep secrets outside logs.

## Core records / 核心记录

### Request

~~~json
{
  "id": "req_demo_001",
  "version": 1,
  "type": "payment_extension",
  "status": "received",
  "dataMode": "fictional",
  "intake": {
    "channel": "prototype_inbox",
    "externalMessageId": null,
    "text": "Could we pay invoice DEMO-101 on 30 October instead?",
    "receivedAt": "2026-10-16T06:00:00Z"
  },
  "customerId": null,
  "invoiceId": null,
  "requestedDueDate": null,
  "requestReason": null,
  "activeAnalysisId": null,
  "decisionId": null
}
~~~

Extraction can propose resolved fields, but saving requires backend validation against authorised evidence. An ambiguous customer/invoice remains unresolved. Staff need not supply a preassembled account summary.

### EvidenceSnapshot and ExtensionFacts

EvidenceSnapshot stores {id, requestId, requestVersion, asOfDate, businessTimezone, evidenceVersion, customer, invoice, confirmedNotes, missingFields, sourceRefs}. The invoice includes customerId, originalDueDate, currentEffectiveDueDate, outstandingAmount, applicableTermsRef and sourceRefs. Existing approved extensions may explain currentEffectiveDueDate without replacing originalDueDate.

ExtensionFacts stores {snapshotId, invoiceOutstanding, currentEffectiveDueDate, requestedDueDate, extensionDays, daysOverdue, missingFields, sourceRefs}. Each computed value is a sourced field {value, sourceRefs}; unavailable value is null.

- extensionDays = requestedDueDate minus currentEffectiveDueDate, in calendar days. Positive extension required in this flow.
- daysOverdue = max(0, asOfDate minus currentEffectiveDueDate), only for a verified positive outstanding balance and verified due date. Fully paid invoice returns 0; unknown balance/date returns unknown.
- Extension does not add the invoice amount to exposure. Outstanding balance changes only through verified payments/adjustments, not this approval.
- If payment allocation or due terms cannot be established, do not calculate lateness from aggregate ledger totals. Require clarification.
- Request date must be later than asOfDate and currentEffectiveDueDate. Unsupported/non-extension requests require clarification; no silent conversion to another request type.

MissingField = {field, reason, neededFrom, sourceRefs}. neededFrom is staff or owner. In v0.1 all clarification tasks appear in the internal prototype UI, not an external customer channel.

### AnalysisResult

~~~json
{
  "id": "analysis_demo_001",
  "requestId": "req_demo_001",
  "requestVersion": 2,
  "snapshotId": "snapshot_demo_001",
  "aiStatus": "live",
  "modelId": "configured-at-runtime",
  "promptVersion": "extension-v0.1",
  "route": "awaiting_owner",
  "missingFields": [],
  "brief": {
    "summary": "Customer requests a later payment date for DEMO-101.",
    "facts": [],
    "context": [],
    "uncertainties": [],
    "suggestedOption": null
  },
  "actionIds": ["action_demo_001"],
  "createdAt": "2026-10-16T06:00:10Z"
}
~~~

aiStatus: live, mocked or failed. route: needs_information or awaiting_owner. brief facts/context are sourced statements {text, sourceRefs}; uncertainties are explicit strings. suggestedOption is null or {outcome: approve|decline, proposedDueDate, explanation, sourceRefs}, never a committed outcome or authority. A suggested approval needs a proposed date; decline has null. API responses distinguish an AI proposal from a Decision.

Model-returned numbers/dates are checked against ExtensionFacts; unsupported claims invalidate the brief or are shown as uncertainty, never saved as facts. The backend derives route from validated completeness, not solely from a model route string.

### OwnerDecision and ResponseDraft

~~~json
{
  "id": "decision_demo_001",
  "requestId": "req_demo_001",
  "requestVersionBefore": 2,
  "analysisId": "analysis_demo_001",
  "evidenceVersion": "evidence_demo_v1",
  "outcome": "approve",
  "approvedDueDate": "2026-10-30",
  "reason": "Approved for this invoice only.",
  "scope": { "kind": "single_invoice", "invoiceId": "invoice_demo_101" },
  "decidedBy": "owner_demo_001",
  "decidedAt": "2026-10-16T06:01:00Z"
}
~~~

outcome: approve or decline. A changed valid date is still approve, with the owner's selected date. approvedDueDate is null for decline. reason is required and brief. decidedBy/time/scope are server-generated/validated. Only one final decision per request in v0.1.

ResponseDraft = {id, requestId, decisionId, text, generation: live|mocked|template, deliveryStatus: not_sent, createdAt}. It must match the committed outcome/date and approved scope, and contain no new commitments. Model drafts are structured around fixed decision fields; if validation cannot establish faithfulness, use a deterministic template. Saving a draft never marks a message sent. Staff review is required before copying it out of the prototype; semantic faithfulness of free text is not established by a JSON schema.

### Task and run records / 任务与运行记录

ApprovalTask = {id, requestId, requestVersion, analysisId, snapshotId, evidenceVersion, mode: agent|manual_fallback, status: pending|decided|superseded, createdAt}. The owner screen displays its expected request/evidence versions. ClarificationTask = {id, requestId, requestVersion, missingFields, question, status: pending|answered|superseded, createdAt, answerRefs}. Tasks preserve history when replaced.

AnalysisRun = {id, requestId, requestVersion, status: running|waiting|finished|failed|superseded, modelId, promptVersion, aiStatus, startedAt, finishedAt, actionIds}. Human answers create a new run; old runs cannot write against a newer version.

Resolved identity/date fields and immutable intake text remain distinct. A run records extracted candidates with message refs; application code validates candidate record IDs and dates before using them. Input/evidence revisions invalidate old tasks. Status/run bookkeeping must not silently change the task's expected input version.

## Internal service signatures / 内部服务接口

| Service call | Contract |
| --- | --- |
| Intake.create | (trustedActor, message, hints, idempotencyKey) → Request |
| Evidence.snapshot | (trustedContext, resolvedCustomerId, resolvedInvoiceId, asOfDate) → EvidenceSnapshot |
| Facts.calculate | (EvidenceSnapshot, requestedDueDate) → ExtensionFacts |
| Agent.run | (requestId, expectedVersion) → AnalysisRun; permitted side effects only through Workflow tool dispatcher |
| Workflow.executeTool | (trustedRunContext, toolName, validatedArguments, actionKey) → persisted result or typed tool error |
| Decision.commit | (trustedOwner, expectedVersions, decisionFields, idempotencyKey) → OwnerDecision |
| History.read | (trustedActor, requestId) → authorised linked records |

### Replaceable model adapter / 可替换模型适配器

respond({task, promptVersion, messages, toolDefinitions}) → {kind: tool_calls, calls: [{callId, name, arguments}]} OR {kind: structured_output, value}.

- task is extract_request, handle_request or draft_reply. Extraction output = {customerQuery, invoiceReference, requestedDueDate, reason, sourceLocators, missingFields}; all candidate values are nullable and untrusted.
- The runner supplies tool definitions only for the current phase. It executes validated calls, appends results and continues within the run cap. A final model answer alone cannot create an approval/clarification task.
- Draft phase receives only the committed decision and necessary fictional identifiers, with saveResponseDraft as its write tool. It cannot read unrelated customers or change the decision.
- Adapter errors normalise to timeout, unavailable or invalid_output. Keep provider SDKs and model-specific messages inside this adapter; no provider or framework is selected by this signature.

## Agent tools / Agent 工具

Every call receives server-injected {businessId, actorId, runId, requestId, requestVersion}. The model cannot choose these. Arguments below are model-visible payloads only.

| Tool | Arguments → result | Side effect / 边界 |
| --- | --- | --- |
| findCustomers | {query} → [{id, displayCode}] | Read-only, business-scoped / 仅读，同企业 |
| getInvoiceFacts | {customerId, invoiceReference?} → candidate invoices + sourced facts + missing fields | Reject cross-customer IDs; multiple matches require clarification / 拒绝跨客户，歧义待补充 |
| getConfirmedKnowledge | {customerId} → confirmed notes with scope/date/refs | Read-only; drafts are excluded / 仅读，排除待确认知识 |
| calculateExtension | {snapshotId, requestedDueDate} → ExtensionFacts | Code calculation; snapshot/request must match / 代码计算，快照需匹配 |
| createClarification | {missingFields, question} → {taskId, status} | Persist one versioned internal task; no customer send / 保存内部任务，不发送 |
| prepareApprovalTask | {snapshotId, brief, suggestedOption} → {taskId, status} | Validate evidence, required fields and run/version; persist awaiting-owner task / 校验后创建审批任务 |
| saveResponseDraft | {decisionId, text} → ResponseDraft | Only after committed decision; validate correspondence, not_sent / 决定提交后才可保存，未发送 |

The backend builds and saves snapshots from validated lookup results before calculateExtension/prepareApprovalTask. It records extraction proposals and tool execution results; the model cannot inject an arbitrary snapshot as trusted evidence.

Tool errors: NOT_FOUND, AMBIGUOUS, MISSING_DATA, STALE_VERSION, FORBIDDEN, INVALID_ARGUMENT, DEPENDENCY_UNAVAILABLE. Route recoverable missing data to one internal clarification task; tool failure/invalid model output can instead require the disclosed manual fallback. Limit each run to 12 tool calls (provisional engineering cap, not a business rule), deduplicate writes by run/request version/action type, and stop on a pending human task. Exactly one active run per request.

There is no approveCredit, changeTerms, sendMessage, publishRule or raw SQL tool in v0.1.

## UI/backend APIs / 界面与后端接口

| Endpoint | Input | Output / effects |
| --- | --- | --- |
| POST /api/requests | {messageText, customerHint?, invoiceHint?}; Idempotency-Key header | 202 {requestId, version, status}; save intake and schedule/resume run |
| GET /api/requests/:id | Authenticated session | Request + current task/analysis + history, authorised by role/business |
| POST /api/requests/:id/clarifications/:taskId/answers | {expectedRequestVersion, answers}; Idempotency-Key | 202; validate field types/refs, preserve answer provenance, supersede analysis/task and resume |
| POST /api/requests/:id/reanalyse | {expectedRequestVersion}; Idempotency-Key | 202; refresh snapshot and create one run; valid only before decision |
| POST /api/requests/:id/decisions | {expectedRequestVersion, analysisId, evidenceVersion, outcome, approvedDueDate, reason}; Idempotency-Key | 201 Decision; owner only, atomic commit, then start draft generation |
| GET /api/requests/:id/response-draft | Authenticated session | 200 ResponseDraft, or explicit pending/failed generation status |

Answers are a list of {field, value, sourceRef?}, restricted to the task's missing fields. Identity fields must resolve to authorised customer/invoice records. Date/terms answers supplied by staff stay staff_reported until verified under the configured evidence policy; an unverified answer can be included in a manual owner-review brief but cannot silently become a confirmed term. Demo fixtures identify which facts are fictional and treated as verified for demonstration.

Server resolves business/role from session. Staff may submit and answer their authorised tasks, but cannot call the decision endpoint. Demo roles still need server-side separation. A browser role selector is not authority.

- 400 invalid input; 401 no session; 403 forbidden; 404 missing/unauthorised record; 409 stale request/evidence or invalid transition; 422 unresolved required fields.
- Same idempotency key and same payload returns the stored result; same key with a different payload returns 409.
- Before committing, check current invoice state, applicable terms/notes versions, active task/analysis and request version. If evidence has changed, return 409 and require reanalysis.
- Decision + request transition + decision event are one transaction. Agent runs after commit; draft failure never rolls back or repeats the decision.
- Store pending work durably and recover it on process restart. These requirements do not mandate a separate queue service.

## Implementation order / 实现顺序

1. Fictional evidence adapter and deterministic facts functions.
2. Durable request/task/decision records and state checks.
3. Agent tools + replaceable model adapter.
4. Staff intake/status and owner approval screens.
5. Draft generation, reopen history and four acceptance scenarios from MINIMUM-FLOW.md.

Interfaces and states are the v0.1 proposal. API server, database, real model calls and tests of actual functionality have not been implemented by writing this document.
