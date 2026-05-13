from seasonal_vcaptcha.daemon import make_handler


class DummyRecognizer:
    pass


def _handler_class():
    return make_handler(
        recognizer=DummyRecognizer(),
        max_body_bytes=1024,
        max_concurrent_requests=1,
        metrics_enabled=False,
        metrics_path="/metrics",
    )


def test_unix_socket_access_logging_uses_local_for_empty_string_client_address():
    handler_cls = _handler_class()
    handler = object.__new__(handler_cls)
    handler.client_address = ""

    assert handler.address_string() == "local"


def test_tcp_access_logging_still_reports_peer_address():
    handler_cls = _handler_class()
    handler = object.__new__(handler_cls)
    handler.client_address = ("127.0.0.1", 12345)

    assert handler.address_string() == "127.0.0.1"
