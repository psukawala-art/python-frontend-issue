# ==========================================================
#  INDIA AQI CHECKER, PREDICTOR AND ALERT SYSTEM
#
#  What this program does:
#   1. asks the user for an Indian city name
#   2. gets the pollution data of that city
#        (a) live from the internet (Open-Meteo website), or
#        (b) from our own file aqi_real_data.csv, or
#        (c) demo data if both of these are not available
#   3. calculates the AQI with the Indian CPCB method
#   4. tells the condition and how we can reduce the problem
#   5. predicts the AQI for the next 3 days (regression with NumPy)
#   6. draws an alert graph with matplotlib
#   7. saves all the records in CSV files
#
#  Libraries: numpy, pandas, matplotlib, requests, urllib.parse
#    requests     -> sends the request to the website and gets the data
#    urllib.parse -> urlencode() builds the address ?latitude=..&longitude=..


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import requests
from urllib.parse import urlencode

# ---------- settings ----------
USE_LIVE_DATA = True                 # False = do not use the internet
REAL_DATA_FILE = "aqi_real_data.csv" 
HISTORY_FILE = "aqi_history.csv"     
DAYS = 30                            
GASES = ["PM2.5", "PM10", "NO2"]     # pollutants we use

# ---------- cities: name -> (state, latitude, longitude) ----------
cities = {
    "Delhi": ("Delhi", 28.6139, 77.2090),
    "Mumbai": ("Maharashtra", 19.0760, 72.8777),
    "Pune": ("Maharashtra", 18.5204, 73.8567),
    "Nagpur": ("Maharashtra", 21.1458, 79.0882),
    "Nashik": ("Maharashtra", 19.9975, 73.7898),
    "Thane": ("Maharashtra", 19.2183, 72.9781),
    "Aurangabad": ("Maharashtra", 19.8762, 75.3433),
    "Bengaluru": ("Karnataka", 12.9716, 77.5946),
    "Mysuru": ("Karnataka", 12.2958, 76.6394),
    "Mangaluru": ("Karnataka", 12.9141, 74.8560),
    "Chennai": ("Tamil Nadu", 13.0827, 80.2707),
    "Coimbatore": ("Tamil Nadu", 11.0168, 76.9558),
    "Madurai": ("Tamil Nadu", 9.9252, 78.1198),
    "Kolkata": ("West Bengal", 22.5726, 88.3639),
    "Hyderabad": ("Telangana", 17.3850, 78.4867),
    "Visakhapatnam": ("Andhra Pradesh", 17.6868, 83.2185),
    "Ahmedabad": ("Gujarat", 23.0225, 72.5714),
    "Surat": ("Gujarat", 21.1702, 72.8311),
    "Vadodara": ("Gujarat", 22.3072, 73.1812),
    "Rajkot": ("Gujarat", 22.3039, 70.8022),
    "Jaipur": ("Rajasthan", 26.9124, 75.7873),
    "Jodhpur": ("Rajasthan", 26.2389, 73.0243),
    "Lucknow": ("Uttar Pradesh", 26.8467, 80.9462),
    "Kanpur": ("Uttar Pradesh", 26.4499, 80.3319),
    "Agra": ("Uttar Pradesh", 27.1767, 78.0081),
    "Varanasi": ("Uttar Pradesh", 25.3176, 82.9739),
    "Ghaziabad": ("Uttar Pradesh", 28.6692, 77.4538),
    "Noida": ("Uttar Pradesh", 28.5355, 77.3910),
    "Meerut": ("Uttar Pradesh", 28.9845, 77.7064),
    "Prayagraj": ("Uttar Pradesh", 25.4358, 81.8463),
    "Gurugram": ("Haryana", 28.4595, 77.0266),
    "Faridabad": ("Haryana", 28.4089, 77.3178),
    "Chandigarh": ("Chandigarh", 30.7333, 76.7794),
    "Ludhiana": ("Punjab", 30.9010, 75.8573),
    "Amritsar": ("Punjab", 31.6340, 74.8723),
    "Patna": ("Bihar", 25.5941, 85.1376),
    "Ranchi": ("Jharkhand", 23.3441, 85.3096),
    "Jamshedpur": ("Jharkhand", 22.8046, 86.2029),
    "Bhopal": ("Madhya Pradesh", 23.2599, 77.4126),
    "Indore": ("Madhya Pradesh", 22.7196, 75.8577),
    "Gwalior": ("Madhya Pradesh", 26.2183, 78.1828),
    "Raipur": ("Chhattisgarh", 21.2514, 81.6296),
    "Guwahati": ("Assam", 26.1445, 91.7362),
    "Bhubaneswar": ("Odisha", 20.2961, 85.8245),
    "Dehradun": ("Uttarakhand", 30.3165, 78.0322),
    "Srinagar": ("Jammu & Kashmir", 34.0837, 74.7973),
    "Jammu": ("Jammu & Kashmir", 32.7266, 74.8570),
    "Shimla": ("Himachal Pradesh", 31.1048, 77.1734),
    "Panaji": ("Goa", 15.4909, 73.8278),
    "Kochi": ("Kerala", 9.9312, 76.2673),
    "Thiruvananthapuram": ("Kerala", 8.5241, 76.9366),
}

# some cities are also known by their old names
old_names = {
    "bangalore": "bengaluru", "bombay": "mumbai", "calcutta": "kolkata",
    "madras": "chennai", "gurgaon": "gurugram", "allahabad": "prayagraj",
    "trivandrum": "thiruvananthapuram", "vizag": "visakhapatnam",
    "baroda": "vadodara", "mysore": "mysuru", "new delhi": "delhi",
    "cochin": "kochi", "panjim": "panaji",
}

# ---------- CPCB breakpoints ----------
# pollution amount (ug/m3) on one side, sub-index on the other side.
# np.interp joins these points with straight lines.
aqi_points = [0, 50, 100, 200, 300, 400, 500]
points = {
    "PM2.5": [0, 30, 60, 90, 120, 250, 380],
    "PM10": [0, 50, 100, 250, 350, 430, 550],
    "NO2": [0, 40, 80, 180, 280, 400, 520],
}

# zones used in the graph: (from, to, category name)
zones = [(0, 50, "Good"), (50, 100, "Satisfactory"), (100, 200, "Moderate"),
         (200, 300, "Poor"), (300, 400, "Very Poor"), (400, 500, "Severe")]
order = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]

# ---------- information for every category ----------
info = {
    "Good": {
        "color": "#00B050", "text": "black", "level": 0, "alert": "NO ALERT",
        "condition": "Air quality is good. There is little or no risk to health.",
        "tips": ["Enjoy outdoor walks, sports and exercise.",
                 "Keep windows open to ventilate your home."],
        "solutions": ["Keep using public transport, plant trees and segregate waste."],
    },
    "Satisfactory": {
        "color": "#92D050", "text": "black", "level": 1, "alert": "LOW ALERT",
        "condition": "Minor breathing discomfort is possible for very sensitive people.",
        "tips": ["Very sensitive people should avoid long, heavy exertion outdoors.",
                 "Everyone else can continue normal activities."],
        "solutions": ["Do not burn garbage or dry leaves.",
                      "Use public transport, carpool or cycle for short trips."],
    },
    "Moderate": {
        "color": "#FFFF00", "text": "black", "level": 2, "alert": "MODERATE ALERT",
        "condition": "Breathing discomfort for people with lung disease (asthma), "
                     "heart disease, children and older adults.",
        "tips": ["Children, elderly and asthma/heart patients: limit long outdoor exertion.",
                 "Carry your inhaler/medicines if you have asthma.",
                 "Walk in parks away from busy roads; avoid peak-traffic hours."],
        "solutions": ["Sprinkle water on dusty roads; cover construction material.",
                      "Renew vehicle PUC (pollution-under-control) certificates.",
                      "Avoid open burning of waste."],
    },
    "Poor": {
        "color": "#FFC000", "text": "black", "level": 3, "alert": "HIGH ALERT",
        "condition": "Breathing discomfort on prolonged exposure; higher risk for "
                     "people with heart or lung disease.",
        "tips": ["Avoid prolonged or heavy outdoor exercise.",
                 "Wear a well-fitted N95/FFP2 mask outdoors.",
                 "Keep windows closed in high-pollution hours; use a HEPA air purifier.",
                 "Drink enough water; see a doctor for cough, wheeze or chest discomfort."],
        "solutions": ["Strict dust control at construction and demolition sites.",
                      "Stop open burning of waste and crop residue.",
                      "Promote public transport, carpooling and work-from-home.",
                      "Mechanised road sweeping and water sprinkling."],
    },
    "Very Poor": {
        "color": "#FF0000", "text": "white", "level": 4, "alert": "VERY HIGH ALERT",
        "condition": "Respiratory illness is likely on prolonged exposure; even "
                     "healthy people may feel symptoms.",
        "tips": ["Avoid ALL outdoor exercise; stay indoors as much as possible.",
                 "Wear an N95/FFP2 mask if you must go out.",
                 "Keep doors/windows shut; run a HEPA purifier; avoid incense and indoor smoke.",
                 "Children, elderly, pregnant women, heart/lung patients: stay indoors "
                 "and keep medicines handy."],
        "solutions": ["Limit construction work and heavy diesel vehicles.",
                      "Schools should shift to indoor activities or online classes.",
                      "Enforce bans on open burning and firecrackers.",
                      "Add buses/metro services and restrict private vehicles."],
    },
    "Severe": {
        "color": "#C00000", "text": "white", "level": 5, "alert": "HEALTH EMERGENCY",
        "condition": "Healthy people are affected and people with existing disease "
                     "face serious effects. Treat this as a health emergency.",
        "tips": ["Stay indoors with doors and windows sealed; avoid ALL outdoor activity.",
                 "Use a HEPA purifier; wear N95/FFP2 even for short trips.",
                 "Get medical help immediately for breathlessness, chest pain or dizziness.",
                 "Vulnerable people should consider moving temporarily to a cleaner area."],
        "solutions": ["Halt construction/demolition; restrict trucks and diesel generators.",
                      "Close schools / allow work from home.",
                      "Issue public health advisories on TV, radio and SMS.",
                      "Shut major local pollution sources until AQI improves."],
    },
}

# extra tip for the main pollutant
gas_tips = {
    "PM2.5": "Main pollutant is PM2.5 (fine smoke/soot): avoid burning wood, waste or "
             "crop residue, use an N95 mask and a HEPA purifier, and avoid roadside exercise.",
    "PM10": "Main pollutant is PM10 (dust): sprinkle water on roads, cover construction "
            "sites and loose soil, wet-mop instead of sweeping, and avoid dusty areas.",
    "NO2": "Main pollutant is NO2 (vehicle and fuel exhaust): avoid heavy-traffic roads "
           "at rush hour, use public transport/carpool/EVs, service vehicles regularly "
           "and ventilate kitchens.",
}

# long term solutions (added for every category except Good)
long_term = ["Use public transport, cycling, EVs and carpooling.",
             "Plant trees and build green belts; keep roads and soil covered."]


# ==========================================================
#  SMALL HELPER FUNCTIONS
# ==========================================================
def current_time():
    # current Indian time
    return pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)


def get_category(aqi):
    # find the category name for an AQI value
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"


def read_file_or_none(filename, **options):
    # reads a CSV file, gives None if the file is not there yet
    try:
        return pd.read_csv(filename, **options)
    except FileNotFoundError:
        return None


def wrap_text(text, width):
    # breaks a long sentence into lines which are not longer than 'width'
    lines = []
    line = ""
    for word in text.split():
        if len(line) + len(word) + 1 > width and line != "":
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line != "":
        lines.append(line)
    return lines


def make_bullet(text, width, start="* "):
    # wraps the text and puts a bullet at the start of the first line
    lines = wrap_text(text, width)
    result = [start + lines[0]]
    for line in lines[1:]:
        result.append(" " * len(start) + line)
    return result


def edit_distance(a, b):
    # how many letters must be changed to make word a into word b
    # (we use it to find spelling mistakes)
    old_row = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        new_row = [i]
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cost = 0
            else:
                cost = 1
            new_row.append(min(old_row[j] + 1, new_row[j - 1] + 1, old_row[j - 1] + cost))
        old_row = new_row
    return old_row[-1]


# ==========================================================
#  GETTING THE DATA
# ==========================================================
def get_live_data(lat, lon):
    # gets the old hourly data from the Open-Meteo website and
    # changes it into one row for every day

    # urlencode makes the part of the address after the "?"
    settings = urlencode({
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm10,pm2_5,nitrogen_dioxide",
        "past_days": DAYS,
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    })
    url = "https://air-quality-api.open-meteo.com/v1/air-quality?" + settings

    # requests.get sends the request and brings the answer
    response = requests.get(url, timeout=10)
    response.raise_for_status()          
    hourly = response.json()["hourly"]

    df = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "PM2.5": hourly["pm2_5"],
        "PM10": hourly["pm10"],
        "NO2": hourly["nitrogen_dioxide"],
    })
    df[GASES] = df[GASES].apply(pd.to_numeric, errors="coerce")
    df = df[df["time"] <= current_time()]         
    df = df.dropna(how="all", subset=GASES)
    if len(df) < 72:
        raise ValueError("not enough data")

    # one row per day = average of the hours of that day
    df["Date"] = df["time"].dt.normalize()
    daily = df.groupby("Date")[GASES].mean().reset_index()

    # for the last day we use the latest 24 hours (like the official 24 hour average)
    daily.loc[daily.index[-1], GASES] = df.tail(24)[GASES].mean().to_numpy()

    daily[GASES] = daily[GASES].ffill().bfill()    
    if daily[GASES].isna().any().any():
        raise ValueError("a pollutant has no data")
    return daily.tail(DAYS).reset_index(drop=True)


def get_file_data(city):
    # reads the data of this city from our own CSV file (None if not possible)
    data = read_file_or_none(REAL_DATA_FILE, parse_dates=["Date"])
    if data is None:
        return None
    for column in ["City", "Date"] + GASES:
        if column not in data.columns:
            return None
    data = data[data["City"].str.strip().str.lower() == city.lower()]
    data = data.dropna(subset=["Date"])
    if len(data) == 0:
        return None
    data = data.assign(Date=data["Date"].dt.normalize())
    daily = data.groupby("Date")[GASES].mean().reset_index().sort_values("Date")
    daily[GASES] = daily[GASES].ffill().bfill()
    if daily[GASES].isna().any().any() or len(daily) < 15:
        return None                        
    return daily.tail(DAYS).reset_index(drop=True)


def make_demo_data(city):
    # fake data - used ONLY when real data is not available
    today = current_time().normalize()
    seed = sum((i + 1) * ord(letter) for i, letter in enumerate(city.lower()))
    rng = np.random.default_rng(seed + today.toordinal())
    base = rng.uniform(35, 170)
    pm25 = base
    rows = []
    for day in pd.date_range(end=today, periods=DAYS):
        pm25 = 0.75 * pm25 + 0.25 * base + rng.normal(0, 14)
        pm25 = min(max(pm25, 8), 330)
        pm10 = min(max(pm25 * 1.6 + rng.normal(0, 18), 15), 480)
        no2 = min(max(pm25 * 0.35 + rng.normal(0, 7), 4), 130)
        rows.append([day, pm25, pm10, no2])
    return pd.DataFrame(rows, columns=["Date"] + GASES)


def get_data(city, lat, lon):
    # tries live data first, then our CSV file, then demo data
    # gives back: table, source name, a note for the user
    note = ""
    if USE_LIVE_DATA:
        try:
            return get_live_data(lat, lon), "LIVE (Open-Meteo, model estimate)", ""
        except Exception as error:
            note = "Live data not available (" + type(error).__name__ + "). "

    daily = get_file_data(city)
    if daily is not None:
        return daily, "REAL (from " + REAL_DATA_FILE + ")", note + "Using your CSV file instead."

    note = note + "No usable data in " + REAL_DATA_FILE + ". Showing SIMULATED demo data (not real air quality)."
    return make_demo_data(city), "SIMULATED (demo data)", note


# ==========================================================
#  AQI CALCULATION
# ==========================================================
def calculate_aqi(daily):
    # adds the sub-index of every pollutant, the AQI and the main pollutant
    for gas in GASES:
        daily[gas + "_Sub"] = np.interp(daily[gas], points[gas], aqi_points)

    sub_columns = ["PM2.5_Sub", "PM10_Sub", "NO2_Sub"]
    daily["AQI"] = daily[sub_columns].max(axis=1)           
    daily["Main"] = daily[sub_columns].idxmax(axis=1).str.replace("_Sub", "")
    return daily


# ==========================================================
#  PREDICTION (regression with numpy)
#  AQI today = w0 + w1*AQI(1 day ago) + w2*AQI(2 days ago) + w3*AQI(3 days ago)
# ==========================================================
def train_model(values):
    # finds the best weights w0, w1, w2, w3 from the old data
    values = np.array(values, dtype=float)
    inputs = []
    answers = []
    for t in range(3, len(values)):
        inputs.append([1, values[t - 1], values[t - 2], values[t - 3]])
        answers.append(values[t])
    inputs = np.array(inputs)
    answers = np.array(answers)

    # small penalty keeps the weights from becoming too big (ridge regression)
    penalty = np.eye(4) * 1.0
    penalty[0, 0] = 0
    weights = np.linalg.solve(inputs.T @ inputs + penalty, inputs.T @ answers)
    return weights


def predict_aqi(values, days=3):
    # predicts the next days one by one (each prediction is used for the next one)
    weights = train_model(values)
    history = list(values)
    future = []
    for i in range(days):
        x = np.array([1, history[-1], history[-2], history[-3]])
        value = weights @ x
        value = min(max(value, 0), 500)          
        future.append(value)
        history.append(value)
    return future


def check_model(values):
    # checks the model on the last 5 days and compares it with the simple
    # guess "tomorrow = today". Gives (model error, simple guess error).
    values = np.array(values, dtype=float)
    if len(values) < 15:
        return None
    weights = train_model(values[:-5])
    model_errors = []
    guess_errors = []
    for i in range(len(values) - 5, len(values)):
        x = np.array([1, values[i - 1], values[i - 2], values[i - 3]])
        guess = min(max(weights @ x, 0), 500)
        model_errors.append(abs(values[i] - guess))
        guess_errors.append(abs(values[i] - values[i - 1]))
    return np.mean(model_errors), np.mean(guess_errors)


def trend_message(category, future):
    # message about what will happen in the next days
    worst = max(future)
    worst_category = get_category(worst)
    if order.index(worst_category) > order.index(category):
        return "WARNING: AQI is expected to WORSEN to " + worst_category + " (about " + str(round(worst)) + ") within 3 days."
    average_category = get_category(sum(future) / len(future))
    if order.index(average_category) < order.index(category):
        return "Good news: AQI is expected to improve over the next few days."
    return "AQI is expected to stay in about the same range over the next few days."


# ==========================================================
#  CITY INPUT
# ==========================================================
def ask_input(question):
    try:
        return input(question)
    except EOFError:
        return None


def find_city(text):
    # gives (name, state, lat, lon) of the city, or None if not found
    name = text.strip().lower()
    if name in old_names:
        name = old_names[name]

    # 1) exact name
    for city in cities:
        if city.lower() == name:
            return (city,) + cities[city]

    # 2) spelling mistake: find the city with the smallest edit distance
    best_city = ""
    best_distance = 100
    for city in cities:
        distance = edit_distance(name, city.lower())
        if distance < best_distance:
            best_distance = distance
            best_city = city
    if best_distance <= 2 or (len(name) >= 3 and best_city.lower().startswith(name)):
        answer = ask_input("'" + text + "' not found. Did you mean " + best_city + "? (y/n): ")
        if answer is not None and answer.strip().lower().startswith("y"):
            return (best_city,) + cities[best_city]

    # 3) city not in our list: user can type latitude and longitude
    print("'" + text + "' is not in the city list (type 'list' to see all cities).")
    answer = ask_input("Enter its latitude,longitude (example 28.61,77.20) or press Enter to cancel: ")
    if answer is not None and "," in answer:
        try:
            parts = answer.split(",")
            lat = float(parts[0])
            lon = float(parts[1])
            if 6 <= lat <= 37.5 and 68 <= lon <= 98:
                return (text.strip().title(), "Unknown", lat, lon)
            print("These coordinates are outside India.")
        except ValueError:
            print("Could not read the coordinates.")
    return None


# ==========================================================
#  SAVING TO CSV FILES
# ==========================================================
def save_records(row, daily, city, state, source):
    # file 1: one new line for this lookup
    new_row = pd.DataFrame([row])
    old = read_file_or_none(RECORDS_FILE)
    if old is None:
        all_rows = new_row
    else:
        all_rows = pd.concat([old, new_row], ignore_index=True)
    all_rows.to_csv(RECORDS_FILE, index=False)

    # file 2: the daily AQI history of this city
    history = daily[["Date", "PM2.5", "PM10", "NO2", "AQI"]].copy()
    history["Category"] = history["AQI"].apply(get_category)
    history.insert(0, "Source", source.split(" ")[0])
    history.insert(0, "State", state)
    history.insert(0, "City", city)
    old_history = read_file_or_none(HISTORY_FILE, parse_dates=["Date"])
    if old_history is not None:
        history = pd.concat([old_history, history], ignore_index=True)
    history = history.drop_duplicates(subset=["City", "Date", "Source"], keep="last")
    for column in ["PM2.5", "PM10", "NO2", "AQI"]:
        history[column] = history[column].round(2)
    history.to_csv(HISTORY_FILE, index=False)


def show_saved_records():
    records = read_file_or_none(RECORDS_FILE)
    if records is None:
        print("No records saved yet.")
        return
    columns = ["Timestamp", "City", "Source", "AQI", "Category", "Alert", "Tomorrow_AQI"]
    print("\nLast 10 lookups saved in " + RECORDS_FILE + " (total " + str(len(records)) + "):")
    print(records[columns].tail(10).to_string(index=False))


# ==========================================================
#  GRAPH
# ==========================================================
def draw_graph(city, state, source, daily, future, future_dates, data, category, main_gas, tips, message):
    now_aqi = daily["AQI"].iloc[-1]
    last_date = daily["Date"].iloc[-1]

    fig = plt.figure(figsize=(15, 12))
    grid = fig.add_gridspec(3, 2, height_ratios=[1.45, 0.5, 1.15], hspace=0.45, wspace=0.18)
    fig.suptitle("AQI ALERT REPORT - " + city + ", " + state + "\n" + source +
                 "   |   " + current_time().strftime("%d %b %Y %H:%M") + " IST",
                 fontsize=14, fontweight="bold")

    # ----- graph 1: last 30 days + prediction + alert zones -----
    ax1 = fig.add_subplot(grid[0, :])
    top = max(260, max(daily["AQI"].max(), max(future)) * 1.15)
    top = min(top, 500)
    for low, high, name in zones:
        ax1.axhspan(low, high, color=info[name]["color"], alpha=0.2)
        if low < top:
            ax1.text(1.005, (low + min(high, top)) / 2, name,
                     transform=ax1.get_yaxis_transform(), va="center", fontsize=8)
    ax1.plot(daily["Date"], daily["AQI"], marker="o", markersize=4, color="navy", label="Past AQI")
    bad_days = daily[daily["AQI"] > 200]                  # days above the alert line
    if len(bad_days) > 0:
        ax1.scatter(bad_days["Date"], bad_days["AQI"], color="red", s=40, zorder=5,
                    label="Alert days (AQI > 200)")
    ax1.plot([last_date] + future_dates, [now_aqi] + future, "--s", color="purple",
             label="3-day prediction")
    ax1.axhline(200, color="red", linestyle=":", linewidth=1.6)
    ax1.text(daily["Date"].iloc[7], 203, "ALERT THRESHOLD (AQI 200+)", color="red", fontsize=8)
    ax1.annotate("Now: " + str(round(now_aqi)), (last_date, now_aqi), textcoords="offset points",
                 xytext=(-45, 14), fontsize=10, fontweight="bold",
                 arrowprops=dict(arrowstyle="->"))
    ax1.set_ylim(0, top)
    ax1.set_ylabel("AQI")
    ax1.set_title("AQI trend, alert zones and prediction")
    ax1.tick_params(axis="x", rotation=25)
    ax1.legend(loc="lower left", fontsize=8, ncol=3)

    # ----- graph 2: AQI meter -----
    ax2 = fig.add_subplot(grid[1, :])
    for low, high, name in zones:
        ax2.barh(0, high - low, left=low, color=info[name]["color"], edgecolor="white", height=0.5)
        ax2.text((low + high) / 2, 0, name, ha="center", va="center", fontsize=8,
                 color=info[name]["text"] if name in ("Very Poor", "Severe") else "black")
    ax2.plot(now_aqi, 0.4, "v", color="black", markersize=14)
    ax2.text(now_aqi, 0.62, "NOW " + str(round(now_aqi)), ha="center", fontweight="bold")
    ax2.plot(future[0], -0.4, "^", color="purple", markersize=12)
    ax2.text(future[0], -0.62, "TOMORROW " + str(round(future[0])), ha="center",
             va="top", color="purple", fontweight="bold")
    ax2.set_xlim(0, 500)
    ax2.set_ylim(-1.1, 1.0)
    ax2.set_yticks([])
    for side in ["left", "right", "top"]:
        ax2.spines[side].set_visible(False)
    ax2.set_xlabel("AQI scale (CPCB India)")

    # ----- graph 3: bar chart of the pollutants -----
    ax3 = fig.add_subplot(grid[2, 0])
    today = daily.iloc[-1]
    values = []
    for gas in GASES:
        values.append(today[gas + "_Sub"])
    colors = []
    for v in values:
        colors.append(info[get_category(v)]["color"])
    bars = ax3.bar(GASES, values, color=colors, edgecolor="black")
    for i in range(3):
        if GASES[i] == main_gas:
            bars[i].set_linewidth(3)              
        ax3.text(i, values[i] + 4, str(round(values[i])) + "\n(" + str(round(today[GASES[i]])) + " ug/m3)",
                 ha="center", fontsize=9)
    ax3.axhline(200, color="red", linestyle=":", linewidth=1.5)
    ax3.set_ylim(0, max(260, max(values) * 1.3))
    ax3.set_ylabel("Sub-index")
    ax3.set_title("Pollutant sub-indexes (main pollutant: " + main_gas + ", thick border)")

    # ----- box 4: alert message -----
    ax4 = fig.add_subplot(grid[2, 1])
    ax4.axis("off")
    ax4.add_patch(Rectangle((0, 0.82), 1, 0.18, transform=ax4.transAxes,
                            color=data["color"], clip_on=False))
    ax4.text(0.5, 0.91, "ALERT LEVEL " + str(data["level"]) + "/5 - " + data["alert"] +
             "\nAQI " + str(round(now_aqi)) + " (" + category + ")",
             transform=ax4.transAxes, ha="center", va="center", fontsize=12,
             fontweight="bold", color=data["text"])

    lines = ["CONDITION:"] + wrap_text(data["condition"], 72)
    lines = lines + ["", "WHAT TO DO NOW:"]
    if len(tips) > 4:
        shown = tips[:3] + [tips[-1]]          
    else:
        shown = tips[:4]
    for tip in shown:
        lines = lines + make_bullet(tip, 72, "- ")
    lines = lines + ["", "FORECAST:"] + wrap_text(message, 72)
    ax4.text(0.0, 0.78, "\n".join(lines), transform=ax4.transAxes, va="top", fontsize=8.5)

    filename = "aqi_alert_" + city.lower().replace(" ", "_") + ".png"
    fig.savefig(filename, dpi=110, bbox_inches="tight")
    try:
        plt.show()
    except Exception:
        pass
    plt.close(fig)
    return filename


# ==========================================================
#  FULL REPORT FOR ONE CITY
# ==========================================================
def show_report(city, state, lat, lon):
    # step 1: get the data
    daily, source, note = get_data(city, lat, lon)

    # step 2: calculate the AQI
    daily = calculate_aqi(daily)
    today = daily.iloc[-1]
    aqi = float(today["AQI"])
    category = get_category(aqi)
    data = info[category]
    main_gas = str(today["Main"])

    # step 3: advice (tips for people and solutions for the city)
    tips = list(data["tips"])
    solutions = list(data["solutions"])
    if category != "Good" and category != "Satisfactory":
        tips.append(gas_tips[main_gas])
    if category != "Good":
        solutions = solutions + long_term

    # step 4: prediction
    aqi_list = list(daily["AQI"])
    future = predict_aqi(aqi_list)
    future_dates = []
    for i in range(1, 4):
        future_dates.append(daily["Date"].iloc[-1] + pd.Timedelta(days=i))
    message = trend_message(category, future)
    check = check_model(aqi_list)

    # step 5: print the report
    line = "=" * 72
    print("\n" + line)
    print(" AQI REPORT: " + city + ", " + state + "   (" + current_time().strftime("%d %b %Y %H:%M") + " IST)")
    print(line)
    print(" Data source :", source)
    if note != "":
        print(" NOTE        :", note)
    print(" PM2.5 = " + format(today["PM2.5"], ".1f") + " | PM10 = " + format(today["PM10"], ".1f") +
          " | NO2 = " + format(today["NO2"], ".1f") + "  (ug/m3)")
    print(" AQI         : " + str(round(aqi)) + "  ->  " + category.upper() + "   (main pollutant: " + main_gas + ")")
    print(" ALERT LEVEL : " + str(data["level"]) + "/5  " + data["alert"])

    print("\n CONDITION:")
    for text in wrap_text(data["condition"], 66):
        print("   " + text)
    print("\n WHAT YOU CAN DO NOW:")
    for tip in tips:
        for text in make_bullet(tip, 66):
            print("   " + text)
    print("\n HOW THE CITY / COMMUNITY CAN SOLVE IT:")
    for solution in solutions:
        for text in make_bullet(solution, 66):
            print("   " + text)

    print("\n PREDICTION FOR THE NEXT 3 DAYS:")
    for i in range(3):
        print("   " + future_dates[i].strftime("%a %d %b") + ": AQI " + str(round(future[i])) +
              "  (" + get_category(future[i]) + ")")
    print("   " + message)
    if check is not None:
        print("   Model check (last 5 days): error " + format(check[0], ".1f") + " AQI vs " +
              format(check[1], ".1f") + " for 'same as yesterday'")
    print(line)

    # step 6: save in the CSV files
    row = {
        "Timestamp": current_time().strftime("%Y-%m-%d %H:%M:%S"),
        "City": city, "State": state, "Source": source.split(" ")[0],
        "PM2.5": round(float(today["PM2.5"]), 2), "PM10": round(float(today["PM10"]), 2),
        "NO2": round(float(today["NO2"]), 2),
        "PM2.5_Sub": round(float(today["PM2.5_Sub"]), 1),
        "PM10_Sub": round(float(today["PM10_Sub"]), 1),
        "NO2_Sub": round(float(today["NO2_Sub"]), 1),
        "AQI": round(aqi, 1), "Category": category, "Dominant_Pollutant": main_gas,
        "Alert_Level": data["level"], "Alert": data["alert"],
        "Tomorrow_AQI": round(future[0], 1), "Day2_AQI": round(future[1], 1),
        "Day3_AQI": round(future[2], 1), "Trend": message,
        "Health_Condition": data["condition"], "Actions": " | ".join(tips),
    }
    save_records(row, daily, city, state, source)
    print(" Saved in " + RECORDS_FILE + " and " + HISTORY_FILE)

    # step 7: draw the graph
    filename = draw_graph(city, state, source, daily, future, future_dates,
                          data, category, main_gas, tips, message)
    print(" Alert graph saved as " + filename)


# ==========================================================
#  MAIN PROGRAM
# ==========================================================
print("=" * 72)
print("   INDIA AQI CHECKER, PREDICTOR AND ALERT SYSTEM")
print("=" * 72)

while True:
    text = ask_input("\nEnter an Indian city (or 'list', 'records', 'quit'): ")
    if text is None or text.strip().lower() in ["q", "quit", "exit"]:
        print("Goodbye! Stay safe and breathe clean.")
        break

    text = text.strip()
    if text == "":
        continue
    elif text.lower() == "list":
        print("\nSupported cities:")
        names = sorted(cities)
        for i in range(0, len(names), 4):
            print("  " + "".join(n.ljust(22) for n in names[i:i + 4]))
    elif text.lower() == "records":
        show_saved_records()
    else:
        result = find_city(text)
        if result is not None:
            show_report(result[0], result[1], result[2], result[3])




                                                                                                                                                                                                                                                                                                                                                



