"""Tests for the CineAssist CLI."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from assistant.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def _mock_response(status_code: int = 200, json_data=None):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data) if json_data else ""
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response

        real_resp = Response(status_code, text=resp.text)
        real_req = Request("GET", "http://test")
        resp.raise_for_status.side_effect = HTTPStatusError(
            "error", request=real_req, response=real_resp
        )
    return resp


class TestHealthCommand:
    def test_health_ok(self, runner):
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.get.return_value = _mock_response(
                200, {"status": "ok", "service": "cine-assist"}
            )
            result = runner.invoke(cli, ["health"])
            assert result.exit_code == 0
            assert "OK" in result.output

    def test_health_connection_error(self, runner):
        with patch("assistant.cli.httpx") as mock_httpx:
            from httpx import ConnectError

            mock_httpx.get.side_effect = ConnectError("Connection refused")
            result = runner.invoke(cli, ["health"])
            assert result.exit_code == 1


class TestListCommand:
    def test_list_empty(self, runner):
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.get.return_value = _mock_response(200, [])
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0
            assert "No conversations" in result.output

    def test_list_with_conversations(self, runner):
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.get.return_value = _mock_response(
                200,
                [
                    {
                        "id": "abc-123",
                        "title": "Movie chat",
                        "updated_at": "2026-03-27T10:00:00",
                    },
                    {
                        "id": "def-456",
                        "title": "Booking",
                        "updated_at": "2026-03-27T11:00:00",
                    },
                ],
            )
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0
            assert "Movie chat" in result.output
            assert "Booking" in result.output


class TestDeleteCommand:
    def test_delete_success(self, runner):
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.delete.return_value = _mock_response(
                200, {"status": "deleted"}
            )
            result = runner.invoke(cli, ["delete", "abc-123"])
            assert result.exit_code == 0
            assert "Deleted" in result.output


class TestChatCommand:
    def test_chat_creates_conversation_and_exits(self, runner):
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.post.return_value = _mock_response(
                200, {"id": "new-conv-123"}
            )
            result = runner.invoke(cli, ["chat"], input="quit\n")
            assert result.exit_code == 0
            assert "new-conv-123" in result.output

    def test_chat_sends_message(self, runner):
        responses = [
            # POST /conversations
            _mock_response(200, {"id": "conv-1"}),
            # POST /conversations/conv-1/messages
            _mock_response(
                200,
                {
                    "text": "The Brutalist is a 2025 drama film.",
                    "confidence": "verified",
                    "thinking": None,
                    "tool_calls_made": [],
                },
            ),
        ]
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.post.side_effect = responses
            result = runner.invoke(
                cli, ["chat"], input="Tell me about The Brutalist\nquit\n"
            )
            assert result.exit_code == 0
            assert "The Brutalist" in result.output
            assert "VERIFIED" in result.output

    def test_chat_debug_shows_thinking(self, runner):
        responses = [
            _mock_response(200, {"id": "conv-1"}),
            _mock_response(
                200,
                {
                    "text": "Here are the results.",
                    "confidence": "verified",
                    "thinking": "Let me search for this movie...",
                    "tool_calls_made": [
                        {"name": "search_movies", "input": {"query": "test"}}
                    ],
                },
            ),
        ]
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.post.side_effect = responses
            result = runner.invoke(
                cli, ["chat", "--debug"], input="search test\nquit\n"
            )
            assert result.exit_code == 0
            assert "Thinking" in result.output
            assert "search_movies" in result.output

    def test_chat_resume_conversation(self, runner):
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.get.return_value = _mock_response(
                200,
                {
                    "id": "existing-conv",
                    "title": "Previous chat",
                    "summary": None,
                    "messages": [
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi there!"},
                    ],
                },
            )
            result = runner.invoke(
                cli, ["chat", "-c", "existing-conv"], input="quit\n"
            )
            assert result.exit_code == 0
            assert "Previous chat" in result.output

    def test_chat_confidence_badges(self, runner):
        responses = [
            _mock_response(200, {"id": "conv-1"}),
            _mock_response(
                200,
                {
                    "text": "Response 1",
                    "confidence": "general",
                    "thinking": None,
                    "tool_calls_made": [],
                },
            ),
        ]
        with patch("assistant.cli.httpx") as mock_httpx:
            mock_httpx.post.side_effect = responses
            result = runner.invoke(cli, ["chat"], input="hello\nquit\n")
            assert result.exit_code == 0
            assert "GENERAL KNOWLEDGE" in result.output
