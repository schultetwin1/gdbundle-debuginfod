import lldb

import os
import sys

sys.path.append(os.path.expanduser(os.path.dirname(__file__)))
from debuginfod import try_fetch_symbols

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f debuginfod_lldb.load_symbols symbols')

def has_debug_symbols(module):
    for section in module.section_iter():
        name = section.GetName()
        if name == ".debug_info" or name == ".zdebug_info":
            return True
        for subsection in section:
            name = section.GetName()
            if name == ".debug_info" or name == ".zdebug_info":
                return True
    return False

def get_build_id(module):
    for section in module.section_iter():
        if section.GetName() == ".note.gnu.build-id":
            return module.GetUUIDString().replace("-", "").lower()
        for subsection in section:
            if subsection.GetName() == ".note.gnu.build-id":
                return module.GetUUIDString().replace("-", "").lower()
    return None

def load_symbols(debugger, command, result, internal_dict):
    num_targets = debugger.GetNumTargets()
    for i in range(num_targets):
        target = debugger.GetTargetAtIndex(i)
        for module in target.module_iter():
            build_id = get_build_id(module)
            if build_id:
                file_spec = module.GetFileSpec()
                symbol_file_spec = module.GetSymbolFileSpec()

                if file_spec != symbol_file_spec:
                    continue

                if has_debug_symbols(module):
                    continue

                debug_file = try_fetch_symbols(file_spec, build_id)
                if debug_file:
                    print(f"[debuginfod] Reading symbols from {debug_file}")
                    debugger.HandleCommand(f'target symbols add {debug_file}')
                else:
                    print(f"[debuginfod] Failed to find symbols for {file_spec}")
