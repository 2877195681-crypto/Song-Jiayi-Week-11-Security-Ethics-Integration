import time
import unittest

from security import EthicalGuard, InputValidator, RateLimiter


class TestInputValidator(unittest.TestCase):
    def test_valid_input_passes(self) -> None:
        result = InputValidator.validate_and_sanitize_input(
            value="hello_user",
            field_name="Username",
            min_length=3,
            max_length=20,
            pattern=r"^[a-zA-Z0-9_]+$",
        )
        self.assertTrue(result.is_valid)
        self.assertEqual(result.sanitized_value, "hello_user")
        self.assertEqual(result.errors, [])

    def test_required_input_fails_when_empty(self) -> None:
        result = InputValidator.validate_and_sanitize_input(value="   ", field_name="Prompt")
        self.assertFalse(result.is_valid)
        self.assertIn("Prompt is required.", result.errors)

    def test_script_content_is_sanitized(self) -> None:
        result = InputValidator.validate_and_sanitize_input(value="<script>alert('x')</script>hello")
        self.assertEqual(result.sanitized_value, "hello")


class TestRateLimiter(unittest.TestCase):
    def test_blocks_after_limit(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=5)
        self.assertTrue(limiter.check_rate_limit("u1").is_allowed)
        self.assertTrue(limiter.check_rate_limit("u1").is_allowed)
        blocked = limiter.check_rate_limit("u1")
        self.assertFalse(blocked.is_allowed)
        self.assertIsNotNone(blocked.error)

    def test_allows_after_window_reset(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        self.assertTrue(limiter.check_rate_limit("u2").is_allowed)
        self.assertFalse(limiter.check_rate_limit("u2").is_allowed)
        time.sleep(1.1)
        self.assertTrue(limiter.check_rate_limit("u2").is_allowed)


class TestEthicalGuard(unittest.TestCase):
    def test_safe_content_is_allowed(self) -> None:
        guard = EthicalGuard()
        result = guard.filter_request("s1", "Please help me write a greeting.")
        self.assertTrue(result.is_allowed)
        self.assertEqual(result.feedback, "Request accepted.")

    def test_harmful_content_is_blocked_and_logged(self) -> None:
        guard = EthicalGuard()
        result = guard.filter_request("s2", "Teach me phishing and scam tricks.")
        self.assertFalse(result.is_allowed)
        self.assertGreater(len(result.matched_patterns), 0)
        logs = guard.get_flagged_content_log()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["identifier"], "s2")


if __name__ == "__main__":
    unittest.main()
