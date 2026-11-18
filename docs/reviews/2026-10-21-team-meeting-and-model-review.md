# Team meeting of 21 Oct 2026 and the credit model: decisions, discussion, assumptions, evidence

For the project team to check and correct. Where this document is wrong, please say so; it replaces nothing until you do.

## 1. Sources and how to read this

The sources are two automatic transcripts of the 21 Oct 2026 meeting (about 3 h 45 min; two different speech engines, called V1 and V2 here), a Chinese meeting summary, and Hoang's brief and scripts in the `1021` folder (cleaning script, training script, notebook, documents). The transcripts have no speaker labels, so attribution of statements to people is uncertain and is avoided here. Timestamps are approximate and are V1 unless marked V2. "[?]" marks a transcription doubt. Nothing was run: the scripts and the notebook were read, not executed, and every figure quoted from them is as written in the files.

Two points about the meeting itself:
- The recording starts mid-flow; substantive content begins at about 2:46.
- Tony was not present. He is discussed in the third person, and a short note to "ask Tony" appears at the end (3:42).

## 2. Team decisions (what was explicitly agreed)

### 2.1 Product and scope
- The target owner is a small B2B business that has staff but no managers; not a sole trader, not a large corporation [2:47:35, 2:47:43, 2:05:06]. Stated in passing and not contested.
- The problem: the owner is overloaded by staff requests; the product moves the owner's judgement into a data model plus an AI that acts "as the owner to the staff" [1:39:15, 1:39:25].
- Pitch label used in the room: "Founder's second brain" [1:39:42].
- Credit infrastructure is part of the value claim: small firms often have no policy or credit ceiling. Evidence is from interviews (a Hong Kong meat business and a Vietnamese government business) [1:19:23, 1:43:17].
- Proof-of-concept scope is payment-term (time) extensions only. Credit-limit increases wait until Week 7 to 10 if time allows [1:06:21].
- Why not plain ChatGPT: it has only short-term memory; the product adds a database and computation [11:50-12:58].

### 2.2 Architecture
- Two named parts: Nucleus (system, database, calculations, tools) and Nucleus Lab (chat-style AI interface) [3:14-3:38].
- Agreed flow (whiteboard, "cosmetic changes only" at 1:16:02): staff enters a request, the AI agent calls tools, the fixed numerical models return Yes/No plus a confidence level, the LLM interprets and flags irregular patterns, the output goes to staff, staff agree / disagree / escalate, and everything is written back to the database as historical data [1:08:52, 1:09:07].
- Two phases: a one-time onboarding and ongoing operation [26:21].
- Every decision, including a disagreement, is stored as historical data at once [1:08:52, 33:25].

### 2.3 Authority and escalation
- Staff ask the AI first, not the owner. If the AI is confident, staff proceed; if not, it escalates [30:26].
- Confidence is the trigger. Low confidence in a Yes does not mean a high chance of No; it means escalate [1:35:08-1:35:35].
- Example threshold: "under eighty percent ask the owner" [35:46]. V2 hears "8%" there [?]. The number is an example, not a fixed value, and the threshold must be recorded [35:11].
- All escalation goes to the owner, not to a manager. It may happen in chat, email or by phone, but it must be recorded [1:12:11, 1:12:25].
- If staff go to the owner directly, the system cannot stop it but keeps prompting them to record the decision [1:13:05].
- With little data the AI escalates almost everything until there is enough history [1:27:07].
- Policy default: a credit policy cannot be violated, and a request is by definition an exception, so the default answer is no. A model that always says no is not wrong but not useful; the product's value is the occasional safe yes [1:41:08-1:41:27].
- Staff may disagree with the AI, with friction [1:58-2:14]:
  - a written reason and evidence are required; no disagreement on instinct alone [1:59:08, 2:05:25];
  - one to three rounds of debate with the AI, instant rather than spread over days; treated as 2 rounds, configurable [2:14:05; V2 2:14:16];
  - if staff convince the AI it agrees; if not settled it escalates to the owner;
  - every point of the debate is recorded [2:09:42];
  - when staff disagree again, the system shows a similar past case and its outcome [2:00:22].
- Model says escalate but staff are sure of an answer: it is still escalated to the owner [1:11:53, 1:12:11].
- Model says Yes, staff say No: staff can ask the system to escalate [1:07:35-1:08:02].
- Two owner modes in the control panel: A, the system decides and staff have no say; B, staff may disagree and the owner sees more escalations [1:58:23]. Floated by one member and not rejected; treat as agreed in outline.
- Trust KPI: show the system's current confidence on a dashboard (for example 79 percent); at about 80 percent the owner might start trusting it [1:56:38-1:57:46]. The wording was loose (see section 4).
- The owner is liable for the AI's mistakes, which is why confidence and redundancy exist [1:39:42].
- The control panel is human-only: fixed numerical models and thresholds can be changed only by a person; the AI can propose but not change [2:50:58-2:51:17]. A second panel lists what the AI may reason on (market, owner preference, history, model output) [1:01:41]. The number of debate rounds is also a panel setting [2:01:27].

### 2.4 Numerical model versus LLM
- A fixed computing part, customisable through a control panel, with results readable by both people and the AI agent. The LLM adds reasons the maths cannot [59:44, 1:00:04].
- The numerical model returns Yes/No plus a confidence value, is reproducible, and does not interpret [46:12-47:19].
- The same model set runs for every company [39:51-40:10, 53:05].
- The LLM explains, flags irregular patterns, and does context work on ledger text. It must not change the numbers.
- The LLM decides whether a reason is needed; for an exact repeat of a past case, the number is the reason [1:03:10].
- The builder uses the model code as a framework and does not rewrite it. Retraining uses the same steps: new features, train, test, output, log back [52:48, 2:50:04, 2:51:19].
- Models compared on the same data: baseline, logistic regression, SVM, KNN [39:51, 59:09].
- Retraining is a daily batch after hours, not per request [41:34]. Raised by the model owner and accepted without objection.

### 2.5 What is predicted, and the labels
- Target: approval by the owner of a request, with inputs such as amount, date and customer, and output Yes / No / not sure plus confidence [35:20, 44:34, 44:56].
- The historical data has no real Yes/No ("no one recorded yes or no" [6:49]), so the model owner built a "yes and no proxy" from history [3:17:14]. The accounts of its meaning in 3:17-3:18 are garbled; V1 gives "yes = late but we approved it" and V2 [3:17:24] says "pure late" [?]. Section 6 sets out what the scripts actually do.
- Lateness rule: late is late whatever the amount; partial payment counts as late [2:32:34].
- A customer's trust falls if they ask for 10 days and pay at 12. The numbers use internal records, not what the customer says [2:08:59, 2:08:13].
- Outliers are kept [2:19:10].

### 2.6 Decisions and feedback capture
- The owner decision card in Nucleus records the decision, the reason, and whether the reason applies to the whole client or this case only [1:21:50].
- A system log of ongoing decisions by staff or owner [1:23:56, 1:24:05]. It was not yet wired into the maths [1:13:57-1:14:46].
- Staff notes after each transaction [8:46]. The debate transcript is stored (see 2.3).

### 2.7 Import and onboarding
- First-time setup: the user uploads existing data and the system says what it has, what is missing and what more would help [7:54-8:46].
- Expect messy input, especially description columns [1:44:20].
- The AI does the cleaning, not the user. Target flow: AI extracts context from the ledger and flags inconsistencies; the accountant fixes flagged items; re-import [2:45:14-2:46:43]. In the Lab, a button auto-fills the column mapping and the user reviews [2:35:15].
- The owner does not fix the ledger. The owner answers Tony's questionnaire instead [2:46:43].
- On an unknown code (for example "TTHD") the agent asks the owner, not the person cleaning [2:34:31].
- One currency per dataset; conversion is the accountant's job [2:16:17, 2:18:26]. Currency conversion is not built.
- AI import tasks: extract context, flag inconsistencies, create new variables, clean [2:55:10-2:56:14]. The order of cleaning and flagging was left open.
- Onboarding is not demonstrated live in Week 7, and not rebuilt for Week 10; a UX mockup and an honest statement of limits are used instead [2:44:04, 2:38:35].
- No pre-training on other companies is possible [1:28:27].
- The questionnaire reflects the owner's mind, asked in rotation (for example weekly), and in onboarding creates made-up scenarios from past transactions; each answer is stored as a new historical data point [1:18:03, 1:31:19-1:32:16].

### 2.8 Week 7 presentation plan [3:08-3:41]
- Format: 7 minutes of presentation plus demo, 5 minutes of Q&A; at most 4 content slides plus title and appendix [3:09:44-3:10:08]. Tutors suggest about 3 minutes of slides and 4 of demo [3:27:41].
- Slides: (1) problem and evidence, 45 s; (2) high-level solution and why it works, 45 s; (3) the agentic feature: business process, trigger, action, where the human stays in the loop, data use, 1 min; (4) build environment: tools, models and how they fit, 30 s [3:21:01-3:27:08].
- After the solution slide, go to the live product, then return to the technical slides [3:25:42].
- Everyone speaks for at least about 30 s, subject to the tutor's answer [3:19:34, 3:19:51].
- Live demo plus a screen-recorded backup that shows product use, not onboarding [3:29:21, 2:43:42].
- Appendix: interview list and data sources [3:09:12].
- Message to the audience: be open about limits (no budget, no servers) [2:13:00].
- Cut from the demo: market and policy research ("at scale" only), live onboarding and retraining, false customer data (assume accurate inputs), credit-limit increases, manager tier, pre-training [2:59:09, 2:21:36, 2:07:24, 1:06:21, 2:05:06, 1:28:27].
- Owners and dates as heard:
  - AI import, AI fetching of results and the demo video: Hanting; polish "the math part and the import part" first [3:05:07, 3:29:43]. The due date is heard as "Week six Sunday" [?].
  - Training, testing, logging, confidence score: the model owner; described as done and on standby until Wednesday [3:07:08].
  - BPMN including the disagreement flow by Thursday morning, then success criteria, plus content for slides 1-2: Chris [3:07:42, 3:36:44, 3:08:29].
  - Information for slides 3-4 from another member; Tony makes the slides look good [3:32:07].
  - Information to slide owners by Saturday, slides done Sunday, scripts Sunday night or Monday, final deadline "week 7 Monday", final edits Tuesday [3:38-3:41].
  - Next meeting tomorrow night, 8 to 9 pm [2:44:53].

## 3. Exploratory discussion (floated, not agreed)

- Brain choice: keep a local AI model, or give ChatGPT access to Nucleus through an external MCP with Nucleus as dashboard and storage [10:40-11:27]. Open. The current prototype uses Claude with MCP tools.
- The agent writes new calculations to find more data [25:21]. Objected to: the numbers must stay fixed [2:50:58].
- Evidence in a debate lowers the confidence score until it crosses the threshold and the case escalates [2:10:18, 2:10:58]. Doubted as more complicated in practice [2:11:21]. Not decided.
- Debate with a day between rounds. Instant was preferred [2:13:42].
- Whether the confidence number includes the LLM or only the maths ([2:12:22]). The working answer was that the LLM is a bridge and confidence stays with the maths. Not formally agreed.
- A persona journey for owner and staff [39:07]. Requested, not done.
- Draw.io or MCP for diagrams [1:08:33, 2:02:57].
- Chat-only versus buttons plus chat: "we can have both" [52:12].
- A prepared onboarding video made in Figma [2:22:40]. Partly taken up as a UX mockup.
- A table of entries needed against escalation rate, and estimates from trying 10 or 20 entries [1:32:31, 1:30:29]. A request, not built.
- Credit-limit mode after Week 7 [1:06:41].
- Pulling in market data from the web, and "different sources" at scale [2:11:55, 2:54:14].
- Brand colours (red and yellow) and the icon: "later" [14:11, 14:35].
- A pre-trained common model for new businesses [1:28:14]. Dismissed as impossible.
- Canva for slides; one paid account is needed [0:48].
- Longer-term role of staff in the process [1:38:44, 1:56:16]. Not a decision and not for the external presentation.

## 4. Assumptions stated as fact (no evidence given)

Business and owner:
- The owner is overwhelmed by requests that are "correlated in many ways" [1:40:23].
- "Every business" in this segment has this problem [1:42:31].
- Small firms have no credit ceiling or policy [1:42:57]. Based on one interview.
- The owner's decisions are less than 80 percent consistent [1:57:46].
- The accountant is a separate person with basic accounting knowledge.
- A customer who promises 10 days pays 10 days late [2:08:21]. Hypothetical.

Data:
- 100 entries gives 50 percent escalation and 500 gives 20 percent [1:32:50]. Invented to illustrate.
- One transaction a day gives a useful model in about two months [1:28:05].
- 200 owner answers make "a good model" [1:32:16].
- The ledger fields are enough to infer approvals; only some real Yes/No exist [6:49].
- The demo database has 21 customers [1:46:12] or 14 [2:19:52]. Unresolved.

Model:
- The model is "very comprehensive" [36:37], although nobody had checked what the demo runs [36:56].
- The maths is "never wrong" [46:15]. Reproducible is true; correct is not shown.
- The Lab agent can use the model code when told [53:32]. Unverified.
- 80 percent confidence is enough to trust [1:57:46]. No accuracy figure was shown.

Rules:
- Any lateness counts as late, regardless of amount.
- The owner is always the escalation point; there is no manager level.
- Importing VND shown as AUD would not matter to model training [2:17:34]. Challenged at 2:17:50 and not resolved.

Cost and effort:
- The Lab build took about five days and about 850 dollars of tokens [1:23:16-1:23:41]. Whether a customer would pay for cleaning through a cloud API was not costed [2:36:39].

## 5. Demonstrated evidence (shown or measured)

- No accuracy, precision or recall figure was stated in the meeting. The only numbers were illustrative (79 to 80 percent trust, 100 and 500 entries).
- Nucleus demo [1:20:35-1:25]: buttons for add customer, import data, world knowledge and a set-up page that shows missing data; a staff/owner role switch; the owner decision card; the system log. It ran on mock data, not the raw dataset [1:24:34].
- Nucleus Lab [1:22:11]: chat-style, half built. It says when it cannot answer and which data it used. It ran on the older, uncleaned dataset, not the model owner's cleaned one [1:22:41]. Nucleus and Lab were not yet combined [1:20:48].
- Lab answer test [3:15:59-3:17:06]: for a case already decided it answers; with the date changed to this year it answered "no record". The model owner's observation was that the system "is not predicting, it is retrieving", because the data has no Yes/No to learn from. Not fixed in the meeting.
- Labelled historical rows [3:17:14-3:18:47]: real rows with Yes/No proxies were shown. One company's requests were all denied but it still paid late [3:18:12-3:18:37].
- Import bugs seen [2:14-2:24]:
  - VND amounts displayed as AUD (about 200,000 dollars for 5 million VND) [2:14:54];
  - customer 01's entry of 13 Sep 25 (about 9,700,000) did not import [2:23:37], and an invoice search for "BH" found nothing [2:24:07];
  - a "BH" / "001 13 95" document number was noted for follow-up [V2 2:25:02];
  - invoice 73 was missing from the clean data, then found in the raw file [2:30:36-2:31:03]; its ledger lines are sale, VAT, a line to ignore, and payment, with the balance back to zero [2:31:25];
  - "unknown customer" labels appeared on import [1:44:57].
- AI import: the column-mapping button was still being written during the meeting, and at 3:29:43 was reported as just working and untested [2:35, 3:29:43].
- The server restarted during the import test, which held up the test for several minutes [1:29:57, 1:37:30]. The demo machine had no Python runtime [1:25:50].
- Interpretability was marked as possibly done [2:54:41] but then "not tested" [3:30:04]; it may be removed. Results did not appear because the import was missing.
- The agent's tool list was shown on screen; its content was not read out [3:03:27].
- Process: the whiteboard diagram was photographed [1:04:48, 2:45:32] and is to become a BPMN. It was never fully described in the transcript.
- Not yet shown: the model's output for a real request, the confidence value on screen, the debate flow, the model control panel (its contents are unclear [58:59]).
- Reactions to the preview: the simple chat Lab is "simple enough" [2:21:21]; the role switch and decision card were received well. Too many buttons on Nucleus [53:46]; the import form needs every column selected by hand [2:35:15]; mock data is very thin. The reset needed to show onboarding is not possible because retraining takes too long [2:21:45]. The team asked for the demo to be tested before more features are added [54:18, 55:50].

## 6. The credit model: what it can honestly support

Scope: Hoang's training script (`train_credit_models.py`, "T"), cleaning script (`clean_ntk_data (1).py`, "Clean"; the (1) and (2) copies are byte-identical, 427 lines) and notebook (`NTK_Cleaning_EDA_Training.ipynb`, "NB", 52 cells). Read only; nothing was run.

Summary: the model scores a proxy, not the owner's decision. The claim it can support is a payment-behaviour risk indicator ("this customer has paid late before or is late now"), not "the owner would approve or deny an extension".

### 6.1 Target and labels
- The target is a binary `Proxy Label`: Approve (proxy) = 0, Deny (proxy) = 1 [T:241]. One row is one customer payment (receipt) that carries a label [T:204].
- A payment is a candidate for a label only if, just before it, an open FIFO invoice of that customer was past its due date [Clean:232-273]:
  - customer 0014 is the exception: if overdue, Deny (proxy) [Clean:34];
  - every other customer: if overdue, Approve (proxy);
  - a payment with nothing overdue is left unlabelled.
- Plain reading: "Approve" means the customer paid while something was overdue and, by assumption, was tolerated. "Deny" means the owner has said this customer may never pay late, or (for 0021) that two late receipts were not approved.
- The three customer exceptions come from owner statements: 0014 and 0004 are "never approved to pay late" [Clean:326-327, NB cell 14], and two receipts of 0021 (BC26000041, BC26000067) were unapproved [T:75-85]. They are statements about customers or two receipts, not a decision log.
- Counts [NB cell 22]: 114 payments, 85 labelled, 29 unlabelled and left out. Of the 85 labelled: 77 Approve (13 customers) and 8 Deny. All 8 Deny rows belong to three customers: 0004 (1), 0014 (5), 0021 (2). A summary figure of 426 unlabelled rows counts all 511 ledger rows minus the 85, including non-payment rows.
- Holdout: 2 Deny rows, both from customer 0014, who is also in the training data.
- Consequence: the Deny class is "customer identity plus an overdue payment". The target is deterministic given the customer and whether anything was overdue.
- The Approve label is the weakest part. A late payment is evidence of lateness, not of an approved extension; some customers may have paid late without asking.
- No request records exist: requested amount, requested days and request date are not in the data. NB cell 23 states "The real request date is unavailable."

### 6.2 Features
- 12 numeric features, all computed from the ledger by the replay in T:124-231: `credit_term_days`, `debt_before_m`, `overdue_before_m`, `max_days_past_due_before`, `prior_invoice_documents`, `prior_billed_m`, `prior_received_m`, `prior_receipt_count`, `has_prior_receipt`, `days_since_prior_receipt`, `observed_relationship_days`, `prior_late_receipt_fraction` [T:234-239].
- `credit_term_days` is not in the ledger. It is a hard-coded dictionary by anonymised customer ID [Clean:31-37]: 30 for most, 7 for 0008, 0 for 0017, 0019 and 0021. Its source is described as mapped to the anonymised IDs "in the source list's existing order", so it is an assumption, not a recorded contract term. The Team Context README itself lists payment terms and credit risk as still requiring work.
- The Team Context workbook is not used by any script, and a search found no Proxy/Approve/Deny text in it. It is a translated orientation copy of the raw ledger.
- The label, the status column, Customer_ID, source row and payment amount are excluded from the features [NB cell 23].
- The raw file `NTK Co 12mon (1).xlsx` is one sheet ("Báo cáo"), 537 rows and 14 columns, with Vietnamese headings.

### 6.3 Leakage
- Timing is handled carefully. Each feature snapshot is taken before the history is updated [T:197-231, T:223], and same-day order follows source row. Features use only earlier rows of the same customer, so there is no future-payment leakage.
- Definitional leakage: labels exist only when `overdue_before > 0`, and `overdue_before_m` and `max_days_past_due_before` are computed from that same quantity [Clean:253-271, T:153-155]. Every labelled row therefore has both greater than zero by construction. The model cannot learn "late or not"; it can only learn which customers resemble 0004, 0014 and 0021.
- Identity leakage: `credit_term_days` is a per-customer constant, and the history features (prior billed, relationship days, and so on) act as customer fingerprints. The test set shares 8 customers with training [NB cell 27]. A customer-disjoint split was deliberately not used because it would leave one denial customer per side [NB cell 26].
- The payment's own amount and description are excluded from the features [NB cell 23].
- Replay assumptions: FIFO allocation of payments to invoices, although the Team Context sheet notes allocation is unconfirmed (56 payments without an explicit invoice reference; 3 naming several invoices). Opening balances have unknown age and are never overdue [T:147]. Reconciliation passes: balance difference at most 0.01 VND, 511 exact matches [T:180-182, NB cell 16].

### 6.4 Evaluation
- Sizes [NB cells 22, 27]: 85 labelled rows; training 50 (44 Approve, 6 Deny); holdout 35 (33 Approve, 2 Deny, prevalence 0.057). Deny customers in training: 0004, 0014, 0021; in holdout: 0014.
- One chronological split only; the holdout starts on 2026-07-01, the first day of the last calendar quarter in the data, and the script asserts that training ends before the holdout begins [T:252-259]. No cross-validation, no repeated splits, no confidence intervals, and fixed hyper-parameters with no tuning [T:312-365].
- No calibration step: no calibration curve, no Platt or isotonic scaling, no Brier score or log loss.
- Reported holdout metrics [NB cell 45]:

| Model | Acc | Bal acc | Deny recall | Deny prec | Deny AP |
|---|---|---|---|---|---|
| Majority baseline | 0.943 | 0.500 | 0 | 0 | 0.057 |
| Logistic regression | 0.943 | 0.970 | 1.0 | 0.5 | 0.833 |
| SVM linear | 0.886 | 0.939 | 1.0 | 0.333 | 1.000 |
| SVM RBF | 0.857 | 0.924 | 1.0 | 0.286 | 0.750 |
| XGBoost | 0.886 | 0.470 | 0 | 0 | 0.226 |
| Decision Tree | 0.886 | 0.470 | 0 | 0 | 0.057 |
| Random Forest | 0.914 | 0.485 | 0 | 0 | 0.226 |
| KNN | 0.943 | 0.500 | 0 | 0 | 1.000 |

- How to read the table: with two positives, recall can only be 0, 0.5 or 1. Logistic regression found both denials at the cost of two false denials. KNN has a perfect ranking score (AP 1.0) and zero recall, which shows how unstable the figures are. Four of the seven models are no better than always approving. The notebook itself says not to choose a production model from two holdout denial rows [NB cell 51].

### 6.5 What the score means
- The score is the model's `predict_proba` or decision function, used as a "ranking score" [T:285].
- Logistic regression, trees and forest use balanced class weights, and XGBoost uses `scale_pos_weight` [T:333]. This moves scores away from the 6-in-50 training base rate, and nothing is calibrated. SVM scores are raw margins and "not probabilities" [NB cell 49].
- So the score is only an in-sample ordering of "looks like the late payments of the three Deny customers". It is not a probability of denial, default or lateness. Showing an owner "82 percent risk" would be false precision.

### 6.6 Reproducibility
- Seeds are fixed (`RANDOM_STATE = 42`) and a run manifest with file hashes and package versions is written [T:42, T:446-459], so a re-run on the same cleaned workbook should reproduce.
- It cannot be reproduced from the supplied files:
  - the shipped cleaner is stale: it has only 0014 as an exception, with no 0004 and no 0021 handling, so it gives the 0021 receipts an Approve label, and the training script then stops [T:75-85]. The notebook's cleaner has the extra exceptions;
  - the cleaned workbook the training script expects (`NTK Co 12mon - Python cleaned.xlsx`, T:55) is not in the folder, although NB cell 16 says it matches the notebook;
  - `requirements.txt` was not supplied;
  - the notebook outputs came from Hoang's machine and were not re-run.
- No fitted model is saved: no joblib, pickle or model-save call exists. Models live in memory during a run. Only CSV and PNG outputs and the run manifest persist, so any use would need retraining on 50 rows.

### 6.7 Dependencies
- The training script imports numpy, pandas, matplotlib, seaborn, IPython (`display`), openpyxl, scikit-learn and xgboost [T:21-40]. IPython is unnecessary for a script. The cleaner needs only openpyxl.
- Versions used [NB cell 50]: numpy 2.2.4, pandas 2.2.3, openpyxl 3.1.5, scikit-learn 1.9.1, xgboost 3.2.0, matplotlib 3.10.1, seaborn 0.13.2. On macOS xgboost needs the OpenMP runtime [NB cell 2].
- Runtime was not measured; with 85 rows it should be seconds, and install size would dominate.
- The classifiers cannot run without numpy, scikit-learn and xgboost. The ledger replay [T:124-231] uses plain Python plus pandas timestamps and could be written with the standard library only.

### 6.8 What can ship now

A deterministic ledger replay, not a model. It is testable against the 511-row reconciliation and reports observed payment behaviour.

- Inputs, all derivable from the team's own records: dated invoices (date, amount, customer term days entered by the owner, not hard-coded); dated payments; an opening balance if any, of unknown age; the as-of date; amounts in VND (the unit is unconfirmed in the source). Requested amount and days are carried to the case page, not into a score.
- Outputs: debt and overdue amount now; maximum days past due; count, share and total of earlier receipts made while overdue; relationship length; days since the last receipt; and a reconciliation check against the ledger balance.
- A statement the pipeline can support: "From the records entered so far, this customer has N invoices, VND X is overdue, the oldest is D days past due, and M percent of earlier receipts came while something was overdue." This is observed behaviour from the owner's own ledger. It does not say whether to approve, and must not appear as a percentage chance.

Limitations that must be stated with it:
1. Labels are not recorded decisions. Approve means "was late and not refused"; Deny is the owner's statement about three customers.
2. 85 labelled payments, 8 Deny from 3 customers, 2 Deny rows in the holdout from one customer. No performance claim is meaningful.
3. Customer terms are an assumption in code, the currency is unconfirmed, and FIFO payment allocation is an assumption.
4. Scores are uncalibrated and class-weighted; they are not probabilities.
5. No request-time information (requested amount, days, date) is in the model.
6. The shipped cleaner is behind the notebook and the training script; the cleaned workbook and any model artefact are missing.
7. The data is one small company over 12 months and is not evidence about other businesses.

## 7. Open questions and inputs needed

From the owner(s):
- Real Yes/No decisions; owners rarely report them [29:03].
- Answers to the questionnaire (made-up scenarios).
- Meaning of codes the cleaner cannot read (for example "TTHD") [2:34:31].
- A data dictionary for customer IDs [2:20:08].
- Confirmed payment terms per customer, and the currency of the ledger.

From Hoang:
- The current cleaning script, the cleaned workbook and `requirements.txt`.
- Whether 0004 and 0021 are intended to be Deny in the shipped pipeline, and the source of the per-customer terms.
- The model code in a form the Lab agent can call as a framework [2:50:04].
- Wiring the system log into the maths [1:14:46]; cleaned-data output in the Lab [1:22:41]; standby for fixes until Wednesday.

From Tony:
- Confirmation of current tasks [3:05:59]; review of the questionnaire; slide design and the look of slides 3-4; research items at 3:42 (garbled, [?]).

From Hanting:
- AI import working and tested; AI fetching of results; the demo video; combining Nucleus and Lab; the import bug list; a deployed latest version for testing [3:34:17, 3:43:57].

From Chris:
- BPMN with the disagreement path by Thursday morning; success criteria; slides 1-2.

Unresolved design points:
- What the confidence number includes: maths only, or maths plus LLM [2:12:22].
- How many entries are needed; no estimation method is set.
- The order of cleaning and flagging [2:56:14].
- The exact threshold value and who may change it (the owner only [?]).
- Whether agree/disagree remains when the owner chooses Option A.
- Whether every member must present (ask the tutor); length of the backup video.
- The due-date wording ("Week six Sunday" against "week 7 Monday final") [?].
- The question tutors may ask [1:28:41]: a two-year-old company with one year of records and 500 entries; how long until the system is useful.
- Given the "retrieving, not predicting" observation: what the Lab should say for a case with no history, and how the replay output is shown in place of a score.

## 8. Terms the team uses

- Nucleus / Nucleon: the backend system (database, calculations, tools). The spelling varies in the transcripts. Nucleus Lab: the chat-style AI front end.
- Founder's second brain: the pitch label.
- Owner, staff, AI agent, customer: staff ask the AI; the customer asks staff for a delay. "Staff mind" is rule-based policy; "owner's mind" is changing preference.
- Request: a customer asks to waive a credit limit or term, or to pay late this time. In the proof of concept: a time-limit or payment-extension request.
- Approve / deny / escalate / agree / disagree, with a confidence level.
- Numerical (math) model: the fixed Yes/No plus confidence computation. LLM / reasoning model: explains and flags; it does not change numbers.
- Irregular patterns: red flags raised by the LLM.
- Onboarding: one-time setup (questionnaire, ledger import). Operation: ongoing use. System log: ongoing records of decisions.
- Control panel: where people set models, thresholds, allowed reasoning sources and debate rounds.
- Proxy label: a Yes/No label inferred from history, not a recorded decision.
- Feature engineering: new columns derived from ledger text or history.
- FIFO: first in, first out; payments are matched to the oldest open invoice.
- Overdue, days past due: amount and age of invoices beyond their due date at a given moment.
- Holdout: the later part of the data kept aside for testing. AP: average precision. Calibration: whether a score matches the real frequency of the outcome.
- POC: proof of concept. Week 7 / Week 10: the course milestones. "At scale": future features.
- BPMN: business process diagram. Success criteria: the measures the team will state for the project.
- Agentic feature, build environment: course slide headings.
