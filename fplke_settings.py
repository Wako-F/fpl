import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    season_id: str = os.getenv("FPLKE_SEASON_ID", "2026-27")
    season_label: str = os.getenv("FPLKE_SEASON_LABEL", "2026/27")
    league_id: int = int(os.getenv("FPLKE_LEAGUE_ID", "131"))
    region_id: int = int(os.getenv("FPLKE_REGION_ID", "111"))
    base_url: str = os.getenv("FPLKE_BASE_URL", "https://fantasy.premierleague.com/api")
    user_agent: str = os.getenv(
        "FPLKE_USER_AGENT",
        "fplke-data-platform/1.0 (+editorial-research; contact=fplkenya)",
    )
    request_concurrency: int = int(os.getenv("FPLKE_CONCURRENCY", "4"))
    request_pause_seconds: float = float(os.getenv("FPLKE_REQUEST_PAUSE", "0.15"))
    deep_cohort_size: int = int(os.getenv("FPLKE_DEEP_COHORT_SIZE", "1000"))
    cohort_min_success_rate: float = float(
        os.getenv("FPLKE_COHORT_MIN_SUCCESS_RATE", "0.90")
    )
    content_min_cohort_size: int = int(
        os.getenv("FPLKE_CONTENT_MIN_COHORT_SIZE", "900")
    )

    def __post_init__(self) -> None:
        if self.deep_cohort_size < 1:
            raise ValueError("FPLKE_DEEP_COHORT_SIZE must be positive")
        if not 0 < self.cohort_min_success_rate <= 1:
            raise ValueError("FPLKE_COHORT_MIN_SUCCESS_RATE must be between 0 and 1")
        if not 1 <= self.content_min_cohort_size <= self.deep_cohort_size:
            raise ValueError(
                "FPLKE_CONTENT_MIN_COHORT_SIZE must be between 1 and FPLKE_DEEP_COHORT_SIZE"
            )


settings = Settings()
