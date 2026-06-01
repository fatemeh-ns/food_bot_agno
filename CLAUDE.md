# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```powershell
# Install dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure environment
Copy-Item .env.example .env
# Then set OPENROUTER_API_KEY in .env

# Initialize and seed the local SQLite database
python app/init.py
python db/load_excel.py

# Run the interactive food-ordering CLI
python app/main.py

# Run the Agno tool-calling benchmark
python benchmark_agno.py

# Build/run with Docker Compose
# Note: the app service runs app/main.py; the Postgres service is currently not used by the Python code.
docker compose up --build
```

There is no configured test runner in `requirements.txt`. The only file under `test/` is currently a Gemini smoke script (`test/test_tools.py`), not an automated assertion-based test suite; it requires a `GOOGLEGEMINI_API_KEY` and a `google-genai` install that is not listed in `requirements.txt`. If pytest tests are added later, use the conventional forms:

```powershell
python -m pytest
python -m pytest path\to\test_file.py::test_name
```

## Architecture

This is a small Python CLI food-ordering agent built with Agno and an OpenRouter-compatible OpenAI API endpoint.

- `app/main.py` is the interactive command-line entry point. It maintains a list of Agno `Message` objects as chat history, passes that list to the global `agent`, prints the response, and appends the assistant reply back into the local history.
- `app/agent.py` constructs the global Agno `Agent`. It loads `.env`, creates an `OpenAILike` model using `OPENROUTER_API_KEY`, points the model at `https://openrouter.ai/api/v1`, and registers the two tool functions. The agent is instructed to respond in Persian/Farsi.
- Tool functions live in `tools/` and are plain Python functions registered directly with Agno:
  - `recommend_food(max_price=None, vegetarian=None, spicy=None)` queries the `foods` table with optional SQLite filters.
  - `reserve_food(food_id, user_name, food_name=None)` inserts into `orders`, optionally looks up the food name, and appends a JSON line to `orders.log`.
- Persistence is SQLite, despite `requirements.txt` including `psycopg2-binary` and `docker-compose.yml` defining a Postgres service. `app/db.py` always connects to the local relative path `food.db`, so commands should normally be run from the repository root.
- Database setup is split into schema and data loading: `app/init.py` creates `foods` and `orders`; `db/load_excel.py` imports rows from `data/foods.xlsx` into `foods`.
- `benchmark_agno.py` creates two independent agents with the same model/instructions, one with tools and one without, then compares latency for a fixed Persian prompt.
- `core/models.py` and `core/prompts.py` are currently empty placeholders.

## Important repository notes

- `.env.example` documents `OPENROUTER_API_KEY`; the main agent will not run successfully without it.
- `docker-compose.yml` starts Postgres and Adminer, but the app does not read Postgres connection settings. Do not assume Postgres-backed behavior unless the code is changed from SQLite.
- `food.db` and `orders.log` are runtime artifacts in the repository root. Tool behavior depends on the current contents of `food.db`.
