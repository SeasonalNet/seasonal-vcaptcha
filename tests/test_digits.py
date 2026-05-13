from seasonal_vcaptcha.digits import grammar_from_phrases, words_to_digits


def test_words_to_digits_maps_digit_words_and_oh():
    assert words_to_digits("one oh zero nine") == "1009"


def test_words_to_digits_keeps_numeric_tokens_only():
    assert words_to_digits("captcha 1 two nope 3") == "123"


def test_words_to_digits_honors_max_digits():
    assert words_to_digits("one two three four", max_digits=3) == "123"


def test_grammar_from_phrases_is_compact_json():
    assert grammar_from_phrases(["one", "two"]) == '["one","two"]'
