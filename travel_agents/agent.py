import os
import requests
from typing import Optional
from google.genai import types # type: ignore
from dotenv import load_dotenv # type: ignore
from google.adk.agents import Agent # type: ignore


load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY is not set in your .env file. Agents may not initialize correctly.")


def record_travel_preference(preference_name: str, value: str, session_id: str = "default_session") -> str:
    """Records a specific travel preference provided by the user.
    This tool primarily serves to signal the agent that a piece of information
    has been captured and processed.
    """
    print(f"DEBUG: Storing preference '{preference_name}': '{value}' for session '{session_id}'")
    return f"Successfully recorded {preference_name} as {value}."


information_gathering_agent = None
try:
    information_gathering_agent = Agent(
        model="gemini-1.5-flash",
        name="information_gathering_agent",
        instruction=(
            "You are the Information Gathering Agent for a travel planner. "
            "Your task is to politely ask the user for specific travel details, one by one if necessary. "
            "You MUST gather the following information, in this order if possible, before indicating completion:\n"
            "1. **Destination** (e.g., city, country, 'anywhere warm')\n"
            "2. **Budget** (e.g., 'economy', 'mid-range', 'luxury', or a numerical range like '$1000-$2000')\n"
            "3. **Duration** (e.g., '3 days', '1 week')\n"
            "4. **Travel Dates/Season** (e.g., 'July 2025', 'next spring', 'flexible')\n"
            "5. **Number & Type of Travelers** (e.g., '2 adults', 'family with 2 kids')\n"
            "6. **Primary Interests/Activities** (e.g., 'hiking', 'museums', 'beaches', 'foodie')\n"
            "Use the `record_travel_preference` tool to store each piece of information once you receive it. "
            "Keep asking questions until all required information is gathered. "
            "Once you have successfully called the `record_travel_preference` tool for ALL SIX required pieces of information, "
            "return a brief summary of the collected information and state that you are ready for the itinerary to be generated. "
            "This signal will allow the orchestrator to proceed."
        ),
        description="Gathers essential travel preferences from the user.",
        tools=[
            record_travel_preference
        ],
    )
    print(f"Agent '{information_gathering_agent.name}' created using model '{information_gathering_agent.model}'.")
except Exception as e:
    print(f"Could not create Information Gathering Agent. Check GEMINI_API_KEY. Error: {e}")
    information_gathering_agent = None


suggestion_generation_agent = None
try:
    suggestion_generation_agent = Agent(
        model="gemini-1.5-flash",
        name="suggestion_generation_agent",
        instruction=(
            "You are the Travel Idea Generator Agent. "
            "Your task is to create a travel itinerary based on the user's provided preferences. "
            "For Phase 1, simply acknowledge that you have received the information and would normally generate an itinerary. "
            "Do NOT try to generate an actual itinerary yet, just confirm receipt of the preferences. "
            "Confirm that you received: Destination, Budget, Duration, Dates, Travelers, and Interests."
        ),
        description="Generates detailed travel itineraries based on collected preferences.",
        tools=[],
    )
    print(f"Agent '{suggestion_generation_agent.name}' created using model '{suggestion_generation_agent.model}'.")
except Exception as e:
    print(f"Could not create Suggestion Generation Agent. Check GEMINI_API_KEY. Error: {e}")
    suggestion_generation_agent = None


root_agent = None
try:
    root_agent = Agent(
        model="gemini-1.5-flash",
        name="TravelOrchestrator",
        description="The main coordinator for the travel idea generation process. Handles initial welcome, information gathering, and delegation.",
        instruction=(
            "You are the main Travel Planner Orchestrator. "
            "Your primary task is to guide the user through the travel planning process from start to finish. "
            "**START OF CONVERSATION LOGIC:**\n"
            "1. **Initial Welcome & Transition to Info Gathering:** "
            "   If this is the *very first message* from the user in a new session (e.g., 'Hi', 'Hello', 'Start', or any initial input), "
            "   your response MUST be: 'Hello! I'm your Travel Idea Generator. I'm here to help you plan your perfect trip.' "
            "   Immediately after stating this welcome message, you MUST transfer control to the 'information_gathering_agent' to begin collecting travel details. "
            "   Do not wait for further user input after your welcome message to trigger the information gathering.\n"
            "\n**Subsequent Interactions:**\n"
            "2. **Information Gathering:** Always prioritize delegating to the 'information_gathering_agent' to collect all necessary travel details. "
            "   Stay with this agent until all required information (Destination, Budget, Duration, Dates, Travelers, Interests) is gathered."
            "3. **Suggestion Generation:** Once the 'information_gathering_agent' indicates it has completed gathering all preferences and is ready to proceed, "
            "   take back control and delegate to the 'suggestion_generation_agent' to generate the travel ideas."
            "4. **Farewell:** If the user indicates they are leaving or ending the conversation (e.g., 'Bye', 'Goodbye', 'See you', 'Thanks, bye'), "
            "   respond directly with a polite farewell like 'Goodbye! Have a great day!' "
            "   Do not delegate for farewells; handle them yourself."
            "5. **General Greetings/Small Talk:** If the user sends a simple greeting (e.g., 'Hello', 'Good morning') *after* the initial welcome phase has passed, "
            "   respond politely like 'Hello there! How can I help you further with your trip planning?' or 'Hi! I'm ready to continue planning your trip.' "
            "   Handle these directly without delegating."
            "6. **Other Intents:** For any other user input not covered by the above rules, respond appropriately or guide the user back to the travel planning process (e.g., 'What else can I help you with for your trip?')."
        ),
        tools=[], 
        sub_agents=[
            information_gathering_agent,
            suggestion_generation_agent,
        ],
    )
    print(f"Agent '{root_agent.name}' created using model '{root_agent.model}'.")
except Exception as e:
    print(f"Could not create Root Orchestrator Agent. Check GEMINI_API_KEY. Error: {e}")
    root_agent = None
