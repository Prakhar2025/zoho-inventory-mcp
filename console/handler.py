"""Lambda entry point: Mangum wraps the FastAPI app for API Gateway.

On Lambda the SSE StreamingResponse is buffered by Mangum, so API Gateway
returns the whole frame sequence once the run completes; the console parses
the same protocol either way.
"""

from __future__ import annotations

from mangum import Mangum

from console.backend import app

handler = Mangum(app, lifespan="auto")
