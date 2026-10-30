import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Film, Genre
from ..schemas import FilmCard, FilmDetailOut, FilmPage, GenreOut

router = APIRouter(prefix="/api", tags=["katalog"])

_SORTS = {
    "new": (Film.created_at.desc(), Film.id.desc()),
    "popular": (Film.views.desc(), Film.id.desc()),
    "rating": (Film.rating.desc().nulls_last(), Film.id.desc()),
    "year": (Film.year.desc().nulls_last(), Film.id.desc()),
    "title": (Film.title.asc(),),
}


def _published():
    return select(Film).where(Film.is_published.is_(True))


@router.get("/genres", response_model=list[GenreOut])
def genres(db: Session = Depends(get_db)) -> list[Genre]:
    return list(db.scalars(select(Genre).order_by(Genre.name)))


@router.get("/films", response_model=FilmPage)
def list_films(
    q: str | None = Query(default=None, max_length=100, description="Nomi boʻyicha qidiruv"),
    genre: str | None = Query(default=None, description="Janr slug, masalan: drama"),
    kind: str | None = Query(default=None, pattern="^(film|serial|multfilm)$"),
    year: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    quality: str | None = Query(default=None, pattern="^(HD|FHD|4K)$"),
    premium: bool | None = None,
    sort: str = Query(default="new", pattern="^(new|popular|rating|year|title)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
) -> FilmPage:
    stmt = _published()
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Film.title).like(like), func.lower(Film.original_title).like(like)))
    if genre:
        stmt = stmt.where(Film.genres.any(Genre.slug == genre))
    if kind:
        stmt = stmt.where(Film.kind == kind)
    if year:
        stmt = stmt.where(Film.year == year)
    if year_from:
        stmt = stmt.where(Film.year >= year_from)
    if year_to:
        stmt = stmt.where(Film.year <= year_to)
    if quality:
        stmt = stmt.where(Film.quality == quality)
    if premium is not None:
        stmt = stmt.where(Film.is_premium.is_(premium))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(*_SORTS[sort]).offset((page - 1) * limit).limit(limit)))
    return FilmPage(
        items=[FilmCard.model_validate(f) for f in items],
        total=total,
        page=page,
        limit=limit,
        pages=max(1, math.ceil(total / limit)),
    )


@router.get("/films/featured", response_model=list[FilmDetailOut])
def featured(limit: int = Query(default=5, ge=1, le=20), db: Session = Depends(get_db)) -> list[FilmDetailOut]:
    films = db.scalars(
        _published().where(Film.is_featured.is_(True)).order_by(Film.created_at.desc()).limit(limit)
    )
    return [FilmDetailOut.build(f) for f in films]


@router.get("/films/top", response_model=list[FilmCard])
def top(
    limit: int = Query(default=10, ge=1, le=100),
    kind: str | None = Query(default=None, pattern="^(film|serial|multfilm)$"),
    db: Session = Depends(get_db),
) -> list[Film]:
    stmt = _published()
    if kind:
        stmt = stmt.where(Film.kind == kind)
    return list(db.scalars(stmt.order_by(Film.views.desc(), Film.rating.desc().nulls_last()).limit(limit)))


@router.get("/films/{slug}", response_model=FilmDetailOut)
def film_detail(slug: str, db: Session = Depends(get_db)) -> FilmDetailOut:
    film = db.scalar(_published().where(Film.slug == slug))
    if film is None:
        raise HTTPException(status_code=404, detail="Film topilmadi")
    return FilmDetailOut.build(film)


@router.post("/films/{slug}/view", status_code=204)
def add_view(slug: str, db: Session = Depends(get_db)) -> None:
    film = db.scalar(_published().where(Film.slug == slug))
    if film is None:
        raise HTTPException(status_code=404, detail="Film topilmadi")
    film.views = (film.views or 0) + 1
    db.commit()


@router.get("/films/{slug}/similar", response_model=list[FilmCard])
def similar(slug: str, limit: int = Query(default=6, ge=1, le=24), db: Session = Depends(get_db)) -> list[Film]:
    film = db.scalar(_published().where(Film.slug == slug))
    if film is None:
        raise HTTPException(status_code=404, detail="Film topilmadi")
    genre_ids = [g.id for g in film.genres]
    stmt = _published().where(Film.id != film.id)
    if genre_ids:
        stmt = stmt.where(Film.genres.any(Genre.id.in_(genre_ids)))
    return list(db.scalars(stmt.order_by(Film.rating.desc().nulls_last()).limit(limit)))
