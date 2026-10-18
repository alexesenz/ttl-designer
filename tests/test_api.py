from fastapi.testclient import TestClient

from ttl_designer.app import app

client = TestClient(app)


def test_health_reports_version_and_commit():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["commit"]


def test_analyze_minimizes_and_verifies():
    r = client.post("/api/analyze", json={"equations": "Y = A B' + A C + B C'"})
    assert r.status_code == 200
    body = r.json()
    assert body["inputs"] == ["A", "B", "C"]
    assert body["equivalent"] is True
    m = body["minimization"][0]
    assert m["minterms"] == [2, 4, 5, 6, 7]
    assert sorted(m["minimized"].split(" + ")) == ["A", "B·C'"]
    assert len(body["truth_table"]) == 8


def test_analyze_with_dont_cares():
    r = client.post(
        "/api/analyze",
        json={"equations": "Y = A B C + A' B' C'", "dont_cares": {"Y": [1, 3]}},
    )
    assert r.status_code == 200
    assert r.json()["equivalent"] is True


def test_analyze_parse_error():
    r = client.post("/api/analyze", json={"equations": "Y = A +"})
    assert r.status_code == 422
    assert "posición" in r.json()["detail"]


def test_analyze_unknown_dont_care_output():
    r = client.post("/api/analyze", json={"equations": "Y = A", "dont_cares": {"Q": [0]}})
    assert r.status_code == 422
