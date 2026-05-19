import time

import cvxpy as cp
import numpy as np

from ._types import KeyRateResult
from .channels.base import Channel
from .protocols.base import Protocol


def solve_key_rate_sdp(
    protocol: Protocol,
    channel: Channel,
    solver: str = "CLARABEL",
) -> KeyRateResult:
    dim = protocol.dim_a * protocol.dim_b
    rho = cp.Variable((dim, dim), symmetric=True)

    constraints = [rho >> 0, cp.trace(rho) == 1]

    obs = protocol.observables()
    exp = channel.expectations()
    for name, op in obs.items():
        if name in exp:
            constraints.append(cp.trace(op @ rho) == exp[name])

    i_b = np.eye(protocol.dim_b)
    pinch_ops = [np.kron(p, i_b) for p in protocol.key_projectors()]
    pinched = cp.Variable((dim, dim), symmetric=True)
    constraints.append(pinched == sum(p @ rho @ p for p in pinch_ops))

    objective = cp.Minimize(cp.quantum_rel_entr(rho, pinched, quad_approx=(2, 2)))
    problem = cp.Problem(objective, constraints)

    t0 = time.time()
    problem.solve(solver=solver)
    elapsed = time.time() - t0

    if problem.status not in ("optimal", "optimal_inaccurate"):
        return KeyRateResult(
            r_lower=0.0,
            sdp_status=problem.status or "unknown",
            solve_time_s=elapsed,
        )

    sdp_bits = float(problem.value) / np.log(2.0)
    leak_per_pulse = protocol.leakage(channel)
    r_lower = max(0.0, channel.single_photon_yield() * sdp_bits - leak_per_pulse)

    return KeyRateResult(
        r_lower=r_lower,
        sdp_status=problem.status,
        solve_time_s=elapsed,
    )
