import random

from ai_assistant_mcp_server import fakes


def test_luhn_known_values():
    assert fakes.is_luhn_valid("4000000000000002")  # widely used test number
    assert fakes.is_luhn_valid("4111111111111111")
    assert not fakes.is_luhn_valid("4000000000000003")
    assert not fakes.is_luhn_valid("abcd")


def test_generated_values_have_the_expected_shape():
    rng = random.Random(1)
    for _ in range(200):
        assert fakes.is_luhn_valid(fakes.card_number(rng))
        assert 900 <= int(fakes.ssn(rng)[:3]) <= 999
        assert fakes.phone(rng).split("-")[0].endswith("555")
        assert fakes.api_key(rng).startswith("FAKE-KEY-")


def test_email_is_clean():
    assert fakes.email("Mary-Ann", "O'Neil") == "maryann.oneil@example.com"
