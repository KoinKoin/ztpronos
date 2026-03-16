import streamlit as st
import duckdb
import pandas as pd

con = duckdb.connect("races.duckdb")

st.sidebar.header("Filters")

tipsters = st.sidebar.multiselect(
    "Tipsters",
    con.execute("SELECT DISTINCT redacteur FROM picks").df()["redacteur"]
)

hippodromes = st.sidebar.multiselect(
    "Hippodrome",
    con.execute("SELECT DISTINCT hippodrome FROM picks").df()["hippodrome"]
)

race_types = st.sidebar.multiselect(
    "Race type",
    con.execute("SELECT DISTINCT race_type FROM picks").df()["race_type"]
)
