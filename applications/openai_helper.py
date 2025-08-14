import os
from typing import Optional


def generate_sop_outline(profile: str, program: str, constraints: str = "") -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    prompt = f"""You are an expert admissions editor.
    Draft a bullet-point outline for an SOP.
    Applicant profile: {profile}
    Target program: {program}
    Constraints/preferences: {constraints}
    Structure as: hook, motivation, background, projects, research/industry, fit with program, goals, closing.
    Keep it concise and skimmable.
    """
    if not api_key:
        return (
            "[SOP OUTLINE - DEMO]\n"
            "• Hook: A 2–3 sentence opening tying a defining moment to the program.\n"
            "• Motivation: Why this field matters personally and practically.\n"
            "• Background: Key academics (top 3).\n"
            "• Projects: 2–3 bullets with outcomes/metrics.\n"
            "• Experience: Relevant internships/work.\n"
            "• Program Fit: 2 faculty/labs, 1–2 courses.\n"
            "• Goals: Short-term role, long-term impact.\n"
            "• Closing: Confidence + gratitude.\n"
        )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.responses.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise, structured admissions editor.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return resp.output_text.strip()
    except Exception as e:
        return f"[OpenAI error: {e}]"
