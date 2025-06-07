import sys
import os
from google.adk.runners import Runner # type: ignore
from google.adk.sessions import InMemorySessionService # type: ignore
from google.adk.agents import Agent # type: ignore
from google.genai import types # type: ignore 
from typing import Dict, Any, Optional

# Adjust sys.path to allow imports from sibling directories at the root level
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Load environment variables from the root .env file
from dotenv import load_dotenv # type: ignore
load_dotenv(os.path.join(current_dir, '.env'))


try:
    from common_agents.common_tools_agents import greeting_agent, farewell_agent
except ImportError as e:
    print(f"ERROR: Could not import common_tools_agents. Ensure 'common_agents' directory exists at root. Error: {e}")
    greeting_agent = None
    farewell_agent = None

try:
    from info_gathering_agent.agent import info_gathering_agent # type: ignore
    # Also import the submit_collected_info tool directly from info_gathering_agent.agent.
    # The orchestrator needs to know about it to understand when its called by the sub-agent.
    from info_gathering_agent.agent import submit_collected_info # type: ignore
except ImportError as e:
    print(f"ERROR: Could not import info_gathering_agent. Ensure 'info_gathering_agent' directory exists at root. Error: {e}")
    info_gathering_agent = None
    submit_collected_info = None


def receive_collected_info_from_agent(
    destination: str,
    dates_duration: str,
    budget: str,
    travel_companions: str,
    interests: str,
    pace_of_travel: str,
    accommodation_preference: str,
    dislikes: str,
) -> Dict[str, Any]: # Return type changed to Dict[str, Any]
    
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
    print(f"\n[RootOrchestrator Tool Call] Received collected data:\n{collected_data}\n")
    return collected_data 


# --- Travel Idea Generator Root Orchestrator Definition ---
travel_orchestrator = None
sub_agents_for_travel_orchestrator = []

# Conditionally add sub-agents only if they were successfully imported
if greeting_agent:
    sub_agents_for_travel_orchestrator.append(greeting_agent)
if farewell_agent:
    sub_agents_for_travel_orchestrator.append(farewell_agent)
if info_gathering_agent:
    sub_agents_for_travel_orchestrator.append(info_gathering_agent)


if sub_agents_for_travel_orchestrator:
    travel_orchestrator = Agent(
        model="gemini-1.5-flash", 
        name="TravelIdeaOrchestrator",
        instruction=(
            "You are the main orchestrator for the Travel Idea Generator. "
            "Your primary role is to direct user requests to the appropriate specialist agent and manage the overall flow."
            "You have access to the following specialized agents and tools:\n"
            "  - `GreetingAgent`: Handles greetings like 'Hi', 'Hello'.\n"
            "  - `FarewellAgent`: Handles farewells like 'Bye', 'Goodbye'.\n"
            "  - `InformationGatheringAgent`: Collects all necessary trip details from the user. It will call the `submit_collected_info` tool when done.\n"
            "  - `receive_collected_info_from_agent` tool: You MUST call this tool when you detect that the `InformationGatheringAgent` has completed its task and has called its `submit_collected_info` tool. Pass all arguments exactly as received from `submit_collected_info`.\n"
            "  - `submit_collected_info` tool (from InformationGatheringAgent): This tool is used by the InformationGatheringAgent to submit data. You should listen for its call and then call your own `receive_collected_info_from_agent` tool immediately.\n"
            "\n\n**Conversation Flow Rules:**"
            "\n1.  **Initial Welcome:** Begin by welcoming the user with the message: 'Welcome to the Travel Idea Generator! I can help you plan your next adventure. What kind of trip are you dreaming of?'"
            "\n2.  **Greetings/Farewells:** If the user's input is a greeting or farewell, **delegate immediately** to the respective agent (`GreetingAgent` or `FarewellAgent`)."
            "\n3.  **Information Gathering:** If the user expresses intent to plan a trip or get ideas (e.g., 'plan a trip', 'travel ideas', 'where should I go?'), "
            "    **delegate all subsequent user input to the `InformationGatheringAgent`** until it completes its task. "
            "    Once the `InformationGatheringAgent` calls its `submit_collected_info` tool, you will capture that data by using your own `receive_collected_info_from_agent` tool, passing all arguments exactly as received from `submit_collected_info`."
            "\n4.  **Post-Information Gathering (Future Step):** Once `receive_collected_info_from_agent` is called, acknowledge that information is complete and state that you are ready to generate ideas (e.g., 'Thank you for providing all the details! I have everything I need to start generating personalized travel ideas for you.'). This will be handled by the SuggestionGenerationAgent in Phase 2."
            "\n5.  **Fallback:** For any other query not covered by the above, politely state that you can only assist with travel planning, greetings, or farewells."
        ),
        description="Orchestrates the process of gathering travel information and will eventually generate trip ideas.",
        tools=[receive_collected_info_from_agent, submit_collected_info], 
        sub_agents=sub_agents_for_travel_orchestrator
    )
    print(f"Agent '{travel_orchestrator.name}' created.")
else:
    print("TravelIdeaOrchestrator not created due to missing sub-agents. Check previous error messages.")
