from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Favorite, Film, Payment, User
from ..schemas import FilmCard, PaymentOut

router = APIRouter(prefix="/api/me", tags=["mening hisobim"])


@router.get("/favorites", response_model=list[FilmCard])
def favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Film]:
    stmt = (
        select(Film)
        .join(Favorite, Favorite.film_id == Film.id)
        .where(Favorite.user_id == user.id, Film.is_published.is_(True))
        .order_by(Favorite.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.put("/favorites/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(film_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    film = db.get(Film, film_id)
    if film is None or not film.is_published:
        raise HTTPException(status_code=404, detail="Film topilmadi")
    db.add(Favorite(user_id=user.id, film_id=film_id))
    try:
        db.commit()
    except IntegrityError:  # allaqachon saqlangan — xato emas
        db.rollback()


@router.delete("/favorites/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(film_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    fav = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.film_id == film_id))
    if fav is not None:
        db.delete(fav)
        db.commit()


@router.get("/payments", response_model=list[PaymentOut])
def my_payments(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Payment]:
    return list(db.scalars(select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())))
