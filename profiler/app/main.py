from __future__ import annotations

import argparse
from collections.abc import Callable
import logging
from typing import Sequence

from pydantic_settings import BaseSettings
import structlog

from app.config import ClickHouseConfig, ProfilerConfig, WriteReadConfig
from app.scenarios.write_read import runner as wr_runner

SCENARIOS: tuple[str, ...] = ("write_read",)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ClickHouse profiler runner.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser: argparse.ArgumentParser = subparsers.add_parser(
        "run", help="Run profiler scenarios"
    )
    run_parser.add_argument("scenario", choices=SCENARIOS)
    return parser.parse_args(argv)


def _load_scenario_config(scenario: str):
    if scenario == "write_read":
        return WriteReadConfig()
    raise ValueError(f"unsupported scenario: {scenario}")


def _get_scenario_runner(
    scenario: str,
) -> Callable[[BaseSettings, ClickHouseConfig, ProfilerConfig], str]:
    if scenario == "write_read":
        return wr_runner.run  # pyright: ignore[reportReturnType]
    raise ValueError(f"unsupported scenario: {scenario}")


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = _parse_args(argv)
    logger = structlog.get_logger("profiler.main")

    profiler_config = ProfilerConfig()
    clickhouse_config = ClickHouseConfig()
    scenario = args.scenario
    scenario_config = _load_scenario_config(scenario)

    logger.info(
        "profiler_started",
        scenario=scenario,
        config=scenario_config.model_dump() if scenario_config else {},
    )
    runner = _get_scenario_runner(scenario)

    result = runner(
        scenario_config,
        clickhouse_config,
        profiler_config,
    )

    logger.info(
        "profiler_finished",
        scenario=scenario,
        result=result,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
