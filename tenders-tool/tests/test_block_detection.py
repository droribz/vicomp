"""בדיקות לזיהוי חסימת בוט — מוודאות שאין התרעות שווא על reCAPTCHA אקראי."""
from infra_tenders.adapters.generic import _detect_block


def test_normal_page_with_recaptcha_form_not_blocked():
    # עמוד מכרזים תקין שבמקרה מכיל reCAPTCHA בטופס "צור קשר" — לא חסום!
    html = """<html><body><h1>מכרזים</h1>
      <table><tr><td>מכרז 12/2025</td></tr></table>
      <form class="contact"><div class="g-recaptcha" data-sitekey="abc"></div>
      <script src="https://www.google.com/recaptcha/api.js"></script></form>
      </body></html>""" * 5
    blocked, _ = _detect_block(html, 200, "מכרזים - נתיבי ישראל")
    assert blocked is False


def test_cloudflare_challenge_is_blocked():
    html = "<html><head><title>Just a moment...</title></head><body>" \
           "Checking your browser before accessing.</body></html>"
    blocked, why = _detect_block(html, 403, "Just a moment...")
    assert blocked is True
    assert "just a moment" in why.lower() or "חסימה" in why


def test_access_denied_is_blocked():
    html = "<html><body>Access to this page has been denied.</body></html>"
    blocked, _ = _detect_block(html, 403, "")
    assert blocked is True


def test_short_403_is_blocked():
    blocked, _ = _detect_block("<html><body>Forbidden</body></html>", 403, "")
    assert blocked is True


def test_long_normal_200_not_blocked():
    blocked, _ = _detect_block("<html>" + "x" * 8000 + "</html>", 200, "מכרזים")
    assert blocked is False
