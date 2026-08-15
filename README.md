# 🏁 F1 2026 Race Strategy Simulator

A physics-based race strategy simulator and single-car strategy optimizer for the
2026 Formula 1 regulations (Active Aerodynamics, Manual Override Mode, ~75 kg
fuel tank). Built with Python and [Streamlit](https://streamlit.io).

> ⚠️ This is an educational/hobby model, not an official FIA or team tool. See
> [Model & Assumptions](#model--assumptions) for what is real regulation vs.
> calibrated guesswork.

## What it does

- **Two-car race comparison** — configure two independent pit strategies
  (compound per stint, pit laps, starting grid position) and simulate the
  race lap by lap, including tyre degradation, fuel load, track evolution,
  dirty air / DRS-successor overtaking, and Safety Car / VSC periods.
- **Single-car strategy optimizer** — an exhaustive search + dynamic
  programming solver finds the (approximately) optimal compound sequence and
  pit windows for a given track, lap count, and starting grid position.
- **23 tracks** from the 2026 calendar with per-track degradation, pit loss,
  overtaking difficulty, and Safety Car probability.
- **Grid-position-aware modeling** — front-runners and backmarkers are
  treated differently: clean-air overcuts, traffic on pit return, and
  first-lap congestion all scale with starting position.


## Quickstart

```bash
git clone <your-repo-url>
cd <your-repo-folder>
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

Deployed on [Streamlit Community Cloud](https://streamlit.io/cloud)? No
local setup needed for anyone else — they just open your app's public URL
(https://f1-pitstop-optimiser-j489y4rkzrnqstctkkscqf.streamlit.app). `localhost` only matters for
your own local development.


`race_physics.py` has no dependency on Streamlit and can be imported and run
standalone (`python race_physics.py` runs a sanity-check simulation), which
makes it independently testable — see [Testing](#testing).

## How to use

1. **Race Settings** — pick a track, total laps, and baseline lap time (each
   track has sensible 2026-calibrated defaults).
2. **Track Conditions** — toggle wet conditions, and optionally a
   deterministic or stochastic Safety Car / VSC period.
3. **Strategy A / Strategy B** — for each car, independently set its grid
   position, number of pit stops, tyre compound per stint, and pit lap. Click
   **Run Simulation** to get a lap-by-lap gap chart and full data table.
4. **Optimal Strategy Finder** — set a grid position and constraints (max
   stops, minimum stint length, whether 2 compounds are mandatory), then click
   **Find Optimal Strategy** to get the DP-optimal strategy for a single car
   in reference ("green flag") conditions. You can apply the result directly
   into Strategy A or B with one click.

## Model & assumptions

The simulator combines a few genuinely regulation-driven constants (fuel
tank size, minimum two dry-compound rule) with a number of **calibrated
assumptions** where the real numbers aren't public or don't exist yet for
2026. Every such assumption is tagged `ASSUMPTION` directly in
`race_physics.py`, including:

- Tyre degradation curves and compound offsets (`COMPOUNDS`)
- Outlap penalties per compound (`OUTLAP_PENALTY`)
- Start-compound launch penalty, i.e. the grip/warm-up cost of starting the
  race on a harder tyre (`START_COMPOUND_PENALTY`)
- Track evolution / rubbering-in rate (`TRACK_EVOLUTION_RATE`)
- Safety Car / VSC duration, probability, and lap-time multipliers
- Grid-position effects: first-lap congestion, per-stop traffic risk, and
  the extra cost of pitting early (into a denser pack) vs. late

None of these are drawn from real 2026 telemetry (which doesn't exist yet at
the time of writing) — they're reasoned estimates designed to produce
directionally correct strategic behaviour (e.g. harder tyres favoured from
worse grid slots, softer starts favoured from the front). **If you use this
for anything beyond a demo, recalibrating these constants against real
session data (e.g. via [FastF1](https://github.com/theOehrly/Fast-F1)) would
be the natural next step.**

### Single-car optimizer caveat

`find_optimal_strategy()` optimizes one car in isolation ("green flag"
conditions) — it approximates traffic risk and Safety Car exposure with
static, grid-position-scaled penalties rather than simulating an actual
field of opponents. `simulate_two_car_race()` is the more realistic model
since it simulates real gap-dependent dirty air between two specific cars.

### Known quirk: zero-gap tie-break

When both cars run byte-identical strategies from identical grid positions,
`simulate_two_car_race()` does **not** produce an exact tie. The dirty-air
logic initializes `order = ("A", "B")` and, whenever the previous lap's gap
is exactly `0.0`, always treats car B as the trailing car — so B
consistently picks up the dirty-air penalty and A wins by roughly one
`DIRTY_AIR_TIME_PENALTY` (~0.6s per triggering lap), purely from that
arbitrary tie-break rather than any real strategic difference. This is
covered explicitly in the test suite (see
`test_swapping_strategies_and_grid_positions_mirrors_result`, which checks
symmetry via a strategy swap instead of asserting an exact tie) rather than
silently papered over — it's a minor, easily-triggered-only-by-identical-
inputs edge case, not something that affects any of the actual strategy
comparisons the tool is meant for.

## Testing

`race_physics.py` has no dependency on Streamlit, so it's fully unit-testable
on its own. The suite in `tests/test_race_physics.py` covers three areas:

1. **Config validity** — `TRACK_DATA` / `COMPOUNDS` are well-formed and internally consistent.
2. **Regression tests** — bugs found and fixed during development (e.g. the
   minimum-two-compounds rule silently not applying to 0-stop strategies)
   are pinned down so they can't silently reappear.
3. **Physics sanity checks** — determinism, monotonicity of grid-position
   effects, and backward-compatible defaults (`grid_position=1` must be a
   true no-op).

Run it locally:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

CI runs the same suite automatically on every push/PR via GitHub Actions
(`.github/workflows/tests.yml`).


## Tech stack

- [Streamlit](https://streamlit.io) — UI
- [Plotly](https://plotly.com/python/) — interactive gap chart
- [pandas](https://pandas.pydata.org) / [NumPy](https://numpy.org) — data
  handling and numerical computation

## License

MIT — see [LICENSE](LICENSE).
