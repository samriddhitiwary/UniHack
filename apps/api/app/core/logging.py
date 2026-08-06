"""Standard-output logging configuration."""

import logging


def configure_logging(level: str) -> None:
    """Configure concise logging suitable for local processes and CloudWatch."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
