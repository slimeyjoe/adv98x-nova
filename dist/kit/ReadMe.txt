NOVA for Adv98X @VERSION@: the pack-building kit
================================================

This kit turns your own copy of NOVA ～魅入られた肢体～ (Cat's Pro, PC-9801, 1993) into the pack
nova.pak, which the Adv98X engine plays: in Japanese, or in English with Fuzion's translation. It
holds only tools and the list of the game's files; none of the game.

Adults only: the game contains explicit sexual content.


What you need
-------------

* Python 3.8 or newer (the standard library is enough), on any system.
* Your copy of the PC-98 release: the four floppy disk images (D88, ...), a hard-disk image or
  the installed files; for English, also Fuzion's translation (its hard-disk image).
  docs/game-data.md lists what is accepted.
* The Adv98X program for your system (its release archive).


Building the pack
-----------------

    python3 makepak.py path/to/pc-98 "path/to/Nova [TL-En by Fuzion].hdi"

The files are found by name and checked against the game's inventory (resources/inventory.tsv),
in any mix of directories, archives and disk images; they are copied into resources/original/
here, and the pack is written to build/nova.pak. Run it again without arguments to rebuild the
pack from what was imported.

Put nova.pak next to the adv98x program, or name it with --pak; --lang en plays the English
text. The program's ReadMe has the keys and options.


Licence
-------

The tools are free software under the GNU General Public License, version 3 or later (LICENSE).
The bitmap fonts in engine/source/lrvne/fonts/x11 keep their own licences (the COPYING files
there). NOVA is © 1993 Cat's Pro; this kit is not affiliated with or endorsed by its publisher or
the authors of its engine.
