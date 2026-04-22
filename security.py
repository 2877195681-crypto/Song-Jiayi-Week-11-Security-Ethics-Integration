import html
import re
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    is_valid: bool
    sanitized_value: str
    errors: list[str] = field(default_factory=list)


@dataclass
class RateLimitResult:
    is_allowed: bool
    error: Optional[str] = None
    remaining_requests: int = 0
    retry_after_seconds: int = 0


@dataclass
class ContentFilterResult:
    is_allowed: bool
    feedback: str
    matched_patterns: list[str] = field(default_factory=list)


class InputValidator:
    @staticmethod
    def check_input_length(value: str, min_length: int = 0, max_length: int = 1000) -> Optional[str]:
        length = len(value)
        if length < min_length:
            return f"Input is too short. Minimum length is {min_length} characters."
        if length > max_length:
            return f"Input is too long. Maximum length is {max_length} characters."
        return None

    @staticmethod
    def validate_input_format(value: str, pattern: Optional[str] = None, field_name: str = "Input") -> Optional[str]:
        if pattern and not re.fullmatch(pattern, value):
            return f"{field_name} has an invalid format."
        return None

    @staticmethod
    def sanitize_harmful_content(value: str) -> str:
        cleaned = value.replace("\x00", "")
        cleaned = re.sub(r"<\s*script.*?>.*?<\s*/\s*script\s*>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        return html.escape(cleaned).strip()

    @staticmethod
    def validate_and_sanitize_input(
        value: str,
        field_name: str = "Input",
        min_length: int = 0,
        max_length: int = 1000,
        pattern: Optional[str] = None,
        required: bool = True,
    ) -> ValidationResult:
        errors: list[str] = []
        raw_value = value if value is not None else ""
        if required and not raw_value.strip():
            return ValidationResult(False, "", [f"{field_name} is required."])
        length_error = InputValidator.check_input_length(raw_value, min_length=min_length, max_length=max_length)
        if length_error:
            errors.append(length_error)
        format_error = InputValidator.validate_input_format(raw_value, pattern=pattern, field_name=field_name)
        if format_error:
            errors.append(format_error)
        sanitized_value = InputValidator.sanitize_harmful_content(raw_value)
        return ValidationResult(not errors, sanitized_value, errors)


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._request_history: dict[str, list[float]] = {}

    def _cleanup_old_requests(self, identifier: str, now: float) -> None:
        history = self._request_history.get(identifier, [])
        self._request_history[identifier] = [t for t in history if now - t < self.window_seconds]

    def check_rate_limit(self, identifier: str) -> RateLimitResult:
        now = time.time()
        self._cleanup_old_requests(identifier, now)
        history = self._request_history[identifier]
        if len(history) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - history[0])))
            return RateLimitResult(False, f"Rate limit exceeded. Try again in {retry_after} seconds.", 0, retry_after)
        history.append(now)
        return RateLimitResult(True, None, self.max_requests - len(history), 0)

    def reset_identifier(self, identifier: str) -> None:
        self._request_history.pop(identifier, None)


class EthicalGuard:
    def __init__(self, harmful_patterns: Optional[list[str]] = None) -> None:
        self.harmful_patterns = harmful_patterns or [
            r"\b(hate|violence|attack)\b",
            r"\b(exploit|malware|phishing)\b",
            r"\b(illegal|fraud|scam)\b",
        ]
        self._review_log: list[dict[str, str]] = []

    def check_harmful_content_patterns(self, content: str) -> list[str]:
        return [p for p in self.harmful_patterns if re.search(p, content, flags=re.IGNORECASE)]

    def filter_request(self, user_or_session_id: str, content: str) -> ContentFilterResult:
        matched_patterns = self.check_harmful_content_patterns(content)
        if not matched_patterns:
            return ContentFilterResult(True, "Request accepted.", [])
        self._review_log.append(
            {
                "identifier": user_or_session_id,
                "content": content,
                "matched_patterns": ", ".join(matched_patterns),
                "flagged_at": str(int(time.time())),
            }
        )
        return ContentFilterResult(
            False,
            "Request blocked: your message contains content that violates safety rules.",
            matched_patterns,
        )

    def get_flagged_content_log(self) -> list[dict[str, str]]:
        return list(self._review_log)
