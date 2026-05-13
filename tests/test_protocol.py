from seasonal_vcaptcha.protocol import RecognizeRequest, RecognizeResponse, error_response, ok_response


def test_request_round_trips_json():
    request = RecognizeRequest(path="/tmp/a.wav")
    assert RecognizeRequest.from_json(request.to_json_bytes()).path == "/tmp/a.wav"


def test_ok_response_round_trips_json():
    response = ok_response(
        digits="1234",
        text="one two three four",
        duration_ms=42,
        audio_duration_ms=1000,
        converted=True,
        source="daemon",
    )
    decoded = RecognizeResponse.from_json(response.to_json())
    assert decoded.ok is True
    assert decoded.digits == "1234"
    assert decoded.converted is True


def test_error_response_uses_structured_error():
    response = RecognizeResponse.from_json(error_response("bad", "nope").to_json())
    assert response.ok is False
    assert response.error_code == "bad"
    assert response.error_message == "nope"
