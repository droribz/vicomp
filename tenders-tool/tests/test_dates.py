from datetime import date

from infra_tenders.core.dates import is_expired, parse_hebrew_date


def test_numeric_formats():
    assert parse_hebrew_date("30/12/2026") == date(2026, 12, 30)
    assert parse_hebrew_date("01.01.2025") == date(2025, 1, 1)
    assert parse_hebrew_date("5-3-2025") == date(2025, 3, 5)


def test_two_digit_year():
    assert parse_hebrew_date("30/12/26") == date(2026, 12, 30)


def test_hebrew_month_text():
    assert parse_hebrew_date("15 ביולי 2026") == date(2026, 7, 15)
    assert parse_hebrew_date("1 בינואר 2025") == date(2025, 1, 1)


def test_embedded_in_sentence():
    assert parse_hebrew_date("מועד הגשה אחרון: 20/11/2026 בשעה 12:00") == date(2026, 11, 20)


def test_unparseable_returns_none():
    assert parse_hebrew_date("בקרוב") is None
    assert parse_hebrew_date("") is None
    assert parse_hebrew_date(None) is None


def test_is_expired():
    run_day = date(2026, 6, 2)
    assert is_expired(date(2020, 1, 1), run_day=run_day) is True
    assert is_expired(date(2026, 12, 30), run_day=run_day) is False
    # מכרז ללא מועד מוכר — לא נחשב פג (נשמר לבדיקה).
    assert is_expired(None, run_day=run_day) is False
