# TTCN API

This is the API server for the TTCN (Transfermarkt Club Network) system.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the API

Start the server:
```bash
python API.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

## Authentication

The API uses JWT tokens for authentication. Use the `/api/login` endpoint to obtain a token, then include it in the Authorization header as `Bearer <token>` for protected endpoints.

### Mock Users
- Username: `arsenal`, Password: `password123` (Club: Arsenal)
- Username: `chelsea`, Password: `password123` (Club: Chelsea)
- Username: `man_city`, Password: `password123` (Club: Manchester City)

## Endpoints

### Auth & User
- `POST /api/login` - Login and get JWT token
- `GET /api/me` - Get current club information

### Market
- `GET /api/market/players` - Get players on the market (supports filtering by position, price, league)

### Squad
- `GET /api/squad` - Get owned players
- `POST /api/squad/sell` - Sell a player

### Admin
- `POST /api/admin/start-session` - Start transfer market session
- `POST /api/admin/process-wages` - Process weekly wages for all clubs

## Data Source

The API loads player data from `merged_fbref_transfermarkt.csv` if available. Otherwise, it uses mock data.