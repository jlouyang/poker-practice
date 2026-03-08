"""Integration tests for REST API routes.

Uses FastAPI's TestClient (via httpx) to test endpoints end-to-end
without running a server.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.session import _sessions, get_session
from app.main import app


@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Clear all sessions before and after each test."""
    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def game_session(client: TestClient) -> dict:
    """Create a game and return the full response (game_id + session_token)."""
    res = client.post(
        "/game/create",
        json={
            "num_players": 2,
            "starting_stack": 1000,
            "small_blind": 5,
            "big_blind": 10,
            "difficulty": 30,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "session_token" in data
    return data


@pytest.fixture
def game_id(game_session: dict) -> str:
    return game_session["game_id"]


@pytest.fixture
def auth_headers(game_session: dict) -> dict:
    return {"X-Session-Token": game_session["session_token"]}


class TestCreateGame:
    def test_creates_game_successfully(self, client: TestClient):
        res = client.post(
            "/game/create",
            json={
                "num_players": 6,
                "starting_stack": 1500,
                "small_blind": 10,
                "big_blind": 20,
                "difficulty": 50,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "game_id" in data
        assert "session_token" in data
        assert data["player_seat"] == 0
        assert data["num_players"] == 6

    def test_creates_session_in_registry(self, client: TestClient):
        res = client.post("/game/create", json={"num_players": 2})
        gid = res.json()["game_id"]
        session = get_session(gid)
        assert session is not None
        assert session.human_id == "human"

    def test_minimum_players(self, client: TestClient):
        res = client.post("/game/create", json={"num_players": 2})
        assert res.status_code == 200
        assert res.json()["num_players"] == 2

    def test_validation_rejects_too_few_players(self, client: TestClient):
        res = client.post("/game/create", json={"num_players": 1})
        assert res.status_code == 422

    def test_validation_rejects_too_many_players(self, client: TestClient):
        res = client.post("/game/create", json={"num_players": 10})
        assert res.status_code == 422


class TestGetHint:
    def test_returns_403_without_token(self, client: TestClient):
        res = client.get("/game/nonexistent/hint", headers={"X-Session-Token": "bad"})
        assert res.status_code == 403

    def test_returns_400_when_hand_not_started(self, client: TestClient, game_id: str, auth_headers: dict):
        res = client.get(f"/game/{game_id}/hint", headers=auth_headers)
        assert res.status_code == 400


class TestGetHandStrength:
    def test_returns_403_without_valid_token(self, client: TestClient):
        res = client.get("/game/nonexistent/hand-strength", headers={"X-Session-Token": "bad"})
        assert res.status_code == 403


class TestListProfiles:
    def test_returns_profiles(self, client: TestClient):
        res = client.get("/profiles")
        assert res.status_code == 200
        profiles = res.json()
        assert isinstance(profiles, list)
        assert len(profiles) > 0
        for p in profiles:
            assert "name" in p
            assert "tier" in p
            assert "tightness" in p
            assert "aggression" in p


class TestHandAnalysis:
    def test_returns_404_for_nonexistent_hand(self, client: TestClient):
        res = client.get("/hand/99999/analysis")
        assert res.status_code == 404


class TestHandReplay:
    def test_returns_404_for_nonexistent_hand(self, client: TestClient):
        res = client.get("/hand/99999/replay")
        assert res.status_code == 404


class TestSessionHands:
    def test_returns_empty_list_for_new_session(self, client: TestClient, game_id: str):
        res = client.get(f"/session/{game_id}/hands")
        assert res.status_code == 200
        assert res.json() == []


class TestSessionSummary:
    def test_returns_404_for_empty_session(self, client: TestClient, game_id: str, auth_headers: dict):
        res = client.get(f"/session/{game_id}/summary", headers=auth_headers)
        assert res.status_code == 404


class TestCoachAsk:
    def test_returns_403_without_valid_token(self, client: TestClient):
        res = client.post(
            "/coach/ask",
            json={"question": "Why?", "game_id": "nonexistent"},
            headers={"X-Session-Token": "bad"},
        )
        assert res.status_code == 403

    def test_returns_fallback_when_no_coach_bot(self, client: TestClient, game_id: str, auth_headers: dict):
        res = client.post(
            "/coach/ask",
            json={"question": "Why did you raise?", "game_id": game_id},
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert "No coach bot" in res.json()["answer"]


class TestSessionReview:
    def test_returns_404_for_empty_session(self, client: TestClient, game_id: str, auth_headers: dict):
        res = client.get(f"/session/{game_id}/review", headers=auth_headers)
        assert res.status_code == 404


class TestHealthCheck:
    def test_health_check(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "active_sessions" in data
