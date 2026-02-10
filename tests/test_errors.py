import httpx

from ai_gateway.services.errors import map_provider_exception


def test_map_provider_exception_unknown_provider() -> None:
    err = map_provider_exception(ValueError("Unknown provider: nope"))
    assert err.status_code == 400
    assert err.code == "unknown_provider"
    assert err.type == "invalid_request_error"


def test_map_provider_exception_timeout() -> None:
    err = map_provider_exception(httpx.TimeoutException("timeout"))
    assert err.status_code == 502
    assert err.code == "upstream_timeout"
    assert err.type == "upstream_error"

