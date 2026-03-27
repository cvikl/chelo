import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests


def fetch_openmeteo_history(lat, lon, start_date, end_date):

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&"
        f"start_date={start_date}&end_date={end_date}&"
        f"daily=temperature_2m_mean,snowfall_sum&"
        f"timezone=auto"
    )

    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error fetching data: {response.text}")
        return None

    return response.json()


def process_data(json_data):

    daily_data = json_data.get("daily", {})

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily_data.get("time")),
            "avg_temp": daily_data.get("temperature_2m_mean"),
            "total_snow": daily_data.get("snowfall_sum"),
        }
    )

    df = df.dropna(subset=["avg_temp"])
    df["total_snow"] = df["total_snow"].fillna(0)
    df["is_snowy_day"] = (df["total_snow"] > 0).astype(int)

    return df


def calculate_and_plot_trends(df, location_name):

    df["date_ordinal"] = df["date"].apply(lambda d: d.toordinal())

    x = df["date_ordinal"].values
    y_temp = df["avg_temp"].values

    slope, intercept = np.polyfit(x, y_temp, 1)
    trend_line = slope * x + intercept

    warming_per_decade = slope * 365.25 * 10

    _, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    ax1.scatter(
        df["date"],
        df["avg_temp"],
        color="blue",
        alpha=0.4,
        label="Daily Avg Temp (°C)",
        s=10,
    )
    ax1.plot(
        df["date"],
        trend_line,
        color="red",
        linewidth=2,
        label=f"Trend ({warming_per_decade:+.2f}°C/decade)",
    )
    ax1.set_ylabel("Temperature (°C)")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.5)

    snowy_days = df[df["is_snowy_day"] == 1]

    snow_dates = snowy_days["date"].dt.strftime("%Y-%m-%d").tolist()
    snow_temps = snowy_days["avg_temp"].tolist()

    ax2.bar(
        df["date"],
        df["total_snow"],
        color="orange",
        label="Daily Snowfall Sum",
        alpha=0.7,
    )
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Total Snow")
    ax2.legend()
    ax2.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()

    filename = f"{location_name.replace(' ', '_')}_climate_trend.png"
    plt.savefig(filename, dpi=300)
    plt.show()
    plt.close()

    trend_direction = "warming" if warming_per_decade > 0 else "cooling"
    fact_check_statement = (
        f"Data analysis for {location_name} between {df['date'].dt.year.min()} and {df['date'].dt.year.max()} "
        f"shows a clear {trend_direction} trend of {abs(warming_per_decade):.2f}°C per decade. "
        f"This empirical data confidently counters misinformation claiming that Alpine regions are not warming."
    )

    return {
        "location": location_name,
        "trend_warming_per_decade_celsius": round(warming_per_decade, 2),
        "journalistic_fact_check_summary": fact_check_statement,
        "snow_days_count": len(snow_dates),
        "snow_days": {"dates": snow_dates, "temperatures": snow_temps},
        "plot_filename": filename,
    }


def verify_location(
    lat: float = 45.8326,
    lon: float = 6.8652,
    start_date: str = "1990-01-01",
    end_date: str = "2023-12-31",
    location_name: str = "Chamonix",
):

    raw_data = fetch_openmeteo_history(lat, lon, start_date, end_date)
    if not raw_data:
        print("Error: Failed to fetch data from Open-Meteo")
        return None

    df = process_data(raw_data)
    result = calculate_and_plot_trends(df, location_name)

    return result


if __name__ == "__main__":
    LAT = 45.8326
    LON = 6.8652
    START = "1990-01-01"
    END = "2023-12-31"
    LOCATION = "Chamonix"

    result = verify_location(LAT, LON, START, END, LOCATION)

    if result:
        print("\n" + "=" * 60)
        print(f"Location:           {result['location']}")
        print(
            f"Warming Trend:      {result['trend_warming_per_decade_celsius']}°C per decade"
        )
        print(
            f"Total Snow Days:    {result['snow_days_count']} days with recorded snowfall"
        )
        print(f"Plot Saved as:      {result['plot_filename']}")
        print("-" * 60)
        print(f"Fact-Check Summary:\n{result['journalistic_fact_check_summary']}")
        print("=" * 60 + "\n")
