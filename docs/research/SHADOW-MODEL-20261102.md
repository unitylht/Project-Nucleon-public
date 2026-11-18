# The research hook: Hoang's classifier as a shadow (2 November 2026)

Status: implemented on `main` (prototype `research.py`, hooks in `server.py`, the Owner's Review and Model pages), with tests (`prototype/test_research.py`). Fictional data only. Second step the same day: the loop (refit, versions, settings, promotion, providers), below.

## What it is

Nucleon decides a credit request by the Owner's rulebook (`delegation.evaluate`). That does not change. Every case now also keeps, under `research`:

- `features`: the numeric row a classifier reads, as of the request date: the ladder's features (exposure, customer exposure, days, deposit share, prior late share, size ratio, the yes/no flags) and the twelve replay features of the team's pipeline, under the notebook's own names (`credit_term_days`, `debt_before_m`, `overdue_before_m`, `max_days_past_due_before`, `prior_invoice_documents`, `prior_billed_m`, `prior_received_m`, `prior_receipt_count`, `has_prior_receipt`, `days_since_prior_receipt`, `observed_relationship_days`, `prior_late_receipt_fraction`), computed by `behaviour.replay` strictly before the request date. Never recomputed later: a feature read from today's ledger for an old request would leak the outcome.
- `shadow`: when a model file is configured, that model's probability that the Owner declines, with the model's name and version. Shown to the Owner on the Review page as "Research score, not used in this decision". Staff and the assistant never see it. The rules never read it.
- `asOf`: the business date the request was evaluated on (the training table's `request_date`).

## The training table

`GET /api/delegation/training.csv` (Owner only) is one row per decided case the Owner answered: approve or decline, explicit or tacit. Columns: `case_id, kind, dataset, customer_id, request_date, policy_version, handling, owner_decision, outcome`, the ladder features, the twelve replay features, `Target_Deny` (1 = declined). The fictional decision memory is in it, labelled by `dataset` (`fictional_example`, `fictional_evaluation`): filter on `dataset == 'live'` for real decisions. A case decided before this hook existed has the ladder features and blank replay columns.

This is the table the notebook's section 20 asks for: recorded requests with the request date and the Owner's actual decision, instead of lateness proxies. An agent approval becomes a row only once the Owner has agreed or disagreed with it.

## The model file

JSON, a standardised logistic regression:

```json
{"name": "hoang-lr", "version": "1", "features": ["exposure", "extensionDays", "prior_late_receipt_fraction"],
 "mean": [...], "scale": [...], "coef": [...], "intercept": -1.2, "positive": "decline", "trainedOn": {"rows": 120, "positives": 18}}
```

Configured with `"shadowModel": "/path/to/model.json"` in the Records config; the server refuses a malformed file at start. A case missing any of the model's features gets no score (an unknown is never treated as zero).

Two ways to produce one:

- From the notebook: fit `StandardScaler` + `LogisticRegression(class_weight='balanced')` on the exported table, then `research.sklearn_json(scaler, logistic, features, name, version)` writes the JSON (the function imports nothing of scikit-learn; run it where the model is).
- Without packages: `research.fit(rows, features)` is the same model shape fitted by gradient descent, for a smoke test or a machine without scikit-learn.

`GET /api/delegation/research` (Owner only) reports the model in force and its agreement with the Owner over the decided cases that carry a score: how often "decline when probability >= 0.5" matched the Owner's call. A figure to read, not a gate.

## The loop (second step, 2 November 2026)

- **Model versions.** A refit saves a new immutable version in `research_models` (like policy versions). Every scored case records the version that scored it. The Owner's Model page (`#/research`) lists the versions, the model in force, its coefficients, what it was fitted on and who fitted it.
- **Refit.** `POST /api/delegation/research/refit {features?, name?, note?}` (Owner, person, csrf): the provider fits on the training table and the version is saved. Features default to every feature present in every training row with more than one value. Rows of only one class, or none with the features asked, is `409 NOT_ENOUGH_DATA`.
- **Automatic refit.** The setting `autoRefitEvery: N` refits after every N Owner verdicts since the model in force was fitted (counted on live cases). Errors are logged and skipped; a verdict never fails because of a model.
- **Agreement.** Over scored live cases with an Owner verdict: how often "decline when the chance is at or above the threshold" matched the Owner. Fictional cases are in the training table and never in the agreement.
- **Promotion.** Settings `promotion: {enabled, minCases, minAgreement, threshold}`, off by default. When enabled, a model is in force, at least `minCases` scored live cases carry a verdict and the agreement is at least `minAgreement`, the score becomes a recommendation the ladder reads at step 9: a chance at or above `threshold` sends the case to the Owner with the reason "The team's model (name vN) put the chance that you decline at P%, at or above your bar". The agent never declines; the model only ever escalates. Turning promotion off takes effect at the next request. `delegation.evaluate` takes the model as a `scorer` function and stays pure.
- **Providers.** `researchProvider` in the Records config: `{"kind": "builtin"}` (default: the JSON logistic regression fitted and scored in-process) or `{"kind": "http", "url": "...", "timeoutSeconds": 5}` (an external model service: `POST /train` returns the model Nucleon stores, `POST /score` scores a case). `tools/model-service/` is a template that runs the notebook's own scikit-learn pipeline (or its XGBoost) behind those two endpoints; the team swaps the model, Nucleon does not change. A failing or absent service is "no score".
- **Endpoints.** `GET /api/delegation/research` (everything the page shows, with `agreementByVersion`), `POST .../research/settings`, `POST .../research/refit`, `GET .../training.csv`, `GET .../research/model.json` (the model in force). The Control panel carries the settings and the status too; the Owner's assistant answers model questions through the read-only `modelStatus` tool.

## The exception band (3 November 2026)

Hoang's point, accepted: the cases that overwhelm the Owner are the ones that breach the policy, and a model that can only escalate does not reduce them. So the Owner can now delegate an **exception band** (`policy.exceptions`, Control panel, off by default): a breach of a money limit by at most `maxOverExposureShare` of the limit, or of the longest extension by at most `maxExtraDays`, is approved by the agent when (1) every failing check is one of `decision_exposure`, `customer_exposure`, `trial_exposure`, `new_customer_exposure`, `extension_days`; (2) the model in force scores the case and puts the chance of the Owner's approval at or above `minModelApprove`; (3) the Owner approved at least `minSimilarApproved` of the 5 closest comparable cases. The checks inside the band are marked `exception` on the card, the reason names the model's figure and the comparable count, the case carries `exception.applied`, and the Review page labels it. Everything else about the ladder is unchanged: steps 1, 3 to 9 still escalate, the agent never declines, and the Owner can override.

A **prepared decline** (`suggestDeclineAbove`): when a case goes to the Owner and the model's chance of a decline is at or above the setting, the card carries a suggested decline with its reason, and the Review page gives the Owner one click. The decision is still the Owner's.

## What it is not, yet

- The promoted model only escalates; it never approves anything the rules would not, and never declines (PM-017). Letting a confident "approve" skip the Owner where the rules would escalate is a further product decision, not built.
- The notebook's proxy-labelled NTK data is not loaded here (PM-014); the shared instance fits on the fictional decision memory until real decisions exist, and that is labelled as such on every version.
- Agreement is one number (match at the threshold). Precision and recall per class, and calibration, belong on the page once there are enough real cases to make them mean something.

## Decision checklist (D13)

1. **Owner's net work**: none added. The Owner sees one extra line on a case they already read; nothing to set up or maintain.
2. **Growing autonomy**: advances it. The table and the shadow score are the measurement that lets a model earn a place at step 9; until then nothing changes. This is not a human gate.
3. **Deterministic and verifiable**: yes. The score is a stored function of stored numbers; tests pin that the handling is identical with and without a model and that the evaluation carries nothing of it.
4. **Reversible and configurable**: yes. One config key; remove it and only the feature rows remain.

Autonomy-maximising alternative, shown and not recommended: let the model's confidence replace step 9 now, both ways (a confident "approve" also skips the Owner where the rules would escalate). Not recommended because no real decisions exist to validate it on (the notebook's own section 20) and because the rules' escalations each name a bound the Owner set; the built loop keeps the model as a one-way check the Owner can switch on once it has earned it, which is the same path the agent itself takes through the track-record gate.
