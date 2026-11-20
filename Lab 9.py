import asyncio
import os
import time

import requests
import streamlit as st
from agents import Agent, Runner, function_tool

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
MODEL = "gpt-5-mini"


# ---------------------------------------------------------------
# Part B: your Lab 5 weather function (unchanged) + a tool wrapper
# ---------------------------------------------------------------
def get_current_weather(location):
    url = f'https://wttr.in/{location}?format=j1'
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise Exception(f'wttr.in error: status {response.status_code}')
    try:
        data = response.json()
    except ValueError:
        raise Exception(f'Could not find a location named {location}')
    current = data['current_condition'][0]
    return {'location': location,
            'temperature': float(current['temp_F']),
            'description': current['weatherDesc'][0]['value'],
            'feels_like': float(current['FeelsLikeF']),
            'humidity': float(current['humidity']),
            'wind_speed': float(current['windspeedMiles']),
            'cloud_cover': float(current['cloudcover']),
            'uv_index': float(current['uvIndex'])}


@function_tool
def get_weather(location: str = "Syracuse, NY") -> dict:
    """Get the current weather for a city.

    Returns temperature and feels-like temperature (both in Fahrenheit),
    a short description, humidity (%), wind speed (mph), cloud cover (%)
    and UV index. Accepts a city with a state or country, such as
    'Syracuse, NY' or 'Lima, Peru'. If no location is given, use 'Syracuse, NY'.
    If the location can't be found, an error is raised.
    """
    return get_current_weather(location)


# ---------------------------------------------------------------
# Part C: the team
# ---------------------------------------------------------------
weather_agent = Agent(
    name="Weather agent",
    instructions=(
        "You are a weather reporter. Always call get_weather for the "
        "requested location first. Then summarize the facts clearly "
        "(temperature, feels-like, conditions, humidity, wind, cloud cover, "
        "UV index). Do NOT give clothing or activity advice. If the tool "
        "returns an error or the location can't be found, say so plainly "
        "and do not invent weather data."
    ),
    tools=[get_weather],
    model=MODEL,
)

stylist_agent = Agent(
    name="Stylist agent",
    instructions=(
        "You are a stylist. You will be given a weather summary. Recommend "
        "what to wear today: layers, footwear, accessories (sunscreen, hat, "
        "umbrella, etc.) and why. Keep it concise and practical. Only use "
        "the weather facts you are given."
    ),
    model=MODEL,
)

activity_agent = Agent(
    name="Activity agent",
    instructions=(
        "You are an outdoor activity planner. You will be given a weather "
        "summary. Suggest 3 to 4 activities that suit the conditions, "
        "including one indoor backup. Keep it concise. Only use the "
        "weather facts you are given."
    ),
    model=MODEL,
)

manager_agent = Agent(
    name="Manager",
    instructions=(
        "You coordinate a team to answer 'what should I wear and do today' "
        "questions. First call weather_report for the location. If it "
        "reports an error or an unknown location, tell the user and stop. "
        "Otherwise pass the weather summary to outfit_advice and "
        "activity_ideas, then combine everything into one friendly answer "
        "with three short sections: Weather, What to wear, What to do."
    ),
    tools=[
        weather_agent.as_tool(
            tool_name="weather_report",
            tool_description="Get a factual summary of today's weather for a "
                             "city. Input: the city, e.g. 'Lima, Peru'.",
        ),
        stylist_agent.as_tool(
            tool_name="outfit_advice",
            tool_description="Recommend what to wear. Input: the weather "
                             "summary text.",
        ),
        activity_agent.as_tool(
            tool_name="activity_ideas",
            tool_description="Suggest activities that suit the weather. "
                             "Input: the weather summary text.",
        ),
    ],
    model=MODEL,
)

# ---------------------------------------------------------------
# Part E: single agent for comparison
# ---------------------------------------------------------------
single_agent = Agent(
    name="Single agent",
    instructions=(
        "You are a 'What to Wear' assistant. Call get_weather for the "
        "user's location (default 'Syracuse, NY'). Then give: a short "
        "weather summary, what to wear today (layers, footwear, "
        "accessories), and 3 to 4 outdoor activities that suit the weather "
        "with one indoor backup. If the location can't be found, say so "
        "and do not invent weather data."
    ),
    tools=[get_weather],
    model=MODEL,
)


# One event loop for the whole app (avoids "Event loop is closed")
@st.cache_resource
def get_event_loop():
    return asyncio.new_event_loop()


def run(agent, prompt):
    start = time.perf_counter()
    result = get_event_loop().run_until_complete(Runner.run(agent, prompt))
    return result, time.perf_counter() - start


# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
st.title("What to Wear Crew")

mode = st.radio("Run with:", ["Team (manager + specialists)", "Single agent"])
city = st.text_input("Enter a city:", placeholder="e.g. Syracuse, NY")

if st.button("Get advice"):
    location = city if city else "Syracuse, NY"
    agent = manager_agent if mode.startswith("Team") else single_agent

    with st.spinner("Working... a team run can take 20 to 40 seconds"):
        result, seconds = run(
            agent, f"What should I wear and do today in {location}?")

    with st.chat_message("assistant"):
        st.write(result.final_output)

    # Part D: behind the scenes
    usage = result.context_wrapper.usage
    with st.expander("Behind the scenes"):
        st.write(f"Model requests: {usage.requests} · "
                 f"Tokens: {usage.total_tokens:,} · "
                 f"Time: {seconds:.1f}s · "
                 f"Answered by: {result.last_agent.name}")
        for item in result.new_items:
            if item.type == "tool_call_item":
                st.write(f"{item.agent.name} called {item.raw_item.name}: "
                         f"{item.raw_item.arguments}")
            elif item.type == "tool_call_output_item":
                st.write(f"result: {str(item.output)[:300]}")
            elif item.type == "handoff_output_item":
                st.write(f"handoff: {item.source_agent.name} -> "
                         f"{item.target_agent.name}")


# ---------------------------------------------------------------
# Part D answers (fill these in from YOUR run of the app)
# ---------------------------------------------------------------
# a. Tools the manager called, in order:
#    TODO: copy from "Behind the scenes" (e.g. weather_report -> ...)
#
# b. What the manager sent to the stylist (full forecast or summary?),
#    and who wrote it:
#    TODO: look at the outfit_advice arguments line. Note that the manager
#    model wrote that text, based on the weather agent's output.
#
# c. Where the extra model requests happened:
#    TODO: think about what runs inside each agent-as-tool (the weather
#    agent's own call to get_weather, the stylist's and activity agent's
#    own model calls) and the manager's final call that writes the answer.
