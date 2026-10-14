# project_j417 backend

FastAPI + MongoDB Atlas. All members use the same Atlas database, so everyone sees the same data.

## Setup (each member)
1. Clone the repo.
2. Copy `.env.example` to `.env` and put in the real connection string
   (ask the team lead; never commit `.env`).
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
4. Open the **Generate** tab, choose a summary, study notes, or quiz (and a language), then select **Generate**.

The backend `.env` file must contain a reachable `MONGODB_URI`. The health check reports
an error when MongoDB is not configured or cannot be reached.
