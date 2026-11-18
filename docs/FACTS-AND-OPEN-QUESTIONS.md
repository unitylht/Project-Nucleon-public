# First-build facts and open questions / 首轮开发事实与待确认项

Reviewed: 16 October 2026, Australia/Sydney.

Status: evidence reconciliation for Hanting's first development-preparation step. This note records existing instructions and gaps. It does not adopt a product scope, assign new work to teammates, or authorise live business actions.

## Confirmed instructions / 已确认要求

| Item / 项目 | Current record / 当前记录 | Source |
| --- | --- | --- |
| Product direction / 项目方向 | Stream 1, Founder's Second Brain: reduce owner intervention in business credit requests. Exact first request type remains open. / 减少老板处理企业信用请求的工作，首个请求类型仍未定。 | U2; README |
| Course requirement / 课程要求 | Agentic AI must be core or add substantial value. Specify trigger, inputs, decisions, tool actions, human checks and outcome. / AI 必须承担实质工作，需明确触发、输入、判断、工具动作、人工确认和产出。 | S10; COURSE-REQUIREMENTS |
| Week 7 / 第七周 | Hard stop at 7 minutes, then 5 minutes Q&A. Title plus at most four content slides, approximately 3 minutes slides and at least 4 minutes core demo. Backup recording and accessible PROMPTS.md. / 展示严格七分钟，另有五分钟问答；封面外最多四页内容，约三分钟讲解、至少四分钟核心演示，准备备份录屏和可访问的 PROMPTS.md。 | S11–S12 |
| Development / 开发安排 | Local/home-server first. The temporary skeleton uses Python standard library and SQLite; production stack/model remain open. / 先本地开发，临时骨架使用 Python 标准库与 SQLite，正式技术栈和模型仍未定。 | U1; D001 |
| Shared record / 共享记录 | Repository Markdown is current. HTML maintenance stopped. / 仓库 Markdown 为当前记录，HTML 已停止维护。 | U3; D002; D005 |
| Prototype status / 实现状态 | A runnable fictional workflow exists under prototype/. In live mode a local Gemma model extracts requests, selects permitted tools and prepares clarification/owner-approval tasks; code validates calls and calculations, and the owner decides. Mock/unavailable modes remain for tests. PROMPTS.md records prompts and boundaries. Deployed 18 Oct (`89b92d8`, E007): setup, a Records page with manual entry, and invoice-list CSV import. Deployed to the shared practice demo 18 Oct (`4f45ca7`, E011; phone top-bar fix `a9ce30d`, E012; branch not merged). Interface redesign and QA dispositions on branch `feat/ux-redesign-20261018` (E013; not merged or deployed): records in tables, payments with explicit allocations, payment-list CSV import, opening balances, owner-confirmed completeness and exact amounts only from complete records, with opening credits accounted for (E010). / prototype/ 已有可运行虚构流程；live 模式下由本地 Gemma 模型提取请求、选择获准工具并准备补信息／老板审批任务，代码校验调用与计算，老板决定。mock／unavailable 模式保留用于测试；PROMPTS.md 记录提示词与边界。10 月 18 日已部署（`89b92d8`，E007）：初始设置、手工录入的记录页面与发票清单 CSV 导入。10 月 18 日已部署到共享练习实例（`4f45ca7`，E011；手机顶栏修正 `a9ce30d`，E012；分支尚未合并）。界面重新设计与测试发现处理位于分支 `feat/ux-redesign-20261018`（E013；尚未合并或部署）：记录改存数据表、明确分配的收款记录、收款清单 CSV 导入、期初余额、老板确认的完整性，以及只在记录完整时给出的确切欠款。 | Repository inspection, 16 Oct; E007–E013, 18 Oct |
| Demonstration data / 演示数据 | Use realistic fictional data and distinguish live, mocked and planned functions. / 使用合理虚构数据，明确实做、模拟和计划功能。 | S8; S11–S12 |

## Reported evidence / 已有转述与数据证据

| Item / 项目 | Supported statement / 可以记录的事实 | Limit / 边界 |
| --- | --- | --- |
| Staff authority / 员工授权 | Hoang reported that experienced managers may reach similar answers to the owner but hesitate over responsibility. / Hoang 转述有经验经理可能会判断，但担心责任。 | S9 1:44–3:43; not a directly observed staff test. Business attribution remains open. / 并非直接员工测试，企业归属待核实。 |
| Owner judgement / 老板判断 | Reported factors include amount, duration, promises and relationship context. / 转述因素包括金额、期限、承诺和客户关系。 | S9 28:36–33:24; no confirmed delegation or universal numeric threshold. / 尚无确认的授权或通用数值阈值。 |
| Terms / 付款条款 | Hoang described generally 30-day terms and **two** customer exceptions for the ledger-provider business (NTK = Nutek). A later team report, relayed by Hanting on 17 October, says 30 days for most Nutek customers with **three** exceptions; its original speaker or document is not identified. / Hoang 描述账本企业（NTK 即 Nutek）通常三十天，有**两个**客户例外；Hanting 于 10 月 17 日转述的后续团队信息为多数客户三十天、**三个**例外，原始说话人或文件未确认。 | S9 16:19–17:30; team report relayed 17 Oct. Conflicting and second-hand: record no Nutek terms until the business confirms the default, each exception, the start rule and changes over time. Do not impose an amount cap from an illustrative architecture. / 两种说法相互冲突且均为转述：在企业确认默认条款、各例外、起算规则和变更前，不录入任何 Nutek 条款；不能照架构示例强加金额上限。 |
| Businesses / 企业归属 | Hanting, 17 October: Art of Gelato supplied the owner interview (S2); NTK is **Nutek**, a different business whose receivables ledger the team obtained; Dr. Kyan is another separate business. / Hanting 10 月 17 日说明：Art of Gelato 提供老板访谈（S2）；NTK 即 **Nutek**，是团队取得应收账本的另一家企业；Dr. Kyan 为另一独立企业。 | These materials do not establish one shared business policy. Keep records, owner statements and policies attributed to their own business. Which business, if any, will test with real data remains open (Q01). / 这些材料不构成共同的企业政策，各自记录、老板说法与政策须按企业归属；由哪家企业用真实数据试用仍未定（Q01）。 |
| Ledger / 账本 | Older audit describes 511 rows over 13 months. / 旧审查记载十三个月、五百一十一行。 | S3; not 511 decisions, not a fresh audit, not approval/refusal labels. / 并非五百一十一条审批，不是新审查或批准／拒绝标签。 |
| Latest delivery update / 最新交付进度 | Hoang requested Saturday 17 October delivery while clarifying the description column and other questions with the owners. / Hoang 申请周六十月十七日交付，先向老板澄清 description 列和其他问题。 | S13; requested date, not verified acceptance or completion. Owner meeting outcomes not yet supplied. / 是申请日期，未核验接受或完成，尚未收到访谈结果。 |
| Workload / 工作量 | Team discussed work removed, work added and information reused. Chris offered to draft measurable criteria. / 团队讨论减少、新增和可复用的工作，Chris 承诺起草量化标准。 | S9 33:48–41:46; no baseline or numeric target adopted. / 尚无基线或采纳的量化目标。 |

## Proposals remain proposals / 仍属于提案

- Employee/owner web interfaces, a backend, stored evidence and a replaceable model interface are the architecture direction presented by Hanting, not a confirmed production stack. A fictional subset now runs with a replaceable local-model adapter; this is not a production stack or model selection. / 员工与老板网页、后端、保存证据和模型接口是架构方向，尚非正式技术栈。虚构子集现已通过可替换的本地模型适配器运行，但不代表正式技术栈或模型选择。
- Rules, exception briefs, decision capture and later reuse are candidate mechanisms. The English architecture document explicitly calls itself a discussion proposal. / 规则、例外简报、决策采集与复用是候选机制，英文架构文档明确属于讨论提案。
- Hoang's approved-example experiment is exploratory. Late payment cannot supply verified approval labels, and approval-only testing cannot measure false approvals of refused cases. / Hoang 的批准案例实验仍属探索。晚付不能直接作为获批标签，仅有批准案例不能验证拒绝案例被错批的情况。
- A single owner decision is not a reusable authority rule. Retrieval, explicit knowledge updates and model training are different methods. / 单次决定不等于可复用授权，检索、明确知识更新和模型训练是不同方法。

## Open question register / 待确认项

P0: needed before fixing the business workflow and authority. P1: needed before valid data integration or benefit claims. Contacts below reflect existing roles, not new assignments.

| ID | Missing decision/evidence / 缺少的决定或证据 | Existing contact / 现有对应人 | Effect on development / 对开发的影响 |
| --- | --- | --- | --- |
| Q01 · P0 | Identify the pilot business and link owner reports, policies and ledger to it. / 明确首个案例企业，将老板转述、政策和账本对应起来。 | Hoang + team; Hanting reconciles records / Hoang 与团队，Hanting 核对记录 | Prevent combining Art of Gelato, NTK and unnamed-business claims. / 避免将不同企业证据混用。 |
| Q02 · P0 | Select one request type, its normal manual steps and actual arrival channel. / 选定一个请求类型，确认现有人工步骤及真实接收渠道。 | Team + pilot owner/staff; coordination open / 团队及案例老板／员工，协调待定 | Defines trigger, input and completed business output. Payment extension remains a candidate. / 决定触发、输入和业务产出，延期仍是候选。 |
| Q03 · P0 | Specify what the agent may do independently and what staff/owner must approve, with scope and examples. / 明确 agent 可独立执行的工作，以及员工／老板必须审批的事项、范围和例子。 | Owner via existing contact Hoang / 通过现有联络人 Hoang 获取老板意见 | Until confirmed, financial outcomes remain proposals requiring human approval. / 确认前财务结果只能作为待人工审批的提案。 |
| Q04 · P1 | Receive cleaned data, description-column meanings, field definitions, currency, invoice/payment matching and applicable terms/exceptions. / 取得清理数据、description 含义、字段、币种、发票收款匹配及适用条款例外。 | Hoang | Blocks real-data mapping and valid lateness calculations, not fictional workflow scaffolding. / 阻塞真实数据映射和有效晚付计算，不阻塞虚构流程骨架。 |
| Q05 · P1 | Obtain owner-confirmed approval/refusal cases, reasons and unknown cases. / 取得老板核实的批准、拒绝及未知案例与理由。 | Hoang; scenario coordination open / Hoang，情境协调待定 | Needed for evaluating decision behaviour; no invented labels. / 用于验证判断行为，不能补造标签。 |
| Q06 · P1 | Obtain request frequency, handling/search time, interruptions and new setup/review burden; draft measurable success criteria. / 取得请求频率、处理查找耗时、中断与新增设置复核负担，起草量化成功标准。 | Chris drafts; owner inputs via Hoang; team reviews / Chris 起草，Hoang 对接老板，团队审阅 | Defines net benefit without inventing a target. / 定义净收益，不虚构目标。 |
| Q07 · P1 | Prepare plausible fictional scenarios and assign owner review plus separate evaluation cases. / 准备合理虚构情境，明确老板审阅及独立评估案例。 | Team; Tony's questionnaire informs this; coordinator/date open / 团队，Tony 问卷提供输入，协调与日期未定 | Enables honest end-to-end demo and testing; scenarios are not real-world validation. / 支持如实演示和测试，虚构情境不等于真实验证。 |
| Q08 · Before real data/external actions | Confirm data access/handling, model destination, and any authority for customer communications. / 确认真数据访问处理、模型去向及任何客户沟通授权。 | Owner + team; Tony's trust/privacy research informs explanation / 老板与团队，Tony 研究支持说明 | No existing-channel integration or real customer sending is currently authorised. / 当前没有已获授权的渠道集成或真实客户发送。 |

## Hanting's immediate work boundary / Hanting 当前可推进范围

**Can proceed / 可先做:** reconcile these records; draft one candidate agent workflow with explicit tool actions; define replaceable interfaces and fictional scenarios. These are preparation outputs, not evidence that the team adopted the flow.

**Depends on incoming evidence / 依赖后续输入:** real-data integration and verified term calculations depend on Q04; autonomous financial decisions depend on Q03; model/decision accuracy claims depend on Q05; net time-saving claims depend on Q06.

**First-step completion / 第一步完成标准:** facts, reports and proposals separated; revised data date recorded; unresolved items have evidence needs and existing contacts. A candidate workflow now runs with live local-model case preparation on fictional data; business scope validation and value measurement remain subsequent steps.

References use the source IDs in PROJECT-STATE.md. Meeting details remain in meetings/2026-10-15.md. Current course constraints remain in COURSE-REQUIREMENTS.md. No messages were sent to teammates or owners by this reconciliation.

