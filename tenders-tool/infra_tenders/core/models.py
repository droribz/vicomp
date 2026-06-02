"""מודלי הנתונים האחידים שכל המתאמים מחזירים והליבה צורכת."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TenderStatus(str, Enum):
    """סטטוס זמינות הקבצים של המכרז."""

    FREE = "free"        # כל החומר חינמי והורד
    PAID = "paid"        # חוברת המכרז בתשלום — לא הורד
    PARTIAL = "partial"  # חלק חינמי הורד, חלק בתשלום


class MatchConfidence(str, Enum):
    HIGH = "high"
    LOW = "low"


class TenderFile(BaseModel):
    """קובץ בודד המצורף למכרז."""

    url: str
    # שם הקובץ כפי שיישמר בדיסק (מנורמל). אם None — ייגזר מה-URL/כותרת.
    filename: Optional[str] = None
    # תיאור חופשי מעמוד המכרז (חוברת / מפרט / כתב כמויות / נספח / הסכם / תוכנית)
    label: Optional[str] = None


class Tender(BaseModel):
    """מכרז יחיד כפי שמתאם מחזיר אותו.

    כל השדות מגיעים מעמוד הרשימה/המכרז בלבד — לא מפענוח תוכן ה-PDF.
    """

    # --- זיהוי ---
    source: str                       # מזהה המתאם, למשל "iroads"
    publisher: str                    # שם המפרסם בעברית
    tender_number: Optional[str] = None
    title: str

    # --- תאריכים ---
    submission_deadline: Optional[date] = None  # מועד הגשה אחרון
    publication_date: Optional[date] = None

    # --- קישורים ---
    source_url: str                   # קישור לעמוד המכרז במקור
    files: list[TenderFile] = Field(default_factory=list)

    # --- סיווג (ממולא ע"י מנוע הפילטור) ---
    status: TenderStatus = TenderStatus.FREE
    match_confidence: MatchConfidence = MatchConfidence.HIGH

    # רשימת כל המקורות בהם הופיע המכרז (לאחר איחוד כפילויות)
    sources: list[str] = Field(default_factory=list)

    def identity_key(self) -> str:
        """מפתח זיהוי לאיחוד כפילויות ולאידמפוטנטיות.

        ראשי = מפרסם + מספר מכרז.
        גיבוי (כשאין מספר) = מפרסם + כותרת מנורמלת + מועד הגשה.
        """
        pub = _normalize(self.publisher)
        if self.tender_number and self.tender_number.strip():
            return f"{pub}|{_normalize(self.tender_number)}"
        deadline = self.submission_deadline.isoformat() if self.submission_deadline else "no-date"
        return f"{pub}|{_normalize(self.title)}|{deadline}"


class ScanResult(BaseModel):
    """תוצאת סריקה של מקור בודד — לסיכום בלוג ובטרמינל."""

    source: str
    publisher: str
    found: int = 0          # נמצאו (לאחר פילטור תשתיות)
    downloaded: int = 0     # מכרזים שהורדו (חדשים/עודכנו)
    skipped: int = 0        # דולגו (כבר קיימים, ללא שינוי)
    failed: int = 0         # נכשלו בהורדה
    blocked: bool = False   # נחסם (CAPTCHA / בוט / login ללא פרטים)
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)


def _normalize(text: str) -> str:
    """נרמול טקסט לצורך השוואה: רווחים מרובים, רישיות, גרשיים."""
    if not text:
        return ""
    text = text.replace("׳", "'").replace("״", '"')  # גרש/גרשיים עבריים
    text = " ".join(text.split())
    return text.strip().lower()
