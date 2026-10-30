"""Toʻlov mantigʻi.

Hozir faqat "mock" provayder ishlaydi: u haqiqiy pul olmaydi va faqat sinov uchun.
Click yoki Payme ulash uchun ular bilan merchant shartnomasi, merchant ID va maxfiy kalit
kerak. Ularning rasmiy hujjatlari boʻyicha `ClickProvider` / `PaymeProvider` yoziladi va
webhook ichida `mark_paid()` chaqiriladi — qolgan mantiq (Premiumni yoqish) tayyor.
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from .config import settings
from .models import Payment, Plan, User, utcnow


def create_payment(db: Session, user: User, plan: Plan) -> Payment:
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        amount_uzs=plan.price_uzs,
        provider=settings.payment_provider,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def checkout_url(payment: Payment) -> str | None:
    if payment.provider == "mock":
        return f"{settings.public_base_url}/api/payments/mock/{payment.id}/pay"
    # click / payme: provayderning toʻlov sahifasi manzili shu yerda yasaladi
    return None


def mark_paid(db: Session, payment: Payment, external_id: str | None = None) -> Payment:
    """Toʻlovni toʻlangan deb belgilaydi va foydalanuvchi Premiumini uzaytiradi.

    Bir xil toʻlov ikki marta kelsa (webhook takrorlansa), Premium ikki marta qoʻshilmaydi.
    """
    if payment.status == "paid":
        return payment
    if payment.status != "pending":
        raise ValueError("Bu toʻlovni yakunlab boʻlmaydi")

    now = utcnow()
    user = payment.user
    start = now
    if user.premium_until is not None:
        current = user.premium_until
        if current.tzinfo is None:
            current = current.replace(tzinfo=now.tzinfo)
        if current > now:
            start = current
    user.premium_until = start + timedelta(days=payment.plan.days)

    payment.status = "paid"
    payment.paid_at = now
    if external_id:
        payment.external_id = external_id
    db.commit()
    db.refresh(payment)
    return payment
