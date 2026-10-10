import os

import pytest
from fastapi.testclient import TestClient

#server.pyはimport時に設定とDB接続を作成するため、
#importより前にテスト用の設定を与える
os.environ["SERVER_ALLOWED_IPS"] = '["testclient"]'
os.environ["SERVER_DATABASE_PATH"] = ":memory:"

from server import app, conn

client = TestClient(
    app,
    client=("testclient",50000),
)

@pytest.fixture(autouse=True)
def clear_database():
    with conn:
        conn.execute("DELETE FROM metrics")

    yield

    with conn:
        conn.execute("DELETE FROM metrics")


def test_post_metrics():
    data = {
            "host": "test-pc",
            "cpu": 25.0,
            "memory": 40.0,
            "disk":50.0,
            "gpu":30.0,
    }
    response = client.post("/metrics", json=data)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_latest_all_returns_online_metrics():
    data = {
        "host": "test-pc",
        "cpu": 25.0,
        "memory": 40.0,
        "disk": 50.0,
        "gpu": 30.0,
    }
    post_response = client.post("/metrics", json=data)
    assert post_response.status_code == 200
    assert post_response.json() == {"status": "ok"}

    response = client.get("/latest_all")

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    metrics = next(item for item in result if item["host"] == "test-pc")
    for field in ("cpu", "memory", "disk", "gpu"):
        assert metrics[field] == data[field]
    assert metrics["status"] == "online"


def test_get_history_returns_metrics_in_registration_order():
    samples = [(25.0, 30.0), (10.0, 50.0), (40.0, 20.0)]
    for cpu, gpu in samples:
        response = client.post("/metrics", json={
            "host": "test-pc",
            "cpu": cpu,
            "memory": 40.0,
            "disk": 50.0,
            "gpu": gpu,
        })
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    response = client.get("/history/test-pc")

    assert response.status_code == 200
    history = response.json()
    assert {"timestamps", "cpu", "gpu"} <= history.keys()
    for field in ("timestamps", "cpu", "gpu"):
        assert len(history[field]) == len(samples)
    # 履歴はIDの古い順なので、時刻比較ではなく登録順の値で確認する。
    assert history["cpu"] == [cpu for cpu, gpu in samples]
    assert history["gpu"] == [gpu for cpu, gpu in samples]


def test_post_metrics_without_required_cpu_returns_422():
    response = client.post("/metrics", json={
        "host": "test-pc",
        "memory": 40.0,
        "disk": 50.0,
        "gpu": 30.0,
    })

    assert response.status_code == 422


def test_get_latest_all_returns_metrics_for_multiple_hosts():
    samples = [
        {"host": "pc-a", "cpu": 10.0, "memory": 20.0, "disk": 30.0, "gpu": 40.0},
        {"host": "pc-b", "cpu": 80.0, "memory": 70.0, "disk": 60.0, "gpu": 50.0},
    ]
    for data in samples:
        response = client.post("/metrics", json=data)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    response = client.get("/latest_all")

    assert response.status_code == 200
    result = response.json()
    assert len(result) == 2
    metrics_by_host = {item["host"]: item for item in result}
    assert set(metrics_by_host) == {"pc-a", "pc-b"}
    for data in samples:
        for field in ("cpu", "memory", "disk", "gpu"):
            assert metrics_by_host[data["host"]][field] == data[field]


def test_get_latest_all_returns_only_latest_metrics_for_same_host():
    samples = [
        {"host": "test-pc", "cpu": 10.0, "memory": 20.0, "disk": 30.0, "gpu": 40.0},
        {"host": "test-pc", "cpu": 80.0, "memory": 70.0, "disk": 60.0, "gpu": 50.0},
    ]
    for data in samples:
        response = client.post("/metrics", json=data)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    response = client.get("/latest_all")

    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0]["host"] == "test-pc"
    for field in ("cpu", "memory", "disk", "gpu"):
        assert result[0][field] == samples[1][field]
        assert result[0][field] != samples[0][field]


def test_post_and_get_latest_all_support_pc_without_gpu():
    data = {
        "host": "pc-without-gpu",
        "cpu": 25.0,
        "memory": 40.0,
        "disk": 50.0,
        "gpu": None,
    }
    response = client.post("/metrics", json=data)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    response = client.get("/latest_all")

    assert response.status_code == 200
    metrics = next(item for item in response.json() if item["host"] == data["host"])
    assert metrics["gpu"] is None
    for field in ("cpu", "memory", "disk"):
        assert metrics[field] == data[field]


def test_get_history_returns_only_latest_20_metrics():
    samples = [(float(index), float(index + 30)) for index in range(21)]
    for cpu, gpu in samples:
        response = client.post("/metrics", json={
            "host": "test-pc",
            "cpu": cpu,
            "memory": 40.0,
            "disk": 50.0,
            "gpu": gpu,
        })
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    response = client.get("/history/test-pc")

    assert response.status_code == 200
    history = response.json()
    for field in ("timestamps", "cpu", "gpu"):
        assert len(history[field]) == 20
    assert history["cpu"] == [cpu for cpu, gpu in samples[1:]]
    assert history["gpu"] == [gpu for cpu, gpu in samples[1:]]
    assert samples[0][0] not in history["cpu"]
    assert samples[0][1] not in history["gpu"]
