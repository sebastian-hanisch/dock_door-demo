"""
Ein-Klick-Beispielszenarien und Permalink-Logik - dasselbe SETTING_SPECS-
Muster wie bei den anderen Demos: eine Wahrheitsquelle für Wertebereiche,
aus der sowohl die Slider als auch die Permalink-Begrenzung lesen, inklusive
NaN/Infinity-Schutz.
"""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

from dock_constants import DEFAULT_HALL_DEPTH, DEFAULT_HALL_WIDTH, DEFAULT_N_DOORS


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


SETTING_SPECS = {
    "n_doors_slider": SettingSpec("n_doors", int, DEFAULT_N_DOORS, 4, 40),
    "hall_width_slider": SettingSpec("width", float, DEFAULT_HALL_WIDTH, 30.0, 300.0),
    "hall_depth_slider": SettingSpec("depth", float, DEFAULT_HALL_DEPTH, 10.0, 100.0),
    "flow_concentration_slider": SettingSpec("flow_conc", float, 0.5, 0.0, 1.0),
    "n_hot_lanes_slider": SettingSpec("n_hot", int, 2, 1, 6),
    "seed_input": SettingSpec("seed", int, 7, 0, 2_000_000_000),
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def apply_preset(values):
    """values: Dict von SETTING_SPECS-Schlüssel (z. B. 'n_doors_slider') auf
    den zu setzenden Wert - iteriert wie load_permalink_settings() über
    SETTING_SPECS statt sich auf eine feste Positionsreihenfolge zu
    verlassen. Eine frühere Version nahm sechs positionelle Parameter
    entgegen; eine künftige Umsortierung oder Erweiterung von SETTING_SPECS
    hätte dort stillschweigend falsche Werte zugewiesen, ohne dass ein Test
    das erkannt hätte."""
    unknown = set(values) - set(SETTING_SPECS)
    assert not unknown, f"Unbekannte Preset-Schlüssel (kein Eintrag in SETTING_SPECS): {unknown}"
    for state_key in SETTING_SPECS:
        if state_key in values:
            st.session_state[state_key] = values[state_key]
    st.session_state["force_regen"] = True


def randomize_seed():
    """on_click-Callback für den 'Neues Szenario generieren'-Button - würfelt
    selbst einen neuen Seed, damit ein Klick immer sichtbar wirkt (identisches
    Muster wie in den anderen Demos, siehe dortige Historie zum sonst
    wirkungslosen Button bei unverändertem Seed)."""
    st.session_state["seed_input"] = random.randint(0, 2_000_000_000)
    st.session_state["force_regen"] = True


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    applied_any = False
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if isinstance(value, float) and not math.isfinite(value):
                    continue
                if spec.lo is not None:
                    value = max(spec.lo, value)
                if spec.hi is not None:
                    value = min(spec.hi, value)
                st.session_state[state_key] = value
                applied_any = True
            except (ValueError, TypeError):
                pass
    if applied_any:
        st.session_state["force_regen"] = True
    st.session_state["permalink_loaded"] = True


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def sync_query_params(n_doors, hall_width, hall_depth, flow_concentration, n_hot_lanes, seed):
    try:
        st.query_params["n_doors"] = str(n_doors)
        st.query_params["width"] = str(hall_width)
        st.query_params["depth"] = str(hall_depth)
        st.query_params["flow_conc"] = str(flow_concentration)
        st.query_params["n_hot"] = str(n_hot_lanes)
        st.query_params["seed"] = str(int(seed))
    except Exception:
        pass
