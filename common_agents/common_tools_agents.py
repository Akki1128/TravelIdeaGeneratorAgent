import os
from typing import Optional
from google.adk.agents import Agent
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# --- Common Tools ---
def say_hello(name: Optional[str] = None) -> str:
    """Provides a simple greeting. If a name is provided, it will be used.

    Args:
        name (str, optional): The name of the person to greet. Defaults to a generic greeting if not provided.

    Returns:
        str: A friendly greeting message.
    """
    if name:
        greeting = f"Hello, {name}!"
    else:
        greeting = "Hello there!"
    return greeting

def say_goodbye() -> str:
    """Provides a simple farewell message to conclude the conversation."""
    return "Goodbye! Have a great day."

print("Common Greeting and Farewell tools defined.")

# --- Common Agents ---
greeting_agent = None
try:
    greeting_agent = Agent(
        model="gemini-1.5-flash", # Using Gemini 1.5 Flash for efficiency
        name="GreetingAgent",
        instruction=(
            "You are the Greeting Agent. Your ONLY task is to provide a friendly greeting to the user. "
            "Use the 'say_hello' tool to generate the greeting. "
            "If the user provides their name, make sure to pass it to the tool. "
            "Do not engage in any other conversation or tasks."
        ),
        description="Handles simple greetings and hellos using the 'say_hello' tool.",
        tools=[say_hello],
    )
    print(f"Agent '{greeting_agent.name}' created.")
except Exception as e:
    print(f"Could not create Greeting Agent. Check API Key. Error: {e}")

farewell_agent = None
try:
    farewell_agent = Agent(
        model="gemini-1.5-flash", # Using Gemini 1.5 Flash for efficiency
        name="FarewellAgent",
        instruction=(
            "You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message. "
            "Use the 'say_goodbye' tool when the user indicates they are leaving or ending the conversation "
            "(e.g., using words like 'bye', 'goodbye', 'thanks bye', 'see you'). "
            "Do not perform any other actions."
        ),
        description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
        tools=[say_goodbye],
    )
    print(f"Agent '{farewell_agent.name}' created.")
except Exception as e:
    print(f"Could not create Farewell Agent. Check API Key. Error: {e}")