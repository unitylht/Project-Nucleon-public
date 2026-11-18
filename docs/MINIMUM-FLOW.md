# Minimum PoC flow v0.1 / 最小 PoC 流程

Date: 16 October 2026, Australia/Sydney.
Status: development proposal prepared at Hanting's request. Not team approval, owner delegation or implemented functionality.
Related: [interfaces](MODULE-INTERFACES.md), [facts and open questions](FACTS-AND-OPEN-QUESTIONS.md), [course requirements](COURSE-REQUIREMENTS.md).
Implementation note (16 October): a subset now runs in prototype/ with a live local model; prototype/README.md lists the differences. This document remains the proposal.

## One use case / 一个场景

A customer asks to extend the payment date of one existing invoice. Staff paste the message into a prototype inbox. The agent retrieves the relevant evidence, obtains missing information through an internal task, prepares an owner approval task, and drafts the reply after the owner decides. The record can be reopened.

客户申请延长一张现有发票的付款期限。员工将消息粘贴至原型收件入口，agent 查资料、通过内部任务补信息、准备老板审批任务，并在老板决定后生成回复草稿。处理记录可再次打开。

Reason for this candidate: Hoang reported date-based terms in S9, while the cleaned ledger and exact terms remain unavailable. This is a narrow scenario to validate, not evidence that the pilot business or scope has been selected.

选择依据：S9 中 Hoang 转述了按期限管理的条款，清理数据和确切条款尚未取得。该场景便于缩小验证范围，不代表已经确定案例企业或小组范围。

## Work handed to the agent / 交给 agent 的工作

| Manual work today to verify / 待核实的原人工工作 | Candidate agent action / 候选 agent 动作 | Persisted result / 保存结果 |
| --- | --- | --- |
| Interpret customer message / 读懂客户消息 | Extract invoice/date/reason and resolve identity through lookup tools / 提取发票、日期、理由并调用查询工具确定身份 | Structured proposal with message references / 带消息来源的结构化提取 |
| Search ledger, terms and owner context / 查账本、条款和老板背景 | Retrieve facts and confirmed notes / 读取事实与确认备注 | Evidence snapshot / 证据快照 |
| Discover and chase missing information / 发现缺项并追问 | Create a focused internal clarification task / 创建具体的内部补充任务 | Missing fields, assignee role, answer / 缺项、负责角色、回答 |
| Assemble a case for the owner / 整理给老板的审批材料 | Summarise sources, uncertainty and a proposed response, then invoke prepareApprovalTask / 归纳来源、不确定性和方案，并创建审批任务 | Owner brief and pending task / 老板简报与待办 |
| Write the response and record the case / 写回复并留档 | Draft from the committed decision and save linked history / 按已提交决定生成草稿并关联历史 | Decision + response draft + action log / 决定、回复草稿和动作日志 |

These are benefit hypotheses. Measure work removed and new review/input burden before claiming time savings.
上述为减负假设，需计入新增复核和录入负担后才能宣称节省时间。

## Trigger and flow / 触发与流程

The trigger is a persisted request.received event from staff submission, not the owner opening a dashboard and asking the model for advice. A single-process backend can run the agent; no queue infrastructure or multi-agent framework is required by this contract.

触发点是员工提交后保存的 request.received 事件，不需要老板先打开仪表板再向模型提问。单个后端进程即可运行，不要求消息队列或多 agent 框架。

1. **Receive / 接收:** server authenticates staff, saves the message and intake ID once, then starts an analysis run.
2. **Read and resolve / 提取与核对:** agent extracts candidate fields, calls customer/invoice lookup and retrieves confirmed knowledge. Names in free text are lookup hints, not trusted customer IDs.
3. **Fill gaps / 补缺:** ambiguous identity, invoice, date or applicable terms creates a clarification task. Agent stops that analysis run. Staff answers once, then a new run starts with refreshed evidence.
4. **Calculate and prepare / 计算与准备:** application code calculates invoice balance and date differences from verified inputs. Agent builds a source-linked brief and invokes prepareApprovalTask. The backend validates completeness and stores one pending owner task.
5. **Human decision / 人工决定:** owner approves the requested date, approves a different valid date, or declines. The backend checks role, request/evidence versions and decision payload before committing.
6. **Finish / 收尾:** agent reads the committed decision, drafts an appropriate reply and invokes saveResponseDraft. Reopening shows the original request, evidence, decision, draft and actions. Staff reviews/copies the draft for their normal channel.

No customer message is sent by v0.1. The inbox and clarification tasks are internal prototype functions, clearly disclosed in the demo. A saved approved extension is a prototype decision record; it does not overwrite original invoice terms or update accounting software.

v0.1 不自动向客户发送消息。收件入口与补充任务是内部原型功能，演示时明确说明。保存的延期批准是原型决策记录，不覆盖原发票条款或更新会计系统。

## Agent authority / Agent 权限

- May read authorised fictional evidence, select permitted lookup tools, identify missing fields, create clarification/approval tasks and save drafts.
- May propose an outcome with a short evidence-based explanation. Do not present similarity or a model confidence percentage as approval authority.
- May not commit a financial decision, change payment terms, grant itself authority, send a message or promote a one-off reason to a reusable rule.
- Owner decisions are stored for later retrieval with their original scope. Reusable knowledge/rule publication is deferred.
- Backend code validates permissions, date/amount calculations and state transitions. Untrusted customer messages, retrieved notes and model output cannot change these controls.
- All real-owner and team scope decisions remain open in the fact register. The initial prototype uses owner approval for every financial outcome.

Agent 可读取已授权的虚构证据、选择获准工具、识别缺项、创建补充或审批任务及保存草稿；可提出带简短依据的建议。财务决定由老板提交，权限、计算与状态转换由后端校验。一次审批不会自动成为通用规则。

## States / 状态

| State | Meaning / 含义 | Allowed next / 后续 |
| --- | --- | --- |
| received | Saved and ready for analysis / 已保存待分析 | analysing |
| analysing | One active run / 一次有效分析运行 | needs_information; awaiting_owner |
| needs_information | Waiting for an internal answer / 等待内部补充 | received after a validated answer |
| awaiting_owner | Complete brief or explicit manual-review fallback / 完整简报或明确的人工处理降级 | decided; received if staff changes inputs |
| decided | One owner decision committed / 已提交一条老板决定 | completed after response draft saved |
| completed | Decision and draft persisted / 决定与草稿已保存 | Read-only in v0.1 |

Clarifications, evidence refreshes and owner decisions increment request.version. Old analyses/tasks are superseded, not silently overwritten. A changed request or evidence invalidates an awaiting-owner task and requires a fresh run. A stale owner action returns a conflict.

补充、刷新证据和老板决定会递增版本。旧分析与任务保留但失效。资料变更后重新分析，旧审批动作返回冲突。

## Failure behaviour / 失败处理

- AI timeout, invalid structure or tool-call failure: stop the run and expose the error. If identity/invoice/date/terms are resolved, save a code-built, source-linked manual-review task with aiStatus=failed and no invented recommendation. Otherwise keep an internal clarification task; the owner cannot commit an extension until the required facts are verified. This is a degraded fallback, not a successful live agent run.
- AI reply drafting fails after the decision: preserve the decision and use a deterministic template containing exactly the committed outcome/date. Retrying must not create another decision.
- Missing facts are null/unknown and listed as missing. No fabricated zero balance, due date or refusal label.
- Restarts must recover persisted pending work. Duplicate intake/run/task/decision keys do not create duplicates. No autonomous repeated follow-up loop.

## Minimum data and UI / 最小数据与界面

Records: customers, invoice facts, confirmed notes, requests, analysis snapshots/tool actions, clarification tasks/answers, approval tasks, owner decisions and reply drafts. These can be logical records in one database; no separate service per record.

界面：一个员工请求入口及状态页、一个老板审批页、一个可重新打开的记录页。流程由后台推进，避免让用户逐项点击执行 agent 的内部步骤。选择技术栈与数据库是后续实现决定。

## Four fictional acceptance scenarios / 四个虚构验收情境

| Case | Expected result / 预期 |
| --- | --- |
| Complete request, known invoice and terms / 信息完整 | Agent retrieves evidence, code calculates dates, pending owner task appears without staff assembling a brief. Owner approves; draft matches decision and survives reopen. |
| Missing/ambiguous invoice or terms / 发票或条款缺失 | Agent creates one clarification task; no approval or invented date. Answer resumes a fresh analysis. |
| Owner declines or changes date / 老板拒绝或改期 | Persist that exact outcome. Draft must reflect it, even if the agent proposed another result. |
| AI unavailable / AI 不可用 | Mark failed AI run, show source-linked manual fallback, preserve decision and template draft. Disclose degraded mode. |

Also verify one duplicate submission and one stale owner submission. These test persistence and control, not predictive accuracy. Use realistic fictional data; the actual dataset, owner rules and value claims remain pending.

## Deferred / 暂缓

Over-limit orders, credit-limit increases, partial payments/conditional approvals, financial auto-approval, live ledger imports, accounting writeback, external messaging, policy-builder UI, automatic rule learning, model training and cloud deployment. Keep these out of v0.1 until the narrow flow and business evidence justify expansion.
