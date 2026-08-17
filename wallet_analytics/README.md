# TON Wallet Analytics

A personal, read-only web application for analyzing TON blockchain wallet transactions. Built with Python Flask.

## Features

- **Wallet Connection** — Enter a TON wallet address to start analyzing
- **Transaction History** — Full transaction listing with filtering, search, and pagination
- **Dashboard Analytics** — Total received, sent, net cash flow, fees, and balance
- **Charts** — Activity over time, incoming vs outgoing, monthly cash flow
- **Profit/Loss** — Net cash flow analysis; investment P/L shown as unavailable without cost-basis data
- **USD Pricing** — Optional TON/USD price via CoinGecko
- **Sync** — Full and incremental transaction synchronization with duplicate prevention
- **Change Wallet** — Replace connected wallet with confirmation
- **Jetton Support** — Handles jetton transfers where API provides data
- **Dark Theme** — Modern fintech-inspired dark interface

## Architecture

```
wallet_analytics/
├── app.py                    # Application entry point
├── config.py                 # Configuration classes
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── models.py             # SQLAlchemy models
│   ├── extensions.py         # db, migrate instances
│   ├── routes/
│   │   ├── wallet.py         # Setup, change wallet
│   │   ├── dashboard.py      # Dashboard page
│   │   ├── transactions.py   # Transaction listing
│   │   └── api.py            # JSON API endpoints
│   ├── services/
│   │   ├── ton_client.py     # TON API client
│   │   ├── wallet_sync.py    # Sync orchestration
│   │   ├── analytics.py      # Financial aggregation
│   │   ├── price_service.py  # USD price service
│   │   └── ton_utils.py      # Address validation, utils
│   ├── templates/            # Jinja2 templates
│   └── static/               # CSS, JS
├── migrations/
└── tests/
```

## Requirements

- Python 3.12+
- pip

## Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your settings

# Initialize database
flask db upgrade

# Run application
flask run
```

The app starts at `http://127.0.0.1:5000`.

## Environment Variables

Only `SECRET_KEY` is required. Everything else has sensible defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (dev default) | Flask secret key (change in production) |
| `DATABASE_URL` | `sqlite:///wallet_analytics.db` | Database connection |
| `FLASK_ENV` | `development` | Flask environment |

**No API keys required.** The app uses the public TON Center API which works out of the box.

## TON API

This application uses the **public TON Center API v2** (`toncenter.com/api/v2`).

- **No API key needed** — works immediately with default settings
- Public endpoint has rate limits — the app handles retries and backoff automatically
- If rate limited, wait a moment and try again

## Database

SQLite by default. Tables are auto-created on first run.

### Manual Migration Commands

```bash
flask db init
flask db migrate -m "description"
flask db upgrade
```

## Accounting Rules

```
Total Received  = sum of wallet-relevant incoming transfer amounts
Total Sent      = sum of wallet-relevant outgoing transfer amounts
Net Cash Flow   = Total Received - Total Sent
Total Fees      = sum of network fees
```

**Important:** Net Cash Flow is NOT investment profit. Investment P/L requires historical price and cost-basis data which is not yet implemented.

## Testing

```bash
pytest tests/ -v
```

Tests mock the TON API and test:
- Wallet address validation
- Analytics calculations with Decimal precision
- Transaction direction classification
- Duplicate prevention during sync
- API failure handling
- Pagination

## Production Deployment

### Linux (Gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

### Windows (Waitress)

```bash
waitress-serve --call "app:create_app" --port=8000
```

## Known Limitations

- Public TON API has rate limits (app handles retries automatically)
- Investment P/L requires cost-basis data (not implemented)
- NFT transfers are not financially valued
- Jetton support depends on API availability
- Single-user only — no authentication

## Privacy & Security

- This application **never** requests or stores seed phrases, private keys, or wallet passwords
- All analysis is read-only public blockchain data
- Input validation on all wallet addresses
- SQL injection prevented via SQLAlchemy ORM
- CSRF protection via Flask-WTF
- No secrets committed to repository
