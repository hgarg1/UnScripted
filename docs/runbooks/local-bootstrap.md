# Local bootstrap

1. Copy `.env.example` to `.env`.
2. Run `docker compose up -d`.
3. Install JavaScript dependencies with `pnpm install`.
4. Install Python dependencies with `python -m pip install -e .[dev,ml]`.
5. Start the API with `uvicorn services.api.app.main:app --reload --port 8000`.
6. Start `apps/web` and `apps/admin` with `pnpm --filter @unscripted/web dev` and `pnpm --filter @unscripted/admin dev`.
7. Optionally start `services/event-consumer/app/main.py` and `workers/temporal/app/worker.py`.
