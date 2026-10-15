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
