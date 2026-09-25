import requests
# location can be a city, a zip code, an airport code ('SYR'),
# or a landmark ('Eiffel+Tower')
# note: hard codes units to degrees Fahrenheit
def get_current_weather(location):
    url = f'https://wttr.in/{location}?format=j1'
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise Exception(f'wttr.in error: status {response.status_code}')
    try:
        data = response.json()
    except ValueError:
        # unknown locations come back as plain text, not JSON
        raise Exception(f'Could not find a location named {location}')
    # j1 has three top-level sections:
    # current_condition -- one entry, conditions right now
    # weather -- three entries, one per day, each with
    # min/max, astronomy, and hourly forecasts
    # nearest_area -- the location wttr.in actually matched
    current = data['current_condition'][0]
    # two examples; note that some values are nested one level deeper
    return {'location': location,
        'temperature': float(current['temp_F']),
        'description': current['weatherDesc'][0]['value'],
        'feels_like': float(current['FeelsLikeF']),
        'humidity': float(current['humidity']),
        'wind_speed': float(current['windspeedMiles']),
        'cloud_cover': float(current['cloudcover']),
        'uv_index': float(current['uvIndex'])}

print(get_current_weather("Lima, Peru"))

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

city = st.text_input("Enter a city:", placeholder="e.g. Syracuse, NY")

if city:
    location = city
else:
    location = "Syracuse, NY"
