import gdb
import sys
import os

from elftools.elf.elffile import ELFFile
from pathlib import Path

csfp = os.path.abspath(os.path.dirname(__file__))
if csfp not in sys.path:
    sys.path.insert(0, csfp)

from dbgd_plugin import DbgdPlugin

class DbgdPluginGDB(DbgdPlugin):
    def __init__(self) -> None:
        super().__init__()

    def list_symbols(self, args):
        for objfile in gdb.objfiles():
            if getattr(objfile, 'owner', None) is not None:
                continue

            build_id = get_build_id(objfile)
            path = objfile.filename if hasattr(objfile, 'filename') else None

            has_symbols = symbols_in_objfile(objfile) or any(o.owner == objfile for o in gdb.objfiles())

            print(f"{path} ({build_id}) {has_symbols}")

    def load_symbols(self, args):
        if args.force:
            self._dne.clear()

        for objfile in gdb.objfiles():
            fetch_symbols_for(objfile)

    def autoload_symbols(self, args):
        if args.switch.lower() == 'on':
            self._enable_auto_load()
        elif args.switch.lower() == 'off':
            self._disable_auto_load()
        else:
            print("Unknown switch {}".format(args.switch))

    def _enable_auto_load(self):
        gdb.events.new_objfile.connect(new_objfile)

    def _disable_auto_load(self):
        gdb.events.new_objfile.disconnect(new_objfile)

def get_build_id(objfile):
    return objfile.build_id if hasattr(objfile, 'build_id') else None

def symbols_in_objfile(objfile):
    path = objfile.filename if hasattr(objfile, 'filename') else None
    if path is None or Path(path).exists() is False:
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

    if objfile.filename in plugin._dne:
        return

    build_id = objfile.build_id if hasattr(objfile, 'build_id') else None
    if build_id:
        print(f"[debuginfod] Searching for symbols from {objfile.filename} ({build_id})")
        debug_file = plugin._client.get_debuginfo(build_id)
        if debug_file:
            print(f"[debuginfod] Reading symbols from {debug_file}")
            objfile.add_separate_debug_file(debug_file)
        else:
            print(f"[debuginfod] Failed to find symbols for {objfile.filename}")
            plugin._dne.append(objfile.filename)

def new_objfile(event):
    fetch_symbols_for(event.new_objfile)

gdb.events.new_objfile.connect(new_objfile)

class SymLoadCmd(gdb.Command):
    """Attempts to load symbols for loaded modules by using debuginfod

    Use -f or --force to force re-load
    """

    def __init__(self) -> None:
        super(SymLoadCmd, self).__init__("dbgd", gdb.COMMAND_USER)

    def invoke(self, args, from_tty):
        commands = gdb.string_to_argv(args)
        plugin.run_command(commands)


    def complete(self, text, word):
        # We expect the argument passed to be a symbol so fallback to the
        # internal tab-completion handler for symbols
        return gdb.COMPLETE_SYMBOL

SymLoadCmd()
plugin =  DbgdPluginGDB()