import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
import json
import httpx

# Ensure WEATHER_API_KEY is set for tests that need it
os.environ.setdefault("WEATHER_API_KEY", "test-api-key")

# Import server module functions
from server import validate_date, handle_request, fetch


# ─── validate_date ───────────────────────────────────────────────────────────

class TestValidateDate:
    def test_valid_date(self):
        validate_date("2025-06-15")

    def test_valid_date_end_of_year(self):
        validate_date("2025-12-31")

    def test_valid_date_leap_year(self):
        validate_date("2024-02-29")

    def test_invalid_date_wrong_format(self):
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date("15-06-2025")

    def test_invalid_date_bad_month(self):
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date("2025-13-01")

    def test_invalid_date_bad_day(self):
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date("2025-04-31")

    def test_invalid_date_empty_string(self):
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date("")

    def test_invalid_date_random_string(self):
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date("not-a-date")


# ─── handle_request: initialize ──────────────────────────────────────────────

class TestHandleRequestInitialize:
    @pytest.mark.asyncio
    async def test_initialize_response(self):
        request = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
        response = await handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert response["result"]["serverInfo"]["name"] == "weather-mcp-server"
        assert response["result"]["serverInfo"]["version"] == "1.0.0"
        assert "capabilities" in response["result"]

    @pytest.mark.asyncio
    async def test_initialize_preserves_id(self):
        request = {"jsonrpc": "2.0", "method": "initialize", "id": 42}
        response = await handle_request(request)
        assert response["id"] == 42


# ─── handle_request: tools/list ──────────────────────────────────────────────

class TestHandleRequestToolsList:
    @pytest.mark.asyncio
    async def test_tools_list(self):
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        response = await handle_request(request)

        assert response["result"]["tools"] is not None
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        assert "weather_current" in tool_names
        assert "weather_forecast" in tool_names
        assert "weather_search" in tool_names
        assert len(tools) == 3

    @pytest.mark.asyncio
    async def test_weather_current_schema(self):
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        response = await handle_request(request)
        tools = {t["name"]: t for t in response["result"]["tools"]}

        current = tools["weather_current"]
        assert current["description"] == "Get current weather for a location"
        props = current["inputSchema"]["properties"]
        assert "q" in props
        assert "aqi" in props
        assert current["inputSchema"]["required"] == ["q"]

    @pytest.mark.asyncio
    async def test_weather_forecast_schema(self):
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        response = await handle_request(request)
        tools = {t["name"]: t for t in response["result"]["tools"]}

        forecast = tools["weather_forecast"]
        assert "Get weather forecast" in forecast["description"]
        props = forecast["inputSchema"]["properties"]
        assert "q" in props
        assert "days" in props
        assert forecast["inputSchema"]["required"] == ["q"]

    @pytest.mark.asyncio
    async def test_weather_search_schema(self):
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        response = await handle_request(request)
        tools = {t["name"]: t for t in response["result"]["tools"]}

        search = tools["weather_search"]
        assert "Search for locations" in search["description"]
        props = search["inputSchema"]["properties"]
        assert "q" in props
        assert search["inputSchema"]["required"] == ["q"]


# ─── handle_request: tools/call ──────────────────────────────────────────────

class TestHandleRequestToolsCall:
    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {"name": "unknown_tool", "arguments": {}},
        }
        response = await handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32603

    @pytest.mark.asyncio
    async def test_weather_current_missing_location(self):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {"name": "weather_current", "arguments": {}},
        }
        response = await handle_request(request)

        assert "error" in response
        assert "Location (q) is required" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_weather_forecast_missing_location(self):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {"name": "weather_forecast", "arguments": {}},
        }
        response = await handle_request(request)

        assert "error" in response
        assert "Location (q) is required" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_weather_forecast_days_too_low(self):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {"name": "weather_forecast", "arguments": {"q": "London", "days": 0}},
        }
        response = await handle_request(request)

        assert "error" in response
        assert "Days must be between 1 and 14" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_weather_forecast_days_too_high(self):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {"name": "weather_forecast", "arguments": {"q": "London", "days": 15}},
        }
        response = await handle_request(request)

        assert "error" in response
        assert "Days must be between 1 and 14" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_weather_search_missing_location(self):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {"name": "weather_search", "arguments": {}},
        }
        response = await handle_request(request)

        assert "error" in response
        assert "Location (q) is required" in response["error"]["message"]


# ─── handle_request: unknown method ──────────────────────────────────────────

class TestHandleRequestUnknownMethod:
    @pytest.mark.asyncio
    async def test_unknown_method(self):
        request = {"jsonrpc": "2.0", "method": "unknown/method", "id": 5}
        response = await handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]


# ─── fetch (mocked httpx) ────────────────────────────────────────────────────

class TestFetch:
    @pytest.mark.asyncio
    async def test_fetch_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"current": {"temp_c": 20}}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("server.httpx.AsyncClient", return_value=mock_client):
            result = await fetch("current.json", {"q": "London"})

        assert result == {"current": {"temp_c": 20}}
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "api.weatherapi.com/v1/current.json" in call_args[0][0]
        assert call_args[1]["params"]["key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_fetch_missing_api_key(self):
        # Re-import server module with empty API key to test the module-level check
        import importlib
        with patch.dict(os.environ, {"WEATHER_API_KEY": ""}, clear=False):
            # The module-level var is set at import time, so we test the check directly
            # by temporarily overriding it
            import server as srv
            original_key = srv.WEATHER_API_KEY
            srv.WEATHER_API_KEY = None
            try:
                with pytest.raises(Exception, match="Weather API key not set"):
                    await srv.fetch("current.json", {"q": "London"})
            finally:
                srv.WEATHER_API_KEY = original_key

    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Invalid key"}}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("server.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception, match="WeatherAPI error 400"):
                await fetch("current.json", {"q": "London"})

    @pytest.mark.asyncio
    async def test_fetch_request_error(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

        with patch("server.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception, match="Request error"):
                await fetch("current.json", {"q": "London"})
