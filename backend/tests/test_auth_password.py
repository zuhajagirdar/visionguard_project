import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base
from backend import models, security as auth_security
from backend.tests.test_main import engine, TestingSessionLocal, auth_header

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    """Ensure clean test database with standard demo users configured for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        users_data = [
            ("alice_sub", "Submitter"),
            ("bob_sub", "Submitter"),
            ("charlie_rev", "Reviewer"),
            ("eve_app", "Approver"),
        ]
        demo_hash = auth_security.hash_password("12345")
        for username, role in users_data:
            user = db.query(models.User).filter(models.User.username == username).first()
            if not user:
                user = models.User(username=username, role=role, password_hash=demo_hash)
                db.add(user)
            else:
                user.role = role
                user.password_hash = demo_hash
        db.commit()
    finally:
        db.close()
    yield
    # Ensure tables remain available for subsequent test modules
    Base.metadata.create_all(bind=engine)

def test_login_success_all_demo_roles():
    """Verify demo users across Submitter, Reviewer, and Approver roles log in with password '12345'."""
    credentials = [
        ("alice_sub", "Submitter", "12345"),
        ("charlie_rev", "Reviewer", "12345"),
        ("eve_app", "Approver", "12345"),
    ]
    for username, role, password in credentials:
        resp = client.post(
            "/token",
            data={"username": username, "role": role, "password": password}
        )
        assert resp.status_code == 200, f"Failed for {username}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == role
        assert data["username"] == username

def test_login_incorrect_password():
    """Attempting to log in with an incorrect password returns 401."""
    resp = client.post(
        "/token",
        data={"username": "alice_sub", "role": "Submitter", "password": "wrongpassword"}
    )
    assert resp.status_code == 401
    assert "Incorrect password" in resp.json()["detail"]

def test_login_empty_password():
    """Attempting to log in with an empty or missing password returns 400."""
    resp = client.post(
        "/token",
        data={"username": "alice_sub", "role": "Submitter", "password": ""}
    )
    assert resp.status_code == 400
    assert "Password is required" in resp.json()["detail"]

def test_login_nonexistent_user():
    """Attempting to log in with an unknown username returns 404."""
    resp = client.post(
        "/token",
        data={"username": "nonexistent_user_999", "role": "Submitter", "password": "12345"}
    )
    assert resp.status_code == 404
    assert "User not found" in resp.json()["detail"]

def test_login_role_mismatch():
    """Attempting to log in with a role that differs from the account's configured role returns 400."""
    resp = client.post(
        "/token",
        data={"username": "alice_sub", "role": "Reviewer", "password": "12345"}
    )
    assert resp.status_code == 400
    assert "Role mismatch" in resp.json()["detail"]

def test_password_hashing_security():
    """Verify standard PBKDF2 hashing works and salts are unique."""
    hash1 = auth_security.hash_password("12345")
    hash2 = auth_security.hash_password("12345")
    assert hash1 != hash2, "Salts must be randomly generated so identical passwords have different hashes"
    assert auth_security.verify_password("12345", hash1) is True
    assert auth_security.verify_password("12345", hash2) is True
    assert auth_security.verify_password("wrong", hash1) is False

def test_user_creation_does_not_leak_password_hash():
    """Creating a new user returns UserOut schema which must not contain password or password_hash."""
    resp = client.post(
        "/users/",
        json={"username": "test_user_leak_check", "role": "Submitter", "password": "secret_demo_pwd"}
    )
    assert resp.status_code == 200
    user_data = resp.json()
    assert "password" not in user_data
    assert "password_hash" not in user_data
    assert user_data["username"] == "test_user_leak_check"

def test_token_authorizes_role_actions():
    """Verify that a bearer token acquired via login properly authorizes subsequent API operations."""
    # 1. Login as Submitter
    sub_login = client.post(
        "/token",
        data={"username": "alice_sub", "role": "Submitter", "password": "12345"}
    )
    assert sub_login.status_code == 200
    sub_token = sub_login.json()["access_token"]
    sub_headers = {"Authorization": f"Bearer {sub_token}"}

    # 2. Submitter can create draft request
    create_resp = client.post(
        "/requests/",
        headers=sub_headers,
        json={"type": "Reimbursement", "expense_amount": 75.0, "merchant_name": "Test Cafe", "expense_date": "2026-10-20"}
    )
    assert create_resp.status_code == 200, f"Failed create request: {create_resp.text}"
    req_id = create_resp.json()["id"]

    # 3. Submitter cannot perform reviewer decision
    dec_resp = client.post(
        f"/requests/{req_id}/review",
        headers=sub_headers,
        json={"action": "approve", "reason": "Self approval attempt"}
    )
    assert dec_resp.status_code == 403
    assert "Not authorized as reviewer or approver" in dec_resp.json()["detail"]

    # 4. Reviewer logs in and can view requests
    rev_login = client.post(
        "/token",
        data={"username": "charlie_rev", "role": "Reviewer", "password": "12345"}
    )
    assert rev_login.status_code == 200
    rev_token = rev_login.json()["access_token"]
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    details_resp = client.get(f"/requests/{req_id}/details", headers=rev_headers)
    assert details_resp.status_code == 200
