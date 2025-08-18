from __future__ import annotations

import logging
from typing import Any, Optional

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken


log = logging.getLogger("allauth.hook")


class LoggingSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter that logs detailed information during the social login/connect flow.

    Useful to diagnose why a SocialAccount/SocialToken is not being created.
    """

    def pre_social_login(self, request, sociallogin):
        try:
            acc = getattr(sociallogin, "account", None)
            tok = getattr(sociallogin, "token", None)
            extra = getattr(acc, "extra_data", {}) or {}

            log.debug(
                "pre_social_login: user=%r auth=%s provider=%s uid=%s",
                getattr(request, "user", None),
                bool(getattr(request, "user", None) and request.user.is_authenticated),
                getattr(acc, "provider", None),
                getattr(acc, "uid", None),
            )
            log.debug(
                "extra_data keys=%s email=%s",
                sorted(list(extra.keys())),
                extra.get("email"),
            )
            token_str: Optional[str] = getattr(tok, "token", None)
            if token_str:
                masked = (
                    (token_str[:6] + "…" + token_str[-6:])
                    if len(token_str) > 12
                    else "***"
                )
            else:
                masked = None
            log.debug("token_present=%s token_masked=%s", bool(token_str), masked)

            if getattr(request, "user", None) and request.user.is_authenticated:
                provider_id = None
                try:
                    provider_id = sociallogin.account.get_provider().id  # e.g. "google"
                except Exception:
                    provider_id = getattr(acc, "provider", None)

                log.debug(
                    "auto-connect: linking provider=%s uid=%s to user=%r",
                    provider_id,
                    getattr(acc, "uid", None),
                    request.user,
                )
                try:
                    sociallogin.connect(request, request.user)
                    log.debug("auto-connect: success")
                    try:
                        account, _ = SocialAccount.objects.get_or_create(
                            user=request.user,
                            provider=provider_id or "google",
                            uid=getattr(acc, "uid", ""),
                            defaults={"extra_data": getattr(acc, "extra_data", {})},
                        )
                        app = SocialApp.objects.filter(
                            provider=provider_id or "google"
                        ).first()
                        if not app:
                            log.warning(
                                "auto-connect: no SocialApp found for provider=%s",
                                provider_id,
                            )
                            return
                        if tok:
                            st, _ = SocialToken.objects.get_or_create(
                                app=app,
                                account=account,
                                defaults={"token": tok.token},
                            )
                            updated = False
                            if tok.token and st.token != tok.token:
                                st.token = tok.token
                                updated = True
                            rt = getattr(tok, "token_secret", None)
                            if rt and st.token_secret != rt:
                                st.token_secret = rt
                                updated = True
                            ea = getattr(tok, "expires_at", None)
                            if ea and st.expires_at != ea:
                                st.expires_at = ea
                                updated = True
                            if updated:
                                st.save()
                            log.debug("auto-connect: token ensured (exists=%s)", True)
                    except Exception:
                        log.exception("auto-connect: ensure token failed")
                except Exception as e:
                    log.exception("auto-connect: failed: %s", e)

                try:
                    all_accs = list(
                        SocialAccount.objects.filter(user=request.user).order_by("-id")
                    )
                    by_uid = {}
                    to_delete = []
                    for a in all_accs:
                        if a.uid in by_uid:
                            to_delete.append(a)
                        else:
                            by_uid[a.uid] = a
                    if to_delete:
                        SocialToken.objects.filter(account__in=to_delete).delete()
                        SocialAccount.objects.filter(
                            id__in=[a.id for a in to_delete]
                        ).delete()
                        log.debug(
                            "auto-connect: dedup removed %d older social accounts (by uid)",
                            len(to_delete),
                        )
                except Exception:
                    log.exception("auto-connect: dedup failed")
        except Exception:
            log.exception("pre_social_login: exception while logging context")

        return super().pre_social_login(request, sociallogin)

    def authentication_error(
        self,
        request,
        provider_id: str,
        error: Optional[str] = None,
        exception: Optional[BaseException] = None,
        extra_context: Optional[dict[str, Any]] = None,
    ) -> None:
        log.error(
            "authentication_error provider=%s error=%r exception=%r extra=%r",
            provider_id,
            error,
            exception,
            extra_context,
        )
        return super().authentication_error(
            request, provider_id, error, exception, extra_context
        )
