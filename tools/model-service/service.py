#!/usr/bin/env python3
"""A model service for Nucleon's research hook: the team's own classifier, in the team's own Python environment, behind two endpoints.

    POST /train   {rows: [...], features: [...], name, version, label: "Target_Deny", positive: "decline"}
                  -> {name, version, features, scoring: "http", ref, trainedOn: {...}}        (the model Nucleon stores as that version)
    POST /score   {model: {name, version, features, ref}, features: {name: value}}
                  -> {probability: 0..1}                                                        (the chance the Owner declines)
    GET  /health  -> {ok: true, models: [...]}

Nucleon (config `"researchProvider": {"kind": "http", "url": "http://127.0.0.1:8640"}`) sends the training table here when the Owner refits and asks for a
score on every new case. A failure or a timeout here is "no score" there, never a changed decision.

The pipeline below is the team notebook's logistic regression (StandardScaler + LogisticRegression(class_weight='balanced')); `--family xgboost` fits the
notebook's XGBoost instead (shallow trees, scale_pos_weight from the training labels). Fitted models are pickled under --models-dir and reloaded at start,
so a restart keeps every version Nucleon knows. Requires scikit-learn (and xgboost for that family). All data it sees is what Nucleon sends: no ledger."""
import argparse
import json
import pickle
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MODELS = {}   # ref -> {'features': [...], 'pipeline': fitted}


def fit(rows, features, label, family):
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    X = np.array([[float(r[k]) for k in features] for r in rows])
    y = np.array([int(r[label]) for r in rows])
    if family == 'xgboost':
        from xgboost import XGBClassifier
        weight = int((y == 0).sum()) / max(int((y == 1).sum()), 1)
        model = XGBClassifier(n_estimators=60, max_depth=2, learning_rate=0.05, min_child_weight=2, reg_lambda=5.0, subsample=0.9, colsample_bytree=0.9,
                              scale_pos_weight=weight, random_state=42, eval_metric='logloss')
        model.fit(X, y)
        return model, {}
    pipeline = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight='balanced', max_iter=5000, random_state=42))
    pipeline.fit(X, y)
    scaler, lr = pipeline.named_steps['standardscaler'], pipeline.named_steps['logisticregression']
    # the coefficients travel with the version so the Owner's page can show them (Nucleon still asks this service for every score)
    return pipeline, {'mean': [float(v) for v in scaler.mean_], 'scale': [float(v) for v in scaler.scale_], 'coef': [float(v) for v in lr.coef_[0]], 'intercept': float(lr.intercept_[0])}


def make_handler(models_dir, family):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(self.address_string(), fmt % args)

        def reply(self, status, payload):
            data = json.dumps(payload).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == '/health':
                return self.reply(200, {'ok': True, 'family': family, 'models': sorted(MODELS)})
            self.reply(404, {'error': 'not found'})

        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            except ValueError:
                return self.reply(400, {'error': 'bad json'})
            try:
                if self.path == '/train':
                    features, label = body['features'], body.get('label', 'Target_Deny')
                    rows = [r for r in body['rows'] if all(r.get(k) is not None for k in features)]
                    if len(rows) < 2 or len({int(r[label]) for r in rows}) < 2:
                        return self.reply(409, {'error': 'rows of both classes with every feature are needed'})
                    model, extra = fit(rows, features, label, family)
                    ref = str(body.get('name') or 'team') + '-v' + str(body.get('version', '0'))
                    MODELS[ref] = {'features': features, 'pipeline': model}
                    models_dir.mkdir(parents=True, exist_ok=True)
                    (models_dir / (ref + '.pkl')).write_bytes(pickle.dumps(MODELS[ref]))
                    return self.reply(200, {'name': body.get('name') or 'team', 'version': str(body.get('version', '0')), 'features': features, 'scoring': 'http', 'ref': ref,
                                            'trainedOn': {'rows': len(rows), 'positives': sum(int(r[label]) for r in rows), 'family': family}, **extra})
                if self.path == '/score':
                    ref = (body.get('model') or {}).get('ref')
                    m = MODELS.get(ref)
                    if not m:
                        return self.reply(404, {'error': 'unknown model ' + str(ref)})
                    x = [[float(body['features'][k]) for k in m['features']]]
                    return self.reply(200, {'probability': float(m['pipeline'].predict_proba(x)[0][1])})
            except (KeyError, TypeError, ValueError) as e:
                return self.reply(400, {'error': str(e)[:200]})
            self.reply(404, {'error': 'not found'})
    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--port', type=int, default=8640)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--models-dir', default=str(Path(__file__).resolve().parent / 'models'))
    ap.add_argument('--family', choices=('logistic', 'xgboost'), default='logistic')
    args = ap.parse_args()
    models_dir = Path(args.models_dir)
    for p in models_dir.glob('*.pkl'):
        MODELS[p.stem] = pickle.loads(p.read_bytes())
    print('model service on http://' + args.host + ':' + str(args.port) + ' (' + args.family + ', ' + str(len(MODELS)) + ' model(s) loaded)')
    HTTPServer((args.host, args.port), make_handler(models_dir, args.family)).serve_forever()


if __name__ == '__main__':
    main()
