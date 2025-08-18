# mailwatch/utils.py
from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from dateutil import parser as dateparse
from django.utils import timezone

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken

log = logging.getLogger(__name__)

PROVIDER_GOOGLE = "google"
PROVIDER_MICROSOFT = "microsoft"


@dataclass
class InboxMessage:
    provider: str  # "gmail" | "outlook"
    id: str  # provider message id
    internet_message_id: Optional[str]  # Message-ID if available
    subject: str
    sender: str  # display or email
    snippet: str  # teaser text
    sent_at: dt.datetime  # timezone-aware UTC


def _get_social(user, provider: str) -> Tuple[SocialAccount, SocialApp, SocialToken]:
    """
    Return (account, app, token) for the user's connected provider.
    Raises DoesNotExist if not connected.
    """
    account = SocialAccount.objects.get(user=user, provider=provider)
    app = SocialApp.objects.get(provider=provider)
    token = SocialToken.objects.get(account=account, app=app)
    return account, app, token


def _is_expired(token: SocialToken) -> bool:
    if not token.expires_at:
        return False
    return timezone.now() + dt.timedelta(seconds=30) >= token.expires_at


def _update_token(
    token: SocialToken, access_token: str, expires_in: Optional[int]
) -> None:
    token.token = access_token
    if expires_in:
        token.expires_at = timezone.now() + dt.timedelta(seconds=int(expires_in))
    token.save(update_fields=["token", "expires_at"])


def _refresh_google(app: SocialApp, token: SocialToken) -> None:
    """
    Refresh Google OAuth2 access token using the refresh token.

    NOTE: django-allauth stores the refresh token in token.token_secret by convention.
    If you’ve customized storage, adjust accordingly.
    """
    refresh_token = token.token_secret or (token.token and "")
    if not refresh_token:
        raise RuntimeError(
            "Google refresh_token missing on SocialToken (token_secret)."
        )

    data = {
        "client_id": app.client_id,
        "client_secret": app.secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    resp = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Google refresh failed: {resp.status_code} {resp.text}")

    payload = resp.json()
    _update_token(token, payload["access_token"], payload.get("expires_in"))


def _refresh_microsoft(app: SocialApp, token: SocialToken) -> None:
    """
    Refresh Microsoft (Outlook/Office 365) OAuth2 access token using the refresh token.

    NOTE: as above, refresh_token expected in token.token_secret by convention.
    """
    refresh_token = token.token_secret or (token.token and "")
    if not refresh_token:
        raise RuntimeError(
            "Microsoft refresh_token missing on SocialToken (token_secret)."
        )

    data = {
        "client_id": app.client_id,
        "client_secret": app.secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "offline_access https://graph.microsoft.com/Mail.Read",
        "redirect_uri": app.redirect_uris.splitlines()[0] if app.redirect_uris else "",
    }
    resp = requests.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        data=data,
        timeout=20,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Microsoft refresh failed: {resp.status_code} {resp.text}")

    payload = resp.json()
    _update_token(token, payload["access_token"], payload.get("expires_in"))


def get_access_token(user, provider: str) -> str:
    """
    Return a valid (refreshed if needed) access token for the user + provider.
    """
    account, app, token = _get_social(user, provider)

    if _is_expired(token):
        log.info("Access token expired for %s — refreshing…", provider)
        if provider == PROVIDER_GOOGLE:
            _refresh_google(app, token)
        elif provider == PROVIDER_MICROSOFT:
            _refresh_microsoft(app, token)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    return token.token


def gmail_search_messages(
    access_token: str, query: str, max_results: int = 10
) -> List[str]:
    """Return list of Gmail message IDs for a query."""
    params = {"q": query, "maxResults": max(1, min(max_results, 50))}
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        params=params,
        headers=headers,
        timeout=20,
    )
    if r.status_code == 401:
        raise RuntimeError("Gmail auth failed (401).")
    if r.status_code != 200:
        raise RuntimeError(f"Gmail list error: {r.status_code} {r.text}")

    data = r.json()
    ids = [m["id"] for m in data.get("messages", [])]
    return ids


def gmail_get_message(access_token: str, msg_id: str) -> InboxMessage:
    """Fetch metadata for a single Gmail message ID."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "format": "metadata",
        "metadataHeaders": ["Subject", "From", "Date", "Message-ID"],
    }
    r = requests.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
        headers=headers,
        params=params,
        timeout=20,
    )
    r.raise_for_status()
    payload = r.json()

    headers_list = payload.get("payload", {}).get("headers", [])
    hdr = {h["name"].lower(): h["value"] for h in headers_list}
    subject = hdr.get("subject", "(no subject)")
    from_ = hdr.get("from", "")
    date_raw = hdr.get("date", "")
    msgid = hdr.get("message-id")  # may be like "<xyz@domain>"
    sent_at = (
        dateparse.parse(date_raw).astimezone(timezone.utc)
        if date_raw
        else timezone.now()
    )

    snippet = payload.get("snippet", "")
    return InboxMessage(
        provider="gmail",
        id=payload["id"],
        internet_message_id=msgid,
        subject=subject,
        sender=from_,
        snippet=snippet,
        sent_at=sent_at,
    )


def graph_list_recent(access_token: str, top: int = 25) -> List[Dict]:
    """
    Return a list of recent messages (lightweight projection).
    We use $select to keep it small and $orderby desc by receivedDateTime.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "$top": max(1, min(top, 50)),
        "$select": "id,subject,from,receivedDateTime,internetMessageId,bodyPreview",
        "$orderby": "receivedDateTime desc",
    }
    r = requests.get(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers=headers,
        params=params,
        timeout=20,
    )
    if r.status_code == 401:
        raise RuntimeError("Graph auth failed (401).")
    if r.status_code != 200:
        raise RuntimeError(f"Graph list error: {r.status_code} {r.text}")
    return r.json().get("value", [])


def graph_to_inbox_message(raw: Dict) -> InboxMessage:
    subject = raw.get("subject") or "(no subject)"
    sender = (raw.get("from", {}) or {}).get("emailAddress", {}).get(
        "address", ""
    ) or ""
    preview = raw.get("bodyPreview", "") or ""
    msgid = raw.get("internetMessageId")
    dt_raw = raw.get("receivedDateTime")
    sent_at = (
        dateparse.parse(dt_raw).astimezone(timezone.utc) if dt_raw else timezone.now()
    )
    return InboxMessage(
        provider="outlook",
        id=raw["id"],
        internet_message_id=msgid,
        subject=subject,
        sender=sender,
        snippet=preview,
        sent_at=sent_at,
    )


def likely_matches(subject: str, sender: str, keywords: Iterable[str]) -> bool:
    """
    Very simple heuristic: if any keyword appears in subject or sender (case-insensitive).
    """
    subj = subject.lower()
    snd = sender.lower()
    for kw in keywords:
        k = (kw or "").lower().strip()
        if k and (k in subj or k in snd):
            return True
    return False


def create_social_token(account):
    token = SocialToken.objects.create(
        app=SocialApp.objects.get(provider=account.provider),
        account=account,
        token=account.extra_data["access_token"],
    )
    return token
