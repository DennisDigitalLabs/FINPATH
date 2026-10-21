import asyncio
import json
import logging

from starlette.requests import Request

from backend.main import handle_unexpected_error


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
    assert "sensitive internal diagnostic" in caplog.text
    assert caplog.records[0].exc_info[1] is error