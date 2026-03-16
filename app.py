import streamlit as st
import duckdb
import pandas as pd

st.title("🐎 Tipster Performance Dashboard")

con = duckdb.connect("races.duckdb")

# ---------------------------
# Build base dataset
# ---------------------------

@st.cache_data
def load_dataset():

    query = """
    SELECT
        p.idcourse,
        p.redacteur,
        p.rank AS prono_rank,
        p.horse,
        a.rank AS final_rank,
        c.hippo,
        c.discipline,
        c.distance,
        c.datecourse,
        c.nbpartants
    FROM pronos p
    LEFT JOIN arrivee a
        ON p.idcourse = a.idcourse
        AND p.horse = a.horse
    JOIN course c
        ON p.idcourse = c.idcourse
    """

    return con.execute(query).df()


df = load_dataset()

# ---------------------------
# SIDEBAR FILTERS
# ---------------------------

st.sidebar.header("Filters")

tipsters = st.sidebar.multiselect(
    "Tipsters",
    sorted(df["redacteur"].unique())
)

hippodromes = st.sidebar.multiselect(
    "Hippodrome",
    sorted(df["hippo"].unique())
)

disciplines = st.sidebar.multiselect(
    "Discipline",
    sorted(df["discipline"].unique())
)

date_range = st.sidebar.date_input(
    "Date range",
    [df["datecourse"].min(), df["datecourse"].max()]
)

prono_rank_filter = st.sidebar.selectbox(
    "Prediction rank",
    ["All picks", "Top pick only", "Top 3 picks"]
)

metric = st.sidebar.selectbox(
    "Metric",
    [
        "Top1 rate",
        "Top3 rate",
        "Average final rank",
        "Win count"
    ]
)

groupby = st.sidebar.selectbox(
    "Group results by",
    ["redacteur", "hippo", "discipline"]
)

# ---------------------------
# APPLY FILTERS
# ---------------------------

filtered = df.copy()

if tipsters:
    filtered = filtered[filtered.redacteur.isin(tipsters)]

if hippodromes:
    filtered = filtered[filtered.hippo.isin(hippodromes)]

if disciplines:
    filtered = filtered[filtered.discipline.isin(disciplines)]

filtered = filtered[
    (filtered.datecourse >= pd.to_datetime(date_range[0])) &
    (filtered.datecourse <= pd.to_datetime(date_range[1]))
]

if prono_rank_filter == "Top pick only":
    filtered = filtered[filtered.prono_rank == 1]

elif prono_rank_filter == "Top 3 picks":
    filtered = filtered[filtered.prono_rank <= 3]

# ---------------------------
# METRIC CALCULATION
# ---------------------------

group = filtered.groupby(groupby)

if metric == "Top1 rate":

    result = group.apply(
        lambda x: (x.final_rank == 1).sum() / len(x) * 100
    ).reset_index(name="score")

elif metric == "Top3 rate":

    result = group.apply(
        lambda x: (x.final_rank <= 3).sum() / len(x) * 100
    ).reset_index(name="score")

elif metric == "Average final rank":

    result = group.final_rank.mean().reset_index(name="score")

elif metric == "Win count":

    result = group.apply(
        lambda x: (x.final_rank == 1).sum()
    ).reset_index(name="score")

# Add number of picks
counts = group.size().reset_index(name="picks")

result = result.merge(counts, on=groupby)

result = result.sort_values("score", ascending=False)

# ---------------------------
# DISPLAY
# ---------------------------

st.subheader("Results")

st.dataframe(result, use_container_width=True)

st.bar_chart(
    result.set_index(groupby)["score"]
)
