# bl2wealth

* [Running the program](#running-the-program)
* [Input and Output](#input-and-output)
    * [Other Output Formats](#other-output-formats)
* [Modifying Savegames (JSON Method)](#modifying-savegames-json-method)
* [Modifying Savegames (Using Commandline Arguments)](#modifying-savegames-using-commandline-arguments)
    * [Money](#money)
* [Combining Commandline Options](#combining-commandline-options)
* [Exporting character items](#exporting-character-items)
* [Other commandline options](#other-commandline-options)
    * [Force Overwrites](#force-overwrites)
    * [Help](#help)

# Running the program

`bl2save.py`

The basic form of the utility is to specify and input and output file. If no
other options are given, the utility effectively just copies the savegame
without making any changes, like so:

    python bl2save.py save0001.sav save0002.sav

# Input and Output

By default, the utility saves in a format usable by Borderlands, but you can
specify alternate outputs to use, using the `-o` or `--output` option. The
most useful outputs are:

* **`savegame`** - This is the default, and the only output usable by Borderlands itself.
* **`json`** - This is the most human-editable format, saved in a text-based
  hierarchy in JSON format, which should be fairly reasonable to work with.

For example, saving to a JSON file for later hand-editing:

    python bl2save.py -o json save0001.sav testing.json

After hand-editing a JSON file, you can convert it back by specifying the `-j`
or `--json` option, to tell the utility that you're loading from a JSON file,
like so:

    python bl2save.py -j testing.json save0002.sav
    python bl2save.py --json testing.json save0002.sav

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

1. `python bl2save.py -o json save0001.sav to_edit.json`
2. Edit `to_edit.json` in a text editor, to suit
3. `python bl2save.py -j to_edit.json save0001.sav`

# Modifying Savegames (Using Commandline Arguments)

Alternatively, you can alter many attributes of your character by just using
commandline options. You can specify as few or as many of these as you want.
Note that if you specify `-o items` to save a character's items to a text
file, the majority of these options will have no effect.

## Money

Get rich

    python bl2save.py old.sav new.sav

# Combining Commandline Options

In general, the various options can be combined. To make a few changes to a
savegame but save as parsed JSON:

    python bl2save.py --name "X" --output json save0001.sav x.json

# Exporting character items

All items stored and held in the character's bank or inventory can be exported
to a text file as a list of codes, in a format compatible with Gibbed save
editor. This is accomplished with `-o items` or `--output items` like so:

    python bl2save.py -o items savegame.sav items.txt

# Other commandline options

There are a few other commandline options available when running the utilities.

## Force Overwrites

By default, the utility will refuse to overwrite a file without getting
confirmation from the user first. To disable that yes/no prompt and force
the app to overwrite the file automatically, use `-f` or `--force` like so:

    python bl2save.py -f old.sav new.sav
    python bl2save.py --force old.sav new.sav

## Help

The utility will also show you what all of its commandline options are
at the commandline, using the `-h` or `--help` options:

    python bl2save.py -h
    python bl2save.py --help


```
usage: bl2save.py [-h] [-o {savegame,decoded,decodedjson,json}]
                          input_filename output_filename

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
  -f, --force           force output file overwrite, if the destination file
                        exists (default: False)
```
