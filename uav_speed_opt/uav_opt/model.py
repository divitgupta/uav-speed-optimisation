"""UAV flight-speed model: power, energy, time and reliability as functions of airspeed V.

Power model: rotary-wing UAV model of Zeng, Xu & Zhang (2019), IEEE TWC 18(4).
Reliability model: illustrative exponential model R = exp(-lambda(V) * T), with a
speed-dependent failure rate lambda(V) = lambda0 * (1 + k (V/Vmax)^2) (Phase-1 assumption,
after Petritoli, Leccese & Ciani, 2018). lambda0 and k are ASSUMPTIONS, not company data.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

# Reference coefficients, Zeng et al. (2019), Table I (aircraft weight W = 20 N).
ZENG = dict(P0=79.86, Pi=88.63, U_tip=120.0, v0=4.03, d0=0.6, rho=1.225, s=0.05, A=0.503)
M_REF = 20.0 / 9.81  # kg


@dataclass(frozen=True)
class UAV:
    """A multirotor UAV. Coefficients are scaled from the Zeng reference by mass."""
    mass_kg: float = M_REF          # take-off mass incl. payload (kg)
    v_max: float = 20.0             # published max speed (m/s)
    battery_kJ: float = 250.0       # usable battery energy (kJ)
    lam0: float = 0.01              # base failure rate (per flight-hour) - ASSUMPTION
    k: float = 2.0                  # speed-stress factor - ASSUMPTION

    @property
    def scale(self) -> float:
        return self.mass_kg / M_REF

    def with_payload(self, payload_kg: float) -> "UAV":
        return replace(self, mass_kg=self.mass_kg + payload_kg)


@dataclass(frozen=True)
class Mission:
    distance_km: float = 5.0
    headwind_ms: float = 0.0        # positive = headwind along the route
    r_min: float = 0.995            # required mission reliability


def power_w(V, uav: UAV):
    """Propulsion power P(V) in W.

    P0 and Pi scale linearly with mass (rotor disc area grows with mass => constant disc
    loading, so v0 is unchanged); the parasite term scales with frontal area ~ m^(2/3).
    """
    V = np.asarray(V, dtype=float)
    z, s = ZENG, uav.scale
    blade = z["P0"] * s * (1 + 3 * V**2 / z["U_tip"] ** 2)
    induced = z["Pi"] * s * np.sqrt(np.sqrt(1 + V**4 / (4 * z["v0"] ** 4)) - V**2 / (2 * z["v0"] ** 2))
    parasite = 0.5 * z["d0"] * z["rho"] * z["s"] * z["A"] * s ** (2 / 3) * V**3
    return blade + induced + parasite


def hover_power_w(uav: UAV) -> float:
    return float(power_w(0.0, uav))


def ground_speed(V, mission: Mission):
    return np.asarray(V, dtype=float) - mission.headwind_ms


def time_s(V, mission: Mission):
    vg = ground_speed(V, mission)
    with np.errstate(divide="ignore"):
        return np.where(vg > 0, mission.distance_km * 1000.0 / np.where(vg > 0, vg, 1), np.inf)


def energy_kj(V, uav: UAV, mission: Mission):
    return power_w(V, uav) * time_s(V, mission) / 1000.0


def failure_rate_per_h(V, uav: UAV):
    V = np.asarray(V, dtype=float)
    return uav.lam0 * (1 + uav.k * (V / uav.v_max) ** 2)


def reliability(V, uav: UAV, mission: Mission):
    return np.exp(-failure_rate_per_h(V, uav) * time_s(V, mission) / 3600.0)


def evaluate(V, uav: UAV, mission: Mission) -> dict:
    """All objectives and constraint values for speed(s) V."""
    V = np.asarray(V, dtype=float)
    E = energy_kj(V, uav, mission)
    T = time_s(V, mission) / 60.0
    R = reliability(V, uav, mission)
    feasible = (V <= uav.v_max + 1e-9) & (R >= mission.r_min) & (E <= uav.battery_kJ) & np.isfinite(T)
    return dict(V=V, P=power_w(V, uav), E_kJ=E, T_min=T, R=R, feasible=feasible)


def budget_from_endurance(uav_mass_kg: float, endurance_min: float, eta: float = 0.8) -> float:
    """Usable energy (kJ) implied by a published flight time: eta * P_hover * t."""
    return eta * hover_power_w(UAV(mass_kg=uav_mass_kg)) * endurance_min * 60 / 1000.0
