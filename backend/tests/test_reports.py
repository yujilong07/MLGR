def test_create_report_success(client, auth_headers):
    response = client.post('/reports', headers=auth_headers,
    json={"title": "Work", "discipline" : "Web-tech", 
          "teacher": "Andrew Ng", "group" : "ITAI-24-2", 
          "goal" : "learn something"})
    
    assert response.status_code==201
    data = response.json()

    assert "id" in data
    assert data["title"] == "Work"
    assert data["discipline"] =="Web-tech"
    assert data["teacher"] == "Andrew Ng"
    assert data["group"] =="ITAI-24-2"
    assert data["goal"] == "learn something"

def test_create_report_no_auth(client):
    response = client.post('/reports', headers=None,
    json={"title": "Work", "discipline" : "Web-tech", 
          "teacher": "Andrew Ng", "group" : "ITAI-24-2", 
          "goal" : "learn something"})
    
    assert response.status_code == 401

def test_get_report_by_id_other_user_forbidden(client, auth_headers):
    user1 = client.post('/reports', headers=auth_headers,
    json={"title": "Work", "discipline" : "Web-tech", 
          "teacher": "Andrew Ng", "group" : "ITAI-24-2", 
          "goal" : "learn something"})
    
    data = user1.json()
    report_id = data["id"]

    user2 = client.post("/auth/register", json= {"username": "impostor",
            "email": "impostor@haha.com",
            "password": "12345678"})
    
    user2 = client.post("/auth/login", data={
    "username": "impostor@haha.com",
    "password": "12345678"})

    token_b = user2.json()["access_token"]

    headers_b = {"Authorization": f"Bearer {token_b}"}

    user2 = client.get(f"/reports/{report_id}",headers=headers_b)

    assert user2.status_code == 404


def test_get_reports_empty(client, auth_headers):
    response = client.get("/reports", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_reports_with_items(client, auth_headers):
    client.post("/reports", headers=auth_headers,
        json={"title": "A", "discipline": "Math", "teacher": "T", "group": "G1", "goal": "g"})
    client.post("/reports", headers=auth_headers,
        json={"title": "B", "discipline": "Phys", "teacher": "T", "group": "G1", "goal": "g"})
    response = client.get("/reports", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_reports_no_auth(client):
    response = client.get("/reports")
    assert response.status_code == 401


def test_get_report_by_id_success(client, auth_headers, report_id):
    response = client.get(f"/reports/{report_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == report_id


def test_get_report_not_found(client, auth_headers):
    response = client.get("/reports/9999", headers=auth_headers)
    assert response.status_code == 404


def test_get_report_no_auth(client, report_id):
    response = client.get(f"/reports/{report_id}")
    assert response.status_code == 401


def test_update_report_success(client, auth_headers, report_id):
    response = client.patch(f"/reports/{report_id}", headers=auth_headers,
        json={"title": "Updated Title", "discipline": "New-Disc"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["discipline"] == "New-Disc"
    assert data["teacher"] == "Andrew Ng"  # unchanged


def test_update_report_partial(client, auth_headers, report_id):
    response = client.patch(f"/reports/{report_id}", headers=auth_headers,
        json={"conclusion": "Final conclusion."})
    assert response.status_code == 200
    assert response.json()["conclusion"] == "Final conclusion."


def test_update_report_not_found(client, auth_headers):
    response = client.patch("/reports/9999", headers=auth_headers, json={"title": "X"})
    assert response.status_code == 404


def test_update_report_no_auth(client, report_id):
    response = client.patch(f"/reports/{report_id}", json={"title": "X"})
    assert response.status_code == 401


def test_delete_report_success(client, auth_headers, report_id):
    response = client.delete(f"/reports/{report_id}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get(f"/reports/{report_id}", headers=auth_headers).status_code == 404


def test_delete_report_not_found(client, auth_headers):
    response = client.delete("/reports/9999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_report_no_auth(client, report_id):
    response = client.delete(f"/reports/{report_id}")
    assert response.status_code == 401


def test_delete_report_by_id_other_user_forbidden(client, auth_headers):
    user1 = client.post('/reports', headers=auth_headers,
    json={"title": "Work", "discipline" : "Web-tech", 
          "teacher": "Andrew Ng", "group" : "ITAI-24-2", 
          "goal" : "learn something"})
    
    data = user1.json()
    report_id = data["id"]

    user2 = client.post("/auth/register", json= {"username": "impostor",
            "email": "impostor@haha.com",
            "password": "12345678"})
    
    user2 = client.post("/auth/login", data={
    "username": "impostor@haha.com",
    "password": "12345678"})

    token_b = user2.json()["access_token"]

    headers_b = {"Authorization": f"Bearer {token_b}"}

    user2 = client.delete(f"/reports/{report_id}",headers=headers_b)

    assert user2.status_code == 404
    
    user1 = client.get(f"/reports/{report_id}",headers=auth_headers)

    assert user1.status_code == 200

