import streamlit as st
import duckdb
import pandas as pd
import itertools

st.set_page_config(layout="wide")
st.title("🐎 Betting Strategy Simulator")

# -------------------------
# DB CONNECTION
# -------------------------
con = duckdb.connect("zeturf.duckdb")

# -------------------------
# LOAD DATA
# -------------------------
@st.cache_data
def load_data():
    query = """
    SELECT
        p.idcourse,
        p.redacteur,
        p.rank AS prono_rank,
        p.horse,
        a.rank AS final_rank,
        c.hippo,
        c.discipline,
        c.datecourse,
        r.jg
    FROM pronos p
    LEFT JOIN arrivee a
        ON p.idcourse = a.idcourse
        AND p.horse = a.horse
    JOIN course c
        ON p.idcourse = c.idcourse
    JOIN rapports r
        ON p.idcourse = r.idcourse
    """
    return con.execute(query).df()

df = load_data()

# -------------------------
# SIDEBAR FILTERS
# -------------------------
st.sidebar.header("Filters")

tipsters = st.sidebar.multiselect("Tipster", df["redacteur"].unique())
hippos = st.sidebar.multiselect("Hippodrome", df["hippo"].unique())
disciplines = st.sidebar.multiselect("Discipline", df["discipline"].unique())

date_range = st.sidebar.date_input(
    "Date range",
    [df["datecourse"].min(), df["datecourse"].max()]
)

# apply filters
filtered = df.copy()

if tipsters:
    filtered = filtered[filtered.redacteur.isin(tipsters)]

if hippos:
    filtered = filtered[filtered.hippo.isin(hippos)]

if disciplines:
    filtered = filtered[filtered.discipline.isin(disciplines)]

filtered = filtered[
    (filtered.datecourse >= pd.to_datetime(date_range[0])) &
    (filtered.datecourse <= pd.to_datetime(date_range[1]))
]

# -------------------------
# STRATEGY OPTIONS
# -------------------------
st.sidebar.header("Strategy")

strategies = {
    "Top pick combos": "s1",
    "No top pick": "s2",
    "Top pick vs outsiders": "s3"
}

strategy_label = st.sidebar.selectbox("Strategy", list(strategies.keys()))
strategy_code = strategies[strategy_label]

target_profit = st.sidebar.number_input(
    "Stop when profit reaches (€)",
    value=0.0
)

stop_after_win = st.sidebar.checkbox("Stop after first win")

initial_bankroll = st.sidebar.number_input("Initial bankroll (€)", value=100.0)

use_kelly = st.sidebar.checkbox("Use Kelly betting")

# -------------------------
# SIMULATION FUNCTION
# -------------------------
def simulate(df):

    results = []

    grouped = df.groupby(["datecourse", "hippo", "idcourse", "redacteur"])

    for (date, hippo, race, tipster), group in grouped:

        group = group.sort_values("prono_rank")
        #picks = group.head(4)["horse"].tolist()
        picks = group.sort_values("prono_rank")["horse"].tolist()
        if len(picks) < 4:
            continue

        top2 = set(group[group["final_rank"] <= 2]["horse"])
        jg = group["jg"].iloc[0]

        all_horses = df[df["idcourse"] == race]["horse"].unique().tolist()
        
        # build pairs
        if strategy_code == "s1":
            pairs = [(picks[0], picks[i]) for i in range(1, 4)]
        elif strategy_code == "s2":
            pairs = list(itertools.combinations(picks[1:4], 2))
        elif strategy_code == "s3":
            outsiders = [h for h in all_horses if h not in picks]
            pairs = [(picks[0], h) for h in outsiders]

        win = any(set(pair) == top2 for pair in pairs)

        stake = len(pairs)

        profit = (jg if win else 0) - stake

        results.append({
            "date": date,
            "hippo": hippo,
            "race": race,
            "tipster": tipster,
            "profit": profit,
            "win": win,
            "jg": jg,
            "bets": stake
        })

    res = pd.DataFrame(results)
    res = res.sort_values(["date", "race"])

    # cumulative profit per day
    res["cum_profit"] = res.groupby(
        ["date", "tipster"]
    )["profit"].cumsum()

    # STOP CONDITIONS
    def apply_stop(group):

        group = group.copy()

        if target_profit > 0:
            reached = group["cum_profit"] >= target_profit
            if reached.any():
                group = group.loc[:reached.idxmax()]

        if stop_after_win:
            wins = group["win"]
            if wins.any():
                group = group.loc[:wins.idxmax()]

        return group

    res = res.groupby(["date", "tipster"], group_keys=False).apply(apply_stop)

    return res


res = simulate(filtered)

# -------------------------
# BANKROLL SIMULATION
# -------------------------
bankroll = initial_bankroll
bankrolls = []

for _, row in res.iterrows():

    if use_kelly:
        p = 0.15  # estimated win probability
        b = row["jg"] - 1
        f = max((p * (b + 1) - 1) / b, 0)
        stake = bankroll * f
    else:
        stake = row["bets"]

    if row["bets"] > 0:
        bankroll += (row["profit"] / row["bets"]) * stake

    bankrolls.append(bankroll)

res["bankroll"] = bankrolls

# -------------------------
# DISPLAY
# -------------------------

st.subheader("📊 Per race results")
st.dataframe(res, use_container_width=True)

# -------------------------
# DAILY
# -------------------------
daily = res.groupby(["date", "tipster"]).agg({
    "profit": "sum",
    "bets": "sum",
    "win": "sum"
}).reset_index()

daily["roi"] = daily["profit"] / daily["bets"]

st.subheader("📅 Daily performance")
st.dataframe(daily, use_container_width=True)

# -------------------------
# HIPPO PERFORMANCE
# -------------------------
hippo_perf = res.groupby(["hippo", "tipster"]).agg({
    "profit": "sum",
    "bets": "sum",
    "win": "sum"
}).reset_index()

hippo_perf["roi"] = hippo_perf["profit"] / hippo_perf["bets"]

st.subheader("🏟️ Hippodrome performance")
st.dataframe(hippo_perf, use_container_width=True)

# -------------------------
# SPEED TO PROFIT
# -------------------------
def races_to_target(group, target=5):
    group = group.sort_values(["date", "race"])
    group["cum"] = group["profit"].cumsum()
    reached = group[group["cum"] >= target]
    return len(group) if reached.empty else reached.index[0] + 1

speed = []

for hippo, g in res.groupby("hippo"):
    speed.append({
        "hippo": hippo,
        "races_to_5€": races_to_target(g, 5)
    })

st.subheader("⚡ Speed to profit")
st.dataframe(pd.DataFrame(speed))

# -------------------------
# CHARTS
# -------------------------
st.subheader("📈 Cumulative profit")
st.line_chart(res.groupby("date")["profit"].sum().cumsum())

st.subheader("💰 Bankroll evolution")
st.line_chart(res["bankroll"])
