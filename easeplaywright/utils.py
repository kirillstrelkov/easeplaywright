"""easeplaywright utilities."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from random import choice
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable


def get_timestamp() -> str:
    """Return current timestamp."""
    timetuple = datetime.now().timetuple()  # noqa: DTZ005
    t = timetuple[:6]
    return f"{t[0]}{t[1]:02d}{t[2]:02d}{t[3]:02d}{t[4]:02d}{t[5]:02d}"


def get_random_value(values: list[Any], *val_to_skip: str) -> Any:  # noqa: ANN401
    """Return random value from list."""
    tmp_values = list(values)
    for skipped in val_to_skip:
        tmp_values.remove(skipped)
    return choice(tmp_values)  # noqa: S311


class Logger:
    """Logger class."""

    def __init__(
        self,
        name: str | None = None,
        *,
        log_to_console: bool = True,
        file_path: str | None = None,
        handler: logging.Handler | Callable[..., Any] | None = None,
        level: int = logging.INFO,
    ) -> None:
        """Initialize."""
        self.__logger = logger

        if log_to_console:
            self.__logger.add(sys.stdout, filter=name, level=level)

        if file_path:
            self.__logger.add(file_path, filter=name, level=level)

        if handler:
            self.__logger.add(handler, filter=name, level=level)

    def debug(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log debug message."""
        self.__logger.info(msg, *args, **kwargs)

    def info(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log info message."""
        self.__logger.info(msg, *args, **kwargs)

    def warn(self, msg: str, *args: object, **kwargs: object) -> None:
        """Log warning message."""
        self.__logger.warning(msg, *args, **kwargs)

    warning = warn
