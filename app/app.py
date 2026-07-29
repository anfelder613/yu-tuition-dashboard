"""
YU Peer Tuition Dashboard -- Slice 1.

Streamlit app that queries Postgres directly (no flat-file reads baked into
the app -- see CLAUDE.md > Stack). Shows published out-of-state tuition for
YU and 5 peer institutions, undergraduate and graduate as distinct series,
for AY2015-16 through AY2024-25.
"""

import os

import pandas as pd
import plotly.graph_objects as go
import psycopg
import streamlit as st

DEFAULT_DATABASE_URL = "postgresql://yu:yu_local_dev@localhost:55433/yu_tuition"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

YU_KEY = "yu"
YU_COLOR = "#00205B"       # YU blue -- bold, distinct
PEER_COLORS = [
    "#8C8C8C", "#B08D57", "#5B8C5A", "#6C5B8C", "#8C5B5B",
]
UNDERGRAD_DASH = "solid"
GRAD_DASH = "dash"


def academic_year_label(start_year: int) -> str:
    """year=2024 -> '2024-25'. Confirmed start-year convention -- see CLAUDE.md."""
    return f"{start_year}-{str(start_year + 1)[-2:]}"


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    query = """
        SELECT i.key AS institution_key, i.name AS institution_name,
               t.academic_year, t.level, t.tuition_usd, t.fees_usd
        FROM tuition_fees t
        JOIN institutions i ON i.key = t.institution_key
        ORDER BY i.key, t.academic_year, t.level;
    """
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc.name for desc in cur.description]
            rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    df["academic_year_label"] = df["academic_year"].apply(academic_year_label)
    df["total_usd"] = df["tuition_usd"] + df["fees_usd"]
    return df


def format_dollars(value: int) -> str:
    return f"${value:,.0f}"


st.set_page_config(page_title="YU Peer Tuition Dashboard", layout="wide")

try:
    data = load_data()
except psycopg.OperationalError:
    st.error(
        "Could not connect to the database. Make sure Postgres is running "
        "(`docker compose up -d`) and the data has been loaded "
        "(`python3 scripts/load_ipeds_tuition.py`)."
    )
    st.stop()

institutions = (
    data[["institution_key", "institution_name"]]
    .drop_duplicates()
    .set_index("institution_key")["institution_name"]
    .to_dict()
)
peer_keys = [k for k in institutions if k != YU_KEY]

st.title("How does YU's tuition compare to peer institutions?")
st.caption(
    "Published (sticker-price) tuition, not what any student actually pays after aid. "
    "Dollars are not inflation-adjusted."
)

col_filters, col_chart = st.columns([1, 3])

with col_filters:
    st.subheader("Filters")

    shown_peers = st.multiselect(
        "Peer institutions",
        options=peer_keys,
        default=peer_keys,
        format_func=lambda k: institutions[k],
    )

    year_min, year_max = int(data["academic_year"].min()), int(data["academic_year"].max())
    year_range = st.slider(
        "Academic year range",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
        format="%d",
    )
    st.caption(
        f"{academic_year_label(year_range[0])} through {academic_year_label(year_range[1])}"
    )

    shown_levels = st.multiselect(
        "Level",
        options=["undergraduate", "graduate"],
        default=["undergraduate", "graduate"],
        format_func=str.capitalize,
    )

    show_fees = st.checkbox("Show required fees and total (tuition + fees)", value=False)

shown_keys = [YU_KEY] + shown_peers
filtered = data[
    data["institution_key"].isin(shown_keys)
    & data["academic_year"].between(year_range[0], year_range[1])
    & data["level"].isin(shown_levels)
]

with col_chart:
    if not shown_levels:
        st.info("Select at least one level (undergraduate or graduate) to see the chart.")
        st.stop()

    fig = go.Figure()

    color_for_key = {YU_KEY: YU_COLOR}
    for idx, key in enumerate(peer_keys):
        color_for_key[key] = PEER_COLORS[idx % len(PEER_COLORS)]

    for key in shown_keys:
        name = institutions[key]
        is_yu = key == YU_KEY
        for level, dash in (("undergraduate", UNDERGRAD_DASH), ("graduate", GRAD_DASH)):
            level_data = filtered[
                (filtered["institution_key"] == key) & (filtered["level"] == level)
            ].sort_values("academic_year")
            if level_data.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=level_data["academic_year_label"],
                    y=level_data["tuition_usd"],
                    name=f"{name} ({level})",
                    mode="lines+markers",
                    line=dict(
                        color=color_for_key[key],
                        dash=dash,
                        width=3.5 if is_yu else 1.75,
                    ),
                    marker=dict(size=7 if is_yu else 5),
                    customdata=level_data[["fees_usd", "total_usd"]],
                    hovertemplate=(
                        f"<b>{name}</b> ({level})<br>"
                        "%{x}<br>Tuition: $%{y:,.0f}"
                        + ("<br>Fees: $%{customdata[0]:,.0f}<br>Total: $%{customdata[1]:,.0f}"
                           if show_fees else "")
                        + "<extra></extra>"
                    ),
                )
            )

            if show_fees:
                fig.add_trace(
                    go.Scatter(
                        x=level_data["academic_year_label"],
                        y=level_data["total_usd"],
                        name=f"{name} ({level}) total incl. fees",
                        mode="lines",
                        line=dict(
                            color=color_for_key[key],
                            dash="dot",
                            width=2.5 if is_yu else 1.25,
                        ),
                        opacity=0.6,
                        hovertemplate=(
                            f"<b>{name}</b> ({level}) total<br>"
                            "%{x}<br>Total (tuition + fees): $%{y:,.0f}<extra></extra>"
                        ),
                    )
                )

    fig.update_layout(
        xaxis_title="Academic Year",
        yaxis_title="Tuition",
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
        legend_title="Institution (level)",
        hovermode="closest",
        height=650,
        margin=dict(t=20),
    )

    st.plotly_chart(fig, use_container_width=True)

if show_fees:
    st.caption(
        "Solid/dashed lines are tuition alone (undergraduate/graduate). "
        "Dotted lines are the total of tuition + required fees."
    )
