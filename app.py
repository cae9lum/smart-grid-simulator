import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Smart Grid Simulator Pro", layout="wide")

st.title("⚡ Smart Microgrid Energy Simulator Pro")
st.markdown("Advanced modeling of renewable energy generation, battery storage (BESS) balancing, and financial yield in Kazakhstan.")

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.header("🎛️ Simulation Parameters")

# Фича 1: Локализация по регионам РК
location = st.sidebar.selectbox(
    "Select Kazakhstan Region", 
    ["Astana (Balanced)", "Shymkent (High Solar)", "Ekiabastuz (High Wind)"]
)

max_solar = st.sidebar.slider("Max Solar Capacity (kW)", 0, 100, 50)
max_wind = st.sidebar.slider("Max Wind Capacity (kW)", 0, 100, 40)
battery_capacity = st.sidebar.slider("Battery Storage Capacity (kWh)", 10, 500, 200)
weather_condition = st.sidebar.selectbox("Weather Conditions", ["Sunny & Windy", "Cloudy & Calm", "Storm / Gale"])

# Корректировка факторов генерации в зависимости от выбранного региона
region_solar_multiplier = 1.0
region_wind_multiplier = 1.0

if location == "Shymkent (High Solar)":
    region_solar_multiplier = 1.4  # На юге солнце светит ярче
    region_wind_multiplier = 0.7
elif location == "Ekiabastuz (High Wind)":
    region_solar_multiplier = 0.8
    region_wind_multiplier = 1.5  # В Павлодарской области мощнее ветра

# --- 24-HOUR MODELING ---
hours = np.arange(0, 24)

# Load Profile
load = 30 + 20 * np.sin((hours - 6) * np.pi / 12) + 15 * np.exp(-((hours - 19)**2) / 4)
load = np.clip(load, 10, 100)

np.random.seed(42)

# Weather-dependent factors modified by region multipliers
if weather_condition == "Sunny & Windy":
    solar_factor = np.maximum(0, np.sin(hours * np.pi / 24)) * region_solar_multiplier
    wind_factor = (0.6 + 0.3 * np.sin(hours * np.pi / 6)) * region_wind_multiplier
elif weather_condition == "Cloudy & Calm":
    solar_factor = np.maximum(0, np.sin(hours * np.pi / 24)) * 0.2 * region_solar_multiplier
    wind_factor = (0.15 + np.random.normal(0, 0.02, 24)) * region_wind_multiplier
else: # Storm / Gale
    solar_factor = np.maximum(0, np.sin(hours * np.pi / 24)) * 0.05 * region_solar_multiplier
    wind_base = 0.6 + 0.2 * np.cos(hours * np.pi / 4)
    wind_noise = np.random.normal(0, 0.15, 24) 
    wind_factor = np.clip(wind_base + wind_noise, 0.2, 1.0) * region_wind_multiplier

# Ограничиваем факторы, чтобы они не превышали 100% эффективности
solar_factor = np.clip(solar_factor, 0, 1.2)
wind_factor = np.clip(wind_factor, 0, 1.2)

solar_gen = max_solar * solar_factor
wind_gen = max_wind * wind_factor
total_gen = solar_gen + wind_gen

# --- SMART ANALYTICS ---
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Smart Analytics")
if st.sidebar.button("Calculate Optimal BESS"):
    temp_battery = battery_capacity * 0.5
    needed_extra_capacity = 0
    for i in range(24):
        net_flow = total_gen[i] - load[i]
        temp_battery += net_flow
        if temp_battery < 0:
            needed_extra_capacity += abs(temp_battery)
            temp_battery = 0
    optimal_bess = round(battery_capacity + needed_extra_capacity, 1)
    st.sidebar.success(f"💡 Recommended BESS Capacity: {optimal_bess} kWh")

# 3. Battery Storage Balancing Algorithm
battery_level = battery_capacity * 0.5
battery_history = []
status_history = []
clean_energy_used = 0 # Считаем, сколько зеленой энергии реально потреблено

for i in range(len(hours)):
    net = total_gen[i] - load[i]
    
    if net > 0:
        battery_level += net
        clean_energy_used += load[i] # Дом полностью на ВИЭ
        if battery_level > battery_capacity:
            battery_level = battery_capacity
            status = "🔋 Surplus (Battery Full)"
        else:
            status = "⚡ Charging Battery"
    else:
        # Энергии не хватает, смотрим сколько можем взять из батареи
        available_from_battery = battery_level
        battery_level += net 
        
        if battery_level <= 0:
            battery_level = 0
            status = "🚨 BLACKOUT (Power Deficit!)"
            clean_energy_used += (total_gen[i] + available_from_battery)
        else:
            status = "🔌 Discharging Battery"
            clean_energy_used += load[i]
            
    battery_history.append(battery_level)
    status_history.append(status)

# --- Фича 2: Расчет финансовой выгоды (Экономика в тенге) ---
# Средний тариф для юрлиц в Астане ~28 тенге за кВтч
tariff_kzt = 28.0 
total_load_kwh = load.sum()
money_saved_kzt = clean_energy_used * tariff_kzt
co2_saved_kg = clean_energy_used * 0.4 # ~0.4 кг CO2 экономится на каждый кВтч зеленой энергии

# --- DASHBOARD VISUALIZATION ---
df = pd.DataFrame({
    "Hour": hours,
    "Load (kW)": load,
    "Solar Generation (kW)": solar_gen,
    "Wind Generation (kW)": wind_gen,
    "Battery Charge (kWh)": battery_history,
    "Grid Status": status_history
})

# Ряд 1: Главные технические метрики
col1, col2, col3 = st.columns(3)
col1.metric("Peak Power Demand", f"{int(load.max())} kW")
col2.metric("Max Renewable Generation", f"{int(total_gen.max())} kW")

has_blackout = "🚨 BLACKOUT (Power Deficit!)" in status_history
col3.metric(
    label="Overall Grid Status", 
    value="🚨 BLACKOUT" if has_blackout else "Stable", 
    delta="Grid Deficiency Detected" if has_blackout else "Grid Fully Balanced", 
    delta_color="inverse" if has_blackout else "normal"
)

st.markdown("---")
# Ряд 2: Экономические и экологические метрики стартапа
ec1, ec2, ec3 = st.columns(3)
ec1.metric("Daily Financial Savings", f"{int(money_saved_kzt):,} ₸", delta="Saved vs City Grid")
ec2.metric("CO2 Emissions Reduced", f"{int(co2_saved_kg)} kg", delta="Eco Impact")
ec3.metric("Renewable Self-Sufficiency", f"{int((clean_energy_used / total_load_kwh) * 100)}%", delta="Autonomy Rate")

st.markdown("---")
st.subheader("📊 24-Hour Power Balance Chart")
st.line_chart(df.set_index("Hour")[["Load (kW)", "Solar Generation (kW)", "Wind Generation (kW)"]])

st.subheader("🔋 Battery Energy Storage System (BESS) Dynamics")
st.line_chart(df.set_index("Hour")[["Battery Charge (kWh)"]])

with st.expander("🔍 Detailed Hourly Calculation Table"):
    st.dataframe(df)
streamlit
pandas
numpstreamlit
pandas
numpy



