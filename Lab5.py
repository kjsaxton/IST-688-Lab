import requests
import json
import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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

weather_tool = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get todays weather and forecast and use that to give advice on what to wear",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state/country, like 'Syracuse, NY' or 'Lima, Peru'. If there is a request for weather with no location, use 'Syracuse, NY' as the default",
                },
            },
            "required": ["location"],
        },
    },
}

st.title("What to Wear Bot")
city = st.text_input("Enter a city:", placeholder="e.g. Syracuse, NY")

if st.button("Get advice"):
    location = city if city else "Syracuse, NY"

    messages = [
        {"role": "user", "content": f"What should I wear today in {location}, and what outdoor activities suit the weather?"}
    ]

    first_response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=messages,
        tools=[weather_tool],
        tool_choice="auto",
    )

    first_message = first_response.choices[0].message
    tool_calls = first_message.tool_calls

    if not tool_calls:
        st.markdown(first_message.content)
    else:
        messages.append(first_message)
        for tool_call in tool_calls:
            args = json.loads(tool_call.function.arguments)
            weather_data = get_current_weather(args["location"])
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(weather_data),
            })

        second_response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages,
        )
        st.markdown(second_response.choices[0].message.content)
