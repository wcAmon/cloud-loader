"""Integration tests for API endpoints."""

import io

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from cloud_loader.database import get_session
from cloud_loader.main import app


@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session, tmp_path):
    """Create a test client with dependency overrides."""
    from cloud_loader import config

    original_upload_dir = config.settings.upload_dir
    config.settings.upload_dir = tmp_path / "uploads"
    config.settings.upload_dir.mkdir(parents=True, exist_ok=True)

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    config.settings.upload_dir = original_upload_dir


def test_root_returns_documentation(client: TestClient):
    """Root endpoint should return API documentation for non-browser clients."""
    # Simulate curl/API client (Accept: */*)
    response = client.get("/", headers={"Accept": "*/*"})
    assert response.status_code == 200
    assert "Cloud-Loader API" in response.text
    assert "POST /upload" in response.text
    assert "GET /download" in response.text


def test_root_redirects_browser(client: TestClient):
    """Root endpoint should redirect browsers to /human."""
    # Simulate browser (Accept: text/html first)
    response = client.get(
        "/",
        headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        follow_redirects=False
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/human"


def test_human_page_returns_html(client: TestClient):
    """Human page should return HTML with service information."""
    response = client.get("/human")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Cloud-Loader" in response.text
    assert "AI Assistant Services Platform" in response.text


def test_upload_returns_code(client: TestClient):
    """Upload should return a 6-character code."""
    file_content = b"test backup content"
    response = client.post(
        "/upload",
        files={"file": ("backup.zip", io.BytesIO(file_content), "application/zip")},
    )
    assert response.status_code == 200

    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert data["code"].isalnum()
    assert "expires_at" in data


def test_upload_rejects_large_file(client: TestClient):
    """Upload should reject files exceeding size limit."""
    from cloud_loader import config

    original_max = config.settings.max_file_size_mb
    config.settings.max_file_size_mb = 0  # Set to 0 MB for test

    file_content = b"x" * 1024  # 1KB file
    response = client.post(
        "/upload",
        files={"file": ("backup.zip", io.BytesIO(file_content), "application/zip")},
    )
    assert response.status_code == 400

    config.settings.max_file_size_mb = original_max


def test_full_upload_download_flow(client: TestClient):
    """Test complete upload and download flow."""
    file_content = b"this is a test backup file content"

    # Upload
    upload_response = client.post(
        "/upload",
        files={"file": ("backup.zip", io.BytesIO(file_content), "application/zip")},
    )
    assert upload_response.status_code == 200
    code = upload_response.json()["code"]

    # Download
    download_response = client.get(f"/download/{code}")
    assert download_response.status_code == 200
    assert download_response.content == file_content


def test_download_invalid_code_format(client: TestClient):
    """Download should reject invalid code format."""
    response = client.get("/download/invalid")
    assert response.status_code == 400


def test_download_nonexistent_code(client: TestClient):
    """Download should return 404 for nonexistent code."""
    response = client.get("/download/abc123")
    assert response.status_code == 404


# MD Storage tests


def test_store_md_returns_code(client: TestClient):
    """Store MD should return a 6-character code."""
    response = client.post(
        "/md",
        json={
            "content": "# Test\n\nThis is a test MD file.",
            "metadata": {
                "filename": "CLAUDE.md",
                "purpose": "Project instructions",
                "install_path": "project root",
            },
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert data["code"].isalnum()
    assert "message" in data  # No expires_at - MD files are permanent


def test_store_md_various_filenames(client: TestClient):
    """Store MD should accept various MD filenames."""
    response = client.post(
        "/md",
        json={
            "content": "# Agents\n\nInstructions for Codex.",
            "metadata": {
                "filename": "AGENTS.md",
                "purpose": "Agent configuration",
                "install_path": "~/.codex/",
            },
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["code"]) == 6


def test_store_md_missing_metadata(client: TestClient):
    """Store MD should reject missing metadata."""
    response = client.post(
        "/md",
        json={
            "content": "# Test",
        },
    )
    assert response.status_code == 422  # Validation error


def test_get_md_by_code(client: TestClient):
    """Get MD should return MD data with metadata."""
    # Create MD storage
    create_response = client.post(
        "/md",
        json={
            "content": "# Content\n\nHello world.",
            "metadata": {
                "filename": "DEVELOPMENT.md",
                "purpose": "Development guidelines",
                "install_path": "project root",
            },
        },
    )
    code = create_response.json()["code"]

    # Get MD
    get_response = client.get(f"/md/{code}")
    assert get_response.status_code == 200

    data = get_response.json()
    assert data["code"] == code
    assert data["metadata"]["filename"] == "DEVELOPMENT.md"
    assert data["metadata"]["purpose"] == "Development guidelines"
    assert data["metadata"]["install_path"] == "project root"
    assert "# Content" in data["content"]
    assert data["download_count"] == 1


def test_get_md_raw(client: TestClient):
    """Get MD raw should return plain text content."""
    # Create MD storage
    content = "# My File\n\nThis is the content."
    create_response = client.post(
        "/md",
        json={
            "content": content,
            "metadata": {
                "filename": "TEST.md",
                "purpose": "Test file",
                "install_path": "anywhere",
            },
        },
    )
    code = create_response.json()["code"]

    # Get raw
    raw_response = client.get(f"/md/{code}/raw")
    assert raw_response.status_code == 200
    assert raw_response.text == content
    assert "text/markdown" in raw_response.headers["content-type"]


def test_get_md_invalid_code(client: TestClient):
    """Get MD should reject invalid code format."""
    response = client.get("/md/invalid")
    assert response.status_code == 400


def test_get_md_nonexistent(client: TestClient):
    """Get MD should return 404 for nonexistent code."""
    response = client.get("/md/abc123")
    assert response.status_code == 404


def test_md_download_count_increments(client: TestClient):
    """Download count should increment on each access."""
    # Create MD storage
    create_response = client.post(
        "/md",
        json={
            "content": "# Test",
            "metadata": {
                "filename": "COUNT.md",
                "purpose": "Count test",
                "install_path": "test",
            },
        },
    )
    code = create_response.json()["code"]

    # Get MD multiple times
    client.get(f"/md/{code}")
    client.get(f"/md/{code}")
    response = client.get(f"/md/{code}")

    assert response.json()["download_count"] == 3
