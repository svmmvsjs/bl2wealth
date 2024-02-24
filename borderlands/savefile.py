import argparse
import base64
import binascii
import dataclasses
import hashlib
import io
import json
import os
import struct
import sys
from typing import List, Tuple, Dict, Any, Optional, IO, Union

from borderlands.challenges import Challenge, unwrap_challenges, wrap_challenges
from borderlands.config import parse_args
from borderlands.util.bitstreams import ReadBitstream, WriteBitstream
from borderlands.util.common import conv_binary_to_str, rotate_data_right, xor_data, create_body
from borderlands.util.common import invert_structure, replace_raw_item_key
from borderlands.util.data_types import PlayerDict
from borderlands.util.errors import BorderlandsError
from borderlands.util.huffman import (
    read_huffman_tree,
    make_huffman_tree,
    write_huffman_tree,
    invert_tree,
    huffman_decompress,
    huffman_compress,
)
from borderlands.util.lzo1x import lzo1x_decompress, lzo1x_1_compress
from borderlands.util.protobuf import (
    read_protobuf_value,
    read_repeated_protobuf_value,
    write_repeated_protobuf_value,
    read_protobuf,
    apply_structure,
    write_protobuf,
    remove_structure,
)


@dataclasses.dataclass(frozen=True)
class InputFileData:
    filename: str
    filehandle: IO
    close: bool


class BaseApp:
    """
    Base application class.
    """

    item_sizes = (
        (8, 17, 20, 11, 7, 7, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16),
        (8, 13, 20, 11, 7, 7, 17, 17, 17, 17, 17, 17, 17, 17, 17, 17, 17),
    )

    item_header_sizes = (
        (("type", 8), ("balance", 10), ("manufacturer", 7)),
        (("type", 6), ("balance", 10), ("manufacturer", 7)),
    )

    def __init__(
            self,
            *,
            args: List[str],
            item_struct_version: int,
            game_name: str,
            item_prefix: str,
            black_market_keys: Tuple[str, ...],
            unlock_choices: List[str],  # Available choices for --unlock option
            challenges: Dict[int, Challenge],
    ) -> None:
        # B2 version is 7
        self.item_struct_version = item_struct_version

        # Item export/import prefix
        self.item_prefix = item_prefix

        self.black_market_keys = black_market_keys

        # There are two possible ways of uniquely identifying challenges in this file:
        # via their numeric position in the list, or by what looks like an internal
        # ID (though that ID is constructed a little weirdly, so I'm not sure if it's
        # actually intended to be used that way or not).
        #
        # I did run some tests, and it looks like internally, B2 probably does use
        # that ID field to identify the challenges...  You can mess around with the
        # order in which they're saved to the file, but so long as the ID field
        # is still pointing to the challenge you want, it'll be read in properly
        # (and then when you save your game, they'll be written back out in the
        # original order).
        #
        # Given that, I decided to go ahead and use that probably-ID field as the
        # index on this dict, rather than the order.  That should be slightly more
        # flexible for anyone editing the JSON directly, and theoretically
        # shouldn't be a problem in the future since there won't be any new major
        # DLC for B2
        self.challenges = challenges

        # Parse Arguments
        self.config = parse_args(
            args=args,
            setup_currency_args=self.setup_currency_args,
            setup_game_specific_args=self.setup_game_specific_args,
            game_name=game_name,
            unlock_choices=unlock_choices,
        )

        # Sets up our main save_structure var which controls how we read the file
        self.save_structure = self.create_save_structure()

    def pack_item_values(self, is_weapon: int, values: list) -> bytes:
        i = 0
        item_bytes = bytearray(32)
        for value, size in zip(values, self.item_sizes[is_weapon]):
            if value is None:
                break
            j = i >> 3
            value = value << (i & 7)
            while value != 0:
                item_bytes[j] |= value & 0xFF
                value = value >> 8
                j = j + 1
            i = i + size
        if (i & 7) != 0:
            value = 0xFF << (i & 7)
            item_bytes[i >> 3] |= value & 0xFF
        return bytes(item_bytes[: (i + 7) >> 3])

    def unpack_item_values(self, is_weapon: int, data: bytes) -> List[Optional[int]]:
        i = 8
        data = b' ' + data
        end = len(data) * 8
        result: List[Optional[int]] = []
        for size in self.item_sizes[is_weapon]:
            j = i + size
            if j > end:
                result.append(None)
                continue
            value = 0
            for b in data[j >> 3: (i >> 3) - 1: -1]:
                value = (value << 8) | b
            result.append((value >> (i & 7)) & ~(0xFF << size))
            i = j
        return result

    def wrap_item(self, *, is_weapon: int, values: list, key: int) -> bytes:
        item = self.pack_item_values(is_weapon, values)
        header = struct.pack(">Bi", (is_weapon << 7) | self.item_struct_version, key)
        return header + create_body(item=item, header=header, key=key)

    def unwrap_item(self, data: bytes) -> Tuple[int, List[Optional[int]], int]:
        version_type, key = struct.unpack(">Bi", data[:5])
        is_weapon = version_type >> 7
        raw = rotate_data_right(xor_data(data[5:], key >> 5), key & 31)
        return is_weapon, self.unpack_item_values(is_weapon, raw[2:]), key

    def unwrap_black_market(self, value: bytes) -> dict:
        sdu_list = read_repeated_protobuf_value(value, 0)
        return dict(zip(self.black_market_keys, sdu_list))

    def wrap_black_market(self, value: dict) -> bytes:
        sdu_list = [value[k] for k in self.black_market_keys[: len(value)]]
        return write_repeated_protobuf_value(sdu_list, 0)

    def unwrap_challenges(self, data: bytes) -> dict:
        return unwrap_challenges(data=data, challenges=self.challenges, endian=self.config.endian)

    def wrap_challenges(self, data: dict) -> bytes:
        return wrap_challenges(data=data, endian=self.config.endian)

    def unwrap_item_info(self, value: bytes) -> dict:
        is_weapon, item, key = self.unwrap_item(value)

        data: Dict[str, Any] = {
            'is_weapon': is_weapon,
            'key': key,
            'set': item[0],
            'level': (item[4], item[5]),  # (grade_index, game_stage)
            '_base64': base64.b64encode(value),
        }
        for i, (k, bits) in enumerate(self.item_header_sizes[is_weapon]):
            x = item[1 + i]
            if x is None:
                sys.exit('unwrap_item_info got None instead of int')
            lib = x >> bits
            asset = x & ~(lib << bits)
            data[k] = {"lib": lib, "asset": asset}
        bits = 10 + is_weapon
        parts: List[Optional[Dict[str, Any]]] = []
        for x in item[6:]:
            if x is None:
                parts.append(None)
            else:
                lib = x >> bits
                asset = x & ~(lib << bits)
                parts.append({"lib": lib, "asset": asset})
        data["parts"] = parts
        return data

    def wrap_item_info(self, value: dict) -> bytes:
        parts = [value["set"]]
        for key, bits in self.item_header_sizes[value["is_weapon"]]:
            v = value[key]
            parts.append((v["lib"] << bits) | v["asset"])
        parts.extend(value["level"])  # (grade_index, game_stage)
        bits = 10 + value["is_weapon"]
        for v in value["parts"]:
            if v is None:
                parts.append(None)
            else:
                parts.append((v["lib"] << bits) | v["asset"])
        return self.wrap_item(is_weapon=value["is_weapon"], values=parts, key=value["key"])

    @staticmethod
    def unwrap_player_data(data: bytes) -> bytes:
        """
        Byte order on the few struct calls here appears to actually be
        hardcoded regardless of platform, so we're perhaps just leaving
        them, rather than using self.config.endian as we're doing elsewhere.
        I suspect this might actually be wrong, though, and just happens to
        work.
        """
        if data[:20] != hashlib.sha1(data[20:]).digest():
            raise BorderlandsError("Invalid save file")

        data = lzo1x_decompress(b'\xf0' + data[20:])
        size, wsg, version = struct.unpack('>I3sI', data[:11])
        if version != 2 and version != 0x02000000:
            raise BorderlandsError(f'Unknown save version {version}')

        if version == 2:
            crc, size = struct.unpack(">II", data[11:19])
        else:
            crc, size = struct.unpack("<II", data[11:19])

        bitstream = ReadBitstream(data[19:])
        tree = read_huffman_tree(bitstream)
        player = huffman_decompress(tree, bitstream, size)

        if (binascii.crc32(player) & 0xFFFFFFFF) != crc:
            raise BorderlandsError("CRC check failed")

        return player

    def wrap_player_data(self, player: bytes) -> bytes:
        """
        There's one call in here which had a hard-coded endian, as with
        unwrap_player_data above, so we're leaving that hardcoded for now.
        I suspect that it's wrong to be doing so, though.
        """
        crc = binascii.crc32(player) & 0xFFFFFFFF

        bitstream = WriteBitstream()
        tree = make_huffman_tree(player)
        write_huffman_tree(tree, bitstream)
        huffman_compress(invert_tree(tree), player, bitstream)
        data = bitstream.getvalue() + b"\x00\x00\x00\x00"

        header = struct.pack(">I3s", len(data) + 15, b'WSG')
        header += struct.pack(self.config.endian + "III", 2, crc, len(player))

        data = lzo1x_1_compress(header + data)[1:]

        return hashlib.sha1(data).digest() + data

    def show_save_info(self, data: bytes) -> None:
        """
        Shows information from file data, based on our config object.
        "data" should be the raw data from a save file.

        Note that if a user is both showing info and making changes,
        we're parsing the protobuf twice, since modify_save also does
        that.  Inefficiency!
        """
        player = read_protobuf(self.unwrap_player_data(data))
        self._show_save_info(player)

    def _show_save_info(self, player: PlayerDict) -> None:
        return

    def _set_money(self, player: PlayerDict) -> None:
        if all(
                x is None
                for x in [
                    self.config.money,
                    self.config.eridium,
                    self.config.seraph,
                    self.config.torgue,
                ]
        ):
            return

        raw = player[6][0][1]
        b = io.BytesIO(raw)
        values = []
        while b.tell() < len(raw):
            values.append(read_protobuf_value(b, 0))
        if self.config.money is not None:
            self.debug(f' - Setting available $$$ to {self.config.money}')
            values[0] = self.config.money
        if self.config.eridium is not None:
            self.debug(f' - Setting available Eridium to {self.config.eridium}')
            values[1] = self.config.eridium
        if self.config.seraph is not None:
            self.debug(f' - Setting available Seraph Crystals to {self.config.seraph}')
            values[2] = self.config.seraph
        if self.config.torgue is not None:
            self.debug(f' - Setting available Torgue Tokens to {self.config.torgue}')
            values[4] = self.config.torgue
        player[6][0] = [0, values]

    def _unlock_features(self, player: PlayerDict) -> None:
        if not self.config.unlock:
            return

        if 'slaughterdome' not in self.config.unlock:
            return

        unlocked, notifications = b'', b''
        if 23 in player:
            unlocked = player[23][0][1]
        if 24 in player:
            notifications = player[24][0][1]
        self.debug(' - Unlocking Creature Slaughterdome')
        if 1 not in unlocked:
            unlocked += b"\x01"
        if 1 not in notifications:
            notifications += b"\x01"
        player[23] = [[2, unlocked]]
        player[24] = [[2, notifications]]

    def _fix_challenge_overflow(self, player: PlayerDict) -> None:
        # TODO: rewrite as standalone function and move to bl2_routines.py
        if not self.config.fix_challenge_overflow:
            return

        self.notice('Fix challenge overflow')
        data2 = self.unwrap_challenges(player[15][0][1])

        for save_challenge in data2['challenges']:
            if save_challenge['id'] in self.challenges:
                if save_challenge['total_value'] >= 2000000000:
                    self.notice(f'fix overflow in: {save_challenge["_name"]}')
                    save_challenge['total_value'] = self.challenges[save_challenge['id']].get_max() + 1

        player[15][0][1] = self.wrap_challenges(data2)

    def modify_save(self, data: bytes) -> bytes:
        """
        Performs a set of modifications on file data, based on our
        config object.  "data" should be the raw data from a save
        file.

        Note that if a user is both showing info and making changes,
        we're parsing the protobuf twice, since show_save_info also does
        that.  Inefficiency!
        """

        player = read_protobuf(self.unwrap_player_data(data))

        self._set_money(player)
        self._unlock_features(player)

        self._fix_challenge_overflow(player)
        self._reset_challenge_or_mission(player)

        return self.wrap_player_data(write_protobuf(player))

    def export_items(self, data, output) -> None:
        """
        Exports items stored in savegame data 'data' to the open
        filehandle 'output'
        """
        player = read_protobuf(self.unwrap_player_data(data))
        skipped_count = 0
        for i, name in ((41, "Bank"), (53, "Items"), (54, "Weapons")):
            count = 0
            content = player.get(i)
            if content is None:
                continue
            print(f'; {name}', file=output)
            for field in content:
                raw: bytes = read_protobuf(field[1])[1][0][1]

                # Borderlands uses some sort-of "fake" items to store some DLC
                # data.  As per the Gibbed sourcecode, this includes:
                #   1. "Currency On Hand"  (?)
                #   2. Last Playthrough Number / Playthroughs completed
                #   3. "Has played in UVHM"
                #   4. Overpower levels unlocked
                #   5. Last Overpower selection
                #
                # The data for these is stored in the `unknown2` field, by this
                # app's data definitions (or the protobuf [2] index).  Regardless,
                # these aren't actual items, so we're skipping them.  See Gibbed
                # Gibbed.Borderlands2.FileFormats/SaveExpansion.cs for details
                # on how to parse the `unknown2` field.
                is_weapon, item, key = self.unwrap_item(raw)
                if item[0] == 255 and all([val == 0 for val in item[1:]]):
                    skipped_count += 1
                else:
                    count += 1
                    raw_bytes = replace_raw_item_key(raw, 0)
                    printable = base64.b64encode(raw_bytes).decode("latin1")
                    code = f'{self.item_prefix}({printable})'
                    print(code, file=output)
            self.debug(f' - {name} exported: {count}')

    def create_save_structure(self) -> Dict[int, Any]:
        raise NotImplementedError()

    @staticmethod
    def setup_game_specific_args(parser: argparse.ArgumentParser) -> None:
        """Function to add game-specific arguments."""
        pass

    @staticmethod
    def notice(message) -> None:
        print(message)

    @staticmethod
    def error(message: str) -> None:
        print(f'ERROR: {message}', file=sys.stderr)

    def debug(self, message: str) -> None:
        if self.config.verbose:
            self.notice(message)

    def _read_input_file(self) -> Union[str, bytes]:
        if self.config.input_filename == '-':
            self.debug('Using STDIN for input file')
            return sys.stdin.read()
        else:
            self.debug(f'Opening {self.config.input_filename} for input file')
            with open(self.config.input_filename, 'rb') as inp:
                return inp.read()

    def _convert_json(self, save_data: Union[str, bytes]) -> Union[str, bytes]:
        if not self.config.json:
            return save_data

        self.debug('Interpreting JSON data')
        data = json.loads(save_data)
        if '1' not in data:
            # This means the file had been output as 'json'
            data = remove_structure(data, invert_structure(self.save_structure))
        return self.wrap_player_data(write_protobuf(data))

    def _prepare_output_file(self) -> Optional[Tuple[IO, bool]]:
        self.debug('')
        outfile = self.config.output_filename

        if outfile == '-':
            self.debug('Using STDOUT for output file')
            return sys.stdout, False

        self.debug(f'Use {outfile!r} for output file')
        if os.path.isdir(outfile):
            raise BorderlandsError(f'Output file is an existing directory: {outfile!r}')
        elif os.path.isfile(outfile):
            if self.config.force:
                self.debug(f'Overwriting output file {outfile!r}')
                os.unlink(outfile)
            else:
                # TODO: what is the point of checking input file name?
                if self.config.input_filename == '-':
                    raise BorderlandsError(
                        f'Output filename {outfile!r}' + ' exists and --force not specified, aborting'
                    )
                else:
                    self.notice('')
                    self.notice(f'Output filename {outfile!r} exists')
                    sys.stdout.flush()
                    sys.stderr.flush()
                    sys.stderr.write('Continue and overwrite? [y|N] ')
                    sys.stderr.flush()
                    answer = sys.stdin.readline()
                    if answer[0].lower() == 'y':
                        os.unlink(outfile)
                    else:
                        self.notice('')
                        self.notice('Abort.')
                        return None
        if self.config.output in ('savegame', 'decoded'):
            mode = 'wb'
        else:
            mode = 'w'

        output_file = open(outfile, mode)
        return output_file, True

    def _reset_challenge_or_mission(self, player: PlayerDict) -> None:
        pass

    def run(self):
        """
        loads data, modifies it, and then outputs new file
        """

        self.debug('')
        save_data = self._read_input_file()

        # If we're reading from JSON, convert it
        save_data = self._convert_json(save_data)

        self.debug('Performing requested changes')
        new_data = self.modify_save(save_data)

        self.show_save_info(new_data)

        # If we have an output file, write to it
        if self.config.output_filename is None:
            if new_data != save_data:
                sys.exit('Changes were made but no output file specified')

            self.debug('No output file specified. Exiting!')
            return

        # Open output file
        output_file_info = self._prepare_output_file()
        if output_file_info is None:
            return
        output_file, close = output_file_info

        # Now output based on what we've been told to do
        if self.config.output == 'items':
            self.debug('Exporting items')
            self.export_items(new_data, output_file)
        elif self.config.output == 'savegame':
            self.debug('Writing savegame file')
            output_file.write(new_data)
        else:
            player = self.unwrap_player_data(new_data)
            if self.config.output in ('decodedjson', 'json'):
                self.debug('Converting to JSON for more human-readable output')
                data = read_protobuf(player)
                if self.config.output == 'json':
                    data = apply_structure(data, self.save_structure)
                player = json.dumps(conv_binary_to_str(data), sort_keys=True, indent=4)
            output_file.write(player)

        if close:
            output_file.close()

        self.notice('Done')

    @staticmethod
    def setup_currency_args(parser) -> None:
        raise NotImplementedError()
