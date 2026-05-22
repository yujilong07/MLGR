def test_register_success(client):
    response = client.post("/auth/register", 
    json= {"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["username"] == "testuser"
    assert data["email"] =="test@example.com"
    assert "password" not in data
    assert "hashed_password" not in data

def test_register_fail_repeatable_email(client):
    response = client.post("/auth/register", json = {"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})
    assert response.status_code == 201

    response2 = client.post("/auth/register", json = {"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})
    assert response2.status_code == 409

def test_login_fail_wrong_password(client):
    response = client.post("/auth/register",
    json= {"username": "testuser",
            "email": "test@example.com",
            "password": "password123"})
    assert response.status_code == 201

    response2 = client.post("/auth/login", data={
    "username": "test@example.com",
    "password": "wrong_password"})

    assert response2.status_code == 401


def test_login_success(client):
    client.post("/auth/register", json={"username": "testuser", "email": "test@example.com", "password": "password123"})
    response = client.post("/auth/login", data={"username": "test@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_by_username(client):
    client.post("/auth/register", json={"username": "testuser", "email": "test@example.com", "password": "password123"})
    response = client.post("/auth/login", data={"username": "testuser", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_nonexistent_user(client):
    response = client.post("/auth/login", data={"username": "nobody@example.com", "password": "password123"})
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
    # token is blacklisted — protected route must reject it
    response = client.get("/reports", headers=headers)
    assert response.status_code == 401


def test_logout_no_auth(client):
    response = client.delete("/auth/logout")
    assert response.status_code == 401
