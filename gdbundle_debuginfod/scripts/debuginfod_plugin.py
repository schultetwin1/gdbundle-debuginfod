import gdb

from elftools.elf.elffile import ELFFile
import os
import sys
from pathlib import Path

import pydebuginfod

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

    build_id = objfile.build_id if hasattr(objfile, 'build_id') else None
    if build_id:
        print(f"[debuginfod] Searching for symbols from {objfile.filename} ({build_id})")
        debug_file = pydebuginfod.get_debuginfo(build_id)
        if debug_file:
            print(f"[debuginfod] Reading symbols from {debug_file}")
            objfile.add_separate_debug_file(debug_file)
        else:
            print(f"[debuginfod] Failed to find symbols for {objfile.filename}")

def new_objfile(event):
    fetch_symbols_for(event.new_objfile)

gdb.events.new_objfile.connect(new_objfile)