"""Common exceptions, classes, and functions for DoorstopDemo."""

import argparse
import logging

from demo import VERSION

VERBOSITY = 0  # global verbosity setting for controlling string formatting
STR_VERBOSITY = 3
MAX_VERBOSITY = 4


class DemoError(Exception):

    """Generic DoorstopDemo error."""


class DemoWarning(DemoError, Warning):

    """Generic DoorstopDemo warning."""


class DemoInfo(DemoError, Warning):

    """Generic DoorstopDemo info."""


class HelpFormatter(argparse.HelpFormatter):

    """Command-line help text formatter with wider help text."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, max_help_position=40, **kwargs)


class WarningFormatter(logging.Formatter, object):

    """Logging formatter that displays verbose formatting for WARNING+."""

    def __init__(self, default_format, verbose_format, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_format = default_format
        self.verbose_format = verbose_format

    def format(self, record):  # pragma: no cover, manual test
        """Python 3 hack to change the formatting style dynamically."""
        if record.levelno > logging.INFO:
            self._style._fmt = self.verbose_format  # pylint: disable=W0212
        else:
            self._style._fmt = self.default_format  # pylint: disable=W0212
        return super().format(record)

# Shared command-line arguments
DEBUG = argparse.ArgumentParser(add_help=False)
DEBUG.add_argument('-V', '--version', action='version', version=VERSION)
DEBUG.add_argument('-v', '--verbose', action='count', default=0,
                   help="enable verbose logging")
SHARED = {'formatter_class': HelpFormatter, 'parents': [DEBUG]}
