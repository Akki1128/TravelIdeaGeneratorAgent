import os
import json
import requests
from typing import Optional
from datetime import datetime
from google.genai import types  # type: ignore
from dotenv import load_dotenv
from google.adk.agents import Agent # type: ignore
#from google.adk.runners import Runner # type: ignore
#from google.adk.models.lite_llm import LiteLlm 
#from google.adk.sessions import InMemorySessionService # type: ignore

load_dotenv()

def record_travel_preference(preference_name: str, value: str, session_id: str = "default_session") -> str:
    """Records a specific travel preference provided by the user.
    This tool primarily serves to signal the agent that a piece of information
    has been captured and processed.
    """
    print(f"DEBUG: Storing preference '{preference_name}': '{value}' for session '{session_id}'")
    return f"Successfully recorded {preference_name} as {value}."


print("Travel preference tool defined.")

def suggestion_completion_tool(session_id: str = "default_session") -> str:
    """Signals that the suggestion generation agent has completed its task of generating and presenting travel ideas.
    This tool provides a clear signal for the orchestrator to take the next action.
    """
    print(f"DEBUG: Suggestion generation completed for session '{session_id}'")
    return ""

def format_date_for_api(date_str: str) -> str:
    """
    Converts a date string (DD/MM/YYYY or YYYY-MM-DD) to YYYY-MM-DD format.
    """
    try:
        # Try parsing as DD/MM/YYYY first
        dt_obj = datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        try:
            # If that fails, try YYYY-MM-DD
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # If both fail, raise an error
            raise ValueError(f"Date format not recognized: {date_str}. Expected DD/MM/YYYY or YYYY-MM-DD.")
    # Return in YYYY-MM-DD format, as required by API
    return dt_obj.strftime("%Y-%m-%d")


def search_flights(
    departure_city: str,
    departure_country_code: str, 
    destination_city: str,
    destination_country_code: str, 
    start_date: str, 
    end_date: str,    
    session_id: str = "default_session"
) -> str:
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
    if not RAPIDAPI_KEY:
        return json.dumps({"error": "RapidAPI key not configured. Please set RAPIDAPI_KEY in your .env file."})

    url = "https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip" 

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "kiwi-com-cheap-flights.p.rapidapi.com"
    }

    try:
        formatted_start_date_base = format_date_for_api(start_date)
        formatted_end_date_base = format_date_for_api(end_date)
    except ValueError as e:
        return json.dumps({"error": f"Invalid date format provided to flight search: {e}. Please ensure dates are DD/MM/YYYY or YYYY-MM-DD."})

    formatted_start_date = f"{formatted_start_date_base}T00:00:00"
    formatted_end_date = f"{formatted_end_date_base}T00:00:00"

    # Determine source and destination format: City:name_code or Country:XX
    formatted_departure_location = ""
    if departure_city.lower() == "country" and len(departure_country_code) == 2:
        formatted_departure_location = f"Country:{departure_country_code.strip().upper()}"
    else:
        formatted_departure_location = f"City:{departure_city.strip().lower()}_{departure_country_code.strip().lower()}"

    formatted_destination_location = ""
    if destination_city.lower() == "country" and len(destination_country_code) == 2:
        formatted_destination_location = f"Country:{destination_country_code.strip().upper()}"
    else:
        formatted_destination_location = f"City:{destination_city.strip().lower()}_{destination_country_code.strip().lower()}"
    
    params = {
        "round_trip": "1",
        "source": formatted_departure_location,
        "destination": formatted_destination_location,
        "outboundDepartmentDateStart": formatted_start_date, 
        "outboundDepartmentDateEnd": formatted_end_date,
        "inboundDepartureDateStart": formatted_start_date, 
        "inboundDepartureDateEnd": formatted_end_date,     
        "adults": "1",
        "children": "0",
        "infants": "0",
        "currency": "USD",
        "limit": "10", 
        "locale": "en",
        "handbags": "1",
        "holdbags": "0",
        "cabinClass": "ECONOMY",
        "sortBy": "QUALITY",
        "sortOrder": "ASCENDING",
        "applyMixedClasses": "true",
        "allowReturnFromDifferentCity": "true",
        "allowChangeInboundDestination": "true",
        "allowChangeInboundSource": "true",
        "allowDifferentStationConnection": "true",
        "enableSelfTransfer": "true",
        "allowOvernightStopover": "true",
        "enableTrueHiddenCity": "true",
        "enableThrowAwayTicketing": "true",
        # "outbound": "SUNDAY,MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY,SATURDAY", 
        "transportTypes": "FLIGHT",
        "contentProviders": "FRESH,KAYAK,KIWI", 
    }

    print(f"DEBUG: Request URL: {url}")
    print(f"DEBUG: Request Headers: {headers}")
    print(f"DEBUG: Request Params: {params}")
    print(f"DEBUG: Calling RapidAPI for Kiwi.com flights: {formatted_departure_location} to {formatted_destination_location} ({formatted_start_date} to {formatted_end_date})")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        print(f"DEBUG: API Response Status Code: {response.status_code}")
        print(f"DEBUG: API Raw Response Text: {response.text}")
        response.raise_for_status() 
        data = response.json()

        # Check for the specific downstream error from Kiwi.com (code 422)
        if data.get('metadata', {}).get('statusPerProvider'):
            for provider_status in data['metadata']['statusPerProvider']:
                if provider_status.get('provider', {}).get('id') == 'ContentProvider:KIWI' and \
                   provider_status.get('errorHappened') and \
                   "code:422" in provider_status.get('errorMessage', ''):
                    return json.dumps({
                        "error": "Flight API (Kiwi.com via RapidAPI) encountered a processing error (code 422) for this specific query. It might be due to the route, dates being too far in the future, or the complexity of the search for this API. Please try different dates or a major international hub if you haven't already."
                    })

        # Check if itineraries were found and are valid
        if data and data.get('itinerariesCount', 0) > 0 and data.get('itineraries'):
            cheapest_flight = data['itineraries'][0] 
            
            if cheapest_flight and 'price' in cheapest_flight and 'deep_link' in cheapest_flight:
                return json.dumps({
                    "min_price": cheapest_flight['price'],
                    "booking_link": cheapest_flight['deep_link'],
                    "currency": cheapest_flight.get('currency', params['currency'])
                })
        
        # Fallback if itinerariesCount is 0 (no flights found) but no specific 422 caught or data structure is unexpected
        return json.dumps({"error": "No budget-friendly flights found for these dates and destination."})

    except requests.exceptions.Timeout:
        return json.dumps({"error": "Flight API request timed out. Please try again later."})
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Flight API request failed: {e}. Check network, RapidAPI key, or ensure source/destination format is correct (e.g., City:warsaw_pl or Country:GB)."})
    except Exception as e:
        return json.dumps({"error": f"Error processing flight data: {e}"})

information_gathering_agent = None
try:
    information_gathering_agent = Agent(
        model="gemini-1.5-flash",
        name="information_gathering_agent",
        instruction=(
            "You are the Information Gathering Agent for a budget-friendly travel planner. "
            "Your primary goal is to politely and systematically gather all necessary travel details from the user. "
            "You MUST gather the following five (5) pieces of information. If the user provides multiple pieces of information in one go, extract them and mark them as gathered. If any information is missing, ask for it in a single, consolidated follow-up.\n\n"

            "**Initial Greeting and Question:**\n"
            "\"Hello! To help me create the best personalized travel ideas for you, please tell me:\n"
            "1.  **Your Departure City/Airport:** (e.g., 'New York', 'London Heathrow')\n"
            "2.  **Your desired Geographical Scope/Region:** (e.g., 'domestic', 'international', 'open to anywhere', 'Europe', 'Southeast Asia')\n"
            "3.  **Your Trip Duration:** (e.g., '3 days', '1 week', '10 days')\n"
            "4.  **Your Travel Start Date:** (e.g., '01/07/2025' or '2025-12-01')\n"
            "5.  **Your Primary Interests/Activities:** (e.g., 'hiking', 'museums', 'beaches', 'foodie adventures')\n\n"
            "Providing as much detail as possible upfront helps me give you the best suggestions!\"\n\n"

            "**During Information Gathering:**\n"
            "Use the `record_travel_preference` tool to store each piece of information once you receive it. "
            "Your conversational response MUST be in natural language only and should be concise. "
            "Acknowledge the information received with a brief, natural language confirmation (e.g., 'Got it!', 'Thanks for that!'). "
            "Do NOT include the tool call code (e.g., `print(...)`) or its direct output in your conversational response. "
            "\n\n"
            "**Special Handling for Departure City (Q1):**\n"
            "When the user provides their 'Departure City/Airport', record it using `record_travel_preference('Departure City', user_provided_city_value)`. No further tool calls or clarifications are needed for this field for now. Proceed to check for other missing information.\n\n"

            "**Special Handling for Travel Dates (Q4):**\n"
            "When the user provides their 'Travel Dates', make sure to extract both the start and end dates. Record them separately as `record_travel_preference('Start Date', start_date_value)` and `record_travel_preference('End Date', end_date_value)`. Guide the user to provide dates in DD/MM/YYYY or BCE-MM-DD format if they give ambiguous input.\n\n"
            "If the user provides a duration like '1 week' and a start date '2025-07-01', you must internally convert '1 week' to 7 days and calculate the end date '2025-07-07'."
            
            "**General Missing Information Handling:**\n"
            "If any other information (Geographical Scope, Duration, Interests) is missing after the user's initial or subsequent responses, identify *all* the missing items and ask for them in a single, clear follow-up question. For example: "
            "\"Thanks for [provided info]! I still need to know your [Missing Q1], [Missing Q2], and [Missing Q3]. Could you please provide those?\"\n\n"

            "**CONDITIONAL FOLLOW-UPS for Geographical Scope (Q2):**\n"
            "After the initial 5 questions are answered, you should only ask clarifying questions about 'Geographical Scope/Region' IF the user's initial input for this field was general (e.g., 'domestic', 'international', or 'open to anywhere'). "
            "**If the user has already provided a specific continent, sub-continent, or major region (e.g., 'Europe', 'Southeast Asia', 'North America', 'South America', 'East Asia', 'Middle East', 'Africa', 'Australia'), then NO further clarification is needed for the Geographical Scope; it is considered complete.** "
            "For general inputs, use the following to refine:\n"
            "- If user indicated 'domestic': \"Great! For a domestic trip, are you thinking of a specific region or state (e.g., the Pacific Northwest, Florida, California), or more a type of local getaway (e.g., a bustling city break, a relaxing nature retreat, or a coastal escape)?\" (Use `record_travel_preference('Domestic Region Type', value)`)\n"
            "- If user indicated 'international' (and did NOT specify a continent/major region): \"Fantastic! For an international adventure, do you have a particular continent or major region in mind (e.g., Europe, Southeast Asia, South America)? Or any specific climate preference (e.g., warm beaches, snowy mountains, mild cities, desert heat)?\" (Use `record_travel_preference('International Region Climate', value)`)\n"
            "- If user indicated 'open to suggestions anywhere': \"Perfect, let's explore! Do you have a general climate preference (e.g., warm and sunny, cold and snowy, four seasons) or a broad type of experience you're leaning towards (e.g., adventure, deep relaxation, cultural immersion, historical exploration)?\" (Use `record_travel_preference('Global Preference Type', value)`)\n\n"

            "**COMPLETION:** Once you have successfully called the `record_travel_preference` tool for ALL FIVE required pieces of information (Departure City, Geographical Scope, Duration, Start Date, End Date, including any conditional scope details if applicable), "
            "return a brief summary of the collected information in natural language (not use any print or code formation for showing the summary)."
            "Clearly state that all necessary details have been gathered and you are now ready for amazing budget-friendly travel ideas."
            "The summary should be formatted as a list like 'Departure City: [value], Geographical Scope: [value], etc.' using the names from the 5 points above."
        ),
        description="Gathers essential travel preferences from the user, with a focus on budget-friendly travel details, including departure location.",
        tools=[
            record_travel_preference,
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
            "You are the Budget-Friendly Travel Idea Generator Agent. "
            "Your primary task is to propose 5 distinct and compelling budget-friendly travel *ideas* (destinations) based on the user's collected preferences. "
            "The information you have received includes: Departure City/Airport, Geographical Scope/Region, Duration, Start Date, End Date, and Primary Interests/Activities. "
            "**Crucially, you MUST use the `search_flights` tool to verify flight costs and ensure your suggestions are truly budget-friendly.** "

            "**VERY IMPORTANT for Flight Search Parameters:**\n"
            "The `search_flights` tool requires the `source` and `destination` parameters to be in a specific format: `City:cityname_countrycode` (e.g., `City:newyork_us`, `City:london_uk`, `City:delhi_in`). Sometimes it can also take `Country:XX` (e.g., `Country:GB`).\n"
            "**You are fully responsible for determining the correct `cityname_countrycode` or `Country:XX` for ALL locations you pass to `search_flights` (both the user's departure location and each brainstormed destination).**\n"
            "   - For the user's **departure location**, identify its primary airport city and its corresponding 2-letter ISO country code. (e.g., if 'San Francisco' is the departure city, use 'sanfrancisco' and 'us'). If the user implies a departure country (e.g., 'from the UK'), you can use 'Country' as `departure_city` and 'UK' as `departure_country_code`.\n"
            "   - For each **brainstormed destination**, identify the most appropriate airport city and its 2-letter ISO country code. \n"
            "   - **Critical Strategy for International Destinations:** For long-haul international trips (e.g., US to Asia), when you brainstorm a destination that is not a major international gateway (e.g., Rishikesh in India), **you MUST first search flights to the nearest *major international airport hub* for that region** (e.g., for Rishikesh, search to Delhi - `City:delhi_in`, or for Munnar, search to Kochi - `City:kochi_in`). This is because smaller airports may not have reliable direct international flight data in the API, or the API might fail for long-distance searches to them. The idea is to find a budget-friendly flight *to the country*, and then the detailed itinerary can suggest further local travel from that main hub. For domestic flights, you can continue to use the nearest regional airport if appropriate.\n" # <-- **THIS IS THE KEY CHANGE**

            "**Workflow:**\n"
            "1. **Brainstorm Destinations:** Based on the user's geographical scope, duration, dates, and interests, brainstorm a list of **6-8 potential destinations** that could align with 'budget-friendly' travel. Consider a diverse set of options within the specified region/interests. When brainstorming, explicitly think about major airport hubs or popular entry points for the region.\n"
            "2. **Determine Country Codes, Verify Flights & Select Best Ideas:** For each brainstormed destination:\n"
            "  a. **First, perform an internal lookup/reasoning step:** Determine the most accurate city name and its 2-letter ISO country code that the `search_flights` API would recognize, especially considering the nearest airport for non-airport destinations as described above."
            "  b. **Determine the 2-letter ISO country code for the user's Departure City.** If the user only provides a country (e.g. 'UK'), treat 'Country' as the city name and the country code as 'uk'.\n"
            "  c. **Then, call the `search_flights` tool**, passing the precisely formatted city names (e.g., 'London' for `destination_city`, 'uk' for `destination_country_code`) along with the dates.\n"
            "  **Handle API Errors:** If `search_flights` returns an error (e.g., \"API request failed\" or \"No budget-friendly flights found\"), analyze the error. If it indicates a problem with the city/country code, try a different, more common airport in the region, or move on to the next brainstormed idea. If it's a general API issue, note it. \n"
            "  From the destinations with verified, budget-friendly flights, select the **5 best ideas** that seem genuinely budget-friendly and best match the user's preferences (duration, interests). If fewer than 5 ideas are found, present what you have.\n"
            "3. **Present Ideas:** For each of the 5 selected ideas, briefly explain *why* it is budget-friendly (e.g., 'known for affordable living and travel,' 'good value for accommodation and food', 'flights found for X USD') and how it aligns with the user's interests and travel style. "
            "Present these ideas clearly, perhaps as a numbered list. "
            "4. **Signal Completion and Prompt User:** After presenting the ideas, immediately ask the user which idea sounds most exciting for a detailed itinerary (e.g., 'Which idea sounds most exciting for a detailed itinerary?'). **This is your *ABSOLUTE FINAL conversational output*. Immediately after this question, you MUST call the `suggestion_completion_tool()` to signal that you have completed your task. Do NOT generate ANY further natural language text, process any subsequent user input, or attempt to transfer control to any other agent. Control will return to the orchestrator automatically.**"
        ),
        description="Generates multiple distinct budget-friendly travel ideas based on collected preferences.",
        tools=[
            suggestion_completion_tool,
            search_flights,
        ],
    )
    print(f"Agent '{suggestion_generation_agent.name}' created using model '{suggestion_generation_agent.model}'.")
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
            "You will receive the full set of user preferences (Departure City, Geographical Scope, Duration, Start Date, End Date, etc.) AND the specific idea chosen by the user. "
            "Generate a realistic and engaging day-by-day plan, including suggestions for activities, sights, and perhaps food experiences, all aligned with the user's budget and interests. "
            "Present the itinerary clearly, possibly with a brief introduction. After presenting the itinerary, offer a polite closing or ask if the user has any further questions about this plan."
        ),
        description="Generates detailed, day-by-day itineraries for a chosen travel idea.",
        tools=[],
    )
    print(f"Agent '{itinerary_generation_agent.name}' created using model '{itinerary_generation_agent.model}'.")
except Exception as e:
    print(f"Could not create Itinerary Generation Agent. Check GEMINI_API_KEY. Error: {e}")
    itinerary_generation_agent = None

# --- Root Orchestrator Agent ---

root_agent = None
try:
    root_agent = Agent(
        model="gemini-1.5-flash",
        name="TravelOrchestrator",
        description="The main coordinator for the budget-friendly travel idea generation process. Handles initial welcome, information gathering, and delegation.",
        instruction=(
            "You are the main Travel Planner Orchestrator. "
            "Your primary task is to guide the user through the budget-friendly travel planning process from start to finish. "
            "**Critically, when you transfer control to another agent, do NOT announce this transfer to the user. Perform the transfer silently.**\n\n" # MOVED: Global negative constraint for announcements
            "**START OF CONVERSATION LOGIC:**\n"
            "1. **Initial Welcome & Transition to Info Gathering:** "
            "   When a new session begins, or as the initial interaction, your response MUST immediately be: 'Hello! I'm your Budget-Friendly Travel Idea Generator. I'm here to help you plan your perfect trip.' "
            "   Immediately after stating this welcome message, you MUST transfer control to the 'information_gathering_agent' to begin collecting travel details. "
            "   Do not wait for any user input after your welcome message to trigger the information gathering.\n"
            "\n**Subsequent Interactions:**\n"
            "2. **Information Gathering:** Always prioritize delegating to the 'information_gathering_agent' to collect all necessary travel details (Departure City, Geographical Scope, Duration, Start Date, End Date, Interests). "
            "   Stay with this agent until all required information is gathered."
            "3. **Idea Generation:** Once the 'information_gathering_agent' finishes its turn by presenting the summary of gathered information and states it is ready for ideas, **you must immediately** take back control and delegate to the 'suggestion_generation_agent' to generate multiple budget-friendly travel ideas. **Do not wait for any user input between the information summary and the idea generation.** The 'suggestion_generation_agent' will then present the ideas and ask the user which idea they'd like an itinerary for."
            "4. **Itinerary Generation Request Handling:** "
            "   After the 'suggestion_generation_agent' presents ideas, calls its `suggestion_completion_tool()`, and asks for a choice, you, the orchestrator, must carefully listen to the user's next response.\n"
            "   - If the user explicitly asks for an itinerary for one of the suggested ideas (e.g., 'Idea 1', 'Generate for idea 2', 'Yes, for the Bali trip', 'Tell me more about option 1'), "
            "     take back control and then **transfer to the 'itinerary_generation_agent'**, ensuring to pass both the initial collected preferences AND the chosen idea details to it.\n"
            "   - If the user declines an itinerary (e.g., 'No thanks', 'Not right now'), offer to generate more ideas or ask if they have other questions related to travel planning. Do not transfer to `itinerary_generation_agent`.\n"
            "   - If the user asks for something else not related to itinerary generation (e.g., 'What about flights?'), handle it appropriately or guide them back to the itinerary choice."
            "5. **Farewell:** If the user indicates they are leaving or ending the conversation (e.g., 'Bye', 'Goodbye', 'See you', 'Thanks, bye'), "
            "   respond directly with a polite farewell like 'Goodbye! Have a great day!' "
            "   Do not delegate for farewells; handle them yourself."
            "6. **Other Intents:** For any other user input not covered by the above rules, respond appropriately or guide the user back to the travel planning process (e.g., 'What else can I help you with for your budget-friendly trip?')."        ),
        tools=[], # No direct tools for the orchestrator in this phase
        sub_agents=[
            information_gathering_agent,
            suggestion_generation_agent,
            itinerary_generation_agent,
        ],
    )
    print(f"Agent '{root_agent.name}' created using model '{root_agent.model}'.")
except Exception as e:
    print(f"Could not create Root Orchestrator Agent. Check GEMINI_API_KEY. Error: {e}")
    root_agent = None

print("All agents for Budget-Friendly Travel Idea Generator defined, strictly following Google-ADK-Experiment patterns.")