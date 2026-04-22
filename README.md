# Security Module Documentation

## 1) Short System Overview

This project adds a simple security layer in front of LLM requests to reduce abuse and unsafe inputs.

**Problem addressed**
- overly long or malformed inputs
- repeated requests that can overload API usage
- harmful prompts (for example phishing/scam intent)

**Workflow**
1. Validate and sanitize text (`InputValidator`)
2. Check request quota (`RateLimiter`)
3. Filter harmful content (`EthicalGuard`)
4. Send to LLM only if all checks pass

**Key components**
- `InputValidator`: length limits, optional regex format check, sanitization, structured errors
- `RateLimiter`: per-user/session request counting, limit enforcement, retry timing
- `EthicalGuard`: harmful-pattern matching, request blocking, flagged-content review log

---

## 2) Threat Model

**Assets**
- API quota/cost
- service availability
- user safety and trust
- moderation visibility

**Actors**
- normal users
- abusive users sending spam or harmful prompts
- accidental unsafe input from regular users

**Threats considered**
- input abuse: large/malformed/script-like payloads
- request flooding from one user/session
- harmful prompt submission
- lack of traceability for blocked content

**Out of scope**
- distributed attacks across many nodes/IPs
- advanced semantic jailbreak detection
- transport/network security controls

---

## 3) Security Measures Implemented

### Input Validation (`InputValidator`)
- checks `required`, `min_length`, and `max_length` (default max: `1000`)
- optional format validation via regex pattern
- sanitizes by removing null bytes, stripping script tags, escaping HTML
- returns `ValidationResult(is_valid, sanitized_value, errors)`

### Rate Limiting (`RateLimiter`)
- tracks request timestamps by `identifier`
- blocks when requests exceed `max_requests` in `window_seconds`
- returns `RateLimitResult` with `error` and `retry_after_seconds`
- resets automatically as old timestamps expire

### Content Filtering (`EthicalGuard`)
- checks prompt text against harmful regex patterns
- blocks flagged requests and provides user feedback
- stores flagged events in an internal review log
- returns `ContentFilterResult(is_allowed, feedback, matched_patterns)`

---

## 4) How to Use the Security Module

```python
from security import InputValidator, RateLimiter, EthicalGuard

limiter = RateLimiter(max_requests=10, window_seconds=60)
guard = EthicalGuard()
user_id = "session_123"
prompt = "Write a friendly welcome message."

rate = limiter.check_rate_limit(user_id)
if not rate.is_allowed:
    print(rate.error)
else:
    validated = InputValidator.validate_and_sanitize_input(prompt, field_name="Prompt")
    if not validated.is_valid:
        print(validated.errors)
    else:
        filtered = guard.filter_request(user_id, validated.sanitized_value)
        if not filtered.is_allowed:
            print(filtered.feedback)
        else:
            print("Safe to send to LLM:", validated.sanitized_value)
```

Run complete demonstration:

```bash
python demo.py
```

---

## 5) Limitations

- **In-memory state only**: rate-limit counters and flagged logs reset on process restart.
- **Single-instance design**: rate limiting is not shared across multiple servers.
- **Regex-only filtering**: may miss nuanced harmful intent or create false positives.
- **No persistent audit storage**: flagged content is not written to a database.
- **Trust on upstream identity**: user/session identifier quality depends on caller logic.
- **Basic sanitization**: improves safety but is not a complete defense for every attack type.

## Suggested Improvements

- move counters to Redis for distributed rate limiting
- persist moderation logs to secure storage
- add semantic moderation layer beyond regex
- add role-based limits and monitoring dashboards

