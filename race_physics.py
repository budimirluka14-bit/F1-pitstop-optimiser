"""
race_physics.py
Physics and simulation logic for F1 2026 regulations - completely independent
of Streamlit to allow standalone execution and testing.

All non-explicit specification assumptions are tagged with "ASSUMPTION" to indicate
calibration checkpoints.
"""

import itertools
import numpy as np

# ---------------------------------------------------------------------------
# Track Configuration
# ---------------------------------------------------------------------------

# "deg_mult" = tyre degradation rate multiplier based on track abrasiveness
# and cornering load (1.0 = baseline reference). Monaco, Monza, Silverstone,
# Spa, and Barcelona are reference values; others are ASSUMPTIONS calibrated
# against known track characteristics.
# ---------------------------------------------------------------------------
# Track Configuration (F1 2026 Season Calibrated)
# ---------------------------------------------------------------------------

TRACK_DATA = {
    # --- COMPLETED RACES (2026 Season Real Data) ---
    "Albert Park":   {"base_laptime": 81.5,  "overtaking_delta": 1.2, "pit_loss_green": 20.0, "sc_prob": 0.65, "vsc_prob": 0.50, "deg_mult": 1.00, "total_laps": 58}, # Aus GP 2026
    "Shanghai":      {"base_laptime": 95.5,  "overtaking_delta": 0.8, "pit_loss_green": 22.0, "sc_prob": 0.45, "vsc_prob": 0.35, "deg_mult": 1.20, "total_laps": 56}, # China GP 2026
    "Suzuka":        {"base_laptime": 92.5,  "overtaking_delta": 1.2, "pit_loss_green": 22.5, "sc_prob": 0.50, "vsc_prob": 0.40, "deg_mult": 1.30, "total_laps": 53}, # Japan GP 2026
    "Miami":         {"base_laptime": 91.5,  "overtaking_delta": 0.9, "pit_loss_green": 20.0, "sc_prob": 0.50, "vsc_prob": 0.40, "deg_mult": 1.05, "total_laps": 57}, # Miami GP 2026
    "Montreal":      {"base_laptime": 75.2,  "overtaking_delta": 0.8, "pit_loss_green": 18.5, "sc_prob": 0.70, "vsc_prob": 0.50, "deg_mult": 0.90, "total_laps": 70}, # Canada GP 2026
    "Monaco":        {"base_laptime": 74.8,  "overtaking_delta": 2.8, "pit_loss_green": 21.0, "sc_prob": 0.80, "vsc_prob": 0.60, "deg_mult": 0.55, "total_laps": 78}, # Monaco GP 2026
    "Barcelona":     {"base_laptime": 78.2,  "overtaking_delta": 1.3, "pit_loss_green": 22.0, "sc_prob": 0.30, "vsc_prob": 0.30, "deg_mult": 1.40, "total_laps": 66}, # Spain GP 2026
    "Red Bull Ring": {"base_laptime": 68.8,  "overtaking_delta": 0.7, "pit_loss_green": 20.0, "sc_prob": 0.40, "vsc_prob": 0.45, "deg_mult": 0.95, "total_laps": 71}, # Austria GP 2026
    "Silverstone":   {"base_laptime": 91.2,  "overtaking_delta": 1.0, "pit_loss_green": 20.5, "sc_prob": 0.55, "vsc_prob": 0.40, "deg_mult": 1.35, "total_laps": 52}, # UK GP 2026
    "Spa":           {"base_laptime": 107.5, "overtaking_delta": 0.6, "pit_loss_green": 22.0, "sc_prob": 0.60, "vsc_prob": 0.50, "deg_mult": 1.35, "total_laps": 44}, # Belgium GP 2026
    "Hungaroring":   {"base_laptime": 80.8,  "overtaking_delta": 1.7, "pit_loss_green": 20.5, "sc_prob": 0.35, "vsc_prob": 0.30, "deg_mult": 0.85, "total_laps": 70}, # Hungary GP 2026

    # --- UPCOMING RACES (Estimated / Calibrated for 2026 Aero Rules) ---
    "Zandvoort":     {"base_laptime": 74.0,  "overtaking_delta": 1.5, "pit_loss_green": 21.5, "sc_prob": 0.50, "vsc_prob": 0.40, "deg_mult": 1.05, "total_laps": 72},
    "Monza":         {"base_laptime": 82.0,  "overtaking_delta": 0.6, "pit_loss_green": 24.0, "sc_prob": 0.45, "vsc_prob": 0.35, "deg_mult": 0.85, "total_laps": 53},
    "Madrid":        {"base_laptime": 84.5,  "overtaking_delta": 1.2, "pit_loss_green": 21.0, "sc_prob": 0.60, "vsc_prob": 0.45, "deg_mult": 1.00, "total_laps": 55}, # New Street Circuit
    "Baku":          {"base_laptime": 104.5, "overtaking_delta": 0.5, "pit_loss_green": 20.5, "sc_prob": 0.75, "vsc_prob": 0.55, "deg_mult": 0.80, "total_laps": 51},
    "Sakhir":        {"base_laptime": 96.0,  "overtaking_delta": 0.6, "pit_loss_green": 22.5, "sc_prob": 0.40, "vsc_prob": 0.30, "deg_mult": 1.40, "total_laps": 57},
    "Singapore":     {"base_laptime": 95.2,  "overtaking_delta": 1.6, "pit_loss_green": 28.0, "sc_prob": 1.00, "vsc_prob": 0.70, "deg_mult": 0.80, "total_laps": 62},
    "COTA":          {"base_laptime": 99.8,  "overtaking_delta": 0.9, "pit_loss_green": 20.5, "sc_prob": 0.45, "vsc_prob": 0.35, "deg_mult": 1.15, "total_laps": 56},
    "Mexico City":   {"base_laptime": 81.2,  "overtaking_delta": 0.7, "pit_loss_green": 22.0, "sc_prob": 0.50, "vsc_prob": 0.40, "deg_mult": 0.75, "total_laps": 71},
    "Interlagos":    {"base_laptime": 73.8,  "overtaking_delta": 0.7, "pit_loss_green": 21.0, "sc_prob": 0.65, "vsc_prob": 0.50, "deg_mult": 1.10, "total_laps": 71},
    "Las Vegas":     {"base_laptime": 94.2,  "overtaking_delta": 0.5, "pit_loss_green": 21.5, "sc_prob": 0.60, "vsc_prob": 0.45, "deg_mult": 0.90, "total_laps": 50},
    "Losail":        {"base_laptime": 84.8,  "overtaking_delta": 0.8, "pit_loss_green": 22.5, "sc_prob": 0.40, "vsc_prob": 0.35, "deg_mult": 1.40, "total_laps": 57},
    "Yas Marina":    {"base_laptime": 87.8,  "overtaking_delta": 0.8, "pit_loss_green": 21.5, "sc_prob": 0.35, "vsc_prob": 0.30, "deg_mult": 1.00, "total_laps": 58},
}
# ---------------------------------------------------------------------------
# Tyre Parameters (Dry + Wet)
# ---------------------------------------------------------------------------

COMPOUNDS = {
    "SOFT":         {"offset": -0.6, "deg_rate": 0.055, "deg_exp": 1.60, "max_life": 18},
    "MEDIUM":       {"offset": 0.0,  "deg_rate": 0.028, "deg_exp": 1.30, "max_life": 30},
    "HARD":         {"offset": 0.45, "deg_rate": 0.015, "deg_exp": 1.15, "max_life": 45},
    "INTERMEDIATE": {"offset": 2.5,  "deg_rate": 0.020, "deg_exp": 1.20, "max_life": 35},
    "WET":          {"offset": 4.5,  "deg_rate": 0.012, "deg_exp": 1.10, "max_life": 40},
}

DRY_COMPOUNDS = ("SOFT", "MEDIUM", "HARD")
WET_COMPOUNDS = ("INTERMEDIATE", "WET")

# 2026 regulations feature a smaller fuel tank capacity (~70-75 kg)
FUEL_EFFECT_PER_LAP = 0.028

OUTLAP_PENALTY = {
    "HARD": 1.0,
    "MEDIUM": 0.5,
    "INTERMEDIATE": 0.7,
    "WET": 1.3,
}

INLAP_PENALTY = 1.1   # ASSUMPTION: driving to pit lane on worn tyres (1.0-1.2s range)

# --- Start Compound Launch Penalty --------------------------------------
# One-off penalty (s) applied exclusively to the first lap of the race
START_COMPOUND_PENALTY = {
    "SOFT": 0.0,
    "MEDIUM": 0.2,
    "HARD": 0.9,
    "INTERMEDIATE": 0.0,
    "WET": 0.0,
}

DIRTY_AIR_GAP_THRESHOLD = 1.2     # seconds
DIRTY_AIR_TIME_PENALTY = 0.6
DIRTY_AIR_DEG_BOOST = 0.10        # +10% degradation penalty

# Track rubbering / grip evolution parameters
TRACK_EVOLUTION_RATE = 0.025          # seconds lap time gain per lap
TRACK_EVOLUTION_PLATEAU_LAP = 20      # saturation limit lap count

SC_LAPTIME_MULTIPLIER = 1.35
VSC_LAPTIME_MULTIPLIER = 1.15
SC_PIT_LOSS_FACTOR = 0.55
VSC_PIT_LOSS_FACTOR = 0.65
SC_MIN_DURATION, SC_MAX_DURATION = 3, 6
VSC_MIN_DURATION, VSC_MAX_DURATION = 1, 3

# Traffic penalty factor used by DP strategy solver
TRAFFIC_RISK_FACTOR = 3.0

# Dynamic traffic density thresholds based on race progression
TRAFFIC_DENSITY_EARLY_FRAC = 0.35   # early race phase threshold (full penalty)
TRAFFIC_DENSITY_LATE_FRAC = 0.70    # late race phase threshold (floor penalty)
TRAFFIC_DENSITY_LATE_FLOOR = 0.35   # late race traffic density floor


def traffic_density_adj(lap: int, total_laps: int) -> float:
    """Calculates the grid-dependent fraction of traffic penalty applicable for a given lap."""
    frac = lap / total_laps
    if frac <= TRAFFIC_DENSITY_EARLY_FRAC:
        return 1.0
    if frac >= TRAFFIC_DENSITY_LATE_FRAC:
        return TRAFFIC_DENSITY_LATE_FLOOR
    span = TRAFFIC_DENSITY_LATE_FRAC - TRAFFIC_DENSITY_EARLY_FRAC
    t = (frac - TRAFFIC_DENSITY_EARLY_FRAC) / span
    return 1.0 + t * (TRAFFIC_DENSITY_LATE_FLOOR - 1.0)


def pit_lap_traffic_cost(lap: int, total_laps: int, overtaking_delta: float,
                          traffic_risk_factor: float, grid_mult: float) -> float:
    """Calculates expected traffic delay (seconds) when exiting pits on a specific lap."""
    base = traffic_risk_factor * overtaking_delta
    return base * (1.0 + (grid_mult - 1.0) * traffic_density_adj(lap, total_laps))


GRID_START_PENALTY_COEF = 0.4
GRID_TRAFFIC_COEF = 0.15


def grid_congestion_delay(grid_position: int) -> float:
    """Calculates first lap time loss (s) due to turn-1 start congestion."""
    return GRID_START_PENALTY_COEF * float(np.sqrt(max(grid_position - 1, 0)))


def grid_traffic_multiplier(grid_position: int) -> float:
    """Calculates traffic penalty multiplier based on starting grid rank."""
    return 1.0 + GRID_TRAFFIC_COEF * float(np.sqrt(max(grid_position - 1, 0)))


def laptime_delta(tire_age: float, compound: str, degradation_boost: float = 0.0,
                   track_deg_mult: float = 1.0) -> float:
    """Calculates lap time degradation relative to fresh tyres."""
    p = COMPOUNDS[compound]
    effective_age = tire_age * (1.0 + degradation_boost)
    return p["offset"] + (p["deg_rate"] * track_deg_mult) * np.power(effective_age, p["deg_exp"])


def fuel_effect(lap: int, total_laps: int) -> float:
    """Calculates lap time penalty (s) caused by remaining fuel weight."""
    laps_remaining = max(total_laps - lap, 0)
    return FUEL_EFFECT_PER_LAP * laps_remaining


def track_evolution_effect(lap: int, total_laps: int) -> float:
    """Calculates lap time gain (s) from track rubbering evolution."""
    effective_lap = min(lap, TRACK_EVOLUTION_PLATEAU_LAP, total_laps)
    return -TRACK_EVOLUTION_RATE * max(effective_lap - 1, 0)


def expand_stints(strategy, total_laps: int):
    """Expands stint list into per-lap dictionary and pit lap set."""
    per_lap = {}
    pit_laps = set()
    cursor = 1

    for i, stint in enumerate(strategy):
        end_lap = stint["pit_lap"] if stint["pit_lap"] else total_laps
        end_lap = min(end_lap, total_laps)
        for lap in range(cursor, end_lap + 1):
            tire_age = lap - cursor + 1
            is_outlap = (lap == cursor and i > 0)
            per_lap[lap] = (stint["compound"], tire_age, is_outlap)
        if stint["pit_lap"] and i < len(strategy) - 1:
            pit_laps.add(end_lap)
        cursor = end_lap + 1
        if cursor > total_laps:
            break

    return per_lap, pit_laps


def decide_sc_vsc(track: str, total_laps: int, is_wet: bool, simulate_sc: bool, rng: np.random.Generator):
    """Generates random Safety Car or Virtual Safety Car deployment periods."""
    if not simulate_sc or total_laps < 15:
        return {}

    tp = TRACK_DATA[track]
    wet_mult = 1.5 if is_wet else 1.0
    sc_prob = min(tp["sc_prob"] * wet_mult, 1.0)
    vsc_prob = min(tp["vsc_prob"] * wet_mult, 1.0)

    result = {}
    triggered_sc = rng.random() < sc_prob
    triggered_vsc = (not triggered_sc) and (rng.random() < vsc_prob)

    if triggered_sc:
        start = int(rng.integers(8, total_laps - 8))
        duration = int(rng.integers(SC_MIN_DURATION, SC_MAX_DURATION + 1))
        for lap in range(start, min(start + duration, total_laps) + 1):
            result[lap] = "SC"
    elif triggered_vsc:
        start = int(rng.integers(8, total_laps - 8))
        duration = int(rng.integers(VSC_MIN_DURATION, VSC_MAX_DURATION + 1))
        for lap in range(start, min(start + duration, total_laps) + 1):
            result[lap] = "VSC"

    return result


def simulate_two_car_race(strategy_a, strategy_b, track: str, total_laps: int,
                           base_laptime: float = None,
                           is_wet: bool = False, simulate_sc: bool = False, seed: int = 0,
                           manual_sc_laps=None, grid_position_a: int = 1, grid_position_b: int = 1):
    """
    Simulates lap-by-lap race execution for two cars, evaluating tyre degradation,
    fuel load, track evolution, outlap/inlap penalties, traffic effects, and SC/VSC events.
    """
    if track not in TRACK_DATA:
        raise ValueError(f"Unknown track: {track}. Available: {list(TRACK_DATA)}")

    tp = TRACK_DATA[track]
    if base_laptime is None:
        base_laptime = tp["base_laptime"]
    deg_mult = tp["deg_mult"]
    overtaking_delta = tp["overtaking_delta"] * (1.4 if is_wet else 1.0)

    grid_position_a = max(int(grid_position_a), 1)
    grid_position_b = max(int(grid_position_b), 1)
    congestion_delay_a = grid_congestion_delay(grid_position_a)
    congestion_delay_b = grid_congestion_delay(grid_position_b)
    grid_mult_a = grid_traffic_multiplier(grid_position_a)
    grid_mult_b = grid_traffic_multiplier(grid_position_b)

    start_penalty_a = START_COMPOUND_PENALTY.get(strategy_a[0]["compound"], 0.0)
    start_penalty_b = START_COMPOUND_PENALTY.get(strategy_b[0]["compound"], 0.0)

    if manual_sc_laps is not None:
        if isinstance(manual_sc_laps, dict):
            sc_state = {int(lap): kind for lap, kind in manual_sc_laps.items()}
        else:
            sc_state = {int(lap): "SC" for lap in manual_sc_laps}
    else:
        rng = np.random.default_rng(seed)
        sc_state = decide_sc_vsc(track, total_laps, is_wet, simulate_sc, rng)

    stints_a, pit_laps_a = expand_stints(strategy_a, total_laps)
    stints_b, pit_laps_b = expand_stints(strategy_b, total_laps)

    cum_a, cum_b = 0.0, 0.0
    prev_gap_abs = None
    order = ("A", "B")
    rows = []

    for lap in range(1, total_laps + 1):
        comp_a, age_a, out_a = stints_a.get(lap, (strategy_a[-1]["compound"], 1, False))
        comp_b, age_b, out_b = stints_b.get(lap, (strategy_b[-1]["compound"], 1, False))

        pitting_a = lap in pit_laps_a
        pitting_b = lap in pit_laps_b
        both_racing = (prev_gap_abs is not None) and not pitting_a and not pitting_b

        deg_boost_a = deg_boost_b = 0.0
        dirty_air_note = ""
        if both_racing and prev_gap_abs < DIRTY_AIR_GAP_THRESHOLD:
            trailing = order[1]
            if trailing == "B":
                deg_boost_b = DIRTY_AIR_DEG_BOOST
            else:
                deg_boost_a = DIRTY_AIR_DEG_BOOST

        evo = track_evolution_effect(lap, total_laps)
        t_a = (base_laptime + laptime_delta(age_a, comp_a, deg_boost_a, deg_mult)
               + fuel_effect(lap, total_laps) + evo
               + (OUTLAP_PENALTY.get(comp_a, 0.0) if out_a else 0.0)
               + (congestion_delay_a + start_penalty_a if lap == 1 else 0.0))
        t_b = (base_laptime + laptime_delta(age_b, comp_b, deg_boost_b, deg_mult)
               + fuel_effect(lap, total_laps) + evo
               + (OUTLAP_PENALTY.get(comp_b, 0.0) if out_b else 0.0)
               + (congestion_delay_b + start_penalty_b if lap == 1 else 0.0))

        sc_flag = sc_state.get(lap)
        multiplier = SC_LAPTIME_MULTIPLIER if sc_flag == "SC" else (VSC_LAPTIME_MULTIPLIER if sc_flag == "VSC" else 1.0)
        t_a *= multiplier
        t_b *= multiplier

        pit_factor = SC_PIT_LOSS_FACTOR if sc_flag == "SC" else (VSC_PIT_LOSS_FACTOR if sc_flag == "VSC" else 1.0)
        if pitting_a:
            t_a += tp["pit_loss_green"] * pit_factor + INLAP_PENALTY
            t_a += pit_lap_traffic_cost(lap, total_laps, overtaking_delta, TRAFFIC_RISK_FACTOR, grid_mult_a)
        if pitting_b:
            t_b += tp["pit_loss_green"] * pit_factor + INLAP_PENALTY
            t_b += pit_lap_traffic_cost(lap, total_laps, overtaking_delta, TRAFFIC_RISK_FACTOR, grid_mult_b)

        if both_racing and prev_gap_abs < DIRTY_AIR_GAP_THRESHOLD:
            trailing = order[1]
            pace_advantage = (t_a - t_b) if trailing == "A" else (t_b - t_a)
            if pace_advantage < -overtaking_delta:
                dirty_air_note = "MOM overtake possible"
            else:
                if trailing == "B":
                    t_b += DIRTY_AIR_TIME_PENALTY
                else:
                    t_a += DIRTY_AIR_TIME_PENALTY
                dirty_air_note = "dirty air"

        cum_a += t_a
        cum_b += t_b
        gap = cum_b - cum_a
        order = ("A", "B") if gap >= 0 else ("B", "A")
        prev_gap_abs = abs(gap)

        rows.append({
            "lap": lap,
            "compound_a": comp_a, "tire_age_a": age_a, "laptime_a": round(t_a, 3),
            "compound_b": comp_b, "tire_age_b": age_b, "laptime_b": round(t_b, 3),
            "gap_b_minus_a": round(gap, 3),
            "safety_car": sc_flag or "",
            "traffic": dirty_air_note,
        })

    return {
        "rows": rows,
        "total_a": cum_a,
        "total_b": cum_b,
        "delta": cum_b - cum_a,
        "winner": "A" if cum_a < cum_b else ("B" if cum_b < cum_a else "tie"),
        "sc_events": sc_state,
        "grid_position_a": grid_position_a,
        "grid_position_b": grid_position_b,
        "congestion_delay_a": congestion_delay_a,
        "congestion_delay_b": congestion_delay_b,
        "start_penalty_a": start_penalty_a,
        "start_penalty_b": start_penalty_b,
    }


# ---------------------------------------------------------------------------
# Single-car Dynamic Programming Strategy Optimizer
# ---------------------------------------------------------------------------

def _cum_degradation(compound: str, total_laps: int, deg_mult: float = 1.0) -> np.ndarray:
    """Calculates cumulative degradation cost array across laps for a given compound."""
    p = COMPOUNDS[compound]
    ages = np.arange(1, total_laps + 1, dtype=float)
    per_lap = p["offset"] + (p["deg_rate"] * deg_mult) * np.power(ages, p["deg_exp"])
    return np.concatenate(([0.0], np.cumsum(per_lap)))


def _optimize_split(compounds, total_laps: int, min_stint_length: int = 1, deg_mult: float = 1.0,
                     traffic_cost_by_lap=None):
    """Computes optimal stint transition lap boundaries using Dynamic Programming."""
    k = len(compounds)
    if k * min_stint_length > total_laps:
        return None

    cums = {c: _cum_degradation(c, total_laps, deg_mult) for c in set(compounds)}
    max_lives = {c: COMPOUNDS[c]["max_life"] / deg_mult for c in set(compounds)}

    INF = float("inf")
    best = [[INF] * (total_laps + 1) for _ in range(k + 1)]
    parent = [[None] * (total_laps + 1) for _ in range(k + 1)]
    best[0][0] = 0.0

    for j in range(1, k + 1):
        comp = compounds[j - 1]
        cum = cums[comp]
        max_len = max_lives[comp]
        outlap_pen = OUTLAP_PENALTY.get(comp, 0.0) if j > 1 else 0.0
        min_prev = (j - 1) * min_stint_length

        for i in range(j * min_stint_length, total_laps + 1):
            best_val = INF
            best_m = None
            max_m = i - min_stint_length

            for m in range(min_prev, max_m + 1):
                prev = best[j - 1][m]
                if prev == INF:
                    continue
                
                length = i - m
                if length > max_len:
                    continue

                pit_traffic = traffic_cost_by_lap[m] if (traffic_cost_by_lap is not None and j > 1) else 0.0
                cost = prev + cum[length] + outlap_pen + pit_traffic
                if cost < best_val:
                    best_val = cost
                    best_m = m

            best[j][i] = best_val
            parent[j][i] = best_m

    if best[k][total_laps] == INF:
        return None

    cut_points = []
    i = total_laps
    for j in range(k, 0, -1):
        m = parent[j][i]
        cut_points.append(m)
        i = m
    cut_points.reverse()
    return best[k][total_laps], cut_points


def _cutpoints_to_strategy(compounds, cut_points, total_laps: int):
    """Converts raw DP cut points into strategy dictionary structure."""
    ends = list(cut_points[1:]) + [total_laps]
    strategy = []
    for i, comp in enumerate(compounds):
        is_last = (i == len(compounds) - 1)
        strategy.append({"compound": comp, "pit_lap": None if is_last else int(ends[i])})
    return strategy


def find_optimal_strategy(track: str, total_laps: int, base_laptime: float = None,
                           is_wet: bool = False, max_stops: int = 3, min_stint_length: int = 3,
                           require_two_compounds: bool = True, top_n: int = 8,
                           traffic_risk_factor: float = TRAFFIC_RISK_FACTOR,
                           grid_position: int = 1):
    """Identifies the optimal single-car race strategy through DP optimization across compound combinations."""
    if track not in TRACK_DATA:
        raise ValueError(f"Unknown track: {track}. Available: {list(TRACK_DATA)}")
    if total_laps < 1:
        raise ValueError("total_laps must be >= 1")

    grid_position = max(int(grid_position), 1)
    congestion_delay = grid_congestion_delay(grid_position)
    grid_mult = grid_traffic_multiplier(grid_position)

    pool = list(WET_COMPOUNDS) if is_wet else list(DRY_COMPOUNDS)
    tp = TRACK_DATA[track]
    if base_laptime is None:
        base_laptime = tp["base_laptime"]
    pit_loss = tp["pit_loss_green"]
    deg_mult = tp["deg_mult"]
    overtaking_delta = tp["overtaking_delta"] * (1.4 if is_wet else 1.0)
    fuel_total = float(sum(fuel_effect(lap, total_laps) for lap in range(1, total_laps + 1)))
    evo_total = float(sum(track_evolution_effect(lap, total_laps) for lap in range(1, total_laps + 1)))
    base_total = base_laptime * total_laps

    traffic_cost_by_lap = [
        pit_lap_traffic_cost(lap, total_laps, overtaking_delta, traffic_risk_factor, grid_mult)
        for lap in range(total_laps + 1)
    ]

    candidates = []
    for stops in range(0, max_stops + 1):
        k = stops + 1

        for combo in itertools.product(pool, repeat=k):
            if require_two_compounds and len(set(combo)) < 2:
                continue
            result = _optimize_split(combo, total_laps, min_stint_length, deg_mult,
                                      traffic_cost_by_lap=traffic_cost_by_lap)
            if result is None:
                continue
            tire_and_traffic_cost, cut_points = result
            traffic_penalty = sum(
                pit_lap_traffic_cost(m, total_laps, overtaking_delta, traffic_risk_factor, grid_mult)
                for m in cut_points[1:]
            )
            start_penalty = START_COMPOUND_PENALTY.get(combo[0], 0.0)
            estimated_time = (base_total + tire_and_traffic_cost + fuel_total + evo_total
                               + stops * (pit_loss + INLAP_PENALTY)
                               + congestion_delay + start_penalty)
            candidates.append({
                "stops": stops,
                "compounds": combo,
                "cut_points": cut_points,
                "estimated_time": estimated_time,
                "traffic_penalty": traffic_penalty,
                "start_penalty": start_penalty,
            })

    if not candidates:
        raise ValueError(
            "No feasible strategy found for given parameters "
            "(try reducing minimum stint length or increasing total lap count)."
        )

    candidates.sort(key=lambda c: c["estimated_time"])
    best = candidates[0]
    strategy = _cutpoints_to_strategy(best["compounds"], best["cut_points"], total_laps)

    return {
        "strategy": strategy,
        "estimated_time": best["estimated_time"],
        "stops": best["stops"],
        "compounds": best["compounds"],
        "top_candidates": candidates[:top_n],
        "grid_position": grid_position,
        "congestion_delay": congestion_delay,
    }


if __name__ == "__main__":
    strategy_a = [{"compound": "MEDIUM", "pit_lap": 20}, {"compound": "HARD", "pit_lap": None}]
    strategy_b = [{"compound": "HARD", "pit_lap": 25}, {"compound": "MEDIUM", "pit_lap": None}]

    result = simulate_two_car_race(strategy_a, strategy_b, track="Monza", total_laps=53,
                                    base_laptime=88.0, is_wet=False, simulate_sc=True, seed=1)
    print(f"Total A: {result['total_a']:.2f}s | Total B: {result['total_b']:.2f}s")
    print(f"Delta (B-A): {result['delta']:.2f}s | Winner: {result['winner']}")
    print(f"SC/VSC Events: {result['sc_events'] or 'None'}")
