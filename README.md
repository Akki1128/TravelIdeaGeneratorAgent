# ✈️ Budget-Friendly Travel Planner (Google-ADK-Powered)

This project demonstrates a multi-agent travel assistant built using the **Google Agent Development Kit (ADK)** and **Gemini 2.5 Flash**. The assistant helps users plan affordable trips by gathering their preferences, searching real-time flight offers via the **Amadeus API**, and suggesting personalized travel ideas followed by day-wise itineraries.

### 💡 Project Highlights

* **Modular Multi-Agent System:**  
  The assistant is structured into three specialized agents — each responsible for a specific phase of the travel planning journey.

* **Root Orchestrator Agent:**  
  Manages the entire flow — from greeting the user to collecting preferences, generating travel ideas, and optionally creating itineraries.

* **Information Gathering Agent:**  
  Collects 5 key travel details from the user: Departure City, Region Scope, Start Date, Duration, and Interests. Also calculates return date automatically.

* **Suggestion Generation Agent:**  
  Generates **budget-friendly travel ideas** using the **Amadeus Flight Offers API**. Ensures suggestions are realistic by verifying flight cost data.

* **Itinerary Generation Agent:**  
  Creates concise, day-wise travel itineraries for the selected destination.

* **Amadeus API Integration:**  
  Dynamically searches flights using real-time data from Amadeus. Supports authentication caching and robust error handling.

* **Gemini 2.5 Flash Powered:**  
  All agents use Google’s latest Gemini 2.5 Flash model for efficient natural language interaction.

---

### 📦 Folder Structure

```
TravelIdeaGeneratorAgent/
│
├── travel_agents/
│   ├── agent.py              # Core agent logic and orchestration
│   ├── .env.                 # Sample .env for API keys
└── requirements.txt          # Dependencies
│
└── README.md                 # This file
```

---

### ⚙️ Setup Instructions

Follow these steps to run the project on your local machine:

#### 1. **Clone the Repository**
```bash
git clone https://github.com/Akki1128/TravelIdeaGeneratorAgent.git
cd TravelIdeaGeneratorAgent/travel_agents
```

#### 2. **Create and Activate a Virtual Environment**
```bash
python -m venv venv
```

Activate the environment:

- On Windows:
  ```bash
  .\venv\Scripts\activate
  ```

- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

#### 3. **Install Python Dependencies**
```bash
pip install -r requirements.txt
```

---

### 🔑 API Keys Configuration

The project requires access to:

- **Google Gemini API**  
- **Amadeus API** (for flight data)

#### Steps:
1. Copy `.env.template` to `.env` inside `multi_tool_agent/`
2. Add your API keys:
   ```dotenv
   GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   AMADEUS_CLIENT_ID="YOUR_AMADEUS_CLIENT_ID"
   AMADEUS_CLIENT_SECRET="YOUR_AMADEUS_CLIENT_SECRET"
   ```

> 💡 Register at [Google AI Studio](https://aistudio.google.com/) and [developers.amadeus.com](https://developers.amadeus.com/) to get your keys.

---

### 🔍 Features in Detail

#### ✅ Travel Preference Collection
- Guided interaction that gathers:
  - Departure city/airport
  - Region scope (e.g., domestic, Europe)
  - Trip start date
  - Duration (calculates return date)
  - Interests (e.g., hiking, museums)
- Validates and formats dates
- Records each input using a custom tool: `record_travel_preference`

#### ✈️ Budget Travel Idea Generator
- Brainstorms 6–8 potential destinations
- Maps each to its nearest **IATA airport code**
- Calls `search_flights()` using the Amadeus API
- Selects 5 best ideas based on flight cost and user interest
- Summarizes results and prompts user for itinerary choice

#### 📅 Itinerary Generator
- Based on the user’s selected destination
- Returns a **day-by-day plan** with major attractions
- Tailored to interests and duration
- Closes with a friendly message

---

### 📌 Agent Overview

| Agent Name                  | Role                                         |
|----------------------------|----------------------------------------------|
| `TravelOrchestrator`       | Master controller, manages agent transitions |
| `information_gathering_agent` | Collects all 5 required inputs from user |
| `suggestion_generation_agent` | Validates ideas using Amadeus API        |
| `itinerary_generation_agent` | Provides day-wise travel plans             |

---

### 🧪 API Reliability & Error Handling

- Graceful fallback messages if Amadeus returns no flights or invalid data
- Flight searches use a **buffered expiry mechanism** to avoid expired tokens
- All tool calls are logged via print statements for easier debugging

---

### 🚀 Example Use Case

1. Anyone can launches the assistant using the google adk web server by executing command in the root directory
   ```bash
      adk web
   ```
2. System gathers travel preferences
3. Agent searches real Amadeus flights and suggests 5 budget options
4. User selects one
5. Assistant generates itinerary instantly for a duration

---

### 🧰 Future Enhancements (Ideas)

- Add hotel search integration (e.g., Booking.com or Expedia)
- Add location-specific travel restrictions or visa requirements
- Add user memory using Google ADK's session storage
- Add Google Maps integration for visual planning

---

### 🛠 Built With

- [Google Agent Development Kit](https://ai.google.dev/)
- [Google Gemini 2.5 Flash](https://ai.google.dev/models/gemini)
- [Amadeus for Developers](https://developers.amadeus.com/)
- [Python 3.9+](https://www.python.org/)
- [dotenv](https://pypi.org/project/python-dotenv/)
- [Requests](https://docs.python-requests.org/en/latest/)

---

### 📄 License

This project is intended for educational and experimental use. No commercial use or redistribution of API keys or responses allowed.
