from ai_gateway.services.webhooks import hmac_sha256_signature


def test_hmac_sha256_signature() -> None:
    secret = "s3cr3t"
    body = b'{"ok":true}'
    sig = hmac_sha256_signature(secret, body)
    assert sig.startswith("sha256=")
    # Stable value for the test vector above.
    assert sig == "sha256=629c5b4f3ca50d22a893a236367a715cf8148cbf7a749829c7d2eaf89ea74039"
