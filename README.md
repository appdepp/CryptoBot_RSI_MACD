# CryptoBot RSI MACD

Telegram bot for crypto market analysis using Binance data, RSI/MACD-style indicators, and chart generation.

## Features

- Binance market data
- Top crypto pair selection
- Multiple analysis periods
- RSI-based signals
- Telegram inline keyboard flow
- Chart generation with Matplotlib

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Required variables:

```text
BINANCE_API_KEY=
BINANCE_API_SECRET=
TELEGRAM_API_TOKEN=
```

Run:

```bash
python 18.py
```

## Security

Do not commit `.env`, Binance API keys, Telegram tokens, virtual environments, or `pyvenv.cfg`.
