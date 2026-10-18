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


def test_map_full_adder_selects_two_ics():
    r = client.post("/api/map", json={"equations": "S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)"})
    assert r.status_code == 200
    body = r.json()
    assert body["selected"]["ic_count"] == 2
    assert body["selected"]["parts"] == {"74LS00": 1, "74LS86": 1}
    assert len(body["candidates"]) == 10
    assert all(c["equivalent"] for c in body["candidates"] if c["ic_count"] is not None)
    refs = {c["ref"] for c in body["design"]["chips"]}
    assert refs == {"U1", "U2"}
    assert all("." in pin for pins in body["connections"].values() for pin in pins)
    assert body["drc"]["ok"] is True
    assert body["drc"]["power"]["complete"] is False  # 74LS86 sin ICC verificado
    assert [ln["value"] for ln in body["bom"]["lines"] if ln["kind"] == "ic"] == [
        "74LS00",
        "74LS86",
    ]
    assert any(g["target"] == "74LS86" for g in body["bom"]["gaps"])


def test_map_strategy_subset_and_validation():
    r = client.post("/api/map", json={"equations": "Y = A + B", "strategies": ["nor"]})
    assert r.status_code == 200
    assert r.json()["selected"]["parts"] == {"74LS02": 1}
    bad = client.post("/api/map", json={"equations": "Y = A", "strategies": ["magia"]})
    assert bad.status_code == 422


def test_map_parse_error():
    assert client.post("/api/map", json={"equations": "Y = (A"}).status_code == 422


def test_bom_export_csv_and_json():
    payload = {"equations": "Y = (A B)'"}
    r = client.post("/api/bom/export", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.splitlines()[1].startswith("U1,1,ic,74LS00")
    j = client.post("/api/bom/export?format=json", json=payload)
    assert j.json()["lines"][0]["manufacturer_pn"] == "SN74LS00N"
    assert client.post("/api/bom/export?format=xls", json=payload).status_code == 422


def test_map_with_soic_package_option():
    r = client.post("/api/map", json={"equations": "Y = (A B)'", "bom": {"package": "SOIC-14"}})
    assert r.json()["bom"]["lines"][0]["manufacturer_pn"] == "SN74LS00DR"


def test_map_rejects_function_too_large_with_422():
    names = " ".join(f"X{i}" for i in range(14))
    r = client.post("/api/map", json={"equations": f"Y = A' B + {names}"})
    assert r.status_code == 422
    assert "cubos" in r.json()["detail"]
