"""Synthetic value helpers.

Everything here is fake by construction, so the data can be committed, logged and
screenshotted without it being about a real person:

* SSNs use area numbers 900-999. The Social Security Administration never issues
  those, so none of them can belong to a real person.
* Card numbers pass the Luhn check (so they look real to a validator) but use
  test-style prefixes and random digits. They are not issued accounts.
* Phone numbers use the fictional 555-01xx range.
* Email addresses use example.com, which is reserved for documentation.
* Passwords and API keys are made-up strings. API keys start with FAKE- so they can
  never match a real provider's key format (GitHub blocks pushes that do).
"""

from __future__ import annotations

import random

SEASONS = ("Spring", "Summer", "Autumn", "Winter")
WEAK_WORDS = ("Password", "Welcome", "Letmein", "Qwerty", "Dragon", "Monkey", "Sunshine")


def luhn_check_digit(payload: str) -> str:
    """Check digit that makes payload + digit pass the Luhn check."""
    total = 0
    for i, ch in enumerate(reversed(payload)):
        d = int(ch)
        if i % 2 == 0:  # the rightmost payload digit is doubled
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def is_luhn_valid(number: str) -> bool:
    digits = number.replace(" ", "").replace("-", "")
    if not digits.isdigit() or len(digits) < 2:
        return False
    return luhn_check_digit(digits[:-1]) == digits[-1]


def ssn(rng: random.Random) -> str:
    """Social Security number in the never-issued 900-999 area range."""
    return f"{rng.randint(900, 999)}-{rng.randint(1, 99):02d}-{rng.randint(1, 9999):04d}"


def card_number(rng: random.Random) -> str:
    """16-digit Luhn-valid card number with a test-style prefix."""
    prefix = rng.choice(("400000", "555555"))
    body = prefix + "".join(str(rng.randint(0, 9)) for _ in range(9))
    return body + luhn_check_digit(body)


def card_expiry(rng: random.Random) -> str:
    return f"{rng.randint(1, 12):02d}/{rng.randint(27, 31)}"


def phone(rng: random.Random) -> str:
    """Fictional 555-01xx number."""
    return f"({rng.randint(201, 989)}) 555-{rng.randint(100, 199):04d}"


def email(first: str, last: str) -> str:
    clean = "".join(ch for ch in f"{first}.{last}".lower() if ch.isalnum() or ch == ".")
    return f"{clean}@example.com"


def password(rng: random.Random) -> str:
    """A weak, plausible password (the kind found in real credential dumps)."""
    style = rng.randint(0, 2)
    if style == 0:
        return f"{rng.choice(SEASONS)}{rng.randint(2019, 2026)}!"
    if style == 1:
        return f"{rng.choice(WEAK_WORDS)}{rng.randint(1, 999)}"
    return f"{rng.choice(WEAK_WORDS)}@{rng.randint(10, 99)}"


def api_key(rng: random.Random) -> str:
    """Made-up key that cannot match a real provider's format."""
    return "FAKE-KEY-" + "".join(rng.choice("0123456789abcdef") for _ in range(32))


def digits(rng: random.Random, n: int) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(n))
