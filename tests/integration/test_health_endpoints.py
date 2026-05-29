"""Smoke tests on the FastAPI app — docs reachable, auth enforced."""


class TestRoot:
    def test_root_returns_welcome(self, client) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "Yalla" in response.json()["message"]


class TestOpenAPI:
    def test_openapi_json_served(self, client) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        assert body["info"]["title"] == "Yalla - Backend API"
        assert body["info"]["version"] == "1.0.0"

    def test_swagger_docs_served(self, client) -> None:
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestAuthEnforcement:
    def test_protected_route_without_token_returns_401(self, client) -> None:
        response = client.get("/api/social/friends/108")
        assert response.status_code == 401

    def test_protected_route_with_wrong_token_returns_401(self, client) -> None:
        response = client.get(
            "/api/social/friends/108",
            headers={"Authorization": "Bearer not-the-secret"},
        )
        assert response.status_code == 401
