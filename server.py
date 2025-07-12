#!/usr/bin/env python3

import asyncio
import sys
import json
import logging
import httpx
import os
from datetime import datetime

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Set up logging - debug level only if DEBUG environment variable is set
log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(
    level=log_level, 
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('weather-mcp-server.log')
    ]
)
logger = logging.getLogger("WeatherMCP")

# Debug: Log environment setup (only in debug mode)
if DEBUG_MODE:
    logger.debug(f"Environment loaded. API Key present: {bool(WEATHER_API_KEY)}")
    logger.debug(f"API Key length: {len(WEATHER_API_KEY) if WEATHER_API_KEY else 0}")
    logger.debug("Debug logging enabled")

def validate_date(dt_str: str) -> None:
    """Ensure date string is in YYYY-MM-DD format."""
    logger.debug(f"Validating date: {dt_str}")
    try:
        datetime.strptime(dt_str, "%Y-%m-%d")
        logger.debug(f"Date validation successful: {dt_str}")
    except ValueError as e:
        logger.error(f"Date validation failed: {dt_str}, error: {e}")
        raise ValueError(f"Invalid date: {dt_str}. Use YYYY-MM-DD.")

async def fetch(endpoint: str, params: dict) -> dict:
    """Perform async GET to WeatherAPI and return JSON."""
    logger.debug(f"fetch() called with endpoint: {endpoint}, params: {params}")
    
    if not WEATHER_API_KEY:
        logger.error("Weather API key not set.")
        raise Exception("Weather API key not set.")

    params["key"] = WEATHER_API_KEY
    url = f"https://api.weatherapi.com/v1/{endpoint}"
    logger.info(f"Requesting {url}")
    
    async with httpx.AsyncClient() as client:
        logger.debug("HTTPx client created")
        try:
            resp = await client.get(url, params=params)
            logger.debug(f"HTTP response received: status={resp.status_code}")
            
            if resp.status_code != 200:
                try:
                    error_data = resp.json()
                    detail = error_data.get("error", {}).get("message", resp.text)
                except:
                    detail = resp.text
                logger.error(f"WeatherAPI error {resp.status_code}: {detail}")
                raise Exception(f"WeatherAPI error {resp.status_code}: {detail}")
                
            data = resp.json()
            logger.debug(f"JSON parsing successful")
            logger.info(f"WeatherAPI success: {url}")
            return data
            
        except httpx.RequestError as e:
            logger.error(f"HTTPX request error: {e}")
            raise Exception(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise Exception(f"Unexpected error: {e}")

# Simple MCP server implementation
async def handle_request(request):
    """Handle MCP requests."""
    logger.debug(f"Received request: {request}")
    
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    try:
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "weather-mcp-server",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            tools = [
                {
                    "name": "weather_current",
                    "description": "Get current weather for a location",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "q": {
                                "type": "string",
                                "description": "Location query (city name, lat/lon, postal code, etc)"
                            },
                            "aqi": {
                                "type": "string",
                                "description": "Include air quality data ('yes' or 'no')",
                                "default": "no"
                            }
                        },
                        "required": ["q"]
                    }
                },
                {
                    "name": "weather_forecast",
                    "description": "Get weather forecast (1-14 days) for a location",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "q": {
                                "type": "string",
                                "description": "Location query (city name, lat/lon, postal code, etc)"
                            },
                            "days": {
                                "type": "integer",
                                "description": "Number of days (1-14)",
                                "default": 1
                            }
                        },
                        "required": ["q"]
                    }
                },
                {
                    "name": "weather_search",
                    "description": "Search for locations matching query",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "q": {
                                "type": "string",
                                "description": "Location query"
                            }
                        },
                        "required": ["q"]
                    }
                }
            ]
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.debug(f"Calling tool: {tool_name} with args: {arguments}")
            
            if tool_name == "weather_current":
                q = arguments.get("q")
                aqi = arguments.get("aqi", "no")
                if not q:
                    raise ValueError("Location (q) is required")
                result = await fetch("current.json", {"q": q, "aqi": aqi})
                content = json.dumps(result, indent=2)
                
            elif tool_name == "weather_forecast":
                q = arguments.get("q")
                days = arguments.get("days", 1)
                if not q:
                    raise ValueError("Location (q) is required")
                if days < 1 or days > 14:
                    raise ValueError("Days must be between 1 and 14")
                result = await fetch("forecast.json", {"q": q, "days": days})
                content = json.dumps(result, indent=2)
                
            elif tool_name == "weather_search":
                q = arguments.get("q")
                if not q:
                    raise ValueError("Location (q) is required")
                result = await fetch("search.json", {"q": q})
                content = json.dumps(result, indent=2)
                
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": content
                        }
                    ]
                }
            }
        
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
    
    logger.debug(f"Sending response: {response}")
    return response

async def main():
    """Main server loop."""
    logger.info("Starting Weather MCP Server...")
    
    try:
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                response = await handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response), flush=True)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
