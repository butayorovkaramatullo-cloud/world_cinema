from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Payment, Plan, User
from ..payments import checkout_url, create_payment, mark_paid
from ..schemas import CheckoutIn, CheckoutOut, PlanOut

router = APIRouter(prefix="/api", tags=["premium va toʻlov"])


@router.get("/plans", response_model=list[PlanOut])
def plans(db: Session = Depends(get_db)) -> list[Plan]:
    return list(db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_uzs)))


@router.post("/payments/checkout", response_model=CheckoutOut, status_code=status.HTTP_201_CREATED)
def checkout(data: CheckoutIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CheckoutOut:
    plan = db.scalar(select(Plan).where(Plan.code == data.plan_code, Plan.is_active.is_(True)))
    if plan is None:
        raise HTTPException(status_code=404, detail="Tarif topilmadi")
    if settings.payment_provider not in {"mock"}:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"'{settings.payment_provider}' provayderi hali ulanmagan",
        )
    payment = create_payment(db, user, plan)
    return CheckoutOut(
        payment_id=payment.id,
        provider=payment.provider,
        amount_uzs=payment.amount_uzs,
        status=payment.status,
        checkout_url=checkout_url(payment),
    )


# ---------- Sinov (mock) toʻlov ----------
# Faqat PAYMENT_PROVIDER=mock boʻlganda ishlaydi. Haqiqiy pul olinmaydi.

def _mock_payment(payment_id: int, db: Session) -> Payment:
    if settings.payment_provider != "mock":
        raise HTTPException(status_code=404, detail="Topilmadi")
    payment = db.get(Payment, payment_id)
    if payment is None or payment.provider != "mock":
        raise HTTPException(status_code=404, detail="Toʻlov topilmadi")
    return payment


@router.get("/payments/mock/{payment_id}/pay", response_class=HTMLResponse, include_in_schema=False)
def mock_page(payment_id: int, db: Session = Depends(get_db)) -> str:
    payment = _mock_payment(payment_id, db)
    return f"""<!doctype html><html lang="uz"><head><meta charset="utf-8"><title>Sinov toʻlovi</title>
<style>body{{font-family:system-ui;background:#0B0F19;color:#F8FAFC;display:grid;place-items:center;min-height:100vh;margin:0}}
.c{{background:#151B2B;padding:32px;border-radius:20px;box-shadow:inset 0 0 0 1px #334155;max-width:420px}}
button{{background:#FFB454;color:#111827;border:0;border-radius:12px;height:48px;padding:0 24px;font-weight:700;cursor:pointer}}
p{{color:#9CA3AF}}</style></head><body><div class="c">
<h1>Sinov toʻlovi</h1><p>Bu haqiqiy toʻlov emas. Tugma bosilganda Premium yoqiladi.</p>
<p>Tarif: <b>{payment.plan.name}</b> · {payment.amount_uzs:,} soʻm · holat: {payment.status}</p>
<form method="post" action="/api/payments/mock/{payment.id}/pay"><button type="submit">Toʻlovni tasdiqlash</button></form>
</div></body></html>"""


@router.post("/payments/mock/{payment_id}/pay", include_in_schema=False)
def mock_confirm(payment_id: int, db: Session = Depends(get_db)) -> dict:
    payment = _mock_payment(payment_id, db)
    try:
        payment = mark_paid(db, payment, external_id=f"mock-{payment.id}")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"payment_id": payment.id, "status": payment.status, "premium_until": payment.user.premium_until}


# ---------- Haqiqiy provayderlar uchun joy ----------
@router.post("/payments/click/webhook", include_in_schema=False)
@router.post("/payments/payme/webhook", include_in_schema=False)
def provider_webhook() -> None:
    # Click/Payme bilan shartnoma va kalitlar olingach, ularning rasmiy protokoli boʻyicha
    # imzoni tekshirib, tegishli Payment uchun mark_paid() chaqiriladi.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Provayder hali ulanmagan")
