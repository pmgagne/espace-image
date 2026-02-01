def test_read_root(client):
    """Test the root endpoint returns 200 and the index template."""
    response = client.get("/")
    assert response.status_code == 200
    # Check for expected content from templates/index.html
    assert "Espace-Image" in response.text


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
