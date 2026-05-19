from ._types import KeyRateResult
from .channels.base import Channel
from .finite_size import tomamichel_correction
from .protocols.base import Protocol
from .sdp import solve_key_rate_sdp


def key_rate(
    protocol: Protocol,
    channel: Channel,
    *,
    solver: str = "CLARABEL",
    n_signals: int = 0,
    eps_security: float = 1e-10,
) -> KeyRateResult:
    result = solve_key_rate_sdp(protocol, channel, solver=solver)

    if n_signals > 0 and result.r_lower > 0.0:
        n_detected = int(channel.total_yield() * n_signals)
        penalty = tomamichel_correction(n_detected, eps_security)
        result.r_lower = max(
            0.0, result.r_lower - channel.total_yield() * penalty
        )

    return result
