# Health 

> Meal plans, workouts, travel itineraries, and daily routines. Live better.

A multi-tool AI suite with 5 tools, powered by Groq.

---

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Rename `.env.example` to `.env` and add your Groq key (get one free at https://console.groq.com).

```bash
uvicorn main:app --reload
```

Open **http://localhost:8000**

---

## Tools included

- **Recipe from Ingredients** — Cook something great with what you have
- **Travel Itinerary Builder** — Plan your perfect trip in minutes
- **Meal Prep Planner** — Plan your whole week of meals
- **Road Trip Planner** — Epic road trips, zero stress
- **Date Night Planner** — Plan the perfect evening out

Built with [Deplo](https://deplo.app) · Powered by [Groq](https://console.groq.com)
