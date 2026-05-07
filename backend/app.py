import os
import requests
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

OPENWEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
OPENWEATHER_BASE = 'https://api.openweathermap.org/data/2.5'
DEFAULT_CITY = 'Delhi'


def format_daily_summary(date_key, forecast_items):
    temps = [item['main']['temp'] for item in forecast_items]
    humidities = [item['main']['humidity'] for item in forecast_items]
    winds = [item['wind']['speed'] for item in forecast_items]
    pop_values = [item.get('pop', 0.0) for item in forecast_items]
    reference = forecast_items[len(forecast_items) // 2]
    weather = reference['weather'][0]

    return {
        'date': date_key,
        'weekday': datetime.fromisoformat(date_key).strftime('%A'),
        'min_temp': round(min(temps), 1),
        'max_temp': round(max(temps), 1),
        'avg_temp': round(sum(temps) / len(temps), 1),
        'humidity': round(sum(humidities) / len(humidities)),
        'wind_speed': round(sum(winds) / len(winds), 1),
        'rain_chance': round(max(pop_values) * 100),
        'condition': weather['main'],
        'description': weather['description'].title(),
        'icon': weather['icon'],
    }


def aggregate_forecast(forecast_items):
    grouped = defaultdict(list)
    for item in forecast_items:
        date_key = item['dt_txt'][:10]
        grouped[date_key].append(item)

    daily = [format_daily_summary(date_key, items) for date_key, items in grouped.items()]
    return sorted(daily, key=lambda entry: entry['date'])


# List of Indian weather news RSS URLs (replace with actual sources)
RSS_SOURCES = [
    'https://www.thehindu.com/rss/section/2294416.xml',  # Climate & Environment
    'https://www.ndtv.com/rss/weather.xml',            # Weather news
    # Add more RSS feed URLs as needed
]


def fetch_news(max_items_per_source: int = 5):
    """Fetch latest news items from defined RSS sources.

    Returns a list of dictionaries with keys: title, link, source, snippet.
    """
    news_items = []
    for src in RSS_SOURCES:
        try:
            resp = requests.get(src, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            # RSS 2.0 typical structure: <channel><item>...</item></channel>
            channel = root.find('channel')
            if channel is None:
                continue
            for item in channel.findall('item')[:max_items_per_source]:
                title_el = item.find('title')
                link_el = item.find('link')
                desc_el = item.find('description')
                title = title_el.text if title_el is not None else ''
                link = link_el.text if link_el is not None else ''
                description = desc_el.text if desc_el is not None else ''
                # Strip HTML tags from description for snippet
                snippet = description.replace('<![CDATA[', '').replace(']]>', '').strip()
                news_items.append({
                    'title': title,
                    'link': link,
                    'source': src,
                    'snippet': snippet,
                })
        except Exception:
            # Skip failing source
            continue
    return news_items


def detect_upcoming_rain(forecast_items, max_hours=3, pop_threshold=0.25):
    upcoming = []
    current_time = datetime.utcnow()
    for item in forecast_items:
        forecast_time = datetime.utcfromtimestamp(item['dt'])
        seconds_until = (forecast_time - current_time).total_seconds()
        if seconds_until < 0 or seconds_until > max_hours * 3600:
            continue

        rain_pop = item.get('pop', 0.0)
        weather_main = item['weather'][0]['main'].lower()
        will_rain = rain_pop >= pop_threshold or 'rain' in weather_main or 'storm' in weather_main
        if will_rain:
            upcoming.append({
                'time': forecast_time.isoformat() + 'Z',
                'rain_chance': round(rain_pop * 100),
                'condition': item['weather'][0]['description'].title(),
            })

    if not upcoming:
        return {
            'is_rain_expected': False,
            'alert_message': 'No rain expected in the next few hours.',
        }

    earliest = upcoming[0]
    return {
        'is_rain_expected': True,
        'next_rain_at': earliest['time'],
        'rain_chance': earliest['rain_chance'],
        'condition': earliest['condition'],
        'alert_message': 'Rain detected soon. Take cover and keep electronics safe.',
        'details': upcoming,
    }


def get_plant_recommendations(month):
    # Indian seasonal plants mapping
    recommendations = {
        1: ["Marigold", "Spinach", "Mustard"],
        2: ["Petunia", "Carrot", "Radish"],
        3: ["Sunflowers", "Tomato", "Chili"],
        4: ["Zinnia", "Cucumber", "Bitter Gourd"],
        5: ["Cosmos", "Ladyfinger", "Brinjal"],
        6: ["Jasmine", "Bottle Gourd", "Pumpkin"],
        7: ["Hibiscus", "Rice", "Maize"],
        8: ["Lotus", "Sugarcane", "Soybean"],
        9: ["Rose", "Cabbage", "Cauliflower"],
        10: ["Dahlia", "Onion", "Garlic"],
        11: ["Chrysanthemum", "Wheat", "Peas"],
        12: ["Pansy", "Potato", "Fenugreek"]
    }
    return recommendations.get(month, ["General indoor plants"])


def fetch_openweather(endpoint, params):
    if not OPENWEATHER_API_KEY:
        raise RuntimeError('WEATHER_API_KEY is not set in environment variables')

    params = {**params, 'appid': OPENWEATHER_API_KEY, 'units': 'metric'}
    response = requests.get(f'{OPENWEATHER_BASE}/{endpoint}', params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def build_current_weather(raw):
    weather = raw['weather'][0]
    return {
        'city': raw['name'],
        'country': raw['sys'].get('country', ''),
        'temperature': round(raw['main']['temp'], 1),
        'feels_like': round(raw['main']['feels_like'], 1),
        'humidity': raw['main']['humidity'],
        'wind_speed': round(raw['wind']['speed'], 1),
        'condition': weather['main'],
        'description': weather['description'].title(),
        'icon': weather['icon'],
        'timestamp': datetime.utcfromtimestamp(raw['dt']).isoformat() + 'Z',
    }


@app.route('/api/status')
def status():
    return jsonify({
        'status': 'ok',
        'message': 'Weather Forecasting backend is running',
    })


@app.route('/api/weather')
def weather():
    city = request.args.get('city', DEFAULT_CITY).strip() or DEFAULT_CITY

    try:
        current = fetch_openweather('weather', {'q': city})
        forecast_raw = fetch_openweather('forecast', {'q': city})
    except requests.HTTPError as exc:
        error_body = exc.response.json() if exc.response is not None else {'message': str(exc)}
        return jsonify({'error': 'Unable to fetch weather data', 'detail': error_body}), exc.response.status_code if exc.response else 500
    except Exception as exc:
        return jsonify({'error': 'Weather service error', 'detail': str(exc)}), 500

    forecast_items = forecast_raw.get('list', [])
    daily = aggregate_forecast(forecast_items)
    rain_alert = detect_upcoming_rain(forecast_items, max_hours=3, pop_threshold=0.25)

    # Fetch Indian weather news from RSS sources
    news = fetch_news()
    return jsonify({
        'current': build_current_weather(current),
        'daily': daily,
        'rain_alert': rain_alert,
        'news': news,
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get('message', '').lower()
    city = data.get('city', DEFAULT_CITY)

    # Rule-based logic with local intelligence
    try:
        # Fetch data to answer specifically
        forecast_raw = fetch_openweather('forecast', {'q': city})
        forecast_items = forecast_raw.get('list', [])
        daily = aggregate_forecast(forecast_items)
        rain_alert = detect_upcoming_rain(forecast_items)
        
        if "rain" in message:
            if rain_alert['is_rain_expected']:
                reply = f"Yes, rain is expected around {datetime.fromisoformat(rain_alert['next_rain_at'].replace('Z', '')).strftime('%I:%M %p')}. {rain_alert['alert_message']}"
            else:
                today_rain = daily[0]['rain_chance'] if daily else 0
                reply = f"There is a {today_rain}% chance of rain today. {rain_alert['alert_message']}"
        
        elif "thunderstorm" in message or "storm" in message:
            thunderstorm_detected = any("thunderstorm" in d['condition'].lower() for d in daily)
            if thunderstorm_detected:
                reply = "Yes, a thunderstorm is expected. Avoid electrical appliances and stay indoors."
            else:
                reply = "No thunderstorms are currently expected in the forecast."
        
        elif "what should i do" in message or "safety" in message:
            reply = "If it rains soon, take cover immediately, keep electronics safe, and avoid open areas. If there's a thunderstorm, stay indoors and unplug appliances."
        
        elif "plant" in message or "crop" in message:
            current_month = datetime.now().month
            plants = get_plant_recommendations(current_month)
            reply = f"For this month ({datetime.now().strftime('%B')}), the best plants to grow in India are: {', '.join(plants)}."
        
        else:
            # Fallback to "LLM" simulation (Hybrid Architecture)
            reply = "I'm your Weather Assistant. I can help with rain forecasts, thunderstorm warnings, safety tips, and plant recommendations. Try asking 'Will it rain today?'"
            
    except Exception as e:
        reply = "I'm having trouble accessing the latest weather data right now. Please try again in a moment."

    return jsonify({'reply': reply})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
