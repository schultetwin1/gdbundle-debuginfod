import lldb
import shlex

from dbgd_plugin import DbgdPlugin

class DbgdPluginLLDB(DbgdPlugin):
    def __init__(self, debugger) -> None:
        super().__init__()
        self._debugger = debugger
        self._hook_idx = None

    def list_symbols(self, args):
        num_targets = self._debugger.GetNumTargets()
        for i in range(num_targets):
            target = self._debugger.GetTargetAtIndex(i)
            for module in target.module_iter():
                build_id = get_build_id(module)
                file_spec = module.GetFileSpec()
                symbol_file_spec = module.GetSymbolFileSpec()

                print(f"{file_spec} ({build_id}) {has_debug_symbols(module)}")

    def load_symbols(self, args):
        if args.force:
            self._dne.clear()

        num_targets = self._debugger.GetNumTargets()
        for i in range(num_targets):
            target = self._debugger.GetTargetAtIndex(i)
            for module in target.module_iter():
                build_id = get_build_id(module)
                if build_id:
                    file_spec = module.GetFileSpec()
                    symbol_file_spec = module.GetSymbolFileSpec()

                    if file_spec != symbol_file_spec:
                        continue

                    if has_debug_symbols(module):
                        continue

                    if str(file_spec) in self._dne:
                        return

                    print(f"[debuginfod] Searching for symbols from {file_spec} ({build_id})")
                    debug_file = self._client.get_debuginfo(build_id)
                    if debug_file:
                        print(f"[debuginfod] Reading symbols from {debug_file}")
                        run_command(self._debugger, f'target symbols add -s {file_spec} {debug_file}')
                    else:
                        print(f"[debuginfod] Failed to find symbols for {file_spec}")
                        self._dne.append(str(file_spec))

    def autoload_symbols(self, args):
        if args.switch.lower() == 'on':
            self._enable_auto_load()
        elif args.switch.lower() == 'off':
            self.disable_auto_load()
        else:
            print("Unknown switch {}".format(args.switch))

    def _enable_auto_load(self):
        output = run_command(self._debugger, "target stop-hook list")
        if 'dbgd' not in output:
            output = run_command(self._debugger, 'target stop-hook add -o \'dbgd symbols load\'')
            self._hook_idx = int(output.split()[2][1:])


    def _disable_auto_load(self):
        if self._hook_idx is not None:
            output = run_command(self._debugger, 'target stop-hook delete {}'.format(self._hook_idx))
            hook_idx = None

def __lldb_init_module(debugger, internal_dict):
    plugin = DbgdPluginLLDB(debugger)
    internal_dict["dbgd_plugin"] = plugin
    run_command(debugger, 'command script add -f debuginfod_lldb.dbgd dbgd')

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

def dbgd(debugger, command, _result, internal_dict):
    plugin = internal_dict["dbgd_plugin"]
    plugin._debugger = debugger;
    commands = shlex.split(command)
    plugin.run_command(commands)


def run_command(debugger, command):
    res = lldb.SBCommandReturnObject()
    ci = debugger.GetCommandInterpreter()
    ci.HandleCommand(str(command), res, False)
    if res.Succeeded():
        output = res.GetOutput()
        return output.strip() if output else ""
    else:
        raise Exception(res.GetError().strip())
