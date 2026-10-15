# project_j417 backend

FastAPI + MongoDB Atlas. All members use the same Atlas database, so everyone sees the same data.

## Setup (each member)
1. Clone the repo.
2. Copy `.env.example` to `.env` and configure:
   - `MONGODB_URI` with the team database connection string (ask the team lead).
   - The example uses Gemini (`LLM_PROVIDER=gemini`) with
     `LLM_MODEL=gemini-3.5-flash-lite`; set `LLM_API_KEY` to your Gemini API key.
     Anthropic is also supported when configured with its matching provider, key,
     and model.
   - Never commit `.env`.
3. Install and run:
   ```
   py -m pip install -r requirements.txt
   py -m uvicorn main:app --reload
   ```
4. Open http://localhost:8000/docs

## Atlas (team lead, one time)
- Network Access: add `0.0.0.0/0` (allow from anywhere) so every member's IP can connect.
- Database Access: the shared user needs read/write permission.

## Web workflow
1. Start the backend using the setup instructions above.
2. In another terminal, run `cd frontend`, `npm install`, and `npm run dev`.
3. Open the Vite URL, upload the Component 1 JSON file, and select **Run fusion**.
4. Open the **Generate** tab and choose a summary, study notes, or a five-question
   multiple-choice quiz. Select English or Sinhala, then select **Generate**.

Generation requires knowledge items in the database; upload Component 1 output and
run fusion first. Sinhala content is translated from the English result using NLLB-200,
which may download its model the first time it is used. The health check reports an
error when MongoDB is not configured or cannot be reached.
