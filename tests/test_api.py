import asyncio
import json
import logging

from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from backend.main import handle_unexpected_error, handle_validation_error


def test_unexpected_api_exception_is_logged_without_exposing_details(caplog):
    error = RuntimeError("sensitive internal diagnostic")
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/test",
            "raw_path": b"/test",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 80),
            "client": ("localhost", 1234),
            "root_path": "",
        }
    )

    with caplog.at_level(logging.ERROR, logger="backend.main"):
        response = asyncio.run(handle_unexpected_error(request, error))

    assert response.status_code == 500
    assert json.loads(response.body) == {
        "detail": "An unexpected internal error occurred"
    }
    assert "sensitive internal diagnostic" not in caplog.text
    assert "RuntimeError" in caplog.text
    assert caplog.records[0].exc_info is None


def test_validation_error_response_omits_submitted_values():
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/test",
            "raw_path": b"/test",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 80),
            "client": ("localhost", 1234),
            "root_path": "",
        }
    )
    error = RequestValidationError([
        {
            "type": "value_error",
            "loc": ("body", "assessment_data", "monthly_income"),
            "msg": "Invalid value",
            "input": "SENSITIVE_TEST_VALUE",
            "ctx": {"error": ValueError("SENSITIVE_TEST_VALUE")},
        }
    ])

    response = asyncio.run(handle_validation_error(request, error))

    assert response.status_code == 422
    assert b"SENSITIVE_TEST_VALUE" not in response.body