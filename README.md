# Security Module Documentation

## 1) System Overview

### Problem
Applications that accept user input and call LLM APIs face several common risks:

- malformed or unexpectedly large input
- abuse through repeated requests (spam/flooding)
- harmful or policy-violating prompts
- unsafe content being passed to downstream systems

This project provides a lightweight Python security layer to reduce these risks before a request reaches an LLM endpoint.

### Workflow
The intended request flow is:

1. **Input validation and sanitization** (`InputValidator`)
2. **Rate limiting** (`RateLimiter`)
3. **Content filtering** (`EthicalGuard`)
4. **LLM call** (only if all checks pass)

If a request fails any step, the pipeline returns a clear user-facing error message and stops further processing.

### Key Components

The module is implemented in `security.py` and contains three core classes:

- `InputValidator`
  - checks length bounds
  - validates format using regex (optional)
  - sanitizes risky input (for example script tags and null bytes)
  - returns structured validation results

- `RateLimiter`
  - tracks requests per user/session identifier
  - enforces maximum requests per time window
  - returns retry timing when a limit is exceeded
  - automatically resets by removing expired timestamps

- `EthicalGuard`
  - checks content against harmful/inappropriate regex patterns
  - blocks flagged requests
  - records blocked content in an internal review log
  - returns feedback suitable for user display

Example integration is demonstrated in `demo.py`, including a full end-to-end pipeline.

---

## 2) Threat Model

### Assets to Protect

- LLM API usage budget and service availability
- system integrity (prevent harmful payload propagation)
- user trust and platform safety
- moderation/review visibility for suspicious prompts

### Actors

- normal users
- abusive users attempting spam or prompt abuse
- users submitting unsafe text accidentally

### Main Threats Considered

1. **Input abuse**
   - overlong prompts, malformed text, or embedded script-like content
2. **Denial-of-service style request flooding**
   - repeated calls from one session/user in short periods
3. **Harmful content submission**
   - prompts containing clearly unsafe categories (for example phishing/scam)
4. **Operational blind spots**
   - no history of blocked requests for later review

### Out of Scope Threats

- distributed, multi-node rate-limit evasion
- deep semantic policy violations not detectable by regex
- transport-level threats (TLS termination, network MITM)
- database-level persistence security (current log is in memory)

---

## 3) Security Measures Implemented

## A. Input Validation and Sanitization (`InputValidator`)

Implemented controls:

- required-field check (rejects empty/whitespace-only input)
- configurable `min_length` and `max_length` (default max is 1000)
- optional regex format validation
- sanitization:
  - removes null bytes
  - strips `<script>...</script>` blocks
  - escapes HTML special characters

Returned result:

- `ValidationResult.is_valid`
- `ValidationResult.sanitized_value`
- `ValidationResult.errors` (human-readable messages)

Security value:

- reduces injection-style payload risk
- improves reliability by standardizing accepted input shape
- makes validation failures explicit and actionable

## B. Rate Limiting (`RateLimiter`)

Implemented controls:

- per-identifier tracking (`user_id` or `session_id`)
- fixed window behavior using timestamp history
- configurable thresholds (`max_requests`, `window_seconds`)
- exceeded-limit feedback with retry hint

Returned result:

- `RateLimitResult.is_allowed`
- `RateLimitResult.error`
- `RateLimitResult.remaining_requests`
- `RateLimitResult.retry_after_seconds`

Security value:

- mitigates burst abuse and basic automated spam
- protects API quota and backend stability

## C. Content Filtering (`EthicalGuard`)

Implemented controls:

- regex pattern matching for harmful categories
- request blocking when any pattern matches
- flagged request logging for moderation review

Returned result:

- `ContentFilterResult.is_allowed`
- `ContentFilterResult.feedback`
- `ContentFilterResult.matched_patterns`

Security value:

- prevents clearly unsafe prompts from reaching the model
- supports operational review through logged flagged records

---

## 4) How to Use the Security Module

## Basic Usage

```python
from security import InputValidator, RateLimiter, EthicalGuard

limiter = RateLimiter(max_requests=10, window_seconds=60)
guard = EthicalGuard()

user_id = "session_123"
prompt = "Write a friendly greeting for students."

# 1) Rate limit check
rate = limiter.check_rate_limit(user_id)
if not rate.is_allowed:
    print(rate.error)
    raise SystemExit

# 2) Input validation/sanitization
validated = InputValidator.validate_and_sanitize_input(
    value=prompt,
    field_name="Prompt",
    min_length=3,
    max_length=1000,
    required=True
)
if not validated.is_valid:
    print(validated.errors)
    raise SystemExit

# 3) Ethical content filter
filtered = guard.filter_request(user_id, validated.sanitized_value)
if not filtered.is_allowed:
    print(filtered.feedback)
    raise SystemExit

# 4) Safe to call your LLM
safe_prompt = validated.sanitized_value
print("Send to model:", safe_prompt)
```

## Demo Script

Use the included demonstration:

```bash
python demo.py
```

`demo.py` shows:

- each class independently
- full pipeline behavior (safe prompt vs blocked prompt)
- environment loading from `.env` for LLM API settings

---

## 5) Limitations

1. **In-memory state only**
   - `RateLimiter` and `EthicalGuard` logs are process-local and reset on restart.

2. **Single-process assumptions**
   - current rate limiting does not synchronize across multiple servers/containers.

3. **Regex-based moderation**
   - `EthicalGuard` pattern matching is intentionally simple and may miss nuanced harmful intent or produce false positives.

4. **No persistence/audit backend**
   - flagged content is available in memory only (`get_flagged_content_log()`), not stored in a secure database.

5. **No authentication layer**
   - identifier trust depends on upstream logic (session/auth middleware should provide reliable IDs).

6. **Basic sanitization scope**
   - sanitization is useful for common risky patterns but not a complete defense against all injection techniques.

---

## Recommended Next Improvements

- move rate-limit counters to Redis for multi-instance support
- persist moderation logs to a secured datastore
- add richer policy checks (semantic moderation model + allow/deny rules)
- add role-based limits (different thresholds by user tier)
- add monitoring metrics and alerting for abuse trends

