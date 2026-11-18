"""Replaceable model adapter. Provider-specific HTTP details stay inside this module.

respond() returns a normalised AdapterResult:
  kind='tool_calls'        -> calls=[ToolCall(call_id, name, arguments)]
  kind='structured_output' -> value=<parsed JSON>
  kind='text'              -> text=<plain reply>
Every failure is normalised to AdapterError(kind) with kind in timeout | unavailable | invalid_output.

Settings come from a JSON file (see config.example.json). If a provider ever needs a key, the
config names an environment variable; the key itself is never stored in Git, logs or records.
Private reasoning fields returned by a server (for example reasoning_content) are discarded.
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path


class AdapterError(Exception):
    def __init__(self, kind, detail, meta=None):
        super().__init__(kind + ': ' + detail)
        self.kind, self.detail, self.meta = kind, detail, meta or {}


@dataclass
class ToolCall:
    call_id: str
    name: str
    arguments: str  # raw JSON text exactly as the model produced it; validated by the dispatcher


@dataclass
class AdapterResult:
    kind: str
    calls: list = field(default_factory=list)
    value: object = None
    text: str = ''
    meta: dict = field(default_factory=dict)


def load_model_config(path):
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    return config.get('model', config)


class OpenAIChatAdapter:
    """POST {baseUrl}/chat/completions with native tool definitions or a strict JSON schema."""
    name = 'openai_chat_completions'

    def __init__(self, config):
        self.base_url = config['baseUrl'].rstrip('/')
        self.model = config['model']
        self.model_id = config.get('modelId') or self.model
        self.label = config.get('label') or self.model_id
        self.timeout = float(config.get('timeoutSeconds', 120))
        self.temperature = config.get('temperature', 0)
        self.max_tokens = dict(config.get('maxTokens') or {})
        self.extra_body = dict(config.get('extraBody') or {})
        self.tool_choice = config.get('toolChoice', 'required')
        self.identity_url = config.get('identityUrl')
        self.served_model_id = config.get('servedModelId')
        self.expect_arch = config.get('expectArch')
        key_env = config.get('apiKeyEnv')
        self._api_key = os.environ.get(key_env) if key_env else None

    def describe(self):
        return {'label': self.label, 'modelId': self.model_id, 'provider': self.name,
                'baseUrl': self.base_url, 'requestedModel': self.model}

    def identity(self):
        """Best-effort read of the serving process's model list, so records show what was loaded."""
        if not self.identity_url:
            return None
        try:
            with urllib.request.urlopen(self.identity_url, timeout=3) as response:
                listing = json.loads(response.read())
        except (OSError, ValueError) as exc:
            return {'error': 'identity probe failed: ' + type(exc).__name__}
        for entry in listing.get('data', []):
            if entry.get('id') == self.served_model_id:
                found = {k: entry.get(k) for k in ('id', 'publisher', 'arch', 'quantization', 'compatibility_type', 'state', 'loaded_context_length')}
                if self.expect_arch and entry.get('arch') != self.expect_arch:
                    found['warning'] = 'Loaded model architecture is ' + str(entry.get('arch')) + ', expected ' + self.expect_arch + '.'
                return found
        return {'error': 'served model id not listed: ' + str(self.served_model_id)}

    def health(self):
        """Reachability of the chat endpoint plus the identity probe; 3 s timeouts, no model call."""
        headers = {'Authorization': 'Bearer ' + self._api_key} if self._api_key else {}
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base_url + '/models', headers=headers), timeout=3) as response:
                response.read()
            reachable = True
        except (OSError, ValueError):
            reachable = False
        return {'reachable': reachable, 'serving': self.identity() if reachable else None}

    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        body = {'model': self.model, 'messages': messages, 'temperature': self.temperature,
                'max_tokens': int(self.max_tokens.get(task, 800)), 'stream': False, **self.extra_body}
        if tools:
            body['tools'] = tools
            body['tool_choice'] = self.tool_choice
        if schema:
            body['response_format'] = {'type': 'json_schema', 'json_schema': {'name': task, 'strict': True, 'schema': schema}}
        headers = {'Content-Type': 'application/json'}
        if self._api_key:
            headers['Authorization'] = 'Bearer ' + self._api_key
        request = urllib.request.Request(self.base_url + '/chat/completions', data=json.dumps(body).encode(), headers=headers)
        started = time.monotonic()
        wait = self.timeout if timeout is None else max(0.1, min(self.timeout, timeout))
        try:
            with urllib.request.urlopen(request, timeout=wait) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise AdapterError('unavailable', 'model service returned HTTP ' + str(exc.code), self._meta(started))
        except (TimeoutError, socket.timeout):
            raise AdapterError('timeout', 'no complete reply within ' + str(round(wait)) + ' s', self._meta(started))
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise AdapterError('timeout', 'no complete reply within ' + str(round(wait)) + ' s', self._meta(started))
            raise AdapterError('unavailable', 'cannot reach model service: ' + type(exc.reason).__name__, self._meta(started))
        except OSError as exc:
            raise AdapterError('unavailable', 'connection failed: ' + type(exc).__name__, self._meta(started))
        meta = self._meta(started)
        try:
            data = json.loads(raw)
            choice = data['choices'][0]
            message = choice['message']
        except (ValueError, KeyError, IndexError, TypeError):
            raise AdapterError('invalid_output', 'reply envelope is not a chat completion', meta)
        usage = data.get('usage') or {}
        meta.update({'finishReason': choice.get('finish_reason'), 'servedModel': data.get('model'),
                     'promptTokens': usage.get('prompt_tokens'), 'completionTokens': usage.get('completion_tokens')})
        if choice.get('finish_reason') == 'length':
            raise AdapterError('invalid_output', 'reply was cut off at the max_tokens limit', meta)
        if tools and message.get('tool_calls'):
            calls = []
            for index, item in enumerate(message['tool_calls']):
                function = item.get('function') if isinstance(item, dict) else None
                if not isinstance(function, dict) or not isinstance(function.get('name'), str):
                    raise AdapterError('invalid_output', 'tool call without a function name', meta)
                arguments = function.get('arguments', '')
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments)
                calls.append(ToolCall(str(item.get('id') or 'call_' + str(index)), function['name'], arguments))
            return AdapterResult('tool_calls', calls=calls, text=message.get('content') or '', meta=meta)
        content = message.get('content') or ''
        if schema:
            try:
                return AdapterResult('structured_output', value=json.loads(content), meta=meta)
            except ValueError:
                raise AdapterError('invalid_output', 'structured reply is not valid JSON', meta)
        return AdapterResult('text', text=content, meta=meta)

    @staticmethod
    def _meta(started):
        return {'latencyMs': round((time.monotonic() - started) * 1000)}
