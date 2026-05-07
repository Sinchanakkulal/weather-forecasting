import { useEffect, useState } from 'react';

type DailyForecast = {
  date: string;
  weekday: string;
  min_temp: number;
  max_temp: number;
  avg_temp: number;
  humidity: number;
  wind_speed: number;
  rain_chance: number;
  condition: string;
  description: string;
  icon: string;
};

type RainAlert = {
  is_rain_expected: boolean;
  next_rain_at?: string;
  rain_chance?: number;
  condition?: string;
  alert_message: string;
};

type CurrentWeather = {
  city: string;
  country: string;
  temperature: number;
  feels_like: number;
  humidity: number;
  wind_speed: number;
  condition: string;
  description: string;
  icon: string;
  timestamp: string;
};

interface NewsItem {
  title: string;
  link: string;
  source: string;
  snippet: string;
}

type WeatherResponse = {
  current: CurrentWeather;
  daily: DailyForecast[];
  rain_alert: RainAlert;
  news?: NewsItem[];
  thunderstorm_alert?: {
    is_thunderstorm: boolean;
    message: string;
    guidance: string[];
  };
};

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-IN', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

function App() {
  const [city, setCity] = useState('Delhi');
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [notificationPermission, setNotificationPermission] = useState<string>(() =>
    typeof Notification === 'undefined' ? 'denied' : Notification.permission
  );

  const loadWeather = async (searchCity = city) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`/api/weather?city=${encodeURIComponent(searchCity)}`);
      const data = await response.json();
      if (!response.ok) {
        setError(data?.error || 'Could not load weather data.');
        setWeather(null);
      } else {
        // Detect thunderstorm/heavy rain based on daily forecasts
        const thunderstormDetected = data.daily.some((d: DailyForecast) => {
          const cond = d.condition.toLowerCase();
          return (
            cond.includes('thunderstorm') ||
            cond.includes('heavy rain') ||
            (d.rain_chance && d.rain_chance >= 80)
          );
        });
        if (thunderstormDetected) {
          data.thunderstorm_alert = {
            is_thunderstorm: true,
            message: 'Thunderstorm detected. Avoid electrical appliances and stay indoors.',
            guidance: [
              'Stay away from windows and doors.',
              'Unplug electronic devices.',
              'Avoid outdoor activities until the storm passes.',
              'Keep emergency supplies handy.'
            ]
          };
        } else {
          data.thunderstorm_alert = {
            is_thunderstorm: false,
            message: '',
            guidance: []
          };
        }
        setWeather(data);
      }
    } catch (err) {
      setError('Network error while fetching weather data.');
      setWeather(null);
    } finally {
      setLoading(false);
    }
  };

  const requestNotificationPermission = async () => {
    if (typeof Notification === 'undefined') {
      setError('Browser notifications are not supported in this environment.');
      return;
    }
    const permission = await Notification.requestPermission();
    setNotificationPermission(permission);
  };

  // Auto-refresh news and weather every 10 minutes
  useEffect(() => {
    const intervalId = setInterval(() => {
      loadWeather();
    }, 10 * 60 * 1000); // 10 minutes
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (weather?.rain_alert?.is_rain_expected && notificationPermission === 'granted') {
      const notificationDelay = 300000;
      const timeoutId = window.setTimeout(() => {
        new Notification('Rain Alert', {
          body: `${weather.rain_alert.alert_message} Expected at ${new Date(
            weather.rain_alert.next_rain_at ?? ''
          ).toLocaleTimeString('en-IN')}`,
        });
      }, notificationDelay);
      return () => window.clearTimeout(timeoutId);
    }
    return undefined;
  }, [weather, notificationPermission]);

  const tomorrow = weather?.daily?.[1] ?? null;
  const nextDays = weather?.daily?.slice(2, 6) ?? [];

  return (
    <div className="app-shell">
      <header>
        <h1>Weather Forecasting App</h1>
        <p>Realtime weather, tomorrow's forecast, and 4-day outlook with rain detection.</p>
      </header>

      <section className="card search-card">
        <form
          className="search-form"
          onSubmit={(event) => {
            event.preventDefault();
            loadWeather(city);
          }}
        >
          <label htmlFor="city">City</label>
          <input
            id="city"
            value={city}
            onChange={(event) => setCity(event.target.value)}
            placeholder="Enter a city name"
            aria-label="City"
          />
          <button type="submit">Load Weather</button>
        </form>
      </section>

      {/* Thunderstorm Warning */}
      {weather?.thunderstorm_alert?.is_thunderstorm && (
        <section className="card alert-card alert-danger">
          <h2>⚡ Thunderstorm Warning</h2>
          <p>{weather.thunderstorm_alert.message}</p>
          <ul>
            {weather.thunderstorm_alert.guidance.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Existing Rain Alert */}
      {weather?.rain_alert && (
        <section className={`card alert-card ${weather.rain_alert.is_rain_expected ? 'alert-warning' : 'alert-info'}`}>
          <h2>{weather.rain_alert.is_rain_expected ? 'Rain Alert' : 'Weather Update'}</h2>
          <p>{weather.rain_alert.alert_message}</p>
          {weather.rain_alert.is_rain_expected && (
            <p>
              Expected at: {new Date(weather.rain_alert.next_rain_at ?? '').toLocaleTimeString('en-IN')} • Chance: {weather.rain_alert.rain_chance}%
            </p>
          )}
          {notificationPermission !== 'granted' && (
            <div className="notification-controls">
              <button type="button" onClick={requestNotificationPermission}>
                Enable rain notifications
              </button>
            </div>
          )}
        </section>
      )}

      {/* News Section */}
      {weather?.news && weather.news.length > 0 && (
        <section className="news-section card">
          <h2>India Weather News</h2>
          <button type="button" onClick={() => loadWeather()}>Refresh News</button>
          {weather.news.map((item, idx) => (
            <article key={idx} className="news-card">
              <h3><a href={item.link} target="_blank" rel="noopener noreferrer">{item.title}</a></h3>
              <p className="snippet">{item.snippet}</p>
              <p className="source">Source: {item.source}</p>
            </article>
          ))}
        </section>
      )}

      {loading && <div className="status-box">Loading weather data...</div>}
      {error && <div className="error-box">{error}</div>}

      {weather && (
        <main>
          <section className="weather-grid">
            <article className="weather-card current-card">
              <h2>Current Weather</h2>
              <div className="weather-summary">
                <div>
                  <strong>{weather.current.temperature}°C</strong>
                  <p>{weather.current.description}</p>
                </div>
                <div>
                  <p>
                    {weather.current.city}, {weather.current.country}
                  </p>
                  <p>Feels like {weather.current.feels_like}°C</p>
                </div>
              </div>
              <div className="weather-details">
                <span>Humidity: {weather.current.humidity}%</span>
                <span>Wind: {weather.current.wind_speed} m/s</span>
                <span>Updated: {new Date(weather.current.timestamp).toLocaleTimeString('en-IN')}</span>
              </div>
            </article>

            {tomorrow && (
              <article className="weather-card">
                <h2>Tomorrow</h2>
                <p className="forecast-date">{formatDate(tomorrow.date)}</p>
                <p>{tomorrow.description}</p>
                <div className="forecast-row">
                  <span>High {tomorrow.max_temp}°C</span>
                  <span>Low {tomorrow.min_temp}°C</span>
                </div>
                <div className="forecast-row">
                  <span>Humidity {tomorrow.humidity}%</span>
                  <span>Rain {tomorrow.rain_chance}%</span>
                </div>
              </article>
            )}
          </section>

          <section className="forecast-section">
            <h2>Next 4 Days</h2>
            <div className="forecast-grid">
              {nextDays.map((day) => (
                <article key={day.date} className="forecast-card">
                  <p className="forecast-date">{formatDate(day.date)}</p>
                  <strong>{day.condition}</strong>
                  <p>{day.description}</p>
                  <span>Avg {day.avg_temp}°C</span>
                  <span>Rain {day.rain_chance}%</span>
                </article>
              ))}
            </div>
          </section>
        </main>
      )}
    </div>
  );
}

export default App;
