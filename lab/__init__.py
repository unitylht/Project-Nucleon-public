"""Nucleon Lab: a Pydantic AI agent over the records instance's business tool surface (POST api/tools/<name>), with its own
conversation store and an SSE API for the chat front end. Fictional data only."""
import os
import sys
from pathlib import Path

os.environ.setdefault('PYDANTIC_AI_NO_BANNER', '1')
sys.path.append(str(Path(__file__).resolve().parent.parent / 'prototype'))   # the coordinator's guard patterns, reused as they are (stdlib only)
