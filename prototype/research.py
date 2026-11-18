"""The research hook for the team's credit model (Hoang's classifier): the training table Nucleon's cases produce, and a SHADOW score.

What this is. delegation.evaluate decides by the Owner's rulebook and nothing here changes that. A case additionally keeps, under `research`,
the numeric features a classifier would read (the ladder's own features, and the replay's twelve pipeline features computed as of the request
date) and, when a model file is configured, that model's probability that the Owner would decline: a research figure shown to the Owner as
such, stored next to the Owner's real decision so the model can be measured against it, and never read by the rules. The Owner's decisions
build the training table (the labels the team's notebook says it needs: recorded requests with the request date, not lateness proxies).

The model file is JSON, a standardised logistic regression: {"name", "version", "features": [...], "mean": [...], "scale": [...], "coef": [...],
"intercept", "positive": "decline", "trainedOn": {...}}. `fit` produces one here with the standard library (class-balanced, L2-regularised);
`sklearn_json` converts a fitted scikit-learn StandardScaler + LogisticRegression pair, so the notebook's own model can be dropped in.
A feature the case cannot supply makes the score unavailable: an unknown is never treated as zero, here as everywhere in Nucleon.

The loop (2 Nov 2026): the Owner's verdicts fill the table; a refit (by hand on the Research page, or automatically every N verdicts, an Owner setting)
saves a new immutable model version; every scored case records which version scored it; the model's agreement with the Owner accumulates; and once
the Owner's promotion bar is met (enabled, at least N scored real cases, agreement at least X), the score becomes a recommendation the ladder reads at
step 9: a probability of declining at or above the threshold sends the case to the Owner. Off by default, reversible, and the Owner can see every number.

Providers: `builtin` fits and scores the JSON logistic regression here; `http` sends the training table to, and asks scores of, an external service
(the team's own models, scikit-learn or XGBoost, in their own environment; tools/model-service has a template). A provider that fails or times out
yields no score, never an error in a decision."""
import csv
import io
import json
import math
from fractions import Fraction
from pathlib import Path

from behaviour import FEATURES as REPLAY_FEATURES

# The ladder's features (delegation.features_of) as numbers: money in minor units, shares and ratios as floats, yes/no as 1/0, unknown as None.
LADDER_FEATURES = ('exposure', 'customerExposure', 'extensionDays', 'termsDays', 'orderAmount', 'depositShare', 'priorLateShare', 'sizeRatio',
                   'nothingElseOverdue', 'lateUnknown', 'isNew', 'heldCustomer', 'evidenceComplete', 'trialInForce', 'coverageConfirmed')
META = ('case_id', 'kind', 'dataset', 'customer_id', 'request_date', 'policy_version', 'handling', 'owner_decision', 'outcome')
LABEL = 'Target_Deny'   # the notebook's target name: 1 = the Owner declined, 0 = approved
COLUMNS = META + LADDER_FEATURES + REPLAY_FEATURES + (LABEL,)
POSITIVE = 'decline'


def number(value):
    """One feature value as a float, or None when it is unknown (None, or a text that is not a number)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError):
        return None


def numeric(features, names):
    """{name: float or None} for the names, from a features dict as a case stores it (Fractions as text) or as the replay returns it."""
    features = features or {}
    return {k: number(features.get(k)) for k in names}


def case_features(ladder, replay):
    """The feature row a case keeps under research.features: the ladder's features and the replay's, both numeric."""
    return {**numeric(ladder, LADDER_FEATURES), **numeric(replay, REPLAY_FEATURES)}


# ---------------------------------------------------------------- the training table

def training_rows(cases):
    """One row per decided case the Owner answered (approve or decline), in the notebook's shape: the metadata, the numeric features the case kept at request
    time (never recomputed from today's ledger: that would be leakage), and Target_Deny. cases: dicts with id, kind, dataset, customerId, createdAt,
    policyVersion, handling, ownerDecision, outcome, features (the ladder's) and research.features (the full numeric row, when the case has one)."""
    rows = []
    for c in cases:
        if c.get('ownerDecision') not in ('approve', 'decline'):
            continue
        f = (c.get('research') or {}).get('features') or numeric(c.get('features'), LADDER_FEATURES)
        row = {'case_id': c['id'], 'kind': c['kind'], 'dataset': c['dataset'], 'customer_id': c.get('customerId'), 'request_date': ((c.get('research') or {}).get('asOf') or c.get('decidedOn') or c.get('createdAt') or '')[:10],
               'policy_version': c.get('policyVersion'), 'handling': c.get('handling'), 'owner_decision': c['ownerDecision'], 'outcome': c.get('outcome')}
        row.update({k: f.get(k) for k in LADDER_FEATURES + REPLAY_FEATURES})
        row[LABEL] = 1 if c['ownerDecision'] == POSITIVE else 0
        rows.append(row)
    return rows


def csv_text(rows, columns=COLUMNS):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(columns), extrasaction='ignore', lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: ('' if r.get(k) is None else r.get(k)) for k in columns})
    return out.getvalue()


# ---------------------------------------------------------------- the shadow model

def load_model(source):
    """A model from a JSON file path or a dict; None for None. Checked: the vectors agree in length and the numbers are finite."""
    if source is None:
        return None
    m = dict(json.loads(Path(source).read_text(encoding='utf-8')) if isinstance(source, (str, Path)) else source)
    names = list(m.get('features') or [])
    for key in ('mean', 'scale', 'coef'):
        values = list(m.get(key) or [])
        if len(values) != len(names) or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            raise ValueError('shadow model: ' + key + ' must list one finite number per feature')
        m[key] = [float(v) for v in values]
    if not names or any(s == 0 for s in m['scale']):
        raise ValueError('shadow model: features and non-zero scales are required')
    m['intercept'] = float(m.get('intercept') or 0.0)
    m['features'] = names
    m['name'] = str(m.get('name') or 'shadow')
    m['version'] = str(m.get('version') or '0')
    m['positive'] = str(m.get('positive') or POSITIVE)
    return m


def score(model, features):
    """{model, version, positive, probability, available, missing}: the model's probability of its positive class (the Owner declining) for one
    numeric feature row, or unavailable with the features the row lacks. Never raises on data; the rules never read it."""
    missing = [k for k in model['features'] if features.get(k) is None]
    out = {'model': model['name'], 'version': model['version'], 'positive': model['positive'], 'available': not missing, 'missing': missing, 'probability': None}
    if missing:
        return out
    z = model['intercept'] + sum(c * (features[k] - mu) / s for k, mu, s, c in zip(model['features'], model['mean'], model['scale'], model['coef']))
    z = max(-500.0, min(500.0, z))
    out['probability'] = round(1.0 / (1.0 + math.exp(-z)), 4)
    return out


def fit(rows, features, name='nucleon-lr', version='1', l2=1.0, steps=3000, rate=0.05):
    """A standardised, class-balanced, L2-regularised logistic regression on the training rows that have every feature and a label (the notebook's
    LogisticRegression(class_weight='balanced') shape, fitted by plain gradient descent so it needs no package). Both classes must be present.
    Returns the model dict load_model accepts, with trainedOn: how many rows, how many positives, which features."""
    names = list(features)
    data = [([float(r[k]) for k in names], int(r[LABEL])) for r in rows if all(r.get(k) is not None for k in names) and r.get(LABEL) in (0, 1)]
    n = len(data)
    pos = sum(y for _, y in data)
    if n < 2 or pos == 0 or pos == n:
        raise ValueError('fit needs rows of both classes with every feature present (have ' + str(n) + ' rows, ' + str(pos) + ' positive)')
    mean = [sum(x[j] for x, _ in data) / n for j in range(len(names))]
    scale = [math.sqrt(sum((x[j] - mean[j]) ** 2 for x, _ in data) / n) or 1.0 for j in range(len(names))]
    xs = [[(x[j] - mean[j]) / scale[j] for j in range(len(names))] for x, _ in data]
    ys = [y for _, y in data]
    w_pos, w_neg = n / (2.0 * pos), n / (2.0 * (n - pos))   # 'balanced': each class weighs half
    coef, b = [0.0] * len(names), 0.0
    for _ in range(steps):
        g, gb = [0.0] * len(names), 0.0
        for x, y in zip(xs, ys):
            z = b + sum(c * v for c, v in zip(coef, x))
            p = 1.0 / (1.0 + math.exp(-max(-500.0, min(500.0, z))))
            e = (p - y) * (w_pos if y else w_neg)
            gb += e
            for j, v in enumerate(x):
                g[j] += e * v
        coef = [c - rate * (gj / n + l2 * c / n) for c, gj in zip(coef, g)]
        b -= rate * gb / n
    return {'name': name, 'version': version, 'features': names, 'mean': mean, 'scale': scale, 'coef': coef, 'intercept': b, 'positive': POSITIVE,
            'trainedOn': {'rows': n, 'positives': pos, 'features': names, 'method': 'stdlib logistic regression, class-balanced, l2=' + str(l2)}}


def sklearn_json(scaler, logistic, features, name, version, trained_on=None):
    """The same JSON from a fitted scikit-learn StandardScaler and LogisticRegression (the notebook's pipeline): run in the notebook's environment,
    this module imports nothing of scikit-learn. Positive class 1 must be the Owner declining (the notebook's Target_Deny)."""
    return {'name': name, 'version': str(version), 'features': list(features), 'mean': [float(v) for v in scaler.mean_], 'scale': [float(v) for v in scaler.scale_],
            'coef': [float(v) for v in logistic.coef_[0]], 'intercept': float(logistic.intercept_[0]), 'positive': POSITIVE, 'trainedOn': trained_on or {}}


def agreement(cases, threshold=0.5):
    """How the stored shadow scores compare with the Owner's decisions, over the decided cases that have both: n, and how often the model's call
    (decline when probability >= threshold) matched. A research figure for the page and the doc, not a gate."""
    pairs = [(((c.get('research') or {}).get('shadow') or {}).get('probability'), c.get('ownerDecision')) for c in cases]
    pairs = [(p, d) for p, d in pairs if p is not None and d in ('approve', 'decline')]
    if not pairs:
        return {'n': 0, 'agreed': 0, 'threshold': threshold}
    agreed = sum(1 for p, d in pairs if (p >= threshold) == (d == POSITIVE))
    return {'n': len(pairs), 'agreed': agreed, 'threshold': threshold}


# ---------------------------------------------------------------- the Owner's settings, the promotion bar

DEFAULT_SETTINGS = {'autoRefitEvery': None, 'promotion': {'enabled': False, 'minCases': 20, 'minAgreement': 0.8, 'threshold': 0.5}}


def validate_settings(body):
    """The research settings as the Owner saves them, strict: autoRefitEvery (null or 1..1000 verdicts), promotion.enabled, minCases (1..10000), minAgreement
    (0..1), threshold (0..1). An unknown key is an error."""
    require = lambda ok, msg: (_ for _ in ()).throw(ValueError(msg)) if not ok else None
    require(isinstance(body, dict), 'settings are an object')
    require(set(body) <= {'autoRefitEvery', 'promotion'}, 'unknown setting: ' + ', '.join(sorted(set(body) - {'autoRefitEvery', 'promotion'})))
    out = json.loads(json.dumps(DEFAULT_SETTINGS))
    if 'autoRefitEvery' in body:
        v = body['autoRefitEvery']
        require(v is None or (type(v) is int and 1 <= v <= 1000), 'autoRefitEvery is null or a whole number of verdicts from 1 to 1000')
        out['autoRefitEvery'] = v
    p = body.get('promotion', {})
    require(isinstance(p, dict) and set(p) <= set(DEFAULT_SETTINGS['promotion']), 'promotion has enabled, minCases, minAgreement and threshold')
    if 'enabled' in p:
        require(isinstance(p['enabled'], bool), 'promotion.enabled is true or false')
        out['promotion']['enabled'] = p['enabled']
    if 'minCases' in p:
        require(type(p['minCases']) is int and 1 <= p['minCases'] <= 10000, 'promotion.minCases is a whole number from 1 to 10000')
        out['promotion']['minCases'] = p['minCases']
    for k in ('minAgreement', 'threshold'):
        if k in p:
            v = p[k]
            require(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1, 'promotion.' + k + ' is a share from 0 to 1')
            out['promotion'][k] = float(v)
    return out


def choose_features(rows, candidates=LADDER_FEATURES + REPLAY_FEATURES):
    """The features a refit uses when the Owner names none: every candidate present in every training row with more than one distinct value."""
    out = []
    for k in candidates:
        values = [r.get(k) for r in rows]
        if values and all(v is not None for v in values) and len(set(values)) > 1:
            out.append(k)
    return out


def promotion_status(settings, agreement, model):
    """Whether the model's score may act as a recommendation now: the Owner has enabled it, a model is in force, and its agreement with the Owner over scored
    real cases meets the bar. {active, reason, bar}."""
    p = settings['promotion']
    bar = {'minCases': p['minCases'], 'minAgreement': p['minAgreement'], 'threshold': p['threshold']}
    if not p['enabled']:
        return {'active': False, 'reason': 'Promotion is off: the score is research only.', 'bar': bar}
    if not model:
        return {'active': False, 'reason': 'No model is in force.', 'bar': bar}
    n, agreed = agreement['n'], agreement['agreed']
    if n < p['minCases']:
        return {'active': False, 'reason': 'Promotion is on, but only ' + str(n) + ' of the ' + str(p['minCases']) + ' scored cases with your verdict that it needs exist yet.', 'bar': bar}
    rate = agreed / n
    if rate < p['minAgreement']:
        return {'active': False, 'reason': 'Promotion is on, but the model agreed with you on ' + str(agreed) + ' of ' + str(n) + ' cases (' + str(round(rate * 100)) + '%), under the ' +
                str(round(p['minAgreement'] * 100)) + '% you require.', 'bar': bar}
    return {'active': True, 'reason': 'Promotion is on and the bar is met: the model agreed with you on ' + str(agreed) + ' of ' + str(n) + ' cases (' + str(round(rate * 100)) + '%).', 'bar': bar}


def as_recommendation(shadow, promotion, model):
    """What delegation.evaluate reads of the model for one case: the shadow score, whether promotion was active, and, when it was and the score is available,
    the recommendation 'escalate' (probability at or above the threshold) or 'approve', with the sentence the reasons list shows."""
    out = {'shadow': shadow, 'promoted': bool(promotion['active']), 'recommendation': None, 'text': None, 'version': model and model.get('version')}
    if not promotion['active'] or not shadow or not shadow.get('available'):
        return out
    threshold = promotion['bar']['threshold']
    pct = str(round(shadow['probability'] * 100)) + '%'
    if shadow['probability'] >= threshold:
        out['recommendation'] = 'escalate'
        out['text'] = ("The team's model (" + shadow['model'] + ' v' + shadow['version'] + ') put the chance that you decline at ' + pct + ', at or above your ' +
                       str(round(threshold * 100)) + '% bar, so the Owner decides.')
    else:
        out['recommendation'] = 'approve'
        out['text'] = "The team's model (" + shadow['model'] + ' v' + shadow['version'] + ') put the chance that you decline at ' + pct + ', under your bar.'
    return out


# ---------------------------------------------------------------- providers

class BuiltinProvider:
    """Fits and scores the JSON logistic regression in this process."""
    kind = 'builtin'

    def train(self, rows, features, name, version):
        return fit(rows, features, name=name, version=str(version))

    def score(self, model, features):
        return score(model, features)

    def describe(self):
        return {'kind': self.kind}


class HttpProvider:
    """An external model service: POST {url}/train {rows, features, name, version} -> a model JSON (its own shape, kept as the version; `scoring: "http"` means
    the service scores it), POST {url}/score {model, features} -> {probability, available, missing}. A failure or a timeout is no score."""
    kind = 'http'

    def __init__(self, url, timeout=5.0, opener=None):
        import urllib.request
        self.url, self.timeout = url.rstrip('/'), float(timeout)
        self.opener = opener or (lambda req, timeout: urllib.request.urlopen(req, timeout=timeout))

    def _post(self, path, body):
        import urllib.request
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with self.opener(req, self.timeout) as r:
            return json.loads(r.read().decode('utf-8'))

    def train(self, rows, features, name, version):
        m = self._post('/train', {'rows': rows, 'features': list(features), 'name': name, 'version': str(version), 'label': LABEL, 'positive': POSITIVE})
        if not isinstance(m, dict) or not m.get('features'):
            raise ValueError('the model service returned no model')
        m = {**m, 'name': str(m.get('name') or name), 'version': str(version), 'positive': POSITIVE}
        if m.get('scoring') != 'http':
            load_model(m)   # a JSON logistic regression the service returned is checked like a local one
        return m

    def score(self, model, features):
        if model.get('scoring') != 'http':
            return score(model, features)
        missing = [k for k in model['features'] if features.get(k) is None]
        out = {'model': model['name'], 'version': model['version'], 'positive': model['positive'], 'available': False, 'missing': missing, 'probability': None}
        if missing:
            return out
        try:
            r = self._post('/score', {'model': {k: model.get(k) for k in ('name', 'version', 'features', 'ref')}, 'features': {k: features[k] for k in model['features']}})
            p = r.get('probability')
            if isinstance(p, (int, float)) and 0 <= p <= 1:
                out.update(available=True, probability=round(float(p), 4))
            else:
                out['error'] = 'the model service gave no probability'
        except Exception as e:   # the decision never waits on, or fails with, the service
            out['error'] = 'model service: ' + str(e)[:160]
        return out

    def describe(self):
        return {'kind': self.kind, 'url': self.url, 'timeoutSeconds': self.timeout}


def provider_from(config):
    """A provider from the Records config's researchProvider ({"kind": "builtin"} or {"kind": "http", "url", "timeoutSeconds"}); builtin when unset."""
    c = config or {}
    kind = c.get('kind', 'builtin')
    if kind == 'builtin':
        return BuiltinProvider()
    if kind == 'http':
        url = c.get('url')
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            raise ValueError('researchProvider.url must be an http(s) address')
        return HttpProvider(url, c.get('timeoutSeconds', 5))
    raise ValueError('researchProvider.kind is builtin or http')
