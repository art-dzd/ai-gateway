from ai_gateway.services.redaction import redact_chat_payload


def test_redact_chat_payload_hides_content() -> None:
    payload = {
        "model": "gpt-test",
        "messages": [
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "my secret is 123"},
        ],
    }
    red = redact_chat_payload(payload)
    assert red["messages"][0]["content"] == "<redacted>"
    assert red["messages"][1]["content"] == "<redacted>"
    assert red["messages"][1]["content_len"] == len("my secret is 123")
    assert "content_sha256" in red["messages"][1]

