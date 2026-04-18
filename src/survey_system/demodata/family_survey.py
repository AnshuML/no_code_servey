"""Default Hindi family survey JSON (same as legacy Streamlit demo)."""

from __future__ import annotations

from typing import Any

FAMILY_SURVEY_PAYLOAD: dict[str, Any] = {
    "schema_version": "1.0",
    "id": "family_survey_hindi",
    "title": "Parivar / Family survey",
    "questions": [
        {
            "id": "total_members",
            "text": (
                "Aapki family mein kul kitne log hain? "
                "(Khud ko bhi giniye — number bataiye.)"
            ),
            "type": "number",
            "required": True,
            "min_value": 1,
            "max_value": 30,
        },
        {
            "id": "monthly_income_inr",
            "text": (
                "Ghar ki kul monthly income lagbhag kitni hai? "
                "Sirf number bataiye (₹ — Indian Rupees)."
            ),
            "type": "number",
            "required": True,
            "min_value": 0,
            "max_value": 100000000,
        },
        {
            "id": "father_name",
            "text": "Pita ji (father) ka poora naam kya hai?",
            "type": "free_text",
            "required": True,
        },
        {
            "id": "father_occupation",
            "text": "Pita ji kya kaam karte hain? (naukri, business, kheti, retired, etc.)",
            "type": "free_text",
            "required": True,
        },
        {
            "id": "mother_name",
            "text": "Mata ji (mother) ka poora naam kya hai?",
            "type": "free_text",
            "required": True,
        },
        {
            "id": "mother_occupation",
            "text": "Mata ji kya karti hain? (naukri, ghar sambhalna, business, etc.)",
            "type": "free_text",
            "required": True,
        },
        {
            "id": "members_detail",
            "text": (
                "Har family member ke baare mein likhiye: naam, ladka hai ya ladki, "
                "aur wo kya karte hain (padhai, kaam, chhota bachcha, etc.). "
                "Ek line mein ek member — jitne members bataye, sab cover karein."
            ),
            "type": "free_text",
            "required": True,
        },
        {
            "id": "consent",
            "text": (
                "Kya aap ye parivar survey poora karne ke liye sahmat hain "
                "aur jo jawab diye hain wo sahi maan sakte hain?"
            ),
            "type": "yes_no",
            "required": True,
        },
    ],
}
