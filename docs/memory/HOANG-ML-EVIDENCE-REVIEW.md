# Hoang's NTK data/ML exploration — evidence audit
Reviewed from user-shared materials on 2026-10-26. **Not a product requirements source.** Especially `NTK Project Summary.docx` is explicitly identified by the user as **outdated and potentially inaccurate**. Never let it overwrite later design decisions.

## Files inspected (provided in conversation, not committed or copied here)
- `clean_ntk_data (1).py` and `clean_ntk_data (2).py`: byte-for-byte identical cleaning scripts (matching SHA-256).
- `train_credit_models.py`: 7 classifier families plus majority baseline, using payment-row proxy targets.
- `NTK_Cleaning_EDA_Training.ipynb`: fuller notebook with limitations and later labeling rules.
- Original NTK receivables workbook `NTK Co 12mon (1)(1).xlsx`, source report `Báo cáo`, and team-orientation workbook with ledger, English views and questions.
- `NTK Project Summary.docx`: old claims **not** adopted as authoritative facts.

## Supported methodology findings
1. Cleaning scripts classify receivable ledger events (invoice/VAT/payment/netting/adjustment), translate descriptions, track balances and FIFO-style assumed aging. Invoice mentions in narrative are **not confirmed payment allocations**.
2. Cleaning scripts generate **Approval Proxy Label** from payment rows with open overdue customer balances; most are labelled 'Approve (proxy)' when late payments were observed, with special 'Deny (proxy)' exceptions inferred from Owner-related statements. **No recorded request or approval can be inferred from payment alone.**
3. The standalone two cleaners are identical, but they explicitly **combine BNSO/BNNO as ID 0014**, while the notebook dictionary treats **BNSO as ID 0004 and BNNO as ID 0014 separately**. The notebook also includes additional owner-informed denial exceptions (IDs 0004, 0014 and two ID 0021 receipts), while the training script requires the ID 0021 rows to be Deny proxies. This is a **material entity-mapping and label-definition version mismatch**, not just a formatting difference. **Align entity IDs, executable cleaner, cleaned workbook, notebook and trainer before claiming reproducible output.**
4. Training uses retrospective features before an observed **receipt**, not features available at a missing **request date**. Customer-dedicated prediction for a truly new customer is NOT validated by its chronological holdout; repeated customers appear in train and test, and holdout denials are extremely few.
5. Models include Logistic Regression, SVM linear/RBF, XGBoost, Decision Tree, Random Forest and KNN, versus a majority baseline. Their scores describe prediction of **constructed proxy labels**, not real Owner approval accuracy or financial risk calibrated probabilities.
6. Existing financial-feature extraction, translation, reconciliation checks, observable aging and modeling methodology may have research value. Code should be evaluated against current architecture before integration, not dismissed wholesale or adopted as autonomous approval authority.

## Specific cautions
- 'Approve (proxy)' can mean a late receipt occurred, not that any extension was requested or approved.
- 'Deny (proxy)' can be based on a business exception or reported disallowance, not a recorded row-level Owner decision.
- The notebook itself states holdout has only two denial proxies, extremely weak validation and customer/policy confounding.
- No exact owner's decision accuracy can be calculated from this ledger alone.
- Do not use the outdated summary document, its counts or old predictions to override the user's current product vision.
- The NTK ledger is denominated/reported in its own accounting context (including VND); UI examples in AUD are hypothetical and must not be mixed as if measured NTK credit limits.
- No original NTK raw datasets or actual customer names should be added to shared memory docs.

## Appropriate use in Nucleon
**Useful**: deterministic derived features, debt aging indicators, completeness/provenance handling, synthetic test-case generation clearly labeled, method comparison as exploratory research.
**Not proven**: accurate prediction of real Owner credit decisions, generalisation to new customers, permission to auto-approve, verified training labels.
If a teammate proposes ML integration, request a concrete feature/API contract, training labels and evaluation protocol; compare against simpler deterministic business features and LLM+decision-memory agent. Evidence-driven decision, not a personal dispute about tools.
