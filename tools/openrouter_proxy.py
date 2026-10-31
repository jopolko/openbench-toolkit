#!/usr/bin/env python3
"""
Local HTTP sidecar that lets the webui chat talk to OpenRouter without the
API key ever reaching the browser. Mirrors pentest_ui_api.py's shape: a
small loopback-only FastAPI app, no auth beyond the bind (same posture as
msfrpcd/MetasploitMCP/ZAP - loopback-only is the trust boundary here).

Two routes, both OpenAI-schema-compatible so the webui's existing chat
service can point at this instead of the local llama-server router by
swapping the base URL:

    GET  /v1/models            - list OpenRouter's models (no key needed,
                                  this is a public OpenRouter endpoint)
    POST /v1/chat/completions  - proxied to OpenRouter with
                                  OPENROUTER_API_KEY attached server-side;
                                  streams back untouched when the request
                                  asked for stream=true

OPENROUTER_API_KEY is read the same way pentest_agent.py reads ZAP_API_KEY/
NVD_API_KEY/BRAVE_API_KEY - see tools/pentest_secrets.py. No Anthropic/Claude
block here: that constraint is specific to pentest_agent.py's autonomous
tool-calling loop, not to a human driving chat by hand.

Usage:
    .venv/bin/python tools/openrouter_proxy.py --port 8087
"""

import argparse
import json
import sys
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pentest_secrets import read_secret  # noqa: E402 - needs sys.path set first

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
REQUEST_TIMEOUT_SECONDS = 900  # matches pentest_agent.py's --request-timeout default

app = FastAPI(title="openrouter-proxy")
app.add_middleware(
    CORSMiddleware,
    # Loopback-only bind (see main()), so any Origin reaching this at all is
    # already same-machine - wildcard here doesn't widen exposure.
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _openrouter_api_key() -> str:
    return read_secret("OPENROUTER_API_KEY")


def _auth_headers() -> dict:
    key = _openrouter_api_key()
    if not key:
        raise HTTPException(
            500,
            "OPENROUTER_API_KEY is not configured - set it in "
            "systemd/pentest-appliance.env (or $OPENROUTER_API_KEY) and restart "
            "this sidecar.",
        )
    return {"Authorization": f"Bearer {key}"}


@app.get("/v1/models")
def list_models():
    try:
        resp = requests.get(f"{OPENROUTER_BASE_URL}/models", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise HTTPException(502, f"OpenRouter not reachable: {exc}") from exc


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    headers = _auth_headers()
    stream = bool(body.get("stream"))

    if not stream:
        try:
            resp = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions", json=body, headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise HTTPException(502, f"OpenRouter not reachable: {exc}") from exc
        if not resp.ok:
            raise HTTPException(resp.status_code, resp.text)
        return resp.json()

    def gen():
        try:
            with requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions", json=body, headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS, stream=True,
            ) as resp:
                if not resp.ok:
                    # Surface the error as a single SSE data frame rather than a
                    # bare non-2xx status - the webui's chat stream reader only
                    # ever expects "data: ..." lines once it's committed to
                    # treating this as an event-stream response.
                    detail = resp.text
                    yield f"data: {json.dumps({'error': {'message': detail}})}\n\n".encode()
                    return
                # requests defaults text/event-stream to Latin-1 with no charset
                # in the header - same fix pentest_agent.py's own SSE reads use.
                resp.encoding = "utf-8"
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    yield (line + "\n\n").encode("utf-8")
        except requests.RequestException as exc:
            yield f"data: {json.dumps({'error': {'message': str(exc)}})}\n\n".encode()

    return StreamingResponse(gen(), media_type="text/event-stream")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8087)
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
