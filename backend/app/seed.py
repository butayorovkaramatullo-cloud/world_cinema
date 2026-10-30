"""Boshlangʻich maʼlumotlar: janrlar, tariflar, namunaviy filmlar va admin.

Namunaviy filmlar oʻylab topilgan nomlar. Reyting, poster va treyler maydonlari boʻsh —
ularni admin paneldan haqiqiy maʼlumot bilan toʻldiring.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Film, Genre, Plan, User
from .security import hash_password
from .utils import slugify

GENRES = [
    "Jangari", "Komediya", "Drama", "Fantastika", "Qoʻrqinchli", "Melodrama",
    "Tarixiy", "Triller", "Detektiv", "Oilaviy", "Sarguzasht", "Hujjatli",
]

# Narxlar joy belgisi: oʻzingizning narxlaringizni admin/bazada oʻrnating.
PLANS = [
    {"code": "premium_month", "name": "Premium · 1 oy", "price_uzs": 0, "days": 30},
    {"code": "premium_year", "name": "Premium · 1 yil", "price_uzs": 0, "days": 365},
]

DEMO_FILMS = [
    ("Sukunat ortidagi shahar", "film", 2026, ["Drama", "Triller"], "4K", "#3D3A7A", True, False, 134),
    ("Orbita 9", "film", 2026, ["Fantastika"], "4K", "#1F3D5C", True, True, 122),
    ("Qum soati", "film", 2025, ["Drama"], "FHD", "#7A4A2A", True, False, 116),
    ("Oxirgi karvon", "film", 2026, ["Sarguzasht"], "4K", "#C9A27E", False, False, 128),
    ("Shimoliy chiziq", "film", 2026, ["Triller"], "FHD", "#7C93A8", False, False, 109),
    ("Qizil anor bogʻi", "film", 2025, ["Melodrama"], "FHD", "#B5636E", False, False, 101),
    ("Kulrang xona", "film", 2026, ["Detektiv"], "HD", "#8A8A93", False, True, 98),
    ("Togʻlar ortida", "film", 2025, ["Oilaviy"], "4K", "#7F9A6A", False, False, 95),
    ("Yetti eshik", "film", 2026, ["Fantastika"], "FHD", "#6E68B8", False, False, 125),
    ("Yashil chiroq", "film", 2025, ["Komediya"], "FHD", "#4F7A5C", False, False, 92),
    ("Toʻyda koʻrishamiz", "film", 2026, ["Komediya"], "HD", "#B07A5A", False, False, 99),
    ("Jim koʻcha", "film", 2025, ["Triller"], "FHD", "#4D4A63", False, False, 104),
    ("Qorongʻi oʻrmon", "film", 2026, ["Qoʻrqinchli"], "FHD", "#3E4A3A", False, True, 97),
    ("Toshkent. 3:00", "serial", 2026, ["Triller"], "FHD", "#3E4A6B", False, True, None),
    ("Mahalla", "serial", 2026, ["Oilaviy"], "FHD", "#8C4A63", False, False, None),
    ("Choʻl shamoli", "serial", 2024, ["Tarixiy"], "FHD", "#A07C4A", False, False, None),
    ("Soyalar", "serial", 2026, ["Detektiv"], "FHD", "#4A4E5A", False, False, None),
]


def seed(db: Session) -> None:
    genres = {g.name: g for g in db.scalars(select(Genre))}
    for name in GENRES:
        if name not in genres:
            g = Genre(name=name, slug=slugify(name))
            db.add(g)
            genres[name] = g

    existing_plans = set(db.scalars(select(Plan.code)))
    for p in PLANS:
        if p["code"] not in existing_plans:
            db.add(Plan(**p))

    if settings.seed_demo_data and (db.scalar(select(func.count(Film.id))) or 0) == 0:
        for title, kind, year, gnames, quality, color, featured, premium, duration in DEMO_FILMS:
            db.add(Film(
                title=title, slug=slugify(title), kind=kind, year=year, quality=quality,
                poster_color=color, is_featured=featured, is_premium=premium, duration_min=duration,
                genres=[genres[n] for n in gnames],
            ))

    if settings.admin_email and settings.admin_password:
        email = settings.admin_email.lower()
        admin = db.scalar(select(User).where(func.lower(User.email) == email))
        if admin is None:
            db.add(User(email=email, name="Admin", password_hash=hash_password(settings.admin_password), is_admin=True))
        elif not admin.is_admin:
            admin.is_admin = True

    db.commit()
