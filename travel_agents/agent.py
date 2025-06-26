import os
import json
import requests
from typing import Optional
from datetime import datetime, timedelta
from google.genai import types  # type: ignore
from dotenv import load_dotenv
from google.adk.agents import Agent # type: ignore
#from google.adk.runners import Runner # type: ignore
#from google.adk.models.lite_llm import LiteLlm 
#from google.adk.sessions import InMemorySessionService # type: ignore

load_dotenv()

_amadeus_access_token = None
_amadeus_token_expiry = None


def _get_amadeus_access_token():
    """
    Obtains or refreshes an Amadeus API access token.
    Tokens are cached and refreshed if expired.
    """
    global _amadeus_access_token, _amadeus_token_expiry

    # Check if token is still valid (refresh a bit before actual expiry)
    if _amadeus_access_token and _amadeus_token_expiry and datetime.now() < _amadeus_token_expiry:
        print("DEBUG: Using cached Amadeus access token.")
        return _amadeus_access_token

    # Get credentials from environment variables
    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

    if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
        raise ValueError("Amadeus Client ID and/or Client Secret not configured. Please set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in your .env file.")

    token_url = "https://test.api.amadeus.com/v1/security/oauth2/token" # Using test environment
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'client_id': AMADEUS_CLIENT_ID,
        'client_secret': AMADEUS_CLIENT_SECRET
    }

    try:
        print("DEBUG: Requesting new Amadeus access token...")
        response = requests.post(token_url, headers=headers, data=data, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        token_data = response.json()

        _amadeus_access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3500) # Default to 3500 seconds if not specified
        _amadeus_token_expiry = datetime.now() + timedelta(seconds=expires_in - 60) # Subtract 60 seconds for buffer
        print(f"DEBUG: Successfully obtained Amadeus access token. Expires in ~{expires_in} seconds.")
        return _amadeus_access_token

    except requests.exceptions.Timeout:
        raise ConnectionError("Amadeus token request timed out.")
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to obtain Amadeus token: {e}"
        if response and response.text:
            error_msg += f". Response: {response.text}"
        raise ConnectionError(error_msg)
    except KeyError:
        raise ValueError("Invalid response from Amadeus token endpoint (missing access_token or expires_in).")
    except Exception as e:
        raise Exception(f"An unexpected error occurred while getting Amadeus token: {e}")


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
    Converts a date string (DD/MM/YYYY or YYYY-MM-DD) to YYYY-MM-DD format required by Amadeus.
    """
    try:
        if '/' in date_str:
            # Assume DD/MM/YYYY
            dt_object = datetime.strptime(date_str, "%d/%m/%Y")
        elif '-' in date_str:
            # Assume YYYY-MM-DD
            dt_object = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            raise ValueError("Unsupported date format.")
        return dt_object.strftime("%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date format for Amadeus API: {date_str}. Please use DD/MM/YYYY or YYYY-MM-DD. Error: {e}")


def search_flights(
    departure_airport_code: str, # IATA airport code, e.g., "SFO"
    destination_airport_code: str, # IATA airport code, e.g., "DEL"
    start_date: str, # Format: YYYY-MM-DD
    end_date: str, # Format: YYYY-MM-DD
    num_adults: int = 1,
    max_price: Optional[int] = None, # Optional: maximum price for the flight offer
    max_results: int = 5, # Amadeus 'max' parameter for number of results
    session_id: str = "default_session"
) -> str:
    """
    Searches for flight offers using the Amadeus Flight Offers Search API.
    Note: Requires IATA airport codes for departure and destination.
    """
    try:
        access_token = _get_amadeus_access_token()
    except (ValueError, ConnectionError, Exception) as e:
        return json.dumps({"error": f"Authentication Error: {e}"})

    # Using Amadeus test environment URL
    flight_offers_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json" # Request JSON response
    }

    # Format dates to YYYY-MM-DD as required by Amadeus
    try:
        formatted_departure_date = format_date_for_api(start_date)
        formatted_return_date = format_date_for_api(end_date)
    except ValueError as e:
        return json.dumps({"error": f"Invalid date format: {e}. Please ensure dates are YYYY-MM-DD."})

    params = {
        "originLocationCode": departure_airport_code.upper(), # Ensure uppercase IATA
        "destinationLocationCode": destination_airport_code.upper(), # Ensure uppercase IATA
        "departureDate": formatted_departure_date,
        "returnDate": formatted_return_date,
        "adults": num_adults,
        "currencyCode": "USD", # Default currency, can be made a tool parameter
        "max": max_results, # Limit the number of results
    }

    if max_price is not None:
        params["maxPrice"] = max_price # Optional parameter for max price

    print(f"DEBUG: Calling Amadeus Flight Offers Search API: {flight_offers_url}")
    # print(f"DEBUG: Amadeus Request Headers: {headers}") # Avoid logging sensitive token in production
    print(f"DEBUG: Amadeus Request Params: {params}")

    try:
        response = requests.get(flight_offers_url, headers=headers, params=params, timeout=30) # Increased timeout
        print(f"DEBUG: Amadeus API Response Status Code: {response.status_code}")
        print(f"DEBUG: Amadeus API Raw Response Text: {response.text}")
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data.get('data') and len(data['data']) > 0:
            # Amadeus returns a list of flight offers. We'll extract details from the first one.
            cheapest_offer = data['data'][0] 
            
            price_info = cheapest_offer.get('price', {})
            total_price = price_info.get('total')
            currency = price_info.get('currency', params['currencyCode'])
            
            # Amadeus's deep links can be complex to generate, often handled client-side.
            # For simplicity, we'll provide a message and indicate success.
            # If a direct booking link is crucial, a separate Amadeus API (Flight Create Orders) or
            # a different strategy would be needed.

            if total_price:
                return json.dumps({
                    "min_price": float(total_price),
                    "currency": currency,
                    "message": f"Found a flight offer from {departure_airport_code} to {destination_airport_code} for {total_price} {currency} with Amadeus (test environment). Booking details would typically follow. Please note this is from a test API."
                })
        
        return json.dumps({"error": "No flight offers found for these dates and destination with Amadeus."})

    except requests.exceptions.Timeout:
        return json.dumps({"error": "Amadeus API request timed out. Please try again later."})
    except requests.exceptions.RequestException as e:
        error_message = f"Amadeus API request failed: {e}"
        if response and response.status_code != 200:
            try:
                # Amadeus errors often come in a specific 'errors' array
                error_details = response.json()
                if 'errors' in error_details and isinstance(error_details['errors'], list) and len(error_details['errors']) > 0:
                    first_error = error_details['errors'][0]
                    error_message += f". Amadeus Error: {first_error.get('code', '')} - {first_error.get('detail', first_error.get('title', ''))}"
            except json.JSONDecodeError:
                error_message += f". Raw response: {response.text}"
        return json.dumps({"error": error_message})
    except Exception as e:
        return json.dumps({"error": f"Error processing Amadeus flight data: {e}"})


information_gathering_agent = None
try:
    information_gathering_agent = Agent(
        model="gemini-2.5-flash",
        name="information_gathering_agent",
        instruction=(
            "You are the Information Gathering Agent for a budget-friendly travel planner. "
            "Your primary goal is to politely and systematically gather all necessary travel details from the user. "
            "You MUST gather the following five (5) pieces of information. If the user provides multiple pieces of information in one go, extract them and mark them as gathered. If any information is missing, ask for it in a single, consolidated follow-up.\n\n"

            "**Initial Greeting and Question:**\n"
            "\"Hello! To help me create the best personalized travel ideas for you, please tell me:\n"
            "1. **Your Departure City/Airport:** (e.g., 'New York', 'London Heathrow')\n"
            "2. **Your desired Geographical Scope/Region:** (e.g., 'domestic', 'international', 'open to anywhere', 'Europe', 'Southeast Asia')\n"
            "3. **Your Trip Duration:** (e.g., '3 days', '1 week', '10 days')\n"
            "4. **Your Travel Start Date:** (e.g., '01/07/2025' or '2025-12-01')\n"
            "5. **Your Primary Interests/Activities:** (e.g., 'hiking', 'museums', 'beaches', 'foodie adventures')\n\n"
            "Providing as much detail as possible upfront helps me give you the best suggestions!\"\n\n"

            "**During Information Gathering:**\n"
            "Use the `record_travel_preference` tool to store each piece of information once you receive it. "
            "Your conversational response MUST be in natural language only and should be concise. "
            "Acknowledge the information received with a brief, natural language confirmation (e.g., 'Got it!', 'Thanks for that!'). "
            "Do NOT include the tool call code (e.g., `print(...)`) or its direct output in your conversational response. "
            "\n\n"
            "**Special Handling for Departure City (Q1):**\n"
            "When the user provides their 'Departure City/Airport', record it using `record_travel_preference('Departure City', user_provided_city_value)`. No further tool calls or clarifications are needed for this field for now. Proceed to check for other missing information.\n\n"

            "**Special Handling for Travel Dates (Q4) and Duration (Q3):**\n"
            "When the user provides their 'Travel Dates', make sure to extract the start date. Record it as `record_travel_preference('Start Date', start_date_value)`. Guide the user to provide dates in DD/MM/YYYY or ISO 8601 (YYYY-MM-DD) format if they give ambiguous input.\n\n"
            "If the user also provides a 'Trip Duration', extract it. You MUST then calculate the end date by adding the duration *minus one day* to the start date. This means the start date itself counts as the first day of the trip. For example, if the start date is '01/07/2025' and the duration is '7 days', the end date should be '07/07/2025'. Record the calculated end date as `record_travel_preference('End Date', end_date_value)`. "
            "**It is CRITICAL that the 'End Date' recorded is always chronologically AFTER the 'Start Date'. If the user's input implies an end date that is on or before the start date, you MUST politely ask the user to clarify or provide a valid date range (e.g., 'It seems the return date is before the departure date. Could you please clarify your intended dates?')**\n\n"
            "If the user provides a start date but *not* a duration, you MUST explicitly ask for the duration (e.g., 'Okay, and for how long would you like to travel?'). Do not assume a duration.\n\n"
            "**General Missing Information Handling:**\n"
            "If any other information (Geographical Scope, Interests) is missing after the user's initial or subsequent responses, identify *all* the missing items and ask for them in a single, clear follow-up question. For example: "
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
        model="gemini-2.5-flash",
        name="suggestion_generation_agent",
        instruction=(
            "You are the Budget-Friendly Travel Idea Generator Agent. "
            "Your primary task is to propose 5 distinct and compelling budget-friendly travel *ideas* (destinations) based on the user's collected preferences. "
            "The information you have received includes: Departure City/Airport, Geographical Scope/Region, Duration, Start Date, End Date, and Primary Interests/Activities. "
            "**Crucially, you MUST use the `search_flights` tool to verify flight costs and ensure your suggestions are truly budget-friendly.** "

            "**VERY IMPORTANT for Flight Search Parameters:**\n"
            "The `search_flights` tool now requires **IATA airport codes** (e.g., 'SFO' for San Francisco, 'DEL' for Delhi, 'LHR' for London Heathrow) for the `departure_airport_code` and `destination_airport_code` parameters.\n"
            "**You are fully responsible for determining the correct IATA airport code for ALL locations you pass to `search_flights` (both the user's departure location and each brainstormed destination).**\n"
            "  - For the user's **departure location**, identify its primary IATA airport code (e.g., if 'San Francisco' is the departure city, use 'SFO'). If the user implies a departure country (e.g., 'from the UK'), you should infer the most common international gateway airport in that country (e.g., for 'UK' consider 'LHR' for London Heathrow, or 'LGW' for London Gatwick). Prioritize major international hubs for country-level departure inputs.\n"
            "  - For each **brainstormed destination**, identify the most appropriate **IATA airport code** for that location. \n"
            "  - **Critical Strategy for International Destinations:** For long-haul international trips (e.g., US to Asia), when you brainstorm a destination that is not a major international gateway (e.g., Rishikesh in India), **you MUST first search flights to the nearest *major international airport hub* (IATA code) for that region** (e.g., for Rishikesh, search to DEL for Delhi; for Munnar, search to COK for Kochi). This is because smaller airports may not have reliable direct international flight data in the API. The idea is to find a budget-friendly flight *to the country*, and then the detailed itinerary can suggest further local travel from that main hub. For domestic flights, you can continue to use the nearest regional airport if appropriate.\n"

            "**Workflow:**\n"
            "1. **Brainstorm Destinations:** Based on the user's geographical scope, duration, dates, and interests, brainstorm a list of **6-8 potential destinations** that could align with 'budget-friendly' travel. Consider a diverse set of options within the specified region/interests. When brainstorming, explicitly think about major airport hubs or popular entry points for the region.\n"
            "2. **Determine IATA Codes, Verify Flights & Select Best Ideas:** For each brainstormed destination:\n"
            " a. **First, perform an internal lookup/reasoning step:** Determine the most accurate IATA airport code that the `search_flights` API would recognize, especially considering the nearest major international airport hub for non-airport destinations as described above.\n"
            " b. **Then, call the `search_flights` tool**, passing the precisely determined IATA codes (e.g., 'SFO' for `departure_airport_code`, 'DEL' for `destination_airport_code`) along with the exact start and end dates.\n"
            " **Handle API Errors:** If `search_flights` returns an error (e.g., \"Authentication Error\", \"API request timed out\", \"No flight offers found\"), analyze the error. If it indicates a problem with the IATA code, try a different, more common airport in the region, or move on to the next brainstormed idea. If it's a general API issue, note it. \n"
            " From the destinations with verified, budget-friendly flights, select the **5 best ideas** that seem genuinely budget-friendly and best match the user's preferences (duration, interests). If fewer than 5 ideas are found, present what you have.\n"
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
        model="gemini-2.5-flash",
        name="itinerary_generation_agent",
        instruction=(
            "You are the Itinerary Generation Agent. Your task is to create a **concise, day-by-day itinerary** for a *specific travel idea* that the user has chosen. "
            "Focus *only* on providing the **names of key places or attractions the traveler will visit each day**, without lengthy descriptions of activities or experiences. "
            "The itinerary should be presented as a clear, easy-to-read day-by-day list of these locations, aligned with the user's budget and interests. "
            "After presenting the itinerary, offer a polite closing or ask if the user has any further questions about this plan."
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
        model="gemini-2.5-flash",
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