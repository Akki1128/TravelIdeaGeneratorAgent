import os
import requests
from typing import Optional
from google.genai import types # type: ignore
from dotenv import load_dotenv # type: ignore
from google.adk.agents import Agent # type: ignore
from datetime import datetime, timedelta

load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY is not set in your .env file.")

# Load API Key and Host for Kiwi.com API
KIWI_API_KEY = os.getenv("KIWI_API_KEY")
RAPIDAPI_HOST = "kiwi-com-cheap-flights.p.rapidapi.com"

if not KIWI_API_KEY:
    print("WARNING: KIWI_API_KEY is not set in your .env file. Flight price API calls will fail.")

def record_travel_preference(preference_name: str, value: str, session_id: str = "default_session") -> str:

    return f"Successfully recorded {preference_name} as {value}."

def parse_travel_dates(travel_dates_str: str) -> tuple[str, str]:
    
    today = datetime.now()
    if "next month" in travel_dates_str.lower():
        start_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    elif "flexible" in travel_dates_str.lower() or "open" in travel_dates_str.lower():
        start_date = today
        end_date = today + timedelta(days=180)
    elif "july 2025" in travel_dates_str.lower():
        start_date = datetime(2025, 7, 1)
        end_date = datetime(2025, 7, 31)
    else:
        try:
            parsed_date = datetime.strptime(travel_dates_str.split(' ')[0], "%Y-%m-%d")
            start_date = parsed_date
            end_date = parsed_date + timedelta(days=7)
        except ValueError:
            start_date = today
            end_date = today + timedelta(days=30)

    return start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y")


def get_flight_prices(origin: str, destinations: list[str], travel_dates: str) -> str:
    
    print(f"DEBUG: Attempting to get flight prices for origin: {origin}, destinations: {destinations}, dates: {travel_dates}")

    if not KIWI_API_KEY:
        return "Error: KIWI_API_KEY is not configured. Cannot fetch real-time flight prices."

    url = "https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip"

    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": KIWI_API_KEY
    }

    date_from, date_to = parse_travel_dates(travel_dates)

    results = []
    for dest in destinations:
        formatted_dest = f"City%3A{dest.replace(' ', '_')}" 
        formatted_origin = f"City%3A{origin.replace(' ', '_')}" 

        querystring = {
            "source": formatted_origin,
            "destination": formatted_dest,
            "date_from": date_from, 
            "date_to": date_to,
            "adults": "1", 
            "children": "0",
            "infants": "0",
            "currency": "usd",
            "locale": "en",
            "sortby": "price", 
            "limit": "1", 
            "flight_type": "round",
            "return_from": date_from, 
            "return_to": date_to,
            "one_for_city": "true", 
        }
        print(f"DEBUG: Querying Kiwi API with params: {querystring}")

        try:
            response = requests.get(url, headers=headers, params=querystring, timeout=15)
            response.raise_for_status() 
            data = response.json()

            if data and data.get('data'):
                cheapest_flight = None
                if isinstance(data['data'], list) and data['data']:
                    cheapest_flight = min(data['data'], key=lambda x: x.get('price', float('inf')), default=None)
                elif isinstance(data['data'], dict): 
                     for key, flight_info in data['data'].items():
                         if cheapest_flight is None or flight_info.get('price', float('inf')) < cheapest_flight.get('price', float('inf')):
                             cheapest_flight = flight_info

                if cheapest_flight:
                    price = cheapest_flight.get('price')
                    currency = cheapest_flight.get('currency', 'USD').upper()
                    deep_link = cheapest_flight.get('deep_link', 'N/A')
                    results.append(f"To {dest}: ~{price} {currency}. (Book via: {deep_link[:50]}...)")
                else:
                    results.append(f"To {dest}: No direct flights found or prices unavailable.")
            else:
                results.append(f"To {dest}: No flight data found for this search.")

        except requests.exceptions.Timeout:
            results.append(f"Error fetching flights to {dest}: Request timed out.")
        except requests.exceptions.RequestException as e:
            results.append(f"Error fetching flights to {dest}: {e}")
        except Exception as e:
            results.append(f"An unexpected error occurred for {dest}: {e}")

    if not results:
        return "No flight price data could be retrieved for any of the destinations."
    return "Estimated flight prices (from your departure city to suggested destinations):\n" + "\n".join(results)


information_gathering_agent = None
try:
    information_gathering_agent = Agent(
        model="gemini-1.5-flash",
        name="information_gathering_agent",
        instruction=(
            "You are the Information Gathering Agent for a budget-friendly travel planner. "
            "Your primary goal is to politely and systematically gather all necessary travel details from the user. "
            "You MUST gather the following five (5) pieces of information. If the user provides multiple pieces of information in one go, extract them and mark them as gathered. If any information is missing, ask for it one-by-one:\n"
            "1. **Departure City/Airport:** (Crucial for flight prices)\n"
            "2. **Geographical Scope/Region:** (e.g., 'domestic', 'international', 'open to anywhere', or specific region like 'Southeast Asia', 'Europe', 'city break')\n"
            "3. **Duration:** (e.g., '3 days', '1 week')\n"
            "4. **Travel Dates/Season & Flexibility:** (e.g., 'July 2025', 'next spring', 'flexible')\n"
            "5. **Primary Interests/Activities:** (e.g., 'hiking', 'museums', 'beaches', 'foodie', 'nightlife', 'history', 'adventure')\n\n"

            "**Conversational Flow:**\n"
            "**START:** Begin by first attempting to get the user's departure city/airport, explaining why you need it for best results. Then, ask for the core travel preferences.\n"
            "\"Hello! I'm your Budget-Friendly Travel Idea Generator. To find you the best flight deals and personalized ideas, I need to know your departure city or airport. Would you mind telling me where you'd be flying from? (If your platform supports it, you might be prompted to share your current location for auto-detection).\"\n"
            "**IMPORTANT:** If the user denies location or doesn't provide a city, politely reiterate: \"To give you the most accurate and budget-friendly ideas considering flight prices, I really need your current departure city or airport. Could you please provide it?\"\n"
            "Once Departure City is obtained (via direct input or location access), use `record_travel_preference('Departure City', value)`.\n\n"

            "**CONTINUE GATHERING:** After Departure City is confirmed, proceed to ask for the remaining missing information (Geographical Scope, Duration, Dates, Interests) one-by-one, following any conditional logic for Geographical Scope if applicable. Use the `record_travel_preference` tool to store each piece of information once you receive it. Acknowledge the information received before asking the next question.\n\n"

            "**CONDITIONAL FOLLOW-UPS for Geographical Scope (Q2):**\n"
            "- If user indicates 'domestic': \"Great! For a domestic trip, are you thinking of a specific region or state (e.g., the Pacific Northwest, Florida, California), or more a type of local getaway (e.g., a bustling city break, a relaxing nature retreat, or a coastal escape)?\" (Use `record_travel_preference('Domestic Region Type', value)`)\n"
            "- If user indicates 'international': \"Fantastic! For an international adventure, do you have a particular continent or major region in mind (e.g., Europe, Southeast Asia, South America)? Or any specific climate preference (e.g., warm beaches, snowy mountains, mild cities, desert heat)?\" (Use `record_travel_preference('International Region Climate', value)`)\n"
            "- If user indicates 'open to suggestions anywhere': \"Perfect, let's explore! Do you have a general climate preference (e.g., warm and sunny, cold and snowy, four seasons) or a broad type of experience you're leaning towards (e.g., adventure, deep relaxation, cultural immersion, historical exploration)?\" (Use `record_travel_preference('Global Preference Type', value)`)\n\n"

            "**COMPLETION:** Once you have successfully called the `record_travel_preference` tool for ALL FIVE required pieces of information (Departure City, Geographical Scope, Duration, Dates, Interests, including any conditional scope details), "
            "return a brief summary of the collected information. "
            "Clearly state that all necessary details have been gathered and you are now ready for amazing budget-friendly travel ideas powered by flight price data. "
            "The summary should be formatted as a list like 'Departure City: [value], Geographical Scope: [value], etc.' but using the names from the 5 points above."
        ),
        description="Gathers essential travel preferences from the user, with a focus on budget-friendly travel details, including departure location.",
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
            "Your task is to propose 3-4 distinct and compelling budget-friendly travel *ideas* (destinations) based on the user's collected preferences AND real-time flight price data. "
            "The information you have received includes: Departure City/Airport, Geographical Scope/Region, Duration, Travel Dates/Flexibility, and Primary Interests/Activities. "
            "**Workflow:**\n"
            "1. **Brainstorm Destinations:** Based on the user's geographical scope, duration, dates, and interests, brainstorm a list of 5-10 potential destinations that could align with 'budget-friendly' travel (even without an explicit budget, aim for generally cheaper options or those with good value, and avoid obviously expensive places for the given duration/interests).\n"
            "2. **Get Flight Prices:** For each brainstormed destination, use the `get_flight_prices` tool, providing the user's Departure City and Travel Dates. Interpret the results of this tool call to identify truly low-cost flight options from the brainstormed list. Pay attention to both destination type and overall flight cost. If a destination yields no flights or very expensive flights, it's likely not a budget-friendly option for the user.\n"
            "3. **Select Best Ideas:** From the destinations where flights are most budget-friendly AND which best match the user's remaining preferences (duration, interests), select the 3-4 best ideas. Prioritize ideas that seem genuinely budget-friendly based on the flight prices returned.\n"
            "4. **Present Ideas:** For each of the 3-4 selected ideas, briefly explain *why* it is budget-friendly (mentioning estimated flight costs from your tool call, e.g., 'flights starting at ~$X') and how it aligns with the user's interests and travel style. "
            "Present these ideas clearly, perhaps as a numbered list. "
            "Conclude by asking the user if they would like a detailed itinerary for any of the suggested ideas (e.g., 'Which idea sounds most exciting for a detailed itinerary?')."
        ),
        description="Generates multiple distinct budget-friendly travel ideas based on collected preferences and flight price data.",
        tools=[get_flight_prices], # Add the new tool here
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
            "You will receive the full set of user preferences (Departure City, Geographical Scope, Duration, etc.) AND the specific idea chosen by the user. "
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
            "2. **Information Gathering:** Always prioritize delegating to the 'information_gathering_agent' to collect all necessary travel details (Departure City, Geographical Scope, Duration, Dates, Interests). "
            "   Stay with this agent until all required information is gathered."
            "3. **Idea Generation:** Once the 'information_gathering_agent' indicates it has completed gathering all preferences and is ready for ideas, "
            "   take back control and delegate to the 'suggestion_generation_agent' to generate multiple budget-friendly travel ideas using flight price data. "
            "   The 'suggestion_generation_agent' will also ask the user which idea they'd like an itinerary for."
            "4. **Itinerary Generation Request Handling:** "
            "   After the 'suggestion_generation_agent' presents ideas and asks for a choice, you, the orchestrator, must carefully listen to the user's next response.\n"
            "   - If the user explicitly asks for an itinerary for one of the suggested ideas (e.g., 'Generate for idea 2', 'Yes, for the Bali trip', 'Tell me more about option 1'), "
            "     take back control and then **transfer to the 'itinerary_generation_agent'**, ensuring to pass both the initial collected preferences AND the chosen idea details to it.\n"
            "   - If the user declines an itinerary (e.g., 'No thanks', 'Not right now'), offer to generate more ideas or ask if they have other questions related to travel planning. Do not transfer to `itinerary_generation_agent`.\n"
            "   - If the user asks for something else not related to itinerary generation (e.g., 'What about flights?'), handle it appropriately or guide them back to the itinerary choice."
            "5. **Farewell:** If the user indicates they are leaving or ending the conversation (e.g., 'Bye', 'Goodbye', 'See you', 'Thanks, bye'), "
            "   respond directly with a polite farewell like 'Goodbye! Have a great day!' "
            "   Do not delegate for farewells; handle them yourself."
            "6. **General Greetings/Small Talk:** If the user sends a simple greeting (e.g., 'Hello', 'Good morning') *after* the initial phases have passed, "
            "   respond politely like 'Hello there! How can I help you further with your budget-friendly trip planning?' or 'Hi! I'm ready to continue planning your trip.' "
            "   Handle these directly without delegating."
            "7. **Other Intents:** For any other user input not covered by the above rules, respond appropriately or guide the user back to the travel planning process (e.g., 'What else can I help you with for your budget-friendly trip?')."
        ),
        tools=[],
        sub_agents=[
            information_gathering_agent,
            suggestion_generation_agent,
            itinerary_generation_agent,
        ],
    )
except Exception as e:
    print(f"Could not create Root Orchestrator Agent. Check GEMINI_API_KEY. Error: {e}")
    root_agent = None
