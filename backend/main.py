# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Travel Idea Generator Agent Backend",
    description="Backend for an AI agent-based travel idea generator using Google ADK.",
    version="0.0.1",
)

# Configure CORS
origins = [
    "http://localhost:5173", # Standard Vite dev server
    "http://127.0.0.1:5173", # Alternative localhost
    "http://TravelBuddy:5173", # Your custom hostname from previous project if you reuse it
    # Add other frontend origins if applicable (e.g. your production domain)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"message": "Travel Idea Generator Agent Backend is running!"}

# --- Your agentic logic will go here or in a separate module ---
# We will add agentic endpoints and integrate the ADK in subsequent steps.