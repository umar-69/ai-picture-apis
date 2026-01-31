from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.dependencies import get_supabase, get_current_user, get_current_user_optional

# Mock Supabase Client
mock_supabase = MagicMock()
mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]
mock_supabase.storage.from_.return_value.upload.return_value = None
mock_supabase.storage.from_.return_value.get_public_url.return_value = "http://test-url.com/image.jpg"
mock_supabase.auth.sign_up.return_value = {"user": {"id": "test-user"}}
mock_supabase.auth.sign_in_with_password.return_value = {"session": {"access_token": "test-token"}}

# Mock User
mock_user = MagicMock()
mock_user.id = "test-user-id"

# Dependency Overrides
def override_get_supabase():
    return mock_supabase

def override_get_current_user():
    return mock_user

def override_get_current_user_optional():
    return mock_user

app.dependency_overrides[get_supabase] = override_get_supabase
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to AI Picture APIs"}

def test_auth_signup():
    response = client.post("/auth/signup", json={"email": "test@example.com", "password": "password123"})
    assert response.status_code == 200

def test_auth_login():
    response = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert response.status_code == 200

def test_ai_generate():
    response = client.post("/ai/generate", json={"prompt": "A cute cat", "dataset_id": "test-dataset"})
    assert response.status_code == 200
    assert "prompt_used" in response.json()

@patch("app.routers.ai.genai")
def test_dataset_analyze(mock_genai):
    # Mock Gemini response
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"description": "A test image", "tags": ["test"], "lighting": "bright", "colors": ["red"], "vibe": "happy"}'
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    # Create a dummy image file
    files = {'files': ('test.jpg', b'fake-image-content', 'image/jpeg')}
    
    response = client.post(
        "/ai/dataset/analyze",
        data={"dataset_id": "test-dataset"},
        files=files
    )
    
    assert response.status_code == 200
    assert "results" in response.json()

def test_get_dataset_images():
    # Mock the return value for this specific test
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "img1", "image_url": "http://url1.com", "analysis_result": {"tags": ["cool"]}}
    ]
    
    response = client.get("/ai/dataset/test-dataset/images")
    assert response.status_code == 200
    data = response.json()
    assert "images" in data
    assert len(data["images"]) == 1
    assert data["images"][0]["id"] == "img1"
