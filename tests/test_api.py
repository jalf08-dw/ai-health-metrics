import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.main import app, db


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup():
    """Check if database is available for tests."""
    is_healthy, _ = db.health_check()
    if not is_healthy:
        pytest.skip("Database not available for testing")


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_status_endpoint(client):
    """Test status endpoint."""
    response = client.get("/status")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "nl_layer" in data


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "endpoints" in data


def test_list_users(client):
    """Test list users endpoint."""
    response = client.get("/api/users?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "users" in data
    assert isinstance(data["users"], list)


def test_get_nonexistent_user(client):
    """Test getting non-existent user."""
    response = client.get("/api/users/999999")
    
    assert response.status_code == 404


def test_search_users(client):
    """Test search users endpoint."""
    response = client.get("/api/users/search?q=watch")
    
    # May be empty if no matching devices, but should not error
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data


def test_query_metrics_missing_user(client):
    """Test querying metrics for non-existent user."""
    response = client.post("/api/metrics", json={
        "user_id": 999999,
        "metric": "heart_rate",
        "days": 7
    })
    
    assert response.status_code == 404


def test_custom_sql_query(client):
    """Test custom SQL query endpoint."""
    response = client.post("/api/query?sql=SELECT%20COUNT(*)%20FROM%20users%20LIMIT%201000")
    
    assert response.status_code == 200
    data = response.json()
    assert "sql" in data
    assert "row_count" in data
    assert "results" in data
    assert "query_time_ms" in data


def test_custom_sql_dangerous_query(client):
    """Test that dangerous queries are rejected."""
    response = client.post("/api/query?sql=DELETE%20FROM%20users")
    
    assert response.status_code == 400


def test_nl_query_not_configured(client):
    """Test NL query when not configured (no API key)."""
    response = client.post("/api/nl-query", json={
        "question": "What was my heart rate last week?"
    })
    
    # Should either return 503 (not available) or success with error in response
    assert response.status_code in [200, 503]


def test_invalid_metric_type(client):
    """Test with invalid metric type."""
    response = client.post("/api/metrics", json={
        "user_id": 1,
        "metric": "invalid_metric",
        "days": 7
    })
    
    assert response.status_code == 422  # Validation error


def test_invalid_days_range(client):
    """Test with invalid days range."""
    response = client.post("/api/metrics", json={
        "user_id": 1,
        "metric": "heart_rate",
        "days": 200  # Max should be 90
    })
    
    assert response.status_code == 422  # Validation error
