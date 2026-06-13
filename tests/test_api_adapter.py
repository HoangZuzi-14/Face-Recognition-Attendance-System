import sys
import os
from fastapi.testclient import TestClient

# Đảm bảo import đúng
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.api import app

client = TestClient(app)

def test_login_invalid():
    """Kiểm thử đăng nhập thất bại với thông tin sai."""
    response = client.post("/api/auth/login", json={"username": "wrong", "password": "wrong"})
    assert response.status_code == 401
    assert "detail" in response.json()

def test_camera_status():
    """Kiểm thử lấy trạng thái camera mặc định."""
    response = client.get("/api/camera/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data
    assert data["running"] is False

def test_classes_unauthorized():
    """Kiểm thử lấy danh sách lớp học khi không gửi token."""
    response = client.get("/api/classes")
    assert response.status_code == 401
