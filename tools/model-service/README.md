# Model service (the team's classifier behind Nucleon's research hook)

Nucleon itself is standard-library Python and cannot import scikit-learn. This small service runs the team's own model in the team's own environment and answers two calls: `/train` (the training table in, a model out) and `/score` (one case's features in, the chance the Owner declines out). Nucleon stores what `/train` returns as an immutable model version and asks `/score` for every new case; a timeout or an error is "no score" and never changes a decision.

Run it:

```
python3 -m venv venv && venv/bin/pip install scikit-learn        # xgboost too for --family xgboost
venv/bin/python service.py --port 8640                           # --family xgboost for the notebook's XGBoost
```

Point Nucleon at it in the Records config and restart Records:

```json
"researchProvider": {"kind": "http", "url": "http://127.0.0.1:8640", "timeoutSeconds": 5}
```

Then, on the Owner's Model page, "Fit a new version now" sends the training table here. The pipeline is the notebook's (StandardScaler + LogisticRegression, class-balanced; or its XGBoost). Replace `fit()` with any model that has `predict_proba`, keep the two endpoints, and Nucleon needs no change.

What this service sees: the rows Nucleon exports (case id, kind, dataset, request date, the Owner's decision, the numeric features) and the features of each new case. No ledger, no names.
