from allauth.socialaccount.models import SocialAccount, SocialToken
import logging

logger = logging.getLogger(__name__)


def gmail_connection_status(request):
    """
    Add has_gmail_connected to all template contexts.
    This matches the logic used in the dashboard view.
    """
    logger.info(f"Context processor running for user: {request.user}")

    if request.user.is_authenticated:
        social_accounts = SocialAccount.objects.filter(
            user=request.user, provider="google"
        )
        has_account = social_accounts.exists()
        logger.info(
            f"User {request.user.username} has Google SocialAccount: {has_account}"
        )

        social_tokens = SocialToken.objects.filter(
            account__user=request.user, account__provider="google"
        )
        has_token = social_tokens.exists()
        logger.info(f"User {request.user.username} has Google SocialToken: {has_token}")

        has_gmail_connected = has_account and has_token
        logger.info(
            f"User {request.user.username} has_gmail_connected: {has_gmail_connected}"
        )
    else:
        has_gmail_connected = False
        logger.info("User not authenticated, has_gmail_connected: False")

    return {"has_gmail_connected": has_gmail_connected}
