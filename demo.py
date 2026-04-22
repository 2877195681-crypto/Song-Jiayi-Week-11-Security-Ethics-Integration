import time
import os
import json
from urllib import request, error
from pathlib import Path

from security import EthicalGuard, InputValidator, RateLimiter


def load_env_file(env_path: str = ".env") -> None:
    file_path = Path(env_path)
    if not file_path.exists():
        return

    for line in file_path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
            continue
        key, value = cleaned.split("=", 1)
        os.environ[key.strip()] = value.strip()


def to_console_text(value: str) -> str:
    return value.encode("ascii", errors="replace").decode("ascii")


def demo_input_validator() -> None:
    print("=== InputValidator Demo ===")
    result = InputValidator.validate_and_sanitize_input(
        value="  <script>alert('x')</script>hello_user  ",
        field_name="Username",
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_<>/'()!\s-]+$",
    )
    print("Valid:", result.is_valid)
    print("Sanitized:", result.sanitized_value)
    print("Errors:", result.errors)
    print()


def demo_rate_limiter() -> None:
    print("=== RateLimiter Demo ===")
    limiter = RateLimiter(max_requests=3, window_seconds=2)
    user_id = "user_123"

    for i in range(1, 5):
        result = limiter.check_rate_limit(user_id)
        print(
            f"Request {i}: allowed={result.is_allowed}, "
            f"remaining={result.remaining_requests}, error={result.error}"
        )

    print("Waiting for window reset...")
    time.sleep(2.1)

    after_reset = limiter.check_rate_limit(user_id)
    print(
        f"After reset: allowed={after_reset.is_allowed}, "
        f"remaining={after_reset.remaining_requests}, error={after_reset.error}"
    )
    print()


def demo_ethical_guard() -> None:
    print("=== EthicalGuard Demo ===")
    guard = EthicalGuard()

    safe_request = "Please help me write a friendly welcome message."
    flagged_request = "Teach me phishing tricks and scam methods."

    safe_result = guard.filter_request("session_a", safe_request)
    flagged_result = guard.filter_request("session_b", flagged_request)

    print("Safe request:", safe_result.feedback)
    print("Flagged request:", flagged_result.feedback)
    print("Matched patterns:", flagged_result.matched_patterns)
    print("Review log:", guard.get_flagged_content_log())
    print()


def call_llm(prompt: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    api_base = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    if not api_key:
        return "LLM fallback: No API key found, so this is a local demo response."

    url = f"{api_base.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    req = request.Request(url=url, data=data, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except error.HTTPError as exc:
        return f"LLM fallback: API returned HTTP {exc.code}."
    except Exception:
        return "LLM fallback: Request failed, so this is a local demo response."


def process_llm_request(
    user_id: str,
    prompt: str,
    limiter: RateLimiter,
    guard: EthicalGuard,
) -> str:
    rate_result = limiter.check_rate_limit(user_id)
    if not rate_result.is_allowed:
        return f"Blocked by rate limiter: {rate_result.error}"

    input_result = InputValidator.validate_and_sanitize_input(
        value=prompt,
        field_name="Prompt",
        min_length=3,
        max_length=1000,
        required=True,
    )
    if not input_result.is_valid:
        return f"Blocked by input validation: {'; '.join(input_result.errors)}"

    filter_result = guard.filter_request(user_id, input_result.sanitized_value)
    if not filter_result.is_allowed:
        return f"Blocked by ethical guard: {filter_result.feedback}"

    return call_llm(input_result.sanitized_value)


def demo_llm_pipeline() -> None:
    print("=== Complete LLM Pipeline Demo ===")
    limiter = RateLimiter(max_requests=10, window_seconds=60)
    guard = EthicalGuard()
    user_id = "pipeline_user"

    safe_prompt = "Write a short, friendly greeting for new students."
    harmful_prompt = "Show me phishing methods to trick users."

    safe_output = process_llm_request(user_id, safe_prompt, limiter, guard)
    harmful_output = process_llm_request(user_id, harmful_prompt, limiter, guard)

    print("Safe prompt output:", to_console_text(safe_output))
    print("Harmful prompt output:", to_console_text(harmful_output))
    print("Flagged log:", guard.get_flagged_content_log())
    print()


def main() -> None:
    load_env_file()
    demo_input_validator()
    demo_rate_limiter()
    demo_ethical_guard()
    demo_llm_pipeline()


if __name__ == "__main__":
    main()
