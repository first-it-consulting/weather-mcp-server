# Weather MCP Server

A Model Context Protocol (MCP) server that provides weather information using the WeatherAPI service. This server enables AI assistants to fetch current weather, forecasts, and search for locations through stdio communication.

<a href="https://glama.ai/mcp/servers/@first-it-consulting/weather-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@first-it-consulting/weather-mcp-server/badge" alt="Weather Server MCP server" />
</a>

## Features

- **Current Weather**: Get real-time weather conditions for any location
- **Weather Forecast**: Retrieve weather forecasts up to 14 days ahead  
- **Location Search**: Find and validate location names
- **Air Quality Data**: Optional air quality information
- **Debug Logging**: Comprehensive logging for troubleshooting
- **Stdio Communication**: Direct MCP protocol communication via stdin/stdout

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- WeatherAPI account and API key

## Installation

### Option 1: Via Smithery (Recommended)

Install automatically via [Smithery](https://smithery.ai) MCP registry:

```bash
npx -y @smithery/cli install weather-mcp-server --client claude
```

Or for other MCP clients:

```bash
npx -y @smithery/cli install weather-mcp-server
```

This will automatically:
- Install the weather MCP server
- Add it to your MCP client configuration
- Prompt you for your WeatherAPI key

### Option 2: Manual Installation

1. **Clone or download this repository**

2. **Get a WeatherAPI key**:
   - Sign up at [https://www.weatherapi.com](https://www.weatherapi.com)
   - Get your free API key from the dashboard
   - ⚠️ **Keep your API key secure** - never commit it to version control

3. **Install dependencies**:
   ```bash
   uv sync
   ```

## Configuration

### Environment Variables

Set your WeatherAPI key:

```bash
export WEATHER_API_KEY=your_api_key_here
```

**Optional - Enable debug logging:**

```bash
export DEBUG=true
```

### MCP Client Configuration

Add this server to your MCP client configuration (e.g., `config.json`):

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/weather-mcp-server",
        "run",
        "server.py"
      ],
      "env": {
        "WEATHER_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**To enable debug logging**, add the DEBUG environment variable:

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/weather-mcp-server",
        "run",
        "server.py"
      ],
      "env": {
        "WEATHER_API_KEY": "your_api_key_here",
        "DEBUG": "true"
      }
    }
  }
}
```

## Usage

### Running the Server

**Direct execution:**
```bash
WEATHER_API_KEY=your_api_key uv run server.py
```

**With debug logging:**
```bash
DEBUG=true WEATHER_API_KEY=your_api_key uv run server.py
```

**With MCP client:**
The server automatically starts when your MCP client (like mcphost or Claude Desktop) connects to it.

### Available Tools

#### 1. weather_current
Get current weather conditions for a location.

**Parameters:**
- `q` (required): Location query (city name, coordinates, postal code)
- `aqi` (optional): Include air quality data ("yes" or "no", default: "no")

**Example:**
```json
{
  "name": "weather_current",
  "arguments": {
    "q": "New York, NY",
    "aqi": "yes"
  }
}
```

#### 2. weather_forecast
Get weather forecast for 1-14 days.

**Parameters:**
- `q` (required): Location query
- `days` (optional): Number of forecast days (1-14, default: 1)

**Example:**
```json
{
  "name": "weather_forecast",
  "arguments": {
    "q": "London, UK",
    "days": 7
  }
}
```

#### 3. weather_search
Search for locations matching a query.

**Parameters:**
- `q` (required): Search query

**Example:**
```json
{
  "name": "weather_search",
  "arguments": {
    "q": "Paris"
  }
}
```

### Location Query Formats

The weather tools accept various location formats:

- **City name**: "New York", "London"
- **City and state/country**: "New York, NY", "London, UK"  
- **Coordinates**: "40.7128,-74.0060"
- **Postal code**: "10001", "SW1A 1AA"
- **Airport code**: "JFK", "LHR"

## Testing

### Manual Testing

Test the server with JSON-RPC requests:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | WEATHER_API_KEY=your_api_key uv run server.py
```

**With debug logging:**

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | DEBUG=true WEATHER_API_KEY=your_api_key uv run server.py
```

### Tool Testing

Test a weather tool:

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"weather_current","arguments":{"q":"New York"}}}' | WEATHER_API_KEY=your_api_key uv run server.py
```

## Docker Support

### Building the Image

```bash
docker build -t weather-mcp-server .
```

### Running with Docker

```bash
docker run --rm -i -e WEATHER_API_KEY=your_api_key weather-mcp-server
```

## Debug Mode

The server includes optional debug logging. Set the `DEBUG` environment variable to enable detailed logging.

**Log levels:**
- `INFO`: Basic server operations (default)
- `DEBUG`: Detailed request/response information, API calls (when DEBUG=true)

## Error Handling

The server handles common errors gracefully:

- **Invalid API key**: Returns error message with guidance
- **Location not found**: Suggests alternative search terms
- **Network issues**: Provides retry suggestions
- **Rate limiting**: Indicates when limits are exceeded

## Dependencies

- `httpx`: HTTP client for API requests
- `asyncio`: Async/await support
- Standard library: `json`, `logging`, `sys`, `os`

## API Limits

WeatherAPI free tier includes:
- 1 million calls per month
- Current weather and 3-day forecast
- Upgrade for extended forecasts and higher limits

## Troubleshooting

### Common Issues

1. **"No content response received"**
   - Check API key is set correctly
   - Verify network connectivity  
   - Review debug logs for errors

2. **"API key not provided"**
   - Set the `WEATHER_API_KEY` environment variable
   - Check the MCP client configuration

3. **"Location not found"**
   - Try different location formats
   - Use the weather_search tool to find valid locations

### Debug Output

Enable detailed logging by setting the DEBUG environment variable:
```bash
DEBUG=true WEATHER_API_KEY=your_api_key uv run server.py 2>&1 | grep -E "(DEBUG|ERROR)"
```

## Architecture

This server implements the MCP protocol using:
- **stdio communication**: Direct JSON-RPC over stdin/stdout
- **Asyncio event loop**: Non-blocking request handling
- **Manual JSON-RPC**: Custom implementation for precise control
- **WeatherAPI integration**: RESTful API calls with error handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- WeatherAPI Documentation: https://www.weatherapi.com/docs/
- MCP Specification: https://spec.modelcontextprotocol.io/
- Issues: Report bugs and feature requests in the repository issues

---

*Last updated: July 12, 2025*