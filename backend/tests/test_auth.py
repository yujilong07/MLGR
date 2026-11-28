def test_register_success(client):
    response = client.post("/auth/register",
    json={"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"
    assert data["user"]["email"] == "test@example.com"
    assert "password" not in data["user"]
    assert "hashed_password" not in data["user"]


def test_register_derives_username_from_email(client):
    response = client.post("/auth/register",
    json={"email": "alice@example.com", "password": "password123"})

    assert response.status_code == 201
    assert response.json()["user"]["username"] == "alice"


def test_register_fail_repeatable_email(client):
    client.post("/auth/register", json={"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})

    response2 = client.post("/auth/register", json={"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})
    assert response2.status_code == 409


def test_login_fail_wrong_password(client):
    client.post("/auth/register",
    json={"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})

    response2 = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrong_password"})

    assert response2.status_code == 401


def test_login_success(client):
    client.post("/auth/register", json={"username": "testuser", "email": "test@example.com", "password": "password123"})
    response = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"


def test_login_by_username(client):
    client.post("/auth/register", json={"username": "testuser", "email": "test@example.com", "password": "password123"})
    response = client.post("/auth/login", json={"email": "testuser", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_nonexistent_user(client):
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert response.status_code == 401


def test_register_fail_duplicate_username(client):
    client.post("/auth/register", json={"username": "testuser", "email": "first@example.com", "password": "password123"})
    response = client.post("/auth/register", json={"username": "testuser", "email": "second@example.com", "password": "password123"})
    assert response.status_code == 409


def test_register_fail_short_password(client):
    response = client.post("/auth/register", json={"username": "user", "email": "a@b.com", "password": "short"})
    assert response.status_code == 422


def test_register_fail_invalid_email(client):
    response = client.post("/auth/register", json={"username": "user", "email": "not-an-email", "password": "password123"})
    assert response.status_code == 422


def test_logout_success(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.delete("/auth/logout", headers=headers)
    assert response.status_code == 204


def test_logout_blacklists_token(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    client.delete("/auth/logout", headers=headers)
    response = client.get("/reports", headers=headers)
    assert response.status_code == 401


def test_logout_no_auth(client):
    response = client.delete("/auth/logout")
    assert response.status_code == 401


# ── registration problems seen in production ──

def test_same_name_before_at_can_register_twice(client):
    """The username comes from the email; ivan@gmail.com and ivan@ukr.net must both get in."""
    a = client.post("/auth/register", json={"email": "ivan@gmail.com", "password": "password123"})
    b = client.post("/auth/register", json={"email": "ivan@ukr.net", "password": "password123"})
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["user"]["username"] == "ivan" and b.json()["user"]["username"] == "ivan2"
    assert client.post("/auth/login", json={"email": "ivan@ukr.net", "password": "password123"}).status_code == 200


def test_email_is_case_insensitive(client):
    client.post("/auth/register", json={"email": "Olena@Gmail.com", "password": "password123"})
    again = client.post("/auth/register", json={"email": "olena@gmail.com", "password": "password123"})
    assert again.status_code == 409 and "вже існує" in again.json()["detail"]
    assert client.post("/auth/login", json={"email": "OLENA@gmail.com ", "password": "password123"}).status_code == 200


def test_errors_are_in_ukrainian(client):
    r = client.post("/auth/login", json={"email": "nobody@gmail.com", "password": "password123"})
    assert r.status_code == 401 and r.json()["detail"] == "Неправильна пошта або пароль"
    r = client.post("/auth/register", json={"email": "a@gmail.com", "password": "short"})
    assert r.status_code == 422 and "8 символів" in r.json()["detail"][0]["msg"]
    assert client.post("/auth/register", json={"email": "test@1", "password": "password123"}).status_code == 422
