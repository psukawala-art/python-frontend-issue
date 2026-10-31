import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import aqi_backend as aqi

st.set_page_config(
    page_title="AirScope | AQI Intelligence",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f4f7fb; color: #14243a; }
.block-container { padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1500px; }
.hero { background: linear-gradient(120deg,#10243e 0%,#173e5d 60%,#176b70 100%);
        padding: 1.7rem 2rem; border-radius: 20px; color: white; margin-bottom: 1.2rem; }
.hero h1 { font-family: 'Manrope',sans-serif; font-size: 2.15rem; margin: 0; color: white; }
.hero p { margin: .4rem 0 0; color: #d5e6ef; font-size: 1rem; }
.eyebrow { text-transform: uppercase; letter-spacing: .16em; font-size: .72rem; font-weight: 700; color: #76d7c7; }
.metric-card { background: white; border: 1px solid #e4eaf1; border-radius: 16px; padding: 1.1rem 1.25rem; min-height: 135px; box-shadow: 0 5px 18px rgba(18,42,66,.035); }
.metric-label { color: #718096; font-size: .83rem; font-weight: 600; }
.metric-value { color: #122b45; font-family: 'Manrope',sans-serif; font-size: 2rem; font-weight: 800; line-height: 1.3; }
.metric-sub { color: #78889a; font-size: .78rem; margin-top: .25rem; }
.section-title { font-family: 'Manrope',sans-serif; font-size: 1.15rem; font-weight: 800; color: #17324d; margin: .7rem 0 .25rem; }
.muted { color: #718096; font-size: .9rem; }
div[data-testid="stSidebar"] { background: #10243e; }
div[data-testid="stSidebar"] * { color: #f3f7fb; }
.stButton button { border-radius: 10px; font-weight: 700; min-height: 2.7rem; }
div[data-testid="stAlert"] { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

CATEGORY_COLORS = {
    "Good": "#20a779", "Satisfactory": "#8dbb35", "Moderate": "#e4b62c",
    "Poor": "#ee8d36", "Very Poor": "#e05252", "Severe": "#9e2338"
}


def metric_card(label, value, sub=""):
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-sub">{sub}</div></div>',
        unsafe_allow_html=True
    )


def show_table(df):
    # Works on old and new Streamlit: newer versions replaced use_container_width with width="stretch".
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True)


def show_chart(fig):
    # plotly charts already fill the container by default in every Streamlit version.
    st.plotly_chart(fig)


def get_city_details(city_name):
    for name, details in aqi.cities.items():
        if name.lower() == city_name.lower():
            return name, details[0], details[1], details[2]
    return None


st.sidebar.markdown("## 🌿 AirScope")
st.sidebar.caption("INDIA AIR QUALITY INTELLIGENCE")
st.sidebar.markdown("---")
city_names = sorted(aqi.cities.keys())
default_city = city_names.index("Pune") if "Pune" in city_names else 0
selected_city = st.sidebar.selectbox("Select a city", city_names, index=default_city)
st.sidebar.markdown("### Data settings")
st.sidebar.caption("Live Open-Meteo data is attempted first. If unavailable, the project uses the configured CSV file or clearly labelled simulated data.")
show_pollutants = st.sidebar.toggle("Show pollutant details", value=True)
st.sidebar.markdown("---")
st.sidebar.caption("Academic project • AQI estimates and forecasts are informational.")

city, state, lat, lon = get_city_details(selected_city)
st.markdown("""
<div class="hero">
  <div class="eyebrow">Environmental monitoring • India</div>
  <h1>Air quality, made clear.</h1>
  <p>A city-level AQI dashboard with pollutant analysis, three-day forecasting and practical health guidance.</p>
</div>
""", unsafe_allow_html=True)

if st.button("↻ Refresh AQI report", type="primary"):
    st.cache_data.clear()


@st.cache_data(ttl=300, show_spinner=False)
def load_report(city_name, latitude, longitude):
    daily, source, note = aqi.get_data(city_name, latitude, longitude)
    daily = aqi.calculate_aqi(daily.copy())
    future = [float(v) for v in aqi.predict_aqi(list(daily["AQI"]), days=3)]
    return daily, source, note, future


try:
    with st.spinner(f"Analysing air quality for {city}..."):
        daily, source, note, future = load_report(city, lat, lon)
except Exception as exc:
    st.error(f"Unable to prepare the AQI report: {type(exc).__name__}: {exc}")
    st.stop()

today = daily.iloc[-1]
current_aqi = float(today["AQI"])
category = aqi.get_category(current_aqi)
category_data = aqi.info[category]
main_pollutant = str(today["Main"])
future_dates = [pd.Timestamp(daily["Date"].iloc[-1]) + pd.Timedelta(days=i) for i in range(1, 4)]
forecast_category = aqi.get_category(max(future))
trend = aqi.trend_message(category, future)

st.markdown(f'<div class="muted">📍 <b>{city}, {state}</b> &nbsp; • &nbsp; Updated {aqi.current_time().strftime("%d %b %Y, %H:%M IST")} &nbsp; • &nbsp; Source: {source}</div>', unsafe_allow_html=True)
if note:
    st.info(note)
if "SIMULATED" in source:
    st.warning("These values are simulated demo data, not live measurements. Do not use them for health or emergency decisions.")

st.markdown("")
c1, c2, c3, c4 = st.columns(4, gap="medium")
with c1:
    metric_card("CURRENT AQI", f"{round(current_aqi)}", category.upper())
with c2:
    metric_card("DOMINANT POLLUTANT", main_pollutant, f"{float(today[main_pollutant]):.1f} µg/m³")
with c3:
    metric_card("TOMORROW'S AQI", f"{round(future[0])}", aqi.get_category(future[0]))
with c4:
    metric_card("3-DAY OUTLOOK", forecast_category.upper(), f"Peak forecast: {round(max(future))}")

st.markdown("")
alert_color = CATEGORY_COLORS.get(category, "#64748b")
st.markdown(
    f'<div style="background:white;border:1px solid #e4eaf1;border-left:6px solid {alert_color};'
    f'border-radius:14px;padding:1rem 1.2rem;margin:.5rem 0 1rem;">'
    f'<div style="font-weight:800;font-size:1.05rem;color:#17324d;">{category_data["alert"]} · AQI {round(current_aqi)}</div>'
    f'<div style="color:#5f7185;margin-top:.3rem;">{category_data["condition"]}</div></div>',
    unsafe_allow_html=True
)

left, right = st.columns([1.7, 1], gap="large")
with left:
    st.markdown('<div class="section-title">AQI history & 3-day forecast</div>', unsafe_allow_html=True)
    hist = daily[["Date", "AQI"]].copy()
    hist["Period"] = "Historical"
    forecast = pd.DataFrame({
        "Date": [pd.Timestamp(daily["Date"].iloc[-1])] + future_dates,
        "AQI": [current_aqi] + future,
        "Period": ["Forecast"] * 4
    })
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist["AQI"], mode="lines+markers",
        name="Historical AQI", line=dict(color="#176b70", width=3),
        marker=dict(size=5), hovertemplate="%{x|%d %b}<br>AQI: %{y:.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=forecast["Date"], y=forecast["AQI"], mode="lines+markers",
        name="Forecast", line=dict(color="#7c5ce7", width=3, dash="dash"),
        marker=dict(size=8, symbol="diamond"), hovertemplate="%{x|%d %b}<br>Predicted AQI: %{y:.0f}<extra></extra>"))
    for low, high, name in aqi.zones:
        fig.add_hrect(y0=low, y1=high, fillcolor=CATEGORY_COLORS[name], opacity=.09,
                      line_width=0, layer="below")
    fig.add_hline(y=200, line_dash="dot", line_color="#d94c4c",
                  annotation_text="Poor air threshold · 200", annotation_position="top left")
    fig.update_layout(height=390, margin=dict(l=10, r=10, t=25, b=10),
        paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#53677d"),
        legend=dict(orientation="h", y=1.08, x=0), xaxis_title="", yaxis_title="AQI",
        yaxis=dict(range=[0, max(250, min(500, max(max(daily["AQI"]), max(future)) * 1.15))],
                   gridcolor="#edf1f5", zeroline=False),
        xaxis=dict(gridcolor="#edf1f5"))
    show_chart(fig)

with right:
    st.markdown('<div class="section-title">AQI category scale</div>', unsafe_allow_html=True)
    gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=round(current_aqi),
        number={"font": {"size": 42, "color": "#17324d"}},
        title={"text": f"<b>{category}</b><br><span style='font-size:12px;color:#718096'>Indian AQI scale (0–500)</span>"},
        gauge={"axis": {"range": [0, 500], "tickwidth": 1, "tickcolor": "#9aabba"},
               "bar": {"color": alert_color, "thickness": .25},
               "bgcolor": "white", "borderwidth": 0,
               "steps": [{"range": [lo, hi], "color": CATEGORY_COLORS[name] + "25"} for lo, hi, name in aqi.zones],
               "threshold": {"line": {"color": alert_color, "width": 4}, "thickness": .8, "value": current_aqi}}
    ))
    gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=10),
                        paper_bgcolor="white", font=dict(color="#53677d"))
    show_chart(gauge)
    st.markdown(f"**Forecast trend:** {trend}")

if show_pollutants:
    st.markdown('<div class="section-title">Pollutant breakdown</div>', unsafe_allow_html=True)
    pollutant_rows = []
    for gas in aqi.GASES:
        pollutant_rows.append({
            "Pollutant": gas,
            "Concentration (µg/m³)": round(float(today[gas]), 1),
            "Sub-index": round(float(today[gas + "_Sub"]), 1),
            "Category": aqi.get_category(float(today[gas + "_Sub"])),
            "Role": "Dominant pollutant" if gas == main_pollutant else "—"
        })
    poll_df = pd.DataFrame(pollutant_rows)
    p1, p2 = st.columns([1.1, 1], gap="large")
    with p1:
        fig_poll = px.bar(poll_df, x="Pollutant", y="Sub-index", color="Pollutant",
                          text="Sub-index", color_discrete_sequence=["#1d7a83", "#5d8cc6", "#e0a33c"])
        fig_poll.update_layout(height=300, showlegend=False, margin=dict(l=10, r=10, t=20, b=10),
                               paper_bgcolor="white", plot_bgcolor="white",
                               yaxis=dict(gridcolor="#edf1f5"), xaxis_title="")
        show_chart(fig_poll)
    with p2:
        show_table(poll_df)

st.markdown('<div class="section-title">Three-day forecast</div>', unsafe_allow_html=True)
forecast_cols = st.columns(3, gap="medium")
for i, col in enumerate(forecast_cols):
    fcat = aqi.get_category(future[i])
    with col:
        st.markdown(
            f'<div class="metric-card" style="border-top:4px solid {CATEGORY_COLORS[fcat]};">'
            f'<div class="metric-label">{future_dates[i].strftime("%A, %d %b")}</div>'
            f'<div class="metric-value">{round(future[i])}</div>'
            f'<div class="metric-sub">{fcat} · predicted AQI</div></div>',
            unsafe_allow_html=True
        )

st.markdown('<div class="section-title">Health guidance & recommended actions</div>', unsafe_allow_html=True)
advice1, advice2 = st.columns(2, gap="large")
with advice1:
    st.markdown("#### What residents can do")
    for tip in category_data["tips"]:
        st.markdown(f"- {tip}")
    if category != "Good" and category != "Satisfactory":
        st.info(aqi.gas_tips[main_pollutant])
with advice2:
    st.markdown("#### Community-level actions")
    for item in category_data["solutions"]:
        st.markdown(f"- {item}")
    if category != "Good":
        for item in aqi.long_term:
            st.markdown(f"- {item}")

with st.expander("View recent data table"):
    display = daily[["Date", "PM2.5", "PM10", "NO2", "AQI", "Main"]].copy()
    display["Category"] = display["AQI"].apply(aqi.get_category)
    show_table(display.sort_values("Date", ascending=False))

with st.expander("Methodology & limitations"):
    st.markdown("""
    - The dashboard uses the project's existing pollutant-to-sub-index interpolation and takes the maximum pollutant sub-index as AQI.
    - The forecast is a small NumPy regression model using the previous three AQI values. It is a project forecast, not an official forecast.
    - Data source priority: live Open-Meteo model estimates, then `aqi_real_data.csv`, then clearly labelled simulated demo data.
    - Results depend on data availability and the project's simplified AQI calculation. Consult official CPCB/state monitoring sources for health-critical decisions.
    """)

st.markdown("---")
st.caption("AirScope · India AQI Checker, Predictor & Alert System · Academic demonstration")
