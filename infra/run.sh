#!/bin/bash
exec python -m uvicorn console.backend:app --host 0.0.0.0 --port "${PORT:-8000}" --timeout-keep-alive 120 --log-level warning
