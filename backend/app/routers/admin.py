from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_admin
from ..models import Film, Genre, Payment, User, utcnow
from ..schemas import FilmAdminOut, FilmIn, GenreIn, GenreOut, PaymentOut, StatsOut, UserOut
from ..utils import slugify

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_admin)])


def _unique_slug(db: Session, base: str, exclude_id: int | None = None) -> str:
    slug, n = base, 2
    while True:
        stmt = select(Film.id).where(Film.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Film.id != exclude_id)
        if db.scalar(stmt) is None:
            return slug
        slug = f"{base}-{n}"
        n += 1


def _genres(db: Session, ids: list[int]) -> list[Genre]:
    if not ids:
        return []
    found = list(db.scalars(select(Genre).where(Genre.id.in_(ids))))
    if len(found) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Baʼzi janrlar topilmadi")
    return found


def _apply(film: Film, data: FilmIn, db: Session) -> None:
    payload = data.model_dump(exclude={"genre_ids", "slug"})
    for key, value in payload.items():
        setattr(film, key, value)
    film.genres = _genres(db, data.genre_ids)
    film.slug = _unique_slug(db, slugify(data.slug or data.title), exclude_id=film.id)


# ---------- Statistika ----------
@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)) -> StatsOut:
    return StatsOut(
        films=db.scalar(select(func.count(Film.id))) or 0,
        users=db.scalar(select(func.count(User.id))) or 0,
        premium_users=db.scalar(select(func.count(User.id)).where(User.premium_until > utcnow())) or 0,
        paid_payments=db.scalar(select(func.count(Payment.id)).where(Payment.status == "paid")) or 0,
        revenue_uzs=db.scalar(select(func.coalesce(func.sum(Payment.amount_uzs), 0)).where(Payment.status == "paid")) or 0,
    )


# ---------- Filmlar ----------
@router.get("/films", response_model=list[FilmAdminOut])
def admin_films(
    q: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> list[FilmAdminOut]:
    stmt = select(Film).order_by(Film.created_at.desc(), Film.id.desc())
    if q:
        stmt = stmt.where(func.lower(Film.title).like(f"%{q.lower()}%"))
    return [FilmAdminOut.build(f) for f in db.scalars(stmt)]


@router.post("/films", response_model=FilmAdminOut, status_code=status.HTTP_201_CREATED)
def create_film(data: FilmIn, db: Session = Depends(get_db)) -> FilmAdminOut:
    film = Film()
    _apply(film, data, db)
    db.add(film)
    db.commit()
    db.refresh(film)
    return FilmAdminOut.build(film)


@router.put("/films/{film_id}", response_model=FilmAdminOut)
def update_film(film_id: int, data: FilmIn, db: Session = Depends(get_db)) -> FilmAdminOut:
    film = db.get(Film, film_id)
    if film is None:
        raise HTTPException(status_code=404, detail="Film topilmadi")
    _apply(film, data, db)
    db.commit()
    db.refresh(film)
    return FilmAdminOut.build(film)


@router.delete("/films/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_film(film_id: int, db: Session = Depends(get_db)) -> None:
    film = db.get(Film, film_id)
    if film is None:
        raise HTTPException(status_code=404, detail="Film topilmadi")
    db.delete(film)
    db.commit()


# ---------- Janrlar ----------
@router.post("/genres", response_model=GenreOut, status_code=status.HTTP_201_CREATED)
def create_genre(data: GenreIn, db: Session = Depends(get_db)) -> Genre:
    slug = slugify(data.name)
    if db.scalar(select(Genre.id).where(Genre.slug == slug)):
        raise HTTPException(status_code=409, detail="Bu janr mavjud")
    genre = Genre(name=data.name.strip(), slug=slug)
    db.add(genre)
    db.commit()
    db.refresh(genre)
    return genre


@router.delete("/genres/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_genre(genre_id: int, db: Session = Depends(get_db)) -> None:
    genre = db.get(Genre, genre_id)
    if genre is None:
        raise HTTPException(status_code=404, detail="Janr topilmadi")
    db.delete(genre)
    db.commit()


# ---------- Foydalanuvchilar va toʻlovlar ----------
@router.get("/users", response_model=list[UserOut])
def users(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc()).limit(limit)))


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    is_active: bool | None = None,
    is_admin: bool | None = None,
    admin: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.id == admin.id and (is_active is False or is_admin is False):
        raise HTTPException(status_code=400, detail="Oʻzingizni bloklay yoki adminlikdan ola olmaysiz")
    if is_active is not None:
        user.is_active = is_active
    if is_admin is not None:
        user.is_admin = is_admin
    db.commit()
    db.refresh(user)
    return user


@router.get("/payments", response_model=list[PaymentOut])
def payments(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)) -> list[Payment]:
    return list(db.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(limit)))
