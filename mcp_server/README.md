# Weather Prediction MCP Server + Databricks AI Agent

## Overview

This project implements a weather prediction and recommendation system using a custom MCP server and a Databricks AI Agent.

The project was built as part of Day 3 of the Databricks Lakebase Bootcamp. It follows the MCP server + agent architecture demonstrated in the Day 3 Alpaca Markets example, but replaces the trading functionality with weather forecasting and recommendation capabilities.

The system uses Open-Meteo as the weather data provider. Open-Meteo does not require an API key for the functionality used in this project.

The solution supports:

- Current weather conditions
- Multi-day weather forecasts
- Weather-based recommendations
- Relative-date questions such as "tomorrow" and "day after tomorrow"
- Natural-language weather questions through a deployed Databricks AI Agent
- Location resolution and basic typo handling
- Guardrails for ambiguous locations, unsupported dates, and historical weather

---

## Architecture

The application follows a layered architecture where the Databricks AI Agent communicates with a custom MCP server, which retrieves weather data from Open-Meteo.

```text
┌───────────────────────────────┐
│             User              │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Weather Prediction Agent App  │
│       Databricks Apps         │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│     Databricks AI Agent       │
│       / Agent Bricks          │
└───────────────┬───────────────┘
                │
                │ External MCP
                ▼
┌───────────────────────────────┐
│   Custom Weather MCP Server   │
│                               │
│ • get_current_weather         │
│ • get_forecast                │
│ • get_weather_recommendation  │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│       Weather Adapter         │
│      weather_adapter.py       │
└───────────────┬───────────────┘
                │ HTTPS
                ▼
┌───────────────────────────────┐
│        Open-Meteo APIs        │
│                               │
│ • Geocoding                   │
│ • Current Weather             │
│ • Weather Forecast            │
└───────────────────────────────┘
```

### Request Flow

1. The user asks a natural-language weather question.
2. The Databricks AI Agent determines which weather capability is required.
3. The agent invokes the appropriate tool on the custom MCP server.
4. The MCP server delegates API and processing logic to `weather_adapter.py`.
5. The adapter resolves the location and retrieves weather data from Open-Meteo.
6. Structured weather data is returned to the agent.
7. The agent produces a grounded natural-language response.