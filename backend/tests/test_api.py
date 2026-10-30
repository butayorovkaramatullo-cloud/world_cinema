"""API testlari. Ishga tushirish (backend papkasida):  pytest -q"""
import os
import tempfile

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["ADMIN_EMAIL"] = "admin@test.uz"
os.environ["ADMIN_PASSWORD"] = "admin-parol-123"
os.environ["PAYMENT_PROVIDER"] = "mock"
os.environ["SEED_DEMO_DATA"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.utils import slugify, trailer_embed_url  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_token(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.uz", "password": "admin-parol-123"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["is_admin"] is True
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def user_token(client):
    r = client.post("/api/auth/register", json={"email": "Ali@Test.uz", "name": "Ali", "password": "parol12345"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


# ---------- yordamchi funksiyalar ----------
def test_slugify():
    assert slugify("Qizil anor bogʻi") == "qizil-anor-bogi"
    assert slugify("Toshkent. 3:00") == "toshkent-3-00"


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ?t=10", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
    ("https://vimeo.com/76979871", "https://player.vimeo.com/video/76979871"),
    ("https://example.com/video.mp4", None),
    ("https://www.youtube.com/watch?v=bad", None),
])
def test_trailer_embed(url, expected):
    assert trailer_embed_url(url) == expected


# ---------- katalog ----------
def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_catalog_seeded(client):
    r = client.get("/api/films", params={"limit": 100})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 10
    assert all("slug" in f for f in body["items"])


def test_filters(client):
    series = client.get("/api/films", params={"kind": "serial"}).json()
    assert series["total"] >= 1 and all(f["kind"] == "serial" for f in series["items"])
    drama = client.get("/api/films", params={"genre": "drama"}).json()
    assert drama["total"] >= 1
    assert all(any(g["slug"] == "drama" for g in f["genres"]) for f in drama["items"])
    found = client.get("/api/films", params={"q": "orbita"}).json()
    assert [f["title"] for f in found["items"]] == ["Orbita 9"]


def test_detail_featured_similar(client):
    r = client.get("/api/films/orbita-9")
    assert r.status_code == 200 and r.json()["title"] == "Orbita 9"
    assert client.get("/api/films/yoq-film").status_code == 404
    assert len(client.get("/api/films/featured").json()) >= 1
    assert client.get("/api/films/orbita-9/similar").status_code == 200
    assert client.post("/api/films/orbita-9/view").status_code == 204
    assert client.get("/api/films/orbita-9").json()["views"] == 1


# ---------- auth ----------
def test_register_duplicate_and_login(client, user_token):
    dup = client.post("/api/auth/register", json={"email": "ali@test.uz", "name": "Ali", "password": "parol12345"})
    assert dup.status_code == 409
    bad = client.post("/api/auth/login", json={"email": "ali@test.uz", "password": "notogri-parol"})
    assert bad.status_code == 401
    me = client.get("/api/auth/me", headers=_auth(user_token))
    assert me.status_code == 200 and me.json()["email"] == "ali@test.uz" and me.json()["is_premium"] is False
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=_auth("buzilgan.token")).status_code == 401


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "x@test.uz", "name": "X", "password": "123"})
    assert r.status_code == 422


# ---------- saqlanganlar ----------
def test_favorites(client, user_token):
    film_id = client.get("/api/films/orbita-9").json()["id"]
    assert client.put(f"/api/me/favorites/{film_id}", headers=_auth(user_token)).status_code == 204
    assert client.put(f"/api/me/favorites/{film_id}", headers=_auth(user_token)).status_code == 204  # takror xato emas
    favs = client.get("/api/me/favorites", headers=_auth(user_token)).json()
    assert [f["id"] for f in favs] == [film_id]
    assert client.delete(f"/api/me/favorites/{film_id}", headers=_auth(user_token)).status_code == 204
    assert client.get("/api/me/favorites", headers=_auth(user_token)).json() == []
    assert client.put("/api/me/favorites/999999", headers=_auth(user_token)).status_code == 404


# ---------- toʻlov ----------
def test_mock_payment_activates_premium(client, user_token):
    plans = client.get("/api/plans").json()
    assert {p["code"] for p in plans} >= {"premium_month", "premium_year"}
    r = client.post("/api/payments/checkout", json={"plan_code": "premium_month"}, headers=_auth(user_token))
    assert r.status_code == 201, r.text
    pid = r.json()["payment_id"]
    assert r.json()["checkout_url"].endswith(f"/api/payments/mock/{pid}/pay")
    assert client.get(f"/api/payments/mock/{pid}/pay").status_code == 200
    paid = client.post(f"/api/payments/mock/{pid}/pay")
    assert paid.status_code == 200 and paid.json()["status"] == "paid"
    until_1 = client.get("/api/auth/me", headers=_auth(user_token)).json()["premium_until"]
    # takroriy tasdiq Premiumni ikki marta uzaytirmaydi
    client.post(f"/api/payments/mock/{pid}/pay")
    me = client.get("/api/auth/me", headers=_auth(user_token)).json()
    assert me["is_premium"] is True and me["premium_until"] == until_1
    mine = client.get("/api/me/payments", headers=_auth(user_token)).json()
    assert mine[0]["status"] == "paid"
    assert client.post("/api/payments/checkout", json={"plan_code": "yoq"}, headers=_auth(user_token)).status_code == 404


# ---------- admin ----------
def test_admin_requires_admin(client, user_token):
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/admin/stats", headers=_auth(user_token)).status_code == 403


def test_admin_film_crud(client, admin_token):
    h = _auth(admin_token)
    genre = client.post("/api/admin/genres", json={"name": "Anime"}, headers=h)
    assert genre.status_code == 201
    gid = genre.json()["id"]
    data = {
        "title": "Yangi film", "kind": "film", "year": 2026, "quality": "4k",
        "trailer_url": "https://youtu.be/dQw4w9WgXcQ", "genre_ids": [gid], "is_premium": True,
    }
    r = client.post("/api/admin/films", json=data, headers=h)
    assert r.status_code == 201, r.text
    film = r.json()
    assert film["slug"] == "yangi-film" and film["quality"] == "4K"
    assert film["trailer_embed_url"] == "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
    # bir xil nom — slug takrorlanmaydi
    second = client.post("/api/admin/films", json=data, headers=h).json()
    assert second["slug"] == "yangi-film-2"
    # notoʻgʻri treyler havolasi rad etiladi
    bad = client.post("/api/admin/films", json={**data, "trailer_url": "https://example.com/x.mp4"}, headers=h)
    assert bad.status_code == 422
    # tahrirlash va yashirish
    upd = client.put(f"/api/admin/films/{film['id']}", json={**data, "title": "Yangi film (tahrir)", "is_published": False}, headers=h)
    assert upd.status_code == 200 and upd.json()["is_published"] is False
    assert client.get(f"/api/films/{upd.json()['slug']}").status_code == 404  # yashirin film ochiq APIda yoʻq
    # oʻchirish
    assert client.delete(f"/api/admin/films/{film['id']}", headers=h).status_code == 204
    assert client.delete(f"/api/admin/films/{second['id']}", headers=h).status_code == 204
    stats = client.get("/api/admin/stats", headers=h).json()
    assert stats["paid_payments"] >= 1 and stats["users"] >= 2


def test_admin_cannot_block_self(client, admin_token):
    me = client.get("/api/auth/me", headers=_auth(admin_token)).json()
    r = client.patch(f"/api/admin/users/{me['id']}", params={"is_active": False}, headers=_auth(admin_token))
    assert r.status_code == 400


def test_admin_page_served(client):
    r = client.get("/admin")
    assert r.status_code == 200 and "Admin panel" in r.text
