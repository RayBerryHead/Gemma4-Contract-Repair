"""Free-only Gemini Developer API transport with resumable attempt accounting."""
from __future__ import annotations
import fcntl
import json
import re
import os
import subprocess
import time
from pathlib import Path
from typing import Any
import requests

FREE_MODELS = {"gemma-4-31b-it", "gemma-4-26b-a4b-it"}

class ApiPaused(RuntimeError):
    def __init__(self, reason: str, details: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}

def resolve_api_key(project: str) -> tuple[str, str]:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(name):
            return os.environ[name], "environment:" + name
    command = ["gcloud", "services", "api-keys", "list", "--project", project,
               "--filter", "restrictions.apiTargets.service:generativelanguage.googleapis.com",
               "--format=value(name)", "--limit=1"]
    name = subprocess.check_output(command, text=True).strip()
    if not name:
        raise ApiPaused("CREDENTIAL_REQUIRED")
    value = subprocess.check_output(
        ["gcloud", "services", "api-keys", "get-key-string", name,
         "--project", project, "--format=value(keyString)"], text=True).strip()
    if not value:
        raise ApiPaused("CREDENTIAL_REQUIRED")
    return value, "GB10:gcloud-existing-restricted-key"

class FreeGemmaClient:
    def __init__(self, config: dict, ledger: Path):
        if config.get("paid_fallback_enabled") is not False:
            raise ApiPaused("PAID_RESOURCE_REQUIRES_USER_APPROVAL")
        if config.get("endpoint") != "https://generativelanguage.googleapis.com/v1beta":
            raise ApiPaused("UNVERIFIED_PROVIDER_REQUIRES_REVIEW")
        if config.get("model") not in FREE_MODELS:
            raise ApiPaused("MODEL_NOT_IN_VERIFIED_FREE_ALLOWLIST")
        self.config = config
        self.ledger = Path(ledger)
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.key, self.credential_source = resolve_api_key(config["project_id"])

    def _events(self) -> list[dict]:
        if not self.ledger.exists():
            return []
        return [json.loads(line) for line in self.ledger.read_text().splitlines() if line.strip()]

    def _record(self, event: dict) -> None:
        event={**event,"request_tag":getattr(self,"request_tag",None)}
        with self.ledger.open("a") as output:
            output.write(json.dumps(event, ensure_ascii=False) + "\n")

    def generate(self, contents: list[dict], **kwargs) -> dict:
        lock_path=self.ledger.parent/"transport.lock"
        with lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            return self._generate_locked(contents,**kwargs)

    def _generate_locked(self, contents: list[dict], *, tools: list[dict] | None = None,
                 model: str | None = None, tool_mode: str | None = None,
                 max_output_tokens: int | None = None) -> dict:
        model = model or self.config["model"]
        if model not in FREE_MODELS:
            raise ApiPaused("MODEL_NOT_IN_VERIFIED_FREE_ALLOWLIST")
        contents=[{**content,"parts":[part for part in content["parts"]
                    if not (part.get("thought") and "text" in part and "thoughtSignature" not in part)]}
                  for content in contents]
        contents=[content for content in contents if content["parts"]]
        body = {
            "contents": contents,
            "generationConfig": {
                "thinkingConfig": {"thinkingLevel": self.config["thinking_level"],"includeThoughts":False},
                "temperature": self.config["temperature"],
                "maxOutputTokens": max_output_tokens or self.config["max_output_tokens"],
            },
        }
        if tools:
            body["tools"] = [{"functionDeclarations": tools}]
        if tool_mode:
            body["toolConfig"] = {"functionCallingConfig": {"mode": tool_mode}}
        pause_path=self.ledger.parent/"quota-pause.json"
        if pause_path.exists():
            pause=json.loads(pause_path.read_text())
            if pause["not_before"]>time.time():
                raise ApiPaused("FREE_QUOTA_PAUSED_WAIT",pause)
        try:
            count_response=requests.post(
                self.config["endpoint"]+"/models/"+model+":countTokens",
                headers={"x-goog-api-key":self.key,"Content-Type":"application/json"},
                json={"contents":contents},timeout=(20,60))
        except requests.RequestException:
            raise ApiPaused("TOKEN_COUNT_NETWORK_UNAVAILABLE") from None
        self._record({"event":"token_count_finished","http_status":count_response.status_code,"model":model})
        if count_response.status_code!=200:
            raise ApiPaused("TOKEN_COUNT_UNAVAILABLE",{"http_status":count_response.status_code})
        input_tokens=count_response.json()["totalTokens"]+512
        token_limit=self.config.get("observed_input_tpm",16000)
        if input_tokens>token_limit:
            raise ApiPaused("INPUT_EXCEEDS_FREE_TPM",{"input_tokens_with_tool_margin":input_tokens,"input_tpm":token_limit})
        reservation_path=self.ledger.parent/"input-reservations.jsonl"
        for retry in range(3):
            reservations=[json.loads(line) for line in reservation_path.read_text().splitlines()] if reservation_path.exists() else []
            while True:
                recent=[event for event in reservations if event["model"]==model and time.time()-event["started_at"]<60]
                if sum(event["input_tokens"] for event in recent)+input_tokens <= token_limit:
                    break
                time.sleep(max(0.1,min(event["started_at"] for event in recent)+60-time.time()))
            events = self._events()
            attempts = [event for event in events if event.get("event") == "attempt_started"]
            prior = int(self.config.get("prior_preparation_attempts", 2))
            if prior + len(attempts) >= self.config["max_http_attempts"]:
                raise ApiPaused("ATTEMPT_BUDGET_EXHAUSTED")
            pacing_path=self.ledger.parent/"last-request.json"
            last=json.loads(pacing_path.read_text())["started_at"] if pacing_path.exists() else 0
            delay=self.config["minimum_request_interval_seconds"]-(time.time()-last)
            if delay > 0:
                time.sleep(delay)
            attempt = prior + len(attempts) + 1
            started = time.time()
            pacing_path.write_text(json.dumps({"started_at":started}))
            with reservation_path.open("a") as output:
                output.write(json.dumps({"started_at":started,"model":model,"input_tokens":input_tokens})+"\n")
            self._record({"event": "attempt_started", "attempt": attempt, "started_at": started, "model": model})
            try:
                response = requests.post(
                    self.config["endpoint"] + "/models/" + model + ":generateContent",
                    headers={"x-goog-api-key": self.key, "Content-Type": "application/json"},
                    json=body, timeout=(20, self.config.get("read_timeout_seconds", 900)))
            except requests.RequestException as error:
                self._record({"event": "attempt_finished", "attempt": attempt,
                              "status": "UNKNOWN_NETWORK_RESULT", "error_type": type(error).__name__})
                raise ApiPaused("NETWORK_RESULT_UNKNOWN", {"attempt": attempt}) from None
            data = response.json()
            self._record({"event": "attempt_finished", "attempt": attempt,
                          "http_status": response.status_code,
                          "elapsed_seconds": time.time() - started,
                          "usage": data.get("usageMetadata"), "known_price_usd": 0})
            if response.status_code == 200:
                return data
            if response.status_code == 429:
                details = data.get("error", {})
                delay=60.0
                for detail in details.get("details",[]):
                    match=re.fullmatch(r"(\d+(?:\.\d+)?)s",detail.get("retryDelay",""))
                    if match:
                        delay=float(match[1])
                pause={"not_before":time.time()+delay,"provider_error":details}
                pause_path.write_text(json.dumps(pause))
                raise ApiPaused("FREE_QUOTA_PAUSED", pause)
            if response.status_code in {401, 403, 404}:
                raise ApiPaused("CREDENTIAL_OR_MODEL_UNAVAILABLE",
                                {"http_status": response.status_code, "error": data.get("error", {})})
            if response.status_code >= 500 and retry < 2:
                time.sleep(2 ** (retry + 1))
                continue
            raise ApiPaused("PROVIDER_ERROR", {"http_status": response.status_code, "error": data.get("error", {})})
        raise ApiPaused("TRANSIENT_RETRIES_EXHAUSTED")

def tool_response_content(response: dict, results: list[Any]) -> list[dict]:
    content = response["candidates"][0]["content"]
    calls = [part["functionCall"] for part in content["parts"] if "functionCall" in part]
    if len(calls) != len(results):
        raise ValueError("Every function call requires exactly one matching response")
    parts = []
    for call, result in zip(calls, results):
        returned = {"name": call["name"], "response": {"result": result}}
        if call.get("id"):
            returned["id"] = call["id"]
        parts.append({"functionResponse": returned})
    return [content, {"role": "user", "parts": parts}]

def extract_patch(response: dict) -> str:
    content = response["candidates"][0]["content"]
    for part in content.get("parts", []):
        call = part.get("functionCall", {})
        if call.get("name") == "submit_patch":
            return call.get("args", {}).get("diff", "")
    text = "\n".join(part.get("text", "") for part in content.get("parts", []) if not part.get("thought"))
    if "```diff" in text:
        return text.split("```diff", 1)[1].split("```", 1)[0].lstrip("\n")
    return text if text.startswith("diff --git ") or text.startswith("--- ") else ""

PATCH_TOOL = {
    "name":"submit_patch",
    "description":"Submit complete cumulative exact text replacements against the original buggy source.",
    "parameters":{"type":"OBJECT","properties":{"edits":{"type":"ARRAY","items":{
        "type":"OBJECT","properties":{"path":{"type":"STRING"},"old_text":{"type":"STRING"},"new_text":{"type":"STRING"}},
        "required":["path","old_text","new_text"]}}},"required":["edits"]},
}
