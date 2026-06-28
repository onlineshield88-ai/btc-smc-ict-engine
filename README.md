# BTC SMC ICT Engine v2.2

Hybrid BTC trading engine built with pure Python.

## Features

- Hybrid SMC + ICT analysis
- ATR
- RSI
- RSI2
- WMA9
- WMA119
- Fibonacci OTE
- Order Block
- FVG
- Liquidity detection
- Signal scoring
- SQLite history
- Flask REST API

## API

GET /api/dashboard

GET /api/analysis

GET /api/history

GET /api/settings

GET /api/status

GET /health

## Run Backend

python backend/app.py

## Run Engine

python service.py

## Run Both

python start.py
