import logging
from datetime import datetime, timedelta

from django.conf import settings
from django_q.tasks import async_task

from notifications.email.invites import send_invited_email, send_invite_confirmation
from users.models.user import User
import json

log = logging.getLogger(__name__)

IS_TEST_STRIPE = settings.STRIPE_API_KEY.startswith("sk_test")


def club_subscription_activator(product, payment, user):
    now = datetime.utcnow()
    if user.membership_expires_at < now:
        user.membership_expires_at = now  # ignore days in the past

    user.membership_expires_at += product["data"]["timedelta"]
    log.info(f"club_subscription_activator product:{product}, payment:{payment}, user:{user}")

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
        "stripe_id": "price_1Jaj3gFjSIV8F3exf5DYerTE" if not IS_TEST_STRIPE else "price_1Jaj3gFjSIV8F3exf5DYerTE",
        "description": "Год членства в Клубе",
        "amount": 150,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },

    },
    "club1_recurrent_yearly": {
        "code": "club1_recurrent_yearly",
        "stripe_id": "price_1JaOMiFjSIV8F3exYG91oWCl" if not IS_TEST_STRIPE else "price_1JaOMiFjSIV8F3exYG91oWCl",
        "description": "Год членства в Клубе (автопополнение каждый год)",
        "amount": 150,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
    "club1_recurrent_monthly": {
        "code": "club1_recurrent_monthly",
        "stripe_id": "price_1Jaj3TFjSIV8F3exmrekbznT" if not IS_TEST_STRIPE else "price_1Jaj3TFjSIV8F3exmrekbznT",
        "description": "Год членства в Клубе (автопополнение каждый месяц)",
        "amount": 150,
        "recurrent": "monthly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },
    "club3": {
        "code": "club3",
        "stripe_id": "price_1JajDMFjSIV8F3ex8Ktr4E5K" if not IS_TEST_STRIPE else "price_1JajDMFjSIV8F3ex8Ktr4E5K",
        "description": "Членство в Клубе на 3 года",
        "amount": 350,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club3_recurrent_yearly": {
        "code": "club3_recurrent_yearly",
        "stripe_id": "price_1JajDMFjSIV8F3exqr4SwiPo" if not IS_TEST_STRIPE else "price_1JajDMFjSIV8F3exqr4SwiPo",
        "description": "+3 года членства в Клубе (автопополнение каждый год)",
        "amount": 40,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club3_recurrent_monthly": {
        "code": "club3_recurrent_monthly",
        "stripe_id": "price_1JajDMFjSIV8F3exREJebrqX" if not IS_TEST_STRIPE else "price_1JajDMFjSIV8F3exREJebrqX",
        "description": "+3 года членства в Клубе (автопополнение каждый месяц)",
        "amount": 40,
        "recurrent": "monthly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 3),
        },
    },
    "club50": {
        "code": "club50",
        "stripe_id": "price_1JajFlFjSIV8F3ex8FQCdzlq" if not IS_TEST_STRIPE else "price_1JajFlFjSIV8F3ex8FQCdzlq",
        "description": "Членство в Клубе на 5 лет",
        "amount": 1000,
        "recurrent": False,
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 5),
        },
    },
    "club50_recurrent_yearly": {
        "code": "club50_recurrent_yearly",
        "stripe_id": "price_1JajFmFjSIV8F3ex9DlFNhW3" if not IS_TEST_STRIPE else "price_1JajFmFjSIV8F3ex9DlFNhW3",
        "description": "Членство в Клубе на 50 лет (автопополнение каждый год)",
        "amount": 1000,
        "recurrent": "yearly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 5),
        },
    },
    "club50_recurrent_monthly": {
        "code": "club50_recurrent_monthly",
        "stripe_id": "price_1JajFmFjSIV8F3exhnDlEgIn" if not IS_TEST_STRIPE else "price_1JajFmFjSIV8F3exhnDlEgIn",
        "description": "Членство в Клубе на 5 лет (автопополнение каждый месяц)",
        "amount": 1000,
        "recurrent": "monthly",
        "activator": club_subscription_activator,
        "data": {
            "timedelta": timedelta(days=365 * 5),
        },
    },
    "club1_invite": {
        "code": "club1_invite",
        "stripe_id": "price_1IXA3fKgJMaF2rHtq37jPrym" if not IS_TEST_STRIPE else "price_1IX9QuKgJMaF2rHtJnrSs0Ud",
        "description": "Пригласить друга в Клуб",
        "amount": 15,
        "recurrent": False,
        "activator": club_invite_activator,
        "data": {
            "timedelta": timedelta(days=365),
        },
    },

}

TAX_RATE_VAT = "txr_1I82AfKgJMaF2rHtoUStb1cL" if not IS_TEST_STRIPE else None


def find_by_price_id(price_id):
    for product in PRODUCTS.values():
        if product["stripe_id"] == price_id:
            return product
    log.error(f"Can't find the product: {price_id}")
    return None
