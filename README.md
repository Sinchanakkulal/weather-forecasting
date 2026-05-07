# Weather Forecasting App

This repository contains the setup for a weather forecasting application built with a TypeScript frontend and a Python Flask backend.

## What’s included
- Frontend skeleton using Vite + React + TypeScript
- Backend skeleton using Python Flask
- Environment variable support for API keys
- Initial project structure and documentation

## Project Structure
- `frontend/` — React + TypeScript user interface
- `backend/` — Flask API and server helpers
- `task.md` — project plan and task tracker

## Setup
### Frontend
1. Open a terminal in `frontend/`
2. Run `npm install`
3. Run `npm run dev`

### Backend
1. Open a terminal in `backend/`
2. Create a Python virtual environment: `python -m venv venv`
3. Activate the environment:
   - Windows PowerShell: `venv\Scripts\Activate.ps1`
   - Windows CMD: `venv\Scripts\activate.bat`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the app: `python app.py`

## Environment Variables
1. Copy `backend/.env.example` to `backend/.env`
2. Add your OpenWeatherMap API key to `WEATHER_API_KEY`
3. If you plan to add news aggregation, add a news API key to `NEWS_API_KEY`

## Next Steps
- Implement current weather detection
- Build weather forecast pages
- Add rain and thunderstorm alerts
- Integrate Indian weather news aggregation
- Add AI chatbot and seasonal plant recommendations
