from policy_binder.ratelimit import DemoLimiter, client_ip


class Clock:
    def __init__(self, now: float = 1_760_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_per_ip_limit_with_sliding_window() -> None:
    clock = Clock()
    limiter = DemoLimiter(per_ip=2, window_s=600, daily=100, clock=clock)
    assert limiter.check("1.1.1.1") is None
    assert limiter.check("1.1.1.1") is None
    refusal = limiter.check("1.1.1.1")
    assert refusal is not None and "réessayez dans 10 min" in refusal
    assert limiter.check("2.2.2.2") is None  # une autre adresse n'est pas concernée
    clock.now += 601  # la fenêtre a glissé
    assert limiter.check("1.1.1.1") is None


def test_daily_quota_is_global_and_resets_next_day() -> None:
    clock = Clock()
    limiter = DemoLimiter(per_ip=100, window_s=600, daily=2, clock=clock)
    assert limiter.check("a") is None
    assert limiter.check("b") is None
    refusal = limiter.check("c")
    assert refusal is not None and "Quota quotidien" in refusal
    clock.now += 24 * 3600
    assert limiter.check("c") is None


def test_refused_requests_do_not_consume_quota() -> None:
    limiter = DemoLimiter(per_ip=1, window_s=600, daily=2, clock=Clock())
    assert limiter.check("a") is None
    assert limiter.check("a") is not None  # refusée par IP : ne compte pas dans le quota
    assert limiter.check("b") is None


def test_client_ip_uses_last_forwarded_value() -> None:
    assert client_ip("6.6.6.6, 203.0.113.7", "10.0.0.1") == "203.0.113.7"
    assert client_ip(None, "10.0.0.1") == "10.0.0.1"
    assert client_ip("", None) == "inconnu"
