"""Three optimisers for the constrained bi-objective speed problem.

    minimise  {E(V), T(V)}
    s.t.      R(V) >= R_min,  E(V) <= E_battery,  V_min <= V <= V_max
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize_scalar

from .model import UAV, Mission, evaluate

V_MIN = 1.0


@dataclass
class Result:
    method: str
    v_energy: float | None      # min-energy feasible speed
    v_time: float | None        # min-time feasible speed
    v_star: float | None        # weighted-sum optimum
    runtime_ms: float
    evaluations: int
    front: np.ndarray | None = None  # Pareto set (V values)


def grid_search(uav: UAV, mission: Mission, w: float = 0.5, step: float = 0.1) -> Result:
    t0 = time.perf_counter()
    V = np.arange(V_MIN, uav.v_max + 1e-9, step)
    ev = evaluate(V, uav, mission)
    f = ev["feasible"]
    if not f.any():
        return Result("Grid search", None, None, None, (time.perf_counter() - t0) * 1e3, len(V))
    E, T = ev["E_kJ"], ev["T_min"]
    e_min, t_min = E[f].min(), T[f].min()
    J = np.where(f, w * E / e_min + (1 - w) * T / t_min, np.inf)
    vE, vT, vS = V[f][np.argmin(E[f])], V[f].max(), V[np.argmin(J)]
    front = V[f & (V >= vE)]
    return Result("Grid search", float(vE), float(vT), float(vS), (time.perf_counter() - t0) * 1e3, len(V), front)


def _penalised(V, uav, mission):
    ev = evaluate(np.array([V]), uav, mission)
    viol = max(0.0, mission.r_min - ev["R"][0]) * 1e4 + max(0.0, ev["E_kJ"][0] - uav.battery_kJ) / max(uav.battery_kJ, 1)
    return ev, viol


def weighted_sum_scipy(uav: UAV, mission: Mission, w: float = 0.5) -> Result:
    """Bounded Brent search on penalised objectives (SciPy)."""
    t0 = time.perf_counter()
    n = [0]

    def f_energy(V):
        n[0] += 1
        ev, viol = _penalised(V, uav, mission)
        return ev["E_kJ"][0] * (1 + 100 * viol)

    rE = minimize_scalar(f_energy, bounds=(V_MIN, uav.v_max), method="bounded", options={"xatol": 1e-3})
    vE = float(rE.x)
    # min-time feasible speed: largest V that satisfies the constraints (bisection on feasibility)
    lo, hi = vE, uav.v_max
    if _penalised(hi, uav, mission)[1] == 0:
        vT = hi
    else:
        for _ in range(40):
            mid = 0.5 * (lo + hi); n[0] += 1
            lo, hi = (mid, hi) if _penalised(mid, uav, mission)[1] == 0 else (lo, mid)
        vT = lo
    evE = evaluate(np.array([vE]), uav, mission); evT = evaluate(np.array([vT]), uav, mission)
    if not (evE["feasible"][0] and evT["feasible"][0]):
        return Result("Weighted sum (SciPy)", None, None, None, (time.perf_counter() - t0) * 1e3, n[0])
    e_min, t_min = evE["E_kJ"][0], evT["T_min"][0]

    def J(V):
        n[0] += 1
        ev, viol = _penalised(V, uav, mission)
        return w * ev["E_kJ"][0] / e_min + (1 - w) * ev["T_min"][0] / t_min + 100 * viol

    rJ = minimize_scalar(J, bounds=(vE, vT), method="bounded", options={"xatol": 1e-3})
    return Result("Weighted sum (SciPy)", vE, float(vT), float(rJ.x), (time.perf_counter() - t0) * 1e3, n[0] + rE.nfev)


def nsga2(uav: UAV, mission: Mission, w: float = 0.5, pop: int = 40, gens: int = 60, seed: int = 1) -> Result:
    """Pareto front with NSGA-II (pymoo); V* = front point minimising the same weighted sum."""
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import ElementwiseProblem
    from pymoo.optimize import minimize

    class SpeedProblem(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=1, n_obj=2, n_ieq_constr=2, xl=np.array([V_MIN]), xu=np.array([uav.v_max]))

        def _evaluate(self, x, out, *args, **kwargs):
            ev = evaluate(x, uav, mission)
            out["F"] = [ev["E_kJ"][0], ev["T_min"][0]]
            out["G"] = [mission.r_min - ev["R"][0], ev["E_kJ"][0] - uav.battery_kJ]

    t0 = time.perf_counter()
    res = minimize(SpeedProblem(), NSGA2(pop_size=pop), ("n_gen", gens), seed=seed, verbose=False)
    rt = (time.perf_counter() - t0) * 1e3
    if res.X is None:
        return Result("NSGA-II (pymoo)", None, None, None, rt, pop * gens)
    X = np.atleast_2d(res.X)[:, 0]
    F = np.atleast_2d(res.F)
    J = w * F[:, 0] / F[:, 0].min() + (1 - w) * F[:, 1] / F[:, 1].min()
    return Result("NSGA-II (pymoo)", float(X[np.argmin(F[:, 0])]), float(X[np.argmin(F[:, 1])]),
                  float(X[np.argmin(J)]), rt, pop * gens, np.sort(X))
