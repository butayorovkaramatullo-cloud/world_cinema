from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .utils import trailer_embed_url


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORM):
    id: int
    email: str
    name: str
    is_admin: bool
    is_active: bool
    is_premium: bool
    premium_until: datetime | None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Katalog ----------
class GenreOut(ORM):
    id: int
    name: str
    slug: str


class GenreIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)


class FilmCard(ORM):
    id: int
    title: str
    slug: str
    kind: str
    year: int | None
    quality: str
    language: str
    poster_url: str | None
    poster_color: str | None
    rating: float | None
    is_premium: bool
    genres: list[GenreOut]


class FilmDetail(FilmCard):
    original_title: str | None
    country: str | None
    director: str | None
    duration_min: int | None
    age_rating: str | None
    description: str | None
    backdrop_url: str | None
    trailer_url: str | None
    imdb_rating: float | None
    seasons: int | None
    episodes: int | None
    is_featured: bool
    views: int
    created_at: datetime


class FilmDetailOut(FilmDetail):
    trailer_embed_url: str | None = None

    @classmethod
    def build(cls, film) -> "FilmDetailOut":
        out = cls.model_validate(film)
        out.trailer_embed_url = trailer_embed_url(film.trailer_url)
        return out


class FilmPage(BaseModel):
    items: list[FilmCard]
    total: int
    page: int
    limit: int
    pages: int


_KINDS = {"film", "serial", "multfilm"}
_QUALITIES = {"HD", "FHD", "4K"}


class FilmIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    original_title: str | None = Field(default=None, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    kind: str = "film"
    year: int | None = Field(default=None, ge=1888, le=2100)
    country: str | None = Field(default=None, max_length=80)
    director: str | None = Field(default=None, max_length=120)
    duration_min: int | None = Field(default=None, ge=1, le=1000)
    age_rating: str | None = Field(default=None, max_length=10)
    quality: str = "FHD"
    language: str = Field(default="Oʻzbek tilida", max_length=40)
    description: str | None = None
    poster_url: str | None = Field(default=None, max_length=500)
    backdrop_url: str | None = Field(default=None, max_length=500)
    poster_color: str | None = Field(default=None, max_length=20)
    trailer_url: str | None = Field(default=None, max_length=500)
    rating: float | None = Field(default=None, ge=0, le=10)
    imdb_rating: float | None = Field(default=None, ge=0, le=10)
    seasons: int | None = Field(default=None, ge=1)
    episodes: int | None = Field(default=None, ge=1)
    is_featured: bool = False
    is_premium: bool = False
    is_published: bool = True
    genre_ids: list[int] = Field(default_factory=list)

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in _KINDS:
            raise ValueError(f"kind quyidagilardan biri boʻlishi kerak: {', '.join(sorted(_KINDS))}")
        return v

    @field_validator("quality")
    @classmethod
    def _quality(cls, v: str) -> str:
        v = v.upper()
        if v not in _QUALITIES:
            raise ValueError("quality: HD, FHD yoki 4K")
        return v

    @field_validator("trailer_url")
    @classmethod
    def _trailer(cls, v: str | None) -> str | None:
        if v and trailer_embed_url(v) is None:
            raise ValueError("Faqat YouTube yoki Vimeo havolasi qabul qilinadi")
        return v or None


class FilmAdminOut(FilmDetailOut):
    is_published: bool
    updated_at: datetime


# ---------- Toʻlov ----------
class PlanOut(ORM):
    id: int
    code: str
    name: str
    price_uzs: int
    days: int


class CheckoutIn(BaseModel):
    plan_code: str


class CheckoutOut(BaseModel):
    payment_id: int
    provider: str
    amount_uzs: int
    status: str
    checkout_url: str | None


class PaymentOut(ORM):
    id: int
    user_id: int
    amount_uzs: int
    provider: str
    status: str
    external_id: str | None
    created_at: datetime
    paid_at: datetime | None
    plan: PlanOut


class StatsOut(BaseModel):
    films: int
    users: int
    premium_users: int
    paid_payments: int
    revenue_uzs: int
