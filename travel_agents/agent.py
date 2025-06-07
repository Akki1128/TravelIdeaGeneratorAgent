import os
import requests
from typing import Optional
from google.genai import types # type: ignore
from dotenv import load_dotenv # type: ignore
from google.adk.agents import Agent # type: ignore


load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY is not set in your .env file.")


def record_travel_preference(preference_name: str, value: str, session_id: str = "default_session") -> str:

    return f"Successfully recorded {preference_name} as {value}."


information_gathering_agent = None
try:
    information_gathering_agent = Agent(
        model="gemini-1.5-flash",
        name="information_gathering_agent",
        instruction=(
            "You are the Information Gathering Agent for a budget-friendly travel planner. "
            "Your primary goal is to politely and systematically gather all necessary travel details from the user. "
            "You MUST gather the following information. If the user provides multiple pieces of information in one go, extract them and mark them as gathered. If any information is missing, ask for it one-by-one:\n"
            "1. **Geographical Scope/Region:** (e.g., 'domestic', 'international', 'open to anywhere', or specific region like 'Southeast Asia', 'Europe', 'Pacific Northwest', or type like 'city break')\n"
            "2. **Budget:** (e.g., 'ultra-budget', 'comfortable budget', or a numerical range like '$1000-$2000')\n"
            "3. **Duration:** (e.g., '3 days', '1 week')\n"
            "4. **Travel Dates/Season & Flexibility:** (e.g., 'July 2025', 'next spring', 'flexible')\n"
            "5. **Number & Type of Travelers:** (e.g., '2 adults', 'family with 2 kids')\n"
            "6. **Primary Interests/Activities:** (e.g., 'hiking', 'museums', 'beaches', 'foodie', 'nightlife', 'history', 'adventure')\n"
            "7. **Accommodation Preference:** (e.g., 'hostels/guesthouses', 'budget hotels/B&Bs', 'camping')\n"
            "8. **Travel Pace:** (e.g., 'fast-paced', 'relaxed pace')\n"
            "9. **Food Experience:** (e.g., 'street food/self-catering', 'dining out mostly', 'mix')\n"
            "10. **Openness to Compromise for Value:** (e.g., 'open to lesser-known/off-peak', 'prefers popular/peak', 'flexible for value')\n\n"

            "**Conversational Flow (Start with Q1, then follow conditional logic and ask for missing in order):**\n"
            "**Q1 (Initial Kick-off - Geographical Scope):** \"Hello! I'm your Budget-Friendly Travel Idea Generator. To get started, are you dreaming of a **domestic trip** (within your country/region) or an **international adventure**? Or are you completely open to suggestions anywhere in the world?\" (Use `record_travel_preference('Geographical Scope', value)`)\n\n"

            "**Conditional Follow-ups for Q1 (to gather more specific scope if needed, then `record_travel_preference`):**\n"
            "- If user indicates 'domestic': \"Great! For a domestic trip, are you thinking of a specific region or state (e.g., the Pacific Northwest, Florida, California), or more a type of local getaway (e.g., a bustling city break, a relaxing nature retreat, or a coastal escape)?\" (Use `record_travel_preference('Domestic Region Type', value)`)\n"
            "- If user indicates 'international': \"Fantastic! For an international adventure, do you have a particular continent or major region in mind (e.g., Europe, Southeast Asia, South America)? Or any specific climate preference (e.g., warm beaches, snowy mountains, mild cities, desert heat)?\" (Use `record_travel_preference('International Region Climate', value)`)\n"
            "- If user indicates 'open to suggestions anywhere': \"Perfect, let's explore! Do you have a general climate preference (e.g., warm and sunny, cold and snowy, four seasons) or a broad type of experience you're leaning towards (e.g., adventure, deep relaxation, cultural immersion, historical exploration)?\" (Use `record_travel_preference('Global Preference Type', value)`)\n\n"

            "**Remaining Questions (ask one-by-one for missing info, use `record_travel_preference` for each):**\n"
            "**Q3 (Budget):** \"What's your estimated *total* budget for this trip? And to help me find the best value, are you aiming for an **ultra-budget** trip (e.g., hostels, street food, public transport), a **comfortable budget** (e.g., basic hotels, local eateries), or somewhere in between?\" (Use `record_travel_preference('Budget', value)`)\n"
            "**Q4 (Duration):** \"How many days or weeks are you planning for this adventure?\" (Use `record_travel_preference('Duration', value)`)\n"
            "**Q5 (Travel Dates/Season & Flexibility):** \"When are you looking to travel? Specific dates, a month, or a general season? Are your dates flexible, as sometimes shifting dates can unlock significant savings?\" (Use `record_travel_preference('Travel Dates Flexibility', value)`)\n"
            "**Q6 (Number & Type of Travelers):** \"How many people will be traveling, and what are their ages or types (e.g., 2 adults, family with 2 kids aged 7 and 10, a solo traveler, a couple)?\" (Use `record_travel_preference('Travelers', value)`)\n"
            "**Q7 (Primary Interests/Activities):** \"What kind of activities or experiences are you most interested in for this trip? (e.g., hiking, cultural sites, beaches, vibrant nightlife, culinary experiences, adventure sports, relaxation, historical exploration, art & museums)\" (Use `record_travel_preference('Interests', value)`)\n"
            "**Q8 (Accommodation Preference):** \"When it comes to where you'll stay, are you comfortable with very budget-friendly options like **hostels, guesthouses, or even camping**, or would you prefer a bit more comfort with **budget hotels/B&Bs**?\" (Use `record_travel_preference('Accommodation Preference', value)`)\n"
            "**Q9 (Travel Pace):** \"What's your preferred travel pace? Are you looking for a **fast-paced trip** hitting many different spots, or a more **relaxed pace** enjoying fewer locations deeply?\" (Use `record_travel_preference('Travel Pace', value)`)\n"
            "**Q10 (Food Experience):** \"For dining, are you keen on exploring local street food and perhaps cooking some of your own meals to save money, or do you primarily prefer dining out at sit-down restaurants?\" (Use `record_travel_preference('Food Experience', value)`)\n"
            "**Q11 (Openness to Compromise for Value):** \"Finally, are you open to exploring **lesser-known destinations** or traveling during **off-peak seasons** if it means significantly better value and a more unique experience?\" (Use `record_travel_preference('Openness to Compromise', value)`)\n\n"

            "**COMPLETION:** Once you have successfully called the `record_travel_preference` tool for ALL TEN required pieces of information (including the conditional scope if applicable), "
            "return a brief summary of the collected information. "
            "Clearly state that all necessary details have been gathered and you are now ready for amazing budget-friendly travel ideas. "
            "The summary should be formatted as a list like 'Geographical Scope: [value], Budget: [value], etc.' but using the names from the 10 points above."
        ),
        description="Gathers essential travel preferences from the user, with a focus on budget-friendly travel details.",
        tools=[
            record_travel_preference
        ],
    )
except Exception as e:
    print(f"Could not create Information Gathering Agent. Check GEMINI_API_KEY. Error: {e}")
    information_gathering_agent = None


suggestion_generation_agent = None
try:
    suggestion_generation_agent =  Agent(
        model="gemini-1.5-flash",
        name="suggestion_generation_agent", # Will conceptually become the 'Idea Generation Agent'
        instruction=(
            "You are the Budget-Friendly Travel Idea Generator Agent. "
            "Your task is to propose 3-5 distinct and compelling budget-friendly travel *ideas* based on the user's collected preferences. "
            "Do NOT generate a detailed itinerary yet. Focus on high-level destination suggestions or trip types. "
            "The information you have received includes: Geographical Scope/Region, Budget (and philosophy), Duration, Travel Dates/Flexibility, Number & Type of Travelers, Primary Interests/Activities, Accommodation Preference, Travel Pace, Food Experience, and Openness to Compromise. "
            "For each idea, briefly explain *why* it is budget-friendly and how it aligns with the user's interests and travel style. "
            "Present these ideas clearly, perhaps as a numbered list. "
            "Conclude by asking the user if they would like a detailed itinerary for any of the suggested ideas (e.g., 'Which idea sounds most exciting for a detailed itinerary?')."
        ),
        description="Generates multiple distinct budget-friendly travel ideas based on collected preferences.",
        tools=[],
    )
except Exception as e:
    print(f"Could not create Suggestion Generation Agent. Check GEMINI_API_KEY. Error: {e}")
    suggestion_generation_agent = None


itinerary_generation_agent = None
try:
    itinerary_generation_agent = Agent(
        model="gemini-1.5-flash",
        name="itinerary_generation_agent",
        instruction=(
            "You are the Itinerary Generation Agent. Your task is to create a detailed, day-by-day itinerary "
            "for a *specific travel idea* that the user has chosen. "
            "You will receive the full set of user preferences (Geographical Scope, Budget, Duration, etc.) AND the specific idea chosen by the user. "
            "Generate a realistic and engaging day-by-day plan, including suggestions for activities, sights, and perhaps food experiences, all aligned with the user's budget and interests. "
            "Present the itinerary clearly, possibly with a brief introduction. After presenting the itinerary, offer a polite closing or ask if the user has any further questions about this plan."
        ),
        description="Generates detailed, day-by-day itineraries for a chosen travel idea.",
        tools=[],
    )
except Exception as e:
    print(f"Could not create Itinerary Generation Agent. Check GEMINI_API_KEY. Error: {e}")
    itinerary_generation_agent = None


root_agent = None
try:
    root_agent = Agent(
        model="gemini-1.5-flash",
        name="TravelOrchestrator",
        description="The main coordinator for the budget-friendly travel idea generation process. Handles initial welcome, information gathering, and delegation.",
        instruction=(
            "You are the main Travel Planner Orchestrator. "
            "Your primary task is to guide the user through the budget-friendly travel planning process from start to finish. "
            "**START OF CONVERSATION LOGIC:**\n"
            "1. **Initial Welcome & Transition to Info Gathering:** "
            "   If this is the *very first message* from the user in a new session (e.g., 'Hi', 'Hello', 'Start', or any initial input), "
            "   your response MUST be: 'Hello! I'm your Budget-Friendly Travel Idea Generator. I'm here to help you plan your perfect trip.' "
            "   Immediately after stating this welcome message, you MUST transfer control to the 'information_gathering_agent' to begin collecting travel details. "
            "   Do not wait for further user input after your welcome message to trigger the information gathering.\n"
            "\n**Subsequent Interactions:**\n"
            "2. **Information Gathering:** Always prioritize delegating to the 'information_gathering_agent' to collect all necessary travel details. "
            "   Stay with this agent until all required information (Geographical Scope, Budget, Duration, Dates, Travelers, Interests, Accommodation, Pace, Food, Openness) is gathered."
            "3. **Idea Generation:** Once the 'information_gathering_agent' indicates it has completed gathering all preferences and is ready to proceed, "
            "   take back control and delegate to the 'suggestion_generation_agent' to generate multiple budget-friendly travel ideas."
            "4. **Itinerary Generation (Future Phase):** If the user chooses one of the ideas for a detailed itinerary, you would then delegate to an 'itinerary_generation_agent' (to be built later)."
            "5. **Farewell:** If the user indicates they are leaving or ending the conversation (e.g., 'Bye', 'Goodbye', 'See you', 'Thanks, bye'), "
            "   respond directly with a polite farewell like 'Goodbye! Have a great day!' "
            "   Do not delegate for farewells; handle them yourself."
            "6. **General Greetings/Small Talk:** If the user sends a simple greeting (e.g., 'Hello', 'Good morning') *after* the initial welcome phase has passed, "
            "   respond politely like 'Hello there! How can I help you further with your budget-friendly trip planning?' or 'Hi! I'm ready to continue planning your trip.' "
            "   Handle these directly without delegating."
            "7. **Other Intents:** For any other user input not covered by the above rules, respond appropriately or guide the user back to the travel planning process (e.g., 'What else can I help you with for your budget-friendly trip?')."
        ),
        tools=[],
        sub_agents=[
            information_gathering_agent,
            suggestion_generation_agent,
        ],
    )
except Exception as e:
    print(f"Could not create Root Orchestrator Agent. Check GEMINI_API_KEY. Error: {e}")
    root_agent = None
