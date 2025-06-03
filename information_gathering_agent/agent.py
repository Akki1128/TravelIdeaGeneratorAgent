import os
from typing import Dict, Any, Optional
from google.adk.agents import Agent
from google.genai import types # Good practice to keep
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# --- Tool for Information Gathering Agent to Signal Completion ---
def submit_collected_info(
    destination: str,
    dates_duration: str,
    budget: str,
    travel_companions: str,
    interests: str,
    pace_of_travel: str,
    accommodation_preference: str,
    dislikes: str,
) -> Dict[str, Any]:
   
    collected_data = {
        "destination": destination,
        "dates_duration": dates_duration,
        "budget": budget,
        "travel_companions": travel_companions,
        "interests": interests,
        "pace_of_travel": pace_of_travel,
        "accommodation_preference": accommodation_preference,
        "dislikes": dislikes,
    }
    print(f"\n[InfoGatheringAgent Tool Call] Collected Data Submitted:\n{collected_data}\n")
    return collected_data


# --- Information Gathering Agent Definition ---
info_gathering_agent = None
try:
    info_gathering_agent = Agent(
        model="gemini-1.5-flash", # Using Gemini 1.5 Flash for efficiency
        name="InformationGatheringAgent",
        instruction=(
            "You are the **Information Gathering Agent** for a personalized travel idea generator. "
            "Your sole purpose is to collect comprehensive details about the user's upcoming trip. "
            "**You must ask clearly and politely for each piece of information, one question at a time.** "
            "Acknowledge the user's previous answer briefly before asking the next question. "
            "Your conversation flow must ensure you gather the following details, in this specific order:\n\n"
            "1.  **Destination**: Where are they planning to go or interested in going? (e.g., 'Paris', 'Japan', 'Anywhere in Europe'). If they don't have a specific destination, ask if they have a region or continent in mind, or if they're open to suggestions based on other criteria.\n"
            "2.  **Travel Dates/Duration**: When are they planning to travel, or for how long will the trip be? (e.g., 'next summer', 'July 15-20', '3 days', 'a week in spring').\n"
            "3.  **Budget**: What is their estimated budget for the trip? (e.g., 'low', 'medium', 'high', 'around $2000 per person', 'luxury').\n"
            "4.  **Travel Companions**: Who are they traveling with? (e.g., 'solo', 'family with kids', 'partner', 'friends', 'a large group').\n"
            "5.  **Interests**: What are their primary interests for this trip? (e.g., 'adventure sports', 'relaxation', 'cultural experiences', 'foodie exploration', 'nightlife', 'historical sites', 'nature and outdoors', 'shopping', 'art'). Ask for multiple interests if applicable.\n"
            "6.  **Pace of Travel**: Do they prefer a packed itinerary with lots of activities, a relaxed and leisurely pace, or a mix of both?\n"
            "7.  **Accommodation Preference**: What type of accommodation do they prefer? (e.g., 'hotel', 'resort', 'Airbnb/vacation rental', 'hostel', 'boutique hotel', 'camping').\n"
            "8.  **Specific Dislikes/Avoidances**: Are there any activities, places, or types of experiences they specifically want to avoid? (e.g., 'no crowded museums', 'avoid beaches', 'not interested in nightlife').\n\n"
            "**Start the conversation by asking for the destination.** "
            "Once you have successfully collected ALL eight pieces of information, "
            "you **MUST** call the `submit_collected_info` tool with all the gathered details as arguments. "
            "Do not provide a final user-facing message; let the tool call complete the process and signal the next step."
        ),
        description="A specialized agent for collecting comprehensive trip details from the user for travel idea generation.",
        tools=[submit_collected_info], 
    )
    print(f"Agent '{info_gathering_agent.name}' created.")
except Exception as e:
    print(f"Could not create InformationGatheringAgent. Check GOOGLE_API_KEY and model availability. Error: {e}")
