import logging
from datetime import datetime, timedelta

from django.conf import settings
from django_q.tasks import async_task

from notifications.email.invites import send_invited_email, send_invite_confirmation
from users.models.user import User

log = logging.getLogger(__name__)

IS_TEST_STRIPE = settings.STRIPE_API_KEY.startswith("sk_test")


def club_subscription_activator(product, payment, user):
    now = datetime.utcnow()
    if user.membership_expires_at < now:
        user.membership_expires_at = now  # ignore days in the past

    user.membership_expires_at += product["data"]["timedelta"]
    user.membership_platform_type = User.MEMBERSHIP_PLATFORM_DIRECT
    user.membership_platform_data = {
        "reference": payment.reference,
        "recurrent": product.get("recurrent"),
    }
    user.save()

    return True


def club_invite_activator(product, payment, user):
    friend_email = payment.invited_user_email()
    if not friend_email:
        log.error(f"Friend email not set in payment: {payment.id}")
        return club_subscription_activator(product, payment, user)

    friend = User.objects.filter(email=friend_email).first()
    if not friend:
        log.error(f"Friend not found: {friend_email}")
        return club_subscription_activator(product, payment, user)

    async_task(send_invited_email, user, friend)
    async_task(send_invite_confirmation, user, friend)

    return club_subscription_activator(product, payment, friend)


PRODUCTS = {
    "club1": {
        "code": "club1",
        "stripe_id": "price_1ITtayFjSIV8F3exPpJ1M9V8" if not IS_TEST_STRIPE else "price_1ITtayFjSIV8F3exPpJ1M9V8",
        "description": "Год членства в Клубе",
        "amount": 130,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    }
}

TAX_RATE_VAT = "txr_1I82AfKgJMaF2rHtoUStb1cL" if not IS_TEST_STRIPE else None


def find_by_price_id(price_id):
    for product in PRODUCTS.values():
        if product["stripe_id"] == price_id:
            return product
    log.error(f"Can't find the product: {price_id}")
    return None
