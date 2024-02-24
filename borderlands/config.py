import argparse
import os
from typing import Union, Optional, List, Callable, Any, Dict


class Config(argparse.Namespace):
    """
    Class to hold configuration information
    """

    # Given by the user, booleans
    json = False
    big_endian = False
    verbose = True
    force = False

    # Given by the user, strings
    output = 'savegame'
    input_filename = '-'
    output_filename = '-'

    # Former 'modify' options
    money = None
    eridium = None
    seraph = None
    torgue = None

    unlock: Dict[str, Any] = {}
    fix_challenge_overflow = False

    # Config options interpreted from the above
    endian = '<'
    changes = False

    def finish(
        self,
        *,
        parser: argparse.ArgumentParser,
    ) -> None:
        """
        Some extra sanity checks on our options.  "parser" should
        be an active ArgumentParser object we can use to raise
        errors.  "app" is an App object which we use for a couple
        lookups.
        """

        # byte order
        if self.big_endian:
            self.endian = '>'
        else:
            self.endian = '<'

        # Can't read/write to the same file
        if (
            self.output_filename is not None
            and self.input_filename != '-'
            and os.path.abspath(self.input_filename) == os.path.abspath(self.output_filename)
        ):
            parser.error('input_filename and output_filename cannot be the same file')


class DictAction(argparse.Action):
    """
    Custom argparse action to put list-like arguments into
    a dict (where the value will be True) rather than a list.
    This is probably implemented fairly shoddily.
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        """
        Constructor, taken right from https://docs.python.org/2.7/library/argparse.html#action
        """
        if nargs is not None:
            raise ValueError('nargs is not allowed')
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """
        Actually setting a value.  Forces the attr into a dict if it isn't already.
        """
        arg_value = getattr(namespace, self.dest)
        if not isinstance(arg_value, dict):
            arg_value = {}
        arg_value[values] = True
        setattr(namespace, self.dest, arg_value)


def parse_args(
    *,
    args: List[str],
    setup_currency_args: Callable[[argparse.ArgumentParser], None],
    setup_game_specific_args: Callable[[argparse.ArgumentParser], None],
    game_name: str,
    unlock_choices: List[str],
):
    """
    Parse our arguments.
    """
    # Set up our config object
    config = Config()

    parser = argparse.ArgumentParser(
        description=f'Modify {game_name} Save Files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Optional args

    parser.add_argument(
        '-o',
        '--output',
        choices=['savegame', 'decoded', 'decodedjson', 'json', 'items', 'none'],
        default='savegame',
        help="""
                Output file format.  The most useful to humans are: savegame, json, and items.
                If no output file is specified, this will revert to `none`.
                """,
    )

    parser.add_argument(
        '-j',
        '--json',
        action='store_true',
        help='read savegame data from JSON format, rather than savegame',
    )

    parser.add_argument(
        '-b',
        '--bigendian',
        action='store_true',
        dest='big_endian',
        help='change the output format to big-endian, to write PS/xbox save files',
    )

    # TODO: rewrite with "-v/--verbose"
    parser.add_argument(
        '-q',
        '--quiet',
        dest='verbose',
        action='store_false',
        help='quiet output (should generate no output unless there are errors)',
    )

    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help='force output file overwrite, if the destination file exists',
    )

    parser.add_argument(
        '--money',
        type=int,
        help='Money to set for character',
    )

    setup_currency_args(parser)

    parser.add_argument(
        '--unlock',
        action=DictAction,
        choices=unlock_choices,
        default={},
        help='Game features to unlock',
    )

    parser.add_argument(
        '--fix-challenge-overflow',
        action='store_true',
        help='Fix values for challenges which appear as huge negative numbers',
    )

    # Positional args

    parser.add_argument('input_filename', help='Input filename, can be "-" to specify STDIN')

    parser.add_argument(
        'output_filename',
        nargs='?',
        help="""
                Output filename, can be "-" to specify STDOUT.  Can be optional, in
                which case no output file is produced.
                """,
    )

    # Additional game-specific arguments
    setup_game_specific_args(parser)

    # Actually parse the args
    parser.parse_args(args, config)

    # Do some extra fiddling
    config.finish(parser=parser)

    # Some sanity checking with output type and output_filename
    if config.output_filename is None:
        # NOTE: no more config.changes support: check at the end if data changed

        # If we manually specified an output type, we'll also need an output filename.
        # It's possible in this case that the user explicitly set `savegame` as the
        # output, rather than just leaving it at the default, but I don't think it's
        # worth the shenanigans necessary to detect that.
        if config.output not in {'savegame', 'none'}:
            parser.error(f"No output_filename was specified, but output type '{config.output}' was specified")

        # If we got here, we're probably good, but force ourselves to `none` output
        config.output = 'none'

    else:
        # If we have an output filename but `none` output, complain about it.
        if config.output == 'none':
            parser.error("Output filename specified but with `none` output")

    return config
