from dataclasses import dataclass


@dataclass
class KeyRateResult:
    r_lower: float
    sdp_status: str
    solve_time_s: float

    @property
    def secure(self) -> bool:
        return self.r_lower > 0.0 and self.sdp_status in (
            "optimal",
            "optimal_inaccurate",
        )
