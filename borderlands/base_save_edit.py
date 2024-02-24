#!/usr/bin/env python3

import sys
import traceback
from typing import List

from borderlands.bl2 import AppBL2
from borderlands.savefile import BaseApp

ERROR_TEMPLATE = """
Something went wrong.
Arguments: {}
"""


def run(*, game_name: str, args: List[str]) -> None:
    # noinspection PyBroadException
    try:
        app: BaseApp
        if game_name == 'BL2':
            app = AppBL2(args)
        else:
            raise RuntimeError(f'unknown game: {game_name!r}')

        app.run()

    except Exception:
        sys.stdout.flush()
        sys.stderr.flush()
        print(ERROR_TEMPLATE.format(repr(args)), file=sys.stderr)
        traceback.print_exc(None, sys.stderr)
        sys.exit(1)
