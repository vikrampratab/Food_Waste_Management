import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="Food Waste Management Dashboard",
    page_icon="🍲",
    layout="wide"
)

# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown("""
<style>
.main { background-color: #f5f7fa; }
[data-testid="stMetricValue"] {
    font-size: 30px;
    color: #0f766e;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# DATABASE SETUP (auto-create if not present)
# ==================================================

DB_PATH = "food_waste.db"

def init_db():
    """Create and populate the database if it doesn't exist."""
    import random
    from datetime import datetime, timedelta

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS providers_data (
        provider_id INTEGER PRIMARY KEY,
        name TEXT,
        provider_type TEXT,
        location TEXT,
        contact TEXT
    );
    CREATE TABLE IF NOT EXISTS receiver_data (
        receiver_id INTEGER PRIMARY KEY,
        name TEXT,
        receiver_type TEXT,
        location TEXT,
        contact TEXT
    );
    CREATE TABLE IF NOT EXISTS food_listings_data (
        food_id INTEGER PRIMARY KEY,
        provider_id INTEGER,
        food_type TEXT,
        meal_type TEXT,
        quantity INTEGER,
        location TEXT,
        provider_type TEXT,
        listed_date TEXT,
        expiry_date TEXT,
        status TEXT
    );
    CREATE TABLE IF NOT EXISTS claims_data (
        claim_id INTEGER PRIMARY KEY,
        food_id INTEGER,
        receiver_id INTEGER,
        claim_date TEXT,
        status TEXT
    );
    """)

    # Only seed if empty
    if cursor.execute("SELECT COUNT(*) FROM providers_data").fetchone()[0] > 0:
        conn.close()
        return

    random.seed(42)

    provider_types = ["Supermarket", "Restaurant", "Hotel", "Bakery", "Catering", "Household"]
    food_types = ["Vegetarian", "Non-Vegetarian", "Vegan", "Dairy", "Bakery Items", "Fruits & Vegetables"]
    meal_types = ["Breakfast", "Lunch", "Dinner", "Snacks"]
    locations = ["Varanasi", "Lucknow", "Kanpur", "Allahabad", "Agra", "Noida", "Delhi", "Mumbai", "Pune", "Jaipur"]
    claim_statuses = ["Completed", "Pending", "Cancelled"]

    provider_names = [
        "FreshMart Superstore", "Green Valley Supermarket", "City Bazaar", "Metro Foods",
        "Spice Garden Restaurant", "The Grand Hotel", "Annapurna Caterers", "Daily Bread Bakery",
        "Royal Kitchen", "Sunrise Bakery", "Food Junction", "Heritage Foods"
    ]
    receiver_names = [
        "Hope NGO", "Seva Trust", "Hunger Free Foundation", "Annapoorna Shelter",
        "Bal Sahyog Ashram", "Roti Bank", "Goonj Foundation", "Helping Hands",
        "Aasra Shelter", "Pratham NGO", "Udaan Foundation", "Sparsh Trust"
    ]

    providers = [(i, random.choice(provider_names) + f" #{i}", random.choice(provider_types),
                  random.choice(locations), f"98{random.randint(10000000,99999999)}")
                 for i in range(1, 51)]
    cursor.executemany("INSERT INTO providers_data VALUES (?,?,?,?,?)", providers)

    receivers = [(i, random.choice(receiver_names) + f" {i}", "NGO",
                  random.choice(locations), f"97{random.randint(10000000,99999999)}")
                 for i in range(1, 41)]
    cursor.executemany("INSERT INTO receiver_data VALUES (?,?,?,?,?)", receivers)

    base_date = datetime(2024, 1, 1)
    food_listings = []
    for i in range(1, 301):
        p = random.choice(providers)
        listed = base_date + timedelta(days=random.randint(0, 365))
        expiry = listed + timedelta(days=random.randint(1, 5))
        food_listings.append((i, p[0], random.choice(food_types), random.choice(meal_types),
                               random.randint(5, 100), p[3], p[2],
                               listed.strftime("%Y-%m-%d"), expiry.strftime("%Y-%m-%d"),
                               random.choice(["Available", "Claimed", "Expired"])))
    cursor.executemany("INSERT INTO food_listings_data VALUES (?,?,?,?,?,?,?,?,?,?)", food_listings)

    claims = []
    for i in range(1, 201):
        food = random.choice(food_listings)
        claim_date = base_date + timedelta(days=random.randint(0, 365))
        claims.append((i, food[0], random.randint(1, 40),
                        claim_date.strftime("%Y-%m-%d"), random.choice(claim_statuses)))
    cursor.executemany("INSERT INTO claims_data VALUES (?,?,?,?,?)", claims)

    conn.commit()
    conn.close()


init_db()

# ==================================================
# DATABASE CONNECTION
# ==================================================

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_connection()

# ==================================================
# LOAD DATA
# ==================================================

food_data      = pd.read_sql("SELECT * FROM food_listings_data", conn)
claims_data    = pd.read_sql("SELECT * FROM claims_data", conn)
providers_data = pd.read_sql("SELECT * FROM providers_data", conn)
receiver_data  = pd.read_sql("SELECT * FROM receiver_data", conn)

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.title("🍲 Food Waste Management")
st.sidebar.markdown("### Dashboard Filters")

food_filter = st.sidebar.multiselect(
    "Food Type",
    sorted(food_data["food_type"].unique()),
    default=sorted(food_data["food_type"].unique())
)

meal_filter = st.sidebar.multiselect(
    "Meal Type",
    sorted(food_data["meal_type"].unique()),
    default=sorted(food_data["meal_type"].unique())
)

location_filter = st.sidebar.multiselect(
    "Location",
    sorted(food_data["location"].unique()),
    default=sorted(food_data["location"].unique())
)

# ==================================================
# FILTER DATA
# ==================================================

filtered_food = food_data[
    food_data["food_type"].isin(food_filter) &
    food_data["meal_type"].isin(meal_filter) &
    food_data["location"].isin(location_filter)
]

# ==================================================
# TITLE
# ==================================================

st.title("🍲 Food Waste Management Dashboard")
st.markdown("### Analyze food donations, providers, receivers and claims efficiently")
st.divider()

# ==================================================
# KPI CARDS
# ==================================================

c1, c2, c3, c4 = st.columns(4)
c1.metric("🍲 Food Listings", len(filtered_food))
c2.metric("🏢 Providers",     len(providers_data))
c3.metric("🙋 Receivers",     len(receiver_data))
c4.metric("📦 Claims",        len(claims_data))

st.divider()

# ==================================================
# CHART: FOOD TYPE DISTRIBUTION
# ==================================================

food_type_df = (
    filtered_food.groupby("food_type").size()
    .reset_index(name="total_food")
)
fig1 = px.pie(food_type_df, names="food_type", values="total_food",
              title="Food Type Distribution")

# ==================================================
# CHART: PROVIDER TYPE DISTRIBUTION
# ==================================================

provider_type_df = (
    filtered_food.groupby("provider_type").size()
    .reset_index(name="total_food")
)
fig2 = px.bar(provider_type_df, x="provider_type", y="total_food",
              color="provider_type", title="Provider Type Distribution")

# ==================================================
# CHART: CLAIM STATUS
# ==================================================

claim_status = pd.read_sql("""
    SELECT status, COUNT(*) as total_claims
    FROM claims_data GROUP BY status
""", conn)
fig3 = px.pie(claim_status, names="status", values="total_claims",
              hole=0.5, title="Claims Status")

# ==================================================
# CHART: TOP RECEIVERS
# ==================================================

top_receivers = pd.read_sql("""
    SELECT r.name, COUNT(c.claim_id) as total_claims
    FROM receiver_data r
    JOIN claims_data c ON r.receiver_id = c.receiver_id
    GROUP BY r.name
    ORDER BY total_claims DESC
    LIMIT 10
""", conn)
fig4 = px.bar(top_receivers, x="name", y="total_claims",
              color="total_claims", title="Top Receivers")

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    st.plotly_chart(fig2, use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(fig3, use_container_width=True)
with col4:
    st.plotly_chart(fig4, use_container_width=True)

# ==================================================
# CHART: TOP PROVIDERS
# ==================================================

provider_merge = filtered_food.merge(providers_data, on="provider_id")
top_providers = (
    provider_merge.groupby("name").size()
    .reset_index(name="total_food")
    .sort_values("total_food", ascending=False)
    .head(10)
)
fig5 = px.bar(top_providers, x="name", y="total_food",
              color="total_food", title="Top Providers")

# ==================================================
# CHART: LOCATION ANALYSIS
# ==================================================

location_df = (
    filtered_food.groupby("location").size()
    .reset_index(name="total_food")
    .sort_values("total_food", ascending=False)
    .head(10)
)
fig6 = px.bar(location_df, x="location", y="total_food",
              color="total_food", title="Top Food Supply Locations")

col5, col6 = st.columns(2)
with col5:
    st.plotly_chart(fig5, use_container_width=True)
with col6:
    st.plotly_chart(fig6, use_container_width=True)

# ==================================================
# CHART: PROVIDER TYPE VS CLAIMS
# ==================================================

provider_claims = pd.read_sql("""
    SELECT f.provider_type, COUNT(c.claim_id) as total_claims
    FROM food_listings_data f
    JOIN claims_data c ON f.food_id = c.food_id
    GROUP BY f.provider_type
    ORDER BY total_claims DESC
""", conn)
fig7 = px.bar(provider_claims, x="provider_type", y="total_claims",
              color="provider_type", title="Provider Type vs Claims")

st.plotly_chart(fig7, use_container_width=True)

# ==================================================
# DATA TABLE
# ==================================================

st.subheader("📋 Filtered Food Listings")
st.dataframe(filtered_food, use_container_width=True)

# ==================================================
# INSIGHTS
# ==================================================

st.markdown("---")
st.subheader("📊 Key Business Insights")

st.info("""
• Supermarkets are the largest food contributors.

• Restaurants generate the highest claimed food.

• Vegetarian food dominates the listings.

• Breakfast is the most common meal category.

• Completed claims are higher than pending claims.

• Certain locations contribute significantly more food than others.

• Top receivers actively utilize the platform.
""")

st.success(
    "✅ Dashboard Developed Using SQLite + Python + Streamlit | By Vikas Babu "
    "[LinkedIn](https://www.linkedin.com/in/vikasbabu07/)"
)
