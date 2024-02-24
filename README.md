# bl2wealth

* [Running the program](#running-the-program)
* [Input and Output](#input-and-output)
    * [Other Output Formats](#other-output-formats)
* [Modifying Savegames (JSON Method)](#modifying-savegames-json-method)
* [Modifying Savegames (Using Commandline Arguments)](#modifying-savegames-using-commandline-arguments)
    * [Money](#money)
    * [Eridium (Borderlands 2 Only)](#eridium)
    * [Seraph Crystals (Borderlands 2 Only)](#seraph-crystals)
    * [Torgue Tokens (Borderlands 2 Only)](#torgue-tokens)
    * [Unlocks](#unlocks)
        * [Creature Slaughterdome](#creature-slaughterdome)
    * [Fixing Negative-Number Challenges](#fixing-negative-number-challenges)
    * [Resetting features](#resetting-features)
        * [Bad Touch](#bad-touch)   
        * [Doctor's Orders](#doctors-orders)
* [Getting Savegame Information](#getting-savegame-information)
    * [Challenge Accepted achievement progress](#challenge-accepted-achievement-progress)
* [Combining Commandline Options](#combining-commandline-options)
* [Working with Savegames to/from Consoles](#working-with-savegames-tofrom-consoles)
* [Exporting character items](#exporting-character-items)
* [Other commandline options](#other-commandline-options)
    * [Quiet Output](#quiet-output)
    * [Force Overwrites](#force-overwrites)
    * [Help](#help)

# Running the program

`bl2_save_edit.py`

The basic form of the utility is to specify and input and output file. If no
other options are given, the utility effectively just copies the savegame
without making any changes, like so:

    python bl2_save_edit.py save0001.sav save0002.sav

# Input and Output

By default, the utility saves in a format usable by Borderlands, but you can
specify alternate outputs to use, using the `-o` or `--output` option. The
most useful outputs are:

* **`savegame`** - This is the default, and the only output usable by Borderlands itself.
* **`json`** - This is the most human-editable format, saved in a text-based
  heirarchy in JSON format, which should be fairly reasonable to work with.
* **`items`** - This will save the character's inventory and bank into a text
  file which can then be imported into other tools like Gibbed, or imported
  into other characters using this tool.

For example, saving to a JSON file for later hand-editing:

    python bl2_save_edit.py -o json save0001.sav testing.json

After hand-editing a JSON file, you can convert it back by specifying the `-j`
or `--json` option, to tell the utility that you're loading from a JSON file,
like so:

    python bl2_save_edit.py -j testing.json save0002.sav
    python bl2_save_edit.py --json testing.json save0002.sav

To save the character's inventory to a text file:

    python bl2_save_edit.py --output items save0001.save items.txt

## Other Output Formats

There are also a couple other output formats you can specify with `-o`, though
they are primarily only useful to programmers looking to work with the raw data
a little more closely:

* **`decoded`** - The raw protocol buffer data, after decompression.
* **`decodedjson`** - A midway point between `decoded` and `json`, this will generate
  a JSON file, so it'll be technically editable by hand, but most of the internal
  data structures will be present as raw protobuf strings.
* **`none`** - This output won't write a file at all. There's generally no need
  to specify this manually. If you run the utility without an output file, it'll
  switch to this mode automatically (though it will error out if you were also
  specifying an option which would change the savefile in some way).

# Modifying Savegames (JSON Method)

As mentioned above, one way to edit your characters is to save them out
as a parsed JSON file, edit the JSON by hand (in a text editor), and then
re-export the JSON into a savefile. As always, make sure to take backups
of your save files before overwriting them.

1. `python bl2_save_edit.py -o json save0001.sav to_edit.json`
2. Edit `to_edit.json` in a text editor, to suit
3. `python bl2_save_edit.py -j to_edit.json save0001.sav`

# Modifying Savegames (Using Commandline Arguments)

Alternatively, you can alter many attributes of your character by just using
commandline options. You can specify as few or as many of these as you want.
Note that if you specify `-o items` to save a character's items to a text
file, the majority of these options will have no effect.

## Money

Set money with the `--money` option:

    python bl2_save_edit.py --money 3000000 old.sav new.sav

## Eridium

Set available Eridium with the `--eridium` option. Note that the game will
reduce this to a maximum of 500 if you attempt to add more:

    python bl2_save_edit.py --eridium 500 old.sav new.sav

## Seraph Crystals

Set the available Seraph Crystals with the `--seraph` option. The game will
enforce a maximum of 999:

    python bl2_save_edit.py --seraph 999 old.sav new.sav

## Torgue Tokens

Set the available Torgue Tokens with the `--torgue` option. The game will
enforce a maximum of 999:

    python bl2_save_edit.py --torgue 999 old.sav new.sav

## Unlocks

There are a few things which can be unlocked via this utility, with the `--unlock`
option. This option can be specified more than once to unlock more than one
thing.

### Creature Slaughterdome

The Creature Slaughterdome might be unlockable with:

    python bl2_save_edit.py --unlock slaughterdome old.sav new.sav

## Fixing Negative-Number Challenges

Some people find that their game starts showing huge negative numbers for their
challenge variables, caused by the savegame values overflowing the in-game
datatypes. Some threads on the issue:
[one](https://steamcommunity.com/app/49520/discussions/0/1327844097129063344/),
[two](https://steamcommunity.com/app/49520/discussions/0/38596748231645372/).
The `--fix-challenge-overflow` option can fix those up for you, setting them
instead to the max value:

    python bl2_save_edit.py --fix-challenge-overflow old.sav new.sav

Thanks to [Loot Midget](https://github.com/apocalyptech/borderlands2/pull/5)
for this PR!

## Resetting features

Option `--reset` helps to reset some game features.

### Bad Touch

[Bad Touch](https://borderlands.fandom.com/wiki/Bad_Touch) is Moxxi's SMG given to player one per character. 
There is some workaround for obtaining Bad Touch many times 
but it could be spoiled by teammate who takes it right from the Moxxi's hands.

Use `--reset bad-touch` option to restore Bad Touch availability.

### Doctor's Orders

Player or teammates could suddenly get one of four items for this mission and it will influence the midgets farming.

Use `--reset doctors-orders` option to reset Doctor's Orders mission.

Mission will be reset for first active playthrough in this order: UVHM -> TVHM -> Normal mode.

If you want reset both spoiled TVHM and UVHM missions then run script twice with same option. 

# Getting Savegame Information

There's a single option which just shows information about the savegame, instead of
changing anything. If you *only* specify options in this category, you can omit
specifying an output filename, and the utility just print out the requested info
and exit.

## Challenge Accepted achievement progress

To avoid scrolling challenges in game user could use dedicated option
for printing data:

    bl2_save_edit.py --diagnose-challenge-accepted old.sav

That will result something like the following output printed on the console
as the program processes the save:

	Challenge Accepted achievement progress:
	- Shields: Ammo Eater: first level is incomplete, progress 19/20
	- Vehicle: Blue Sparks: first level is incomplete, progress 2/5
	Challenge Accepted: 3 problems found

# Combining Commandline Options

In general, the various options can be combined. To make a few changes to a
savegame but save as parsed JSON:

    python bl2_save_edit.py --name "Laura Palmer" --save-game-id 2 --money 3000000 --output json save0001.sav laura.json

To take that JSON, unlock TVHM and Challenges, and set challenges to their
primed "bonus" levels, and save as a real savefile:

    python bl2_save_edit.py --json --unlock challenges --challenges bonus laura.json save0002.sav

# Working with Savegames to/from Consoles

**NOTE:** As mentioned above, this fork has not actually been tested on
Consoles, so it's possible that the generated savegames might not work. Use
at your own risk!

The safest way to convert a PC savegame to Console, or vice-versa, would be to
use JSON as an intermediate step. For the commands which deal with the
console savegames, be sure to specify the `-b` or `--bigendian` options. For
instance, to convert from a Console savegame to a PC savegame:

    python savegame.py -b -o json xbox.sav pc.json
    python savegame.py -j pc.json pc.sav

Or to convert from a PC savegame to a Console savegame:

    python savegame.py --output json pc.sav xbox.json
    python savegame.py --json --bigendian xbox.json xbox.sav

# Exporting character items

All items stored and held in the character's bank or inventory can be exported
to a text file as a list of codes, in a format compatible with Gibbed save
editor. This is accomplished with `-o items` or `--output items` like so:

    python bl2_save_edit.py -o items savegame.sav items.txt

# Other commandline options

There are a few other commandline options available when running the utilities.

## Quiet Output

By default, the utility is rather chatty and will tell you what it's doing
at all times. To disable output except for errors, use the `-q` or `--quiet`
option:

    python bl2_save_edit.py -q old.sav new.sav
    python bl2_save_edit.py --quiet old.sav new.sav

## Force Overwrites

By default, the utility will refuse to overwrite a file without getting
confirmation from the user first. To disable that yes/no prompt and force
the app to overwrite the file automatically, use `-f` or `--force` like so:

    python bl2_save_edit.py -f old.sav new.sav
    python bl2_save_edit.py --force old.sav new.sav

## Help

The utility will also show you what all of its commandline options are
at the commandline, using the `-h` or `--help` options:

    python bl2_save_edit.py -h
    python bl2_save_edit.py --help


```
usage: bl2_save_edit.py [-h] [-o {savegame,decoded,decodedjson,json,items}]
                          [--money MONEY] [--moonstone MOONSTONE]
                          [--unlock {challenges}]
                          [--challenges {zero,max,bonus}] [--maxammo]
                          input_filename output_filename

Modify Borderlands: The Pre-Sequel Save Files

positional arguments:
  input_filename        Input filename, can be "-" to specify STDIN
  output_filename       Output filename, can be "-" to specify STDOUT

optional arguments:
  -h, --help            show this help message and exit
  -o {savegame,decoded,decodedjson,json,items}, --output {savegame,decoded,decodedjson,json,items}
                        Output file format. The most useful to humans are:
                        savegame, json, and items (default: savegame)
  -j, --json            read savegame data from JSON format, rather than
                        savegame (default: False)
  -b, --bigendian       change the output format to big-endian, to write
                        PS/xbox save files (default: False)
  -q, --quiet           quiet output (should generate no output unless there
                        are errors) (default: True)
  -f, --force           force output file overwrite, if the destination file
                        exists (default: False)
  --money MONEY         Money to set for character (default: None)
                        Moonstone to set for character (default: None)
  --unlock {challenges}
                        Game features to unlock (default: {})
```
