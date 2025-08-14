
# AppMgr — College Applications Manager (Hackathon Starter)

**Stack:** Django + HTMX + Tailwind (CDN), SQLite. Optional OpenAI + IMAP.

## Features
- Dashboard of applications with inline status updates (HTMX).
- Store SOPs, LORs, resumes as text or files.
- SOP Assistant (OpenAI) to draft outlines.
- Email scanner (IMAP) to ingest notifications from Inbox/Junk/Spam.
- Priority field on programs for quick sorting.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://127.0.0.1:8000/

## Email scan (optional)
```bash
export APPMGR_IMAP_HOST=imap.example.com
export APPMGR_IMAP_USER=you@example.com
export APPMGR_IMAP_PASS=yourpassword
python manage.py scan_email
```

## OpenAI SOP Assistant (optional)
```bash
export OPENAI_API_KEY=sk-...
```

## Notes
- This is an MVP starter: no heavy auth flows beyond Django default, no celery. Use cron to run `scan_email` every 15 mins if needed.
- Extend models and templates as desired. Add filtering, tagging, and per-application document links.
- For production, switch to Postgres, configure static, and add proper secrets management.
