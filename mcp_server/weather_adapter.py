import logging
from datetime import date
from typing import Any

import requests


logger = logging.getLogger("weather-adapter")


GEOCODING_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

REQUEST_TIMEOUT = 30

MAX_FORECAST_DAYS = 7


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherAdapter:
    """
    Adapter for Open-Meteo weather APIs.

    All HTTP requests, response parsing, location resolution,
    and recommendation logic live in this class so MCP tools
    can remain thin.
    """

    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "weather-prediction-mcp/1.0"
                )
            }
        )


    def _get_json(
        self,
        url: str,
        params: dict[str, Any],
    ) -> dict:
        """
        Perform a GET request and return parsed JSON.

        Raises:
            RuntimeError: When the remote API request fails
            or does not return valid JSON.
        """

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:
            logger.exception(
                "Weather API request failed"
            )

            raise RuntimeError(
                "Weather service request failed. "
                "Please try again later."
            ) from error

        except ValueError as error:
            raise RuntimeError(
                "Weather service returned an "
                "invalid response."
            ) from error


    def resolve_location(
        self,
        location: str,
    ) -> dict:
        """
        Resolve a natural-language location into coordinates.

        Args:
            location:
                City or place name, for example:
                "Chicago, IL" or "Paris, France".

        Returns:
            Dictionary containing resolved location name,
            latitude, longitude, timezone, country,
            and administrative region.

        Raises:
            ValueError:
                If the location is blank or cannot be found.
        """

        if not isinstance(location, str):
            raise ValueError(
                "location must be a string."
            )

        location = location.strip()

        if not location:
            raise ValueError(
                "location is required."
            )

        data = self._get_json(
            GEOCODING_URL,
            params={
                "name": location,
                "count": 5,
                "language": "en",
                "format": "json",
            },
        )

        results = data.get(
            "results",
            [],
        )

        if not results:
            raise ValueError(
                f"Could not resolve location: {location}"
            )

        match = results[0]

        resolved_name_parts = [
            match.get("name"),
            match.get("admin1"),
            match.get("country"),
        ]

        resolved_name = ", ".join(
            str(part)
            for part in resolved_name_parts
            if part
        )

        return {
            "query": location,
            "resolved_name": resolved_name,
            "latitude": match["latitude"],
            "longitude": match["longitude"],
            "timezone": match.get(
                "timezone",
                "auto",
            ),
            "country": match.get("country"),
            "state_or_region": match.get("admin1"),
        }


    def _weather_description(
        self,
        weather_code: int | None,
    ) -> str:
        """
        Convert an Open-Meteo WMO weather code into
        a readable description.
        """

        if weather_code is None:
            return "Unknown"

        return WEATHER_CODES.get(
            int(weather_code),
            f"Weather code {weather_code}",
        )


    def get_current_weather(
        self,
        location: str,
    ) -> dict:
        """
        Fetch current weather conditions.

        Args:
            location:
                Natural-language location name.

        Returns:
            Clean dictionary with temperature,
            apparent temperature, humidity,
            precipitation, wind, and conditions.
        """

        resolved = self.resolve_location(
            location
        )

        data = self._get_json(
            FORECAST_URL,
            params={
                "latitude": resolved["latitude"],
                "longitude": resolved["longitude"],
                "current": (
                    "temperature_2m,"
                    "apparent_temperature,"
                    "relative_humidity_2m,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "auto",
            },
        )

        current = data.get(
            "current",
            {},
        )

        if not current:
            raise RuntimeError(
                "Current weather data is unavailable "
                f"for {resolved['resolved_name']}."
            )

        weather_code = current.get(
            "weather_code"
        )

        return {
            "location": resolved["resolved_name"],
            "latitude": resolved["latitude"],
            "longitude": resolved["longitude"],
            "timezone": data.get("timezone"),
            "observed_at": current.get("time"),
            "temperature_f": current.get(
                "temperature_2m"
            ),
            "feels_like_f": current.get(
                "apparent_temperature"
            ),
            "humidity_percent": current.get(
                "relative_humidity_2m"
            ),
            "precipitation_inches": current.get(
                "precipitation"
            ),
            "wind_speed_mph": current.get(
                "wind_speed_10m"
            ),
            "weather_code": weather_code,
            "conditions": (
                self._weather_description(
                    weather_code
                )
            ),
        }


    def get_forecast(
        self,
        location: str,
        days: int = 3,
    ) -> dict:
        """
        Fetch a multi-day daily weather forecast.

        Args:
            location:
                Natural-language location name.

            days:
                Number of forecast days to return.
                Allowed range: 1 through 7.

        Returns:
            Dictionary containing resolved location
            details and one clean forecast object per day.
        """

        try:
            days = int(days)
        except (TypeError, ValueError):
            raise ValueError(
                "days must be an integer."
            )

        days = max(
            1,
            min(days, MAX_FORECAST_DAYS),
        )

        resolved = self.resolve_location(
            location
        )

        data = self._get_json(
            FORECAST_URL,
            params={
                "latitude": resolved["latitude"],
                "longitude": resolved["longitude"],
                "daily": (
                    "weather_code,"
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max,"
                    "precipitation_sum,"
                    "wind_speed_10m_max"
                ),
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "forecast_days": days,
                "timezone": "auto",
            },
        )

        daily = data.get(
            "daily",
            {},
        )

        dates = daily.get(
            "time",
            [],
        )

        forecasts = []

        for index, forecast_date in enumerate(
            dates
        ):
            weather_code = self._safe_index(
                daily.get("weather_code", []),
                index,
            )

            forecasts.append(
                {
                    "date": forecast_date,
                    "conditions": (
                        self._weather_description(
                            weather_code
                        )
                    ),
                    "weather_code": weather_code,
                    "high_f": self._safe_index(
                        daily.get(
                            "temperature_2m_max",
                            [],
                        ),
                        index,
                    ),
                    "low_f": self._safe_index(
                        daily.get(
                            "temperature_2m_min",
                            [],
                        ),
                        index,
                    ),
                    "precipitation_probability_percent":
                        self._safe_index(
                            daily.get(
                                "precipitation_probability_max",
                                [],
                            ),
                            index,
                        ),
                    "precipitation_inches":
                        self._safe_index(
                            daily.get(
                                "precipitation_sum",
                                [],
                            ),
                            index,
                        ),
                    "max_wind_speed_mph":
                        self._safe_index(
                            daily.get(
                                "wind_speed_10m_max",
                                [],
                            ),
                            index,
                        ),
                }
            )

        if not forecasts:
            raise RuntimeError(
                "Forecast data is unavailable "
                f"for {resolved['resolved_name']}."
            )

        return {
            "location": resolved["resolved_name"],
            "latitude": resolved["latitude"],
            "longitude": resolved["longitude"],
            "timezone": data.get("timezone"),
            "days_requested": days,
            "forecast": forecasts,
        }


    def get_weather_recommendation(
        self,
        location: str,
        target_date: str,
    ) -> dict:
        """
        Produce a simple weather-based recommendation.

        Rules:
            - Umbrella recommended when precipitation
              probability is >= 40%.
            - Jacket recommended when forecast low is
              <= 50 F.
            - Hot-weather caution when forecast high is
              >= 85 F.
            - Wind caution when maximum wind speed is
              >= 25 mph.

        Args:
            location:
                Natural-language location name.

            target_date:
                Forecast date in YYYY-MM-DD format.

        Returns:
            Forecast values plus derived recommendations
            and explanations.

        Raises:
            ValueError:
                If the date is invalid or outside the
                available forecast window.
        """

        try:
            requested_date = date.fromisoformat(
                target_date
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                "target_date must use YYYY-MM-DD format."
            ) from error

        forecast_data = self.get_forecast(
            location=location,
            days=MAX_FORECAST_DAYS,
        )

        selected = None

        for forecast in forecast_data[
            "forecast"
        ]:
            if (
                forecast["date"]
                == requested_date.isoformat()
            ):
                selected = forecast
                break

        if selected is None:
            raise ValueError(
                "The requested date is outside the "
                "available 7-day forecast window."
            )

        precipitation_probability = (
            selected.get(
                "precipitation_probability_percent"
            )
            or 0
        )

        high_f = selected.get("high_f")
        low_f = selected.get("low_f")

        max_wind_speed = (
            selected.get(
                "max_wind_speed_mph"
            )
            or 0
        )

        recommendations = []
        reasons = []


        if precipitation_probability >= 40:
            recommendations.append(
                "Bring an umbrella."
            )

            reasons.append(
                "Precipitation probability is "
                f"{precipitation_probability}%."
            )


        if (
            low_f is not None
            and low_f <= 50
        ):
            recommendations.append(
                "Bring a jacket or warm layer."
            )

            reasons.append(
                f"The forecast low is {low_f}°F."
            )


        if (
            high_f is not None
            and high_f >= 85
        ):
            recommendations.append(
                "Plan for hot weather and stay hydrated."
            )

            reasons.append(
                f"The forecast high is {high_f}°F."
            )


        if max_wind_speed >= 25:
            recommendations.append(
                "Expect windy conditions."
            )

            reasons.append(
                "Maximum forecast wind speed is "
                f"{max_wind_speed} mph."
            )


        if not recommendations:
            recommendations.append(
                "No special weather gear is indicated "
                "by the current thresholds."
            )

            reasons.append(
                "Rain, temperature, and wind thresholds "
                "were not exceeded."
            )


        return {
            "location": forecast_data["location"],
            "date": selected["date"],
            "forecast": selected,
            "recommendations": recommendations,
            "reasons": reasons,
            "rules_used": {
                "umbrella_precipitation_threshold_percent": 40,
                "jacket_low_temperature_threshold_f": 50,
                "hot_weather_high_temperature_threshold_f": 85,
                "wind_caution_threshold_mph": 25,
            },
        }


    @staticmethod
    def _safe_index(
        values: list,
        index: int,
    ):
        """
        Return a list item safely when API arrays have
        inconsistent lengths.
        """

        if (
            isinstance(values, list)
            and index < len(values)
        ):
            return values[index]

        return None