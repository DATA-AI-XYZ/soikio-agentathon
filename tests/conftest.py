"""Shared test setup: put src/ on the path and default every test to the offline mock backend.

Defaulting the backend to mock (ADR-0015) guarantees no test accidentally hits live Azure when
the env is unset (TESTPLAN-01.3.x risk note). Individual tests override via monkeypatch.setenv."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

os.environ.setdefault("FOUNDRY_IQ_MOCK", "1")
os.environ.setdefault("FOUNDRY_IQ_BACKEND", "mock")
