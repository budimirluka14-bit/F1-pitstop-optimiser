"""
app.py
Streamlit web interface for the F1 2026 Race Strategy Simulator.

Run with:
    streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from race_physics import (
    TRACK_DATA, COMPOUNDS, DRY_COMPOUNDS, WET_COMPOUNDS,
    simulate_two_car_race, find_optimal_strategy,
)

st.set_page_config(page_title="F1 2026 Strategy Simulator", layout="wide")
st.title("🏁 F1 2026 Strategy Simulator")
st.caption("Comparison of two pit stop strategies under 2026 regulations (Active Aero, MOM, 75 kg fuel tank).")


def stint_input_ui(label: str, key_prefix: str, compounds_pool, total_laps: int):
    """Renders sidebar controls for a single strategy (including its own grid
    position) and returns (strategy, grid_position)."""
    st.sidebar.markdown(f"**{label}**")
    grid_position = st.sidebar.number_input(
        f"Grid Position ({label})", min_value=1, max_value=20, value=1,
        key=f"{key_prefix}_grid_position",
        help="Starting grid position for this car — independent of the other strategy and of the Optimal Strategy Finder.",
    )
    num_stops = st.sidebar.number_input(
        f"Number of pit stops ({label})", min_value=0, max_value=3, value=1, key=f"{key_prefix}_stops"
    )
    strategy = []
    prev_lap = 0
    for i in range(num_stops + 1):
        cols = st.sidebar.columns([1.3, 1])
        compound = cols[0].selectbox(
            f"Stint {i + 1} Compound", compounds_pool, key=f"{key_prefix}_comp_{i}"
        )
        if i < num_stops:
            default_lap = min(prev_lap + max(total_laps // (num_stops + 1), 5), total_laps - 1)
            pit_lap = cols[1].number_input(
                "Pit Lap", min_value=prev_lap + 1, max_value=total_laps - 1,
                value=default_lap, key=f"{key_prefix}_pit_{i}"
            )
            strategy.append({"compound": compound, "pit_lap": int(pit_lap)})
            prev_lap = pit_lap
        else:
            strategy.append({"compound": compound, "pit_lap": None})
    return strategy, grid_position


def _apply_strategy_to_session(prefix: str, strategy):
    """Saves the strategy into a temporary key to be applied on the next rerun."""
    st.session_state[f"_pending_apply_{prefix}"] = strategy


def _consume_pending_apply(prefix: str):
    """Updates target widget state keys before building sidebar controls if pending data exists."""
    pending = st.session_state.pop(f"_pending_apply_{prefix}", None)
    if pending is None:
        return
    st.session_state[f"{prefix}_stops"] = len(pending) - 1
    for i, stint in enumerate(pending):
        st.session_state[f"{prefix}_comp_{i}"] = stint["compound"]
        if stint["pit_lap"] is not None:
            st.session_state[f"{prefix}_pit_{i}"] = int(stint["pit_lap"])


# --- SIDEBAR -----------------------------------------------------------
_consume_pending_apply("a")
_consume_pending_apply("b")

st.sidebar.header("Race Settings")

sorted_tracks = sorted(TRACK_DATA.keys())
track = st.sidebar.selectbox("Track", sorted_tracks)
track_defaults = TRACK_DATA[track]

# Reset session state for track-dependent widgets upon changing tracks
if st.session_state.get("_prev_track") != track:
    stale_prefixes = ("a_", "b_", "opt_min_stint", "manual_sc_start", "manual_sc_end")
    for k in list(st.session_state.keys()):
        if k.startswith(stale_prefixes):
            del st.session_state[k]
    st.session_state["_prev_track"] = track

st.sidebar.caption(f"Track Degradation Multiplier: **{track_defaults['deg_mult']:.2f}×** (1.00 = baseline abrasiveness)")

total_laps = st.sidebar.number_input(
    "Total Laps", min_value=15, max_value=80,
    value=int(track_defaults["total_laps"]), key=f"total_laps_{track}"
)
base_laptime = st.sidebar.number_input(
    "Base Lap Time [s]", min_value=60.0, max_value=130.0,
    value=float(track_defaults["base_laptime"]), step=0.5, key=f"base_laptime_{track}"
)

st.sidebar.markdown("**Track Conditions**")
is_wet = st.sidebar.checkbox("Wet Conditions")

manual_sc_enabled = st.sidebar.checkbox(
    "Manual SC/VSC Schedule (Deterministic)", value=False, key="manual_sc_enabled"
)
manual_sc_laps = None
if manual_sc_enabled:
    sc_cols = st.sidebar.columns([1, 1, 1])
    sc_kind = sc_cols[0].selectbox("Type", ["SC", "VSC"], key="manual_sc_kind")
    sc_start = sc_cols[1].number_input(
        "Start Lap", min_value=1, max_value=int(total_laps), value=min(20, int(total_laps)), key="manual_sc_start"
    )
    sc_end = sc_cols[2].number_input(
        "End Lap", min_value=int(sc_start), max_value=int(total_laps),
        value=min(int(sc_start) + 2, int(total_laps)), key="manual_sc_end"
    )
    manual_sc_laps = {lap: sc_kind for lap in range(int(sc_start), int(sc_end) + 1)}
    st.sidebar.caption("Deterministic SC/VSC active — stochastic generator disabled.")

simulate_sc = st.sidebar.checkbox(
    "Simulate SC / VSC (Stochastic)", disabled=manual_sc_enabled
)
seed = st.sidebar.number_input("Random Seed", min_value=0, max_value=9999, value=1, disabled=manual_sc_enabled)

compounds_pool = list(WET_COMPOUNDS) if is_wet else list(DRY_COMPOUNDS)

st.sidebar.divider()
strategy_a, grid_position_a = stint_input_ui("Strategy A (Car 1)", "a", compounds_pool, total_laps)
st.sidebar.divider()
strategy_b, grid_position_b = stint_input_ui("Strategy B (Car 2)", "b", compounds_pool, total_laps)

run = st.sidebar.button("🏎️ Run Simulation", type="primary", use_container_width=True)

st.sidebar.divider()
st.sidebar.markdown("**Optimal Strategy Finder (Single Car)**")
opt_grid_position = st.sidebar.number_input(
    "Grid Position (Optimizer)", min_value=1, max_value=20, value=1, key="opt_grid_position",
    help="Starting grid position used only for this single-car optimal-strategy search — independent of Strategy A/B.",
)
opt_max_stops = st.sidebar.number_input(
    "Max Pit Stops", min_value=0, max_value=3, value=3, key="opt_max_stops"
)
opt_min_stint = st.sidebar.number_input(
    "Min Stint Length [laps]", min_value=1, max_value=max(total_laps - 1, 1),
    value=min(5, max(total_laps - 1, 1)), key="opt_min_stint"
)
opt_require_two = st.sidebar.checkbox(
    "Require Min. 2 Different Compounds", value=True, key="opt_require_two"
)
find_optimal = st.sidebar.button("🔍 Find Optimal Strategy", use_container_width=True)

# --- MAIN ----------------------------------------------------------------
if find_optimal:
    try:
        opt_result = find_optimal_strategy(
            track=track, total_laps=int(total_laps), base_laptime=base_laptime,
            is_wet=is_wet, max_stops=int(opt_max_stops), min_stint_length=int(opt_min_stint),
            require_two_compounds=opt_require_two, grid_position=int(opt_grid_position),
        )
    except ValueError as e:
        st.error(f"Optimization failed: {e}")
        st.session_state.pop("_opt_result", None)
    else:
        st.session_state["_opt_result"] = opt_result

if "_opt_result" in st.session_state:
    opt = st.session_state["_opt_result"]
    st.subheader("🏆 Optimal Strategy (Single Car Estimate)")
    st.caption(
        "Calculated for green-flag reference conditions without traffic, dirty air, or random SC/VSC events. "
        "Use this as a baseline strategy to fine-tune in two-car comparisons."
    )

    strat_rows = []
    cursor = 1
    for stint in opt["strategy"]:
        end = stint["pit_lap"] or int(total_laps)
        strat_rows.append({
            "Stint": f"{cursor}–{end}",
            "Compound": stint["compound"],
            "Length [laps]": end - cursor + 1,
        })
        cursor = end + 1

    c1, c2 = st.columns([2, 1])
    with c1:
        st.dataframe(pd.DataFrame(strat_rows), use_container_width=True, hide_index=True)
    with c2:
        st.metric("Estimated Time", f"{opt['estimated_time']:.2f} s")
        st.metric("Pit Stops", opt["stops"])
        if opt["grid_position"] > 1:
            st.caption(
                f"Start: P{opt['grid_position']} "
                f"(+{opt['congestion_delay']:.2f} s traffic penalty in lap 1)."
            )

    b1, b2 = st.columns(2)
    if b1.button("➡️ Apply as Strategy A", use_container_width=True):
        _apply_strategy_to_session("a", opt["strategy"])
        st.rerun()
    if b2.button("➡️ Apply as Strategy B", use_container_width=True):
        _apply_strategy_to_session("b", opt["strategy"])
        st.rerun()

    with st.expander("📊 Top Candidates by Pit Stop Count"):
        comp_rows = []
        seen_stops = set()
        for c in opt["top_candidates"]:
            if c["stops"] in seen_stops:
                continue
            seen_stops.add(c["stops"])
            comp_rows.append({
                "Stops": c["stops"],
                "Compounds": " → ".join(c["compounds"]),
                "Estimate [s]": round(c["estimated_time"], 2),
            })
        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

    st.divider()

if run:
    try:
        result = simulate_two_car_race(
            strategy_a, strategy_b, track=track, total_laps=int(total_laps),
            base_laptime=base_laptime, is_wet=is_wet, simulate_sc=simulate_sc, seed=int(seed),
            manual_sc_laps=manual_sc_laps,
            grid_position_a=int(grid_position_a),
            grid_position_b=int(grid_position_b),
        )
    except Exception as e:
        st.error(f"Simulation Error: {e}")
        st.stop()

    df = pd.DataFrame(result["rows"])

    # --- Metrics ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Time A", f"{result['total_a']:.2f} s")
    m2.metric("Total Time B", f"{result['total_b']:.2f} s")
    delta = result["delta"]
    winner_label = f"Winner: {result['winner']}" if result["winner"] != "izjednaceno" else "Tie"
    m3.metric("Gap (B − A)", f"{delta:+.2f} s", delta=winner_label)

    if result["grid_position_a"] > 1 or result["grid_position_b"] > 1:
        st.caption(
            f"Grid Start — A: P{result['grid_position_a']} (+{result['congestion_delay_a']:.2f} s), "
            f"B: P{result['grid_position_b']} (+{result['congestion_delay_b']:.2f} s) traffic delay in lap 1."
        )
    if result["start_penalty_a"] or result["start_penalty_b"]:
        st.caption(
            f"Launch penalty on starting compound — A: +{result['start_penalty_a']:.2f} s, "
            f"B: +{result['start_penalty_b']:.2f} s (in lap 1)."
        )

    if result["sc_events"]:
        laps_sc = sorted(result["sc_events"].keys())
        kind = result["sc_events"][laps_sc[0]]
        st.info(f"⚠️ {kind} active from lap {laps_sc[0]} to {laps_sc[-1]}.")

    # --- Gap Chart ---
    st.subheader("Race Interval Progression (Gap Chart)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["lap"], y=df["gap_b_minus_a"], mode="lines",
        name="Gap (B − A)", line=dict(width=2, color="#e10600"),
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    for lap, kind in result["sc_events"].items():
        fig.add_vrect(x0=lap - 0.5, x1=lap + 0.5, fillcolor="yellow", opacity=0.15, line_width=0)
    fig.update_layout(
        xaxis_title="Lap", yaxis_title="Gap [s] (Positive = B behind A)",
        height=420, margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Detailed Data Table ---
    with st.expander("📋 Detailed Lap Breakdown"):
        st.dataframe(df, use_container_width=True, height=500)

else:
    st.info("Configure strategies in the sidebar and click **Run Simulation**.")
    st.markdown("""
    **How to use:**
    1. Select track, total laps, and baseline lap time.
    2. Toggle wet conditions or stochastic Safety Car parameters if needed.
    3. For each strategy (A and B), set its own grid position, pit stop count, compound allocations per stint, and pit windows.
    4. Click *Run Simulation* to analyze the relative race performance.
    """)
