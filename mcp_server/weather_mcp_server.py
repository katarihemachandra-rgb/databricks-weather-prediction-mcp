import os

from fastmcp import FastMCP

from weather_adapter import WeatherAdapter

mcp = FastMCP(
    "Weather Prediction MCP"
)

weather = WeatherAdapter()

@mcp.tool
def get_current_weather(
    location: str,
) -> dict:
    """
    Get current weather conditions for a location.

    IMPORTANT:
    Use this tool ONLY for current or right-now weather.
    DO NOT use this tool for future dates such as tomorrow,
    this weekend, or next week.

    IMPORTANT LOCATION RULE:
    Do not guess a state, province, or country for an ambiguous
    location. If the user provides only an ambiguous city name,
    ask them to clarify the location before calling this tool.

    Args:
        location:
            City or place name, for example
            "Chicago, IL" or "Austin, TX".

    Returns:
        Current temperature, apparent temperature, humidity,
        precipitation, wind speed, and weather conditions.
    """

    return weather.get_current_weather(
        location
    )

@mcp.tool
def get_forecast(
    location: str,
    days: int = 3,
) -> dict:
    """
    Get a multi-day weather forecast starting with today.

    IMPORTANT:
    This tool is REQUIRED for any future-weather question,
    including tomorrow, this weekend, or another upcoming date.

    IMPORTANT LOCATION RULE:
    Do not guess a state, province, or country for an ambiguous
    location. If the user provides only an ambiguous city name,
    ask them to clarify the location before calling this tool.

    The days parameter INCLUDES today:
    - days=1 returns today only.
    - days=2 returns today and tomorrow.
    - days=3 returns today, tomorrow, and the following day.

    For a question about tomorrow, ALWAYS request at least
    days=2 and use the forecast record whose date is tomorrow.

    Always inspect the returned date field before describing
    a forecast as today, tomorrow, or another specific day.

    Args:
        location:
            City or place name.

        days:
            Number of forecast calendar days to return,
            including today. Values are limited to 1 through 7.

    Returns:
        Daily forecasts containing exact dates, conditions,
        high and low temperatures, precipitation probability,
        precipitation amount, and maximum wind speed.
    """

    return weather.get_forecast(
        location=location,
        days=days,
    )

@mcp.tool
def get_weather_recommendation(
    location: str,
    target_date: str,
) -> dict:
    """
    Generate a weather-based action recommendation.

    IMPORTANT:
    This tool MUST be used for questions asking what the user should
    bring, wear, prepare for, or do because of weather.

    Examples:
    - "Should I bring an umbrella tomorrow?"
    - "Do I need a jacket?"
    - "What should I wear?"
    - "Should I prepare for heat or strong wind?"

    DO NOT answer these recommendation questions using get_forecast alone.

    Args:
        location:
            City or place name.

        target_date:
            Exact forecast date in YYYY-MM-DD format.

    Returns:
        Forecast values, recommendations, reasons, and
        the thresholds used to derive the recommendation.
    """

    return weather.get_weather_recommendation(
        location=location,
        target_date=target_date,
    )

if __name__ == "__main__":
    port = int(
        os.getenv(
            "DATABRICKS_APP_PORT",
            os.getenv(
                "PORT",
                "8000",
            ),
        )
    )

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
    )