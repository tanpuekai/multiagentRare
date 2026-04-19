from __future__ import annotations

import json
import time
from typing import Any, Callable
from urllib import request as urllib_request


StreamCallback = Callable[[dict[str, Any]], None]


def _delta_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0] if isinstance(choices[0], dict) else {}
    delta = choice.get("delta")
    if isinstance(delta, dict):
        for key in ("content", "reasoning_content"):
            value = delta.get(key)
            if isinstance(value, str) and value:
                return value
    message = choice.get("message")
    if isinstance(message, dict):
        value = message.get("content")
        if isinstance(value, str) and value:
            return value
    value = choice.get("text")
    return value if isinstance(value, str) else ""


def request_chat_completion_stream(
    *,
    url: str,
    api_key: str,
    body: dict[str, Any],
    user_agent: str,
    on_delta: StreamCallback,
    timeout: int = 240,
) -> str:
    stream_body = dict(body)
    stream_body["stream"] = True
    payload = json.dumps(stream_body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        "Connection": "close",
        "User-Agent": user_agent,
    }
    request = urllib_request.Request(url, data=payload, headers=headers, method="POST")
    chunks: list[str] = []
    saw_event = False
    event_count = 0
    char_count = 0
    started = time.monotonic()
    first_delta_at: float | None = None
    with urllib_request.urlopen(request, timeout=timeout) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line or line.startswith(":"):
                continue
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data:
                continue
            saw_event = True
            if data == "[DONE]":
                break
            payload_obj = json.loads(data)
            if not isinstance(payload_obj, dict):
                continue
            delta = _delta_text(payload_obj)
            if not delta:
                continue
            event_count += 1
            char_count += len(delta)
            if first_delta_at is None:
                first_delta_at = time.monotonic()
            chunks.append(delta)
            on_delta({"delta": delta})
    on_delta(
        {
            "delta": "",
            "done": True,
            "event_count": event_count,
            "char_count": char_count,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "first_delta_ms": int(((first_delta_at or time.monotonic()) - started) * 1000),
        }
    )
    if not saw_event:
        raise ValueError("Streaming response did not return server-sent events.")
    content = "".join(chunks).strip()
    if not content:
        raise ValueError("Streaming response did not contain model content.")
    return content
