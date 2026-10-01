import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import product_service, user_service

PASSWORD = "password123"


def make_product(name: str = "Monitor", **overrides) -> dict:
    return {"name": name, "description": "desc", "price": 9.99, "quantity": 3, **overrides}


@pytest.fixture(autouse=True)
def reset_data() -> None:
    product_service.reset_products()
    user_service.reset_users()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def register_and_login(client: TestClient, username: str) -> dict:
    """Register a user, log in, and return the Authorization header."""
    assert client.post("/auth/register", json={"username": username, "password": PASSWORD}).status_code == 201
    response = client.post("/auth/login", data={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def alice(client: TestClient) -> dict:
    return register_and_login(client, "alice")


@pytest.fixture
def bob(client: TestClient) -> dict:
    return register_and_login(client, "bob")


# ---------- public endpoints ----------

def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Product Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# ---------- authentication ----------

def test_register_returns_user_without_password(client: TestClient) -> None:
    response = client.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "alice"}


def test_password_is_hashed(client: TestClient) -> None:
    client.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    stored = user_service.get_by_username("alice")
    assert stored is not None
    assert stored.hashed_password != PASSWORD
    assert stored.hashed_password.startswith("$argon2")


def test_register_duplicate_username(client: TestClient, alice: dict) -> None:
    response = client.post("/auth/register", json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "password": PASSWORD},
        {"username": "alice", "password": "short"},
        {"username": "alice"},
    ],
)
def test_register_invalid_data(client: TestClient, payload: dict) -> None:
    assert client.post("/auth/register", json=payload).status_code == 422


def test_login_wrong_password(client: TestClient, alice: dict) -> None:
    response = client.post("/auth/login", data={"username": "alice", "password": "wrong-password"})
    assert response.status_code == 401


def test_login_unknown_user(client: TestClient) -> None:
    response = client.post("/auth/login", data={"username": "ghost", "password": PASSWORD})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "method, url",
    [
        ("get", "/products"),
        ("get", "/products/1"),
        ("post", "/products"),
        ("put", "/products/1"),
        ("patch", "/products/1"),
        ("delete", "/products/1"),
        ("delete", "/products"),
    ],
)
def test_products_require_authentication(client: TestClient, method: str, url: str) -> None:
    assert getattr(client, method)(url).status_code == 401


def test_invalid_token_rejected(client: TestClient) -> None:
    response = client.get("/products", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


# ---------- CRUD as a logged-in user ----------

def test_create_and_get_product(client: TestClient, alice: dict) -> None:
    response = client.post("/products", json=make_product(), headers=alice)
    assert response.status_code == 201
    created = response.json()
    assert created["user_id"] == 1
    assert client.get(f"/products/{created['id']}", headers=alice).json() == created
    assert client.get("/products", headers=alice).json() == [created]


def test_trailing_slash_still_works(client: TestClient, alice: dict) -> None:
    assert client.post("/products/", json=make_product(), headers=alice).status_code == 201
    assert len(client.get("/products/", headers=alice).json()) == 1


def test_create_ignores_user_id_and_id_in_body(client: TestClient, alice: dict, bob: dict) -> None:
    body = make_product(user_id=2, id=99)
    created = client.post("/products", json=body, headers=alice).json()
    assert created["user_id"] == 1
    assert created["id"] != 99


def test_replace_product(client: TestClient, alice: dict) -> None:
    product_id = client.post("/products", json=make_product(), headers=alice).json()["id"]
    response = client.put(f"/products/{product_id}", json=make_product("New"), headers=alice)
    assert response.status_code == 200
    assert response.json()["name"] == "New"
    assert response.json()["user_id"] == 1


def test_patch_changes_only_sent_fields(client: TestClient, alice: dict) -> None:
    product_id = client.post("/products", json=make_product(), headers=alice).json()["id"]
    response = client.patch(f"/products/{product_id}", json={"price": 1.5}, headers=alice)
    assert response.status_code == 200
    assert response.json()["price"] == 1.5
    assert response.json()["name"] == "Monitor"


def test_delete_product(client: TestClient, alice: dict) -> None:
    product_id = client.post("/products", json=make_product(), headers=alice).json()["id"]
    assert client.delete(f"/products/{product_id}", headers=alice).status_code == 204
    assert client.get(f"/products/{product_id}", headers=alice).status_code == 404


def test_delete_only_removes_the_given_product(client: TestClient, alice: dict) -> None:
    first = client.post("/products", json=make_product("A"), headers=alice).json()["id"]
    client.post("/products", json=make_product("B"), headers=alice)
    client.delete(f"/products/{first}", headers=alice)
    assert [p["name"] for p in client.get("/products", headers=alice).json()] == ["B"]


@pytest.mark.parametrize(
    "method, kwargs",
    [
        ("get", {}),
        ("put", {"json": make_product()}),
        ("patch", {"json": {"price": 1}}),
        ("delete", {}),
    ],
)
def test_product_not_found(client: TestClient, alice: dict, method: str, kwargs: dict) -> None:
    response = getattr(client, method)("/products/999", headers=alice, **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Product with id 999 not found"}


@pytest.mark.parametrize(
    "payload",
    [
        make_product(price=-1),
        make_product(quantity=-5),
        make_product(name=""),
        {"name": "No price"},
    ],
)
def test_create_invalid_data(client: TestClient, alice: dict, payload: dict) -> None:
    assert client.post("/products", json=payload, headers=alice).status_code == 422


@pytest.mark.parametrize("product_id", ["abc", "0", "-3"])
def test_invalid_product_id(client: TestClient, alice: dict, product_id: str) -> None:
    assert client.get(f"/products/{product_id}", headers=alice).status_code == 422


# ---------- ownership isolation ----------

def test_users_only_see_their_own_products(client: TestClient, alice: dict, bob: dict) -> None:
    client.post("/products", json=make_product("A1"), headers=alice)
    client.post("/products", json=make_product("A2"), headers=alice)
    client.post("/products", json=make_product("B1"), headers=bob)

    alice_names = [p["name"] for p in client.get("/products", headers=alice).json()]
    bob_names = [p["name"] for p in client.get("/products", headers=bob).json()]
    assert alice_names == ["A1", "A2"]
    assert bob_names == ["B1"]


def test_user_cannot_access_others_product(client: TestClient, alice: dict, bob: dict) -> None:
    pid = client.post("/products", json=make_product(), headers=alice).json()["id"]
    url = f"/products/{pid}"
    assert client.get(url, headers=bob).status_code == 404
    assert client.put(url, json=make_product("Hacked"), headers=bob).status_code == 404
    assert client.patch(url, json={"price": 0}, headers=bob).status_code == 404
    assert client.delete(url, headers=bob).status_code == 404
    # Alice's product is untouched
    assert client.get(url, headers=alice).json()["name"] == "Monitor"


# ---------- delete all ----------

def test_delete_all_only_deletes_my_products(client: TestClient, alice: dict, bob: dict) -> None:
    for name in ("A1", "A2"):
        client.post("/products", json=make_product(name), headers=alice)
    for name in ("B1", "B2"):
        client.post("/products", json=make_product(name), headers=bob)

    response = client.delete("/products", headers=alice)
    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert client.get("/products", headers=alice).json() == []
    assert [p["name"] for p in client.get("/products", headers=bob).json()] == ["B1", "B2"]


def test_delete_all_with_no_products(client: TestClient, alice: dict) -> None:
    response = client.delete("/products", headers=alice)
    assert response.status_code == 200
    assert response.json() == {"deleted": 0}
