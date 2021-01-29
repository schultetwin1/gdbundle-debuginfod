import gdb

import argparse
from elftools.elf.elffile import ELFFile
from pathlib import Path

import pydebuginfod

dne_on_server = set()

def symbols_in_objfile(objfile):
    path = objfile.filename if hasattr(objfile, 'filename') else None
    if not Path(path).exists():
        return False

    with open(path, 'rb') as f:
        elf = ELFFile(f)
        return bool(elf.get_section_by_name('.debug_info') or
                    elf.get_section_by_name('.zdebug_info'))

def fetch_symbols_for(objfile):
    if symbols_in_objfile(objfile):
        # The symbols for this binary are in the ELF
        return
    if getattr(objfile, 'owner', None) is not None or any(o.owner == objfile for o in gdb.objfiles()):
        # This is either a separate debug file or this file already
        # has symbols in a separate debug file.
        return

    if objfile.filename in dne_on_server:
        return

    build_id = objfile.build_id if hasattr(objfile, 'build_id') else None
    if build_id:
        print(f"[debuginfod] Searching for symbols from {objfile.filename} ({build_id})")
        debug_file = pydebuginfod.get_debuginfo(build_id)
        if debug_file:
            print(f"[debuginfod] Reading symbols from {debug_file}")
            objfile.add_separate_debug_file(debug_file)
        else:
            print(f"[debuginfod] Failed to find symbols for {objfile.filename}")
            dne_on_server.add(objfile.filename)

def new_objfile(event):
    fetch_symbols_for(event.new_objfile)

gdb.events.new_objfile.connect(new_objfile)

class SymLoadCmd(gdb.Command):
    """Attempts to load symbols for loaded modules by using debuginfod

    Use -f or --force to force re-load
    """

    def __init__(self) -> None:
        super(SymLoadCmd, self).__init__("symload", gdb.COMMAND_USER)

    def invoke(self, args, from_tty):
        parser = argparse.ArgumentParser()
        parser.add_argument("-f", "--force", help="Attempt to reload failed downloads", action="store_true")

        parsed_args = parser.parse_args(gdb.string_to_argv(args))
        if parsed_args.force:
            dne_on_server.clear()

        for objfile in gdb.objfiles():
            fetch_symbols_for(objfile)

    def complete(self, text, word):
        # We expect the argument passed to be a symbol so fallback to the
        # internal tab-completion handler for symbols
        return gdb.COMPLETE_SYMBOL

SymLoadCmd()