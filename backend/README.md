# World Cinema API (backend)

Python + FastAPI backend: filmlar katalogi, roʻyxatdan oʻtish va kirish, saqlanganlar, Premium obuna (hozircha sinov toʻlovi) va admin panel.

## Mahalliy ishga tushirish

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
# .env ichida SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD ni oʻzgartiring
uvicorn app.main:app --reload
```

Ochiladigan manzillar:

- **http://localhost:8000/docs**: barcha endpointlarning interaktiv hujjati (Swagger)
- **http://localhost:8000/admin**: admin panel (`.env` dagi ADMIN_EMAIL va ADMIN_PASSWORD bilan kiriladi)

Testlar:

```bash
pytest -q
```

## Endpointlar

| Usul | Manzil | Vazifasi | Kirish |
|---|---|---|---|
| GET | `/api/health` | Server ishlayaptimi | — |
| POST | `/api/auth/register` | Roʻyxatdan oʻtish → token | — |
| POST | `/api/auth/login` | Kirish → token | — |
| GET | `/api/auth/me` | Joriy foydalanuvchi | token |
| GET | `/api/genres` | Janrlar | — |
| GET | `/api/films` | Katalog: `q, genre, kind, year, year_from, year_to, quality, premium, sort, page, limit` | — |
| GET | `/api/films/featured` | Bosh sahifa banneri | — |
| GET | `/api/films/top` | Eng koʻp koʻrilganlar | — |
| GET | `/api/films/{slug}` | Film sahifasi (+ `trailer_embed_url`) | — |
| GET | `/api/films/{slug}/similar` | Oʻxshash filmlar | — |
| POST | `/api/films/{slug}/view` | Koʻrishlar sonini oshirish | — |
| GET | `/api/me/favorites` | Saqlanganlar | token |
| PUT / DELETE | `/api/me/favorites/{film_id}` | Saqlash / olib tashlash | token |
| GET | `/api/me/payments` | Mening toʻlovlarim | token |
| GET | `/api/plans` | Premium tariflari | — |
| POST | `/api/payments/checkout` | Toʻlov yaratish → `checkout_url` | token |
| GET/POST/PUT/DELETE/PATCH | `/api/admin/...` | Filmlar, janrlar, foydalanuvchilar, toʻlovlar, statistika | admin |

Token soʻrovlarda shunday yuboriladi: `Authorization: Bearer <token>`.

## Treylerlar

Admin paneldagi treyler maydoniga faqat **YouTube** yoki **Vimeo** havolasi qabul qilinadi. API undan `trailer_embed_url` yasaydi, uni saytda `<iframe src="…">` ichida koʻrsatish mumkin.

## Toʻlov (Premium)

- Hozir `PAYMENT_PROVIDER=mock`: bu **sinov toʻlovi**, pul olinmaydi. `checkout_url` ochilib, tugma bosilganda Premium yoqiladi.
- **Click / Payme**: ulash uchun ular bilan merchant shartnomasi tuziladi va merchant ID hamda maxfiy kalit olinadi. Keyin ularning rasmiy hujjatlari boʻyicha `app/payments.py` ga provayder yoziladi va webhook ichida `mark_paid()` chaqiriladi. Premiumni yoqish mantigʻi tayyor; takroriy webhook Premiumni ikki marta uzaytirmaydi.
- `app/seed.py` dagi tarif narxlari **0** qilib qoʻyilgan. Haqiqiy narxlarni bazada belgilang.

## Render'ga joylash

1. render.com da roʻyxatdan oʻting va GitHub hisobingizni ulang.
2. **New → Blueprint** ni bosib, `world_cinema` repozitoriyini tanlang. Render `render.yaml` ni oʻqib, API va PostgreSQL bazani yaratadi.
3. Soʻralganda `ADMIN_EMAIL`, `ADMIN_PASSWORD` va `PUBLIC_BASE_URL` ni kiriting. `PUBLIC_BASE_URL` — Render bergan manzil, masalan `https://world-cinema-api.onrender.com`.
4. `SECRET_KEY` avtomatik yaratiladi.

Bepul tarif haqida eslatma: server 15 daqiqa ishlatilmasa uxlaydi, birinchi soʻrov sekin ochiladi. Bepul PostgreSQL ham muddatli. Aniq shartlarni Render saytida tekshiring.

## Keyingi qadamlar

- Frontend (`index.html`) ni shu API ga ulash: katalog, kirish oynasi, saqlanganlar
- Click yoki Payme integratsiyasi
- Sxema oʻzgarganda Alembic migratsiyalari
- Poster rasmlarini yuklash uchun fayl saqlash (masalan, S3 yoki Cloudinary)
