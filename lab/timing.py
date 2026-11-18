"""Where a turn's time goes, for the turn's meta and the Activity group: each model request (its index, prompt and completion tokens,
latency, the completion cap it was sent with and whether a retry caused it), the time spent waiting on the records, and the rest.
Measurement only: nothing is cached or changed by it. The turn's Timing is a context variable set by the chat route, so every records
call of the turn (the Lab's own and the tools') adds to it without being passed it."""
import contextlib
import contextvars
import time

TURN = contextvars.ContextVar('lab_turn_timing', default=None)


class Timing:
    def __init__(self):
        self.started = time.monotonic()
        self.requests = []   # one per model request, in order
        self.records_ms, self.records_calls = 0.0, 0

    @contextlib.contextmanager
    def records(self):
        t0 = time.monotonic()
        try:
            yield
        finally:
            self.records_ms += (time.monotonic() - t0) * 1000
            self.records_calls += 1

    def model_request(self, latency_ms, prompt, completion, cap, retry):
        self.requests.append({'index': len(self.requests) + 1, 'promptTokens': prompt, 'completionTokens': completion, 'latencyMs': int(latency_ms),
                              'maxTokens': cap, 'retry': retry})

    def summary(self):
        """{totalMs, phases {modelMs, recordsMs, otherMs}, recordsCalls, requests, guardRetries}: model is the sum of the requests'
        latencies, records the time waiting on the records, other the rest of the turn (the Lab's own work and the thread's lock)."""
        total = (time.monotonic() - self.started) * 1000
        model = sum(r['latencyMs'] for r in self.requests)
        return {'totalMs': int(total), 'phases': {'modelMs': int(model), 'recordsMs': int(self.records_ms), 'otherMs': max(0, int(total - model - self.records_ms))},
                'recordsCalls': self.records_calls, 'requests': self.requests, 'guardRetries': sum(1 for r in self.requests if r['retry'] == 'guard')}


@contextlib.contextmanager
def records_call():
    """Time one records call against the turn under way, if any."""
    t = TURN.get()
    if t is None:
        yield
        return
    with t.records():
        yield
