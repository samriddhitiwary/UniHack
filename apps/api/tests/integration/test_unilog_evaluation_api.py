"""Explicit creation and bounded challenge evaluation read APIs."""

import csv
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies.unilog_evaluation import get_unilog_evaluation_service
from app.core.config import Settings, get_settings
from app.domain.unilog_challenge import UnilogDeliveryRecord
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.main import app
from app.repositories.in_memory_unilog_evaluation import InMemoryUnilogEvaluationRepository
from app.services.unilog_evaluation.evaluation_service import UnilogEvaluationService


def _write_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    input_path = tmp_path / "input.csv"
    expected_path = tmp_path / "expected.csv"
    with input_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ["Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf"]
        )
        writer.writerow(
            [
                "ABC",
                "ABC Valve",
                "-- Unbranded --",
                "-- No Unilog Brand --",
                "-- No DIB Brand --",
                "",
            ]
        )
    values = UnilogDeliveryRecord.blank().as_dict()
    values.update(
        {
            "Mfg_Part_Num": "ABC",
            "Part_Desc": "ABC Valve",
            "E1_Brand": "-- Unbranded --",
            "Unilog_Brand": "-- No Unilog Brand --",
            "DIB_Brand": "-- No DIB Brand --",
            "Part_Manuf": "",
            "MANUFACTURER_PART_NUMBER": "ABC",
            "Product Name": "Valve",
            "BRAND_NAME": "Acme®",
        }
    )
    with expected_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=UNILOG_DELIVERY_HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerow({key: "" if value is None else value for key, value in values.items()})
    return input_path, expected_path


def test_create_and_read_evaluation_endpoints_are_explicit_and_bounded(tmp_path: Path) -> None:
    input_path, expected_path = _write_artifacts(tmp_path)
    repository = InMemoryUnilogEvaluationRepository()
    service = UnilogEvaluationService(repository)
    app.dependency_overrides[get_unilog_evaluation_service] = lambda: service
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        unilog_challenge_input_path=input_path,
        unilog_challenge_expected_output_path=expected_path,
    )
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/unilog/evaluations")
            assert created.status_code == 201
            body = created.json()
            evaluation_id = body["evaluationId"]
            row_id = body["labelledRows"][0]["inputRowId"]
            assert body["labelledRowCount"] == 1
            assert body["accuracy"]["bothBlankCount"] == 238
            assert body["batchMetrics"]["processingSuccessRateBp"] == 10_000
            assert client.get("/api/v1/unilog/evaluations/latest").status_code == 200
            assert client.get(f"/api/v1/unilog/evaluations/{evaluation_id}").status_code == 200
            assert (
                client.get(f"/api/v1/unilog/evaluations/{evaluation_id}/summary").status_code == 200
            )
            page = client.get(
                f"/api/v1/unilog/evaluations/{evaluation_id}/fields", params={"limit": 1}
            )
            assert page.status_code == 200
            assert len(page.json()["items"]) == 1
            cursor = page.json()["nextCursor"]
            assert cursor
            assert (
                client.get(
                    f"/api/v1/unilog/evaluations/{evaluation_id}/fields",
                    params={"limit": 1, "cursor": cursor},
                ).status_code
                == 200
            )
            assert (
                client.get(f"/api/v1/unilog/evaluations/{evaluation_id}/rows/{row_id}").json()[
                    "mfgPartNum"
                ]
                == "ABC"
            )
            assert (
                client.get(f"/api/v1/unilog/evaluations/{evaluation_id}/batch").status_code == 200
            )
            assert (
                client.get(f"/api/v1/unilog/evaluations/{evaluation_id}/errors").status_code == 200
            )
            assert (
                client.get(
                    f"/api/v1/unilog/evaluations/{evaluation_id}/fields",
                    params={"cursor": "invalid"},
                ).status_code
                == 400
            )
            assert client.get(f"/api/v1/unilog/evaluations/{'f' * 64}").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_creation_requires_configured_official_paths() -> None:
    app.dependency_overrides[get_unilog_evaluation_service] = lambda: UnilogEvaluationService(
        InMemoryUnilogEvaluationRepository()
    )
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        unilog_challenge_input_path=None,
        unilog_challenge_expected_output_path=None,
    )
    try:
        with TestClient(app) as client:
            assert client.post("/api/v1/unilog/evaluations").status_code == 409
            assert client.get("/api/v1/unilog/evaluations/latest").status_code == 404
    finally:
        app.dependency_overrides.clear()
