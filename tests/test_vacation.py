from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_vacation_preview_returns_synthetic_rows() -> None:
    response = client.get("/api/reports/vacation/preview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["employee_count"] == len(payload["rows"])
    assert payload["employee_count"] > 0
    assert payload["total_amount_due"] > 0
    assert {row["employee_group"] for row in payload["rows"]} == {"Drivers", "Office"}


def test_vacation_csv_has_download_headers_and_columns() -> None:
    response = client.get("/api/reports/vacation.csv")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        'attachment; filename="employee-vacation-balances.csv"'
    )
    assert "Employee group,Employee ID,Employee" in response.content.decode("utf-8-sig")
