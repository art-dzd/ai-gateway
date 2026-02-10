from ai_gateway.auth.apikey import _parse_api_key


def test_parse_api_key_legacy() -> None:
    key_id, secret = _parse_api_key("legacy-token")
    assert key_id is None
    assert secret == "legacy-token"


def test_parse_api_key_new_format_with_prefix() -> None:
    key_id, secret = _parse_api_key("agw_abc123.supersecret")
    assert key_id == "abc123"
    assert secret == "supersecret"


def test_parse_api_key_new_format_without_prefix() -> None:
    key_id, secret = _parse_api_key("abc123.supersecret")
    assert key_id == "abc123"
    assert secret == "supersecret"


def test_parse_api_key_invalid_dot_forms_fallback_to_legacy() -> None:
    # Пустая часть слева/справа от точки: считаем это legacy, чтобы не ломать клиентов.
    assert _parse_api_key(".secret") == (None, ".secret")
    assert _parse_api_key("id.") == (None, "id.")
    assert _parse_api_key("agw_.secret") == (None, "agw_.secret")

