import lldb

import argparse
import pydebuginfod
import shlex

dne_on_server = set()
client = pydebuginfod.Client()
hook_idx = None

def __lldb_init_module(debugger, internal_dict):
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

def dbgd(debugger, command, result, internal_dict):
    parser = argparse.ArgumentParser()

    main_subparsers = parser.add_subparsers()

    parser_symbols = main_subparsers.add_parser('symbols', help="Commands to interact with symbols")

    symbols_subparsers = parser_symbols.add_subparsers()

    parser_symbols_load = symbols_subparsers.add_parser('load', help="Load Symbols")
    parser_symbols_load.add_argument("-f", "--force", help="Force re-load symbols", action="store_true")
    parser_symbols_load.set_defaults(func=load_symbols)
    parser_symbols_autoload = symbols_subparsers.add_parser('autoload', help="Turn symbol load on / off")
    parser_symbols_autoload.add_argument("switch", choices=["on", "off"])
    parser_symbols_autoload.set_defaults(func=autoload_symbols)
    parser_symbols_list = symbols_subparsers.add_parser('list', help="List loaded symbols")
    parser_symbols_list.set_defaults(func=list_symbols)

    parser_servers = main_subparsers.add_parser('servers', help="Add/Remove/View debuginfod servers")

    parser_servers_subparsers = parser_servers.add_subparsers()

    parser_servers_list = parser_servers_subparsers.add_parser('list', help="List urls")
    parser_servers_list.set_defaults(func=list_servers)
    parser_servers_add = parser_servers_subparsers.add_parser('add', help="Add a server")
    parser_servers_add.add_argument("url", help="URL of debuginfod server")
    parser_servers_add.set_defaults(func=add_server)
    parser_servers_rm = parser_servers_subparsers.add_parser('rm', help="Remove a server")
    parser_servers_rm.add_argument("index", help="Index of server")
    parser_servers_rm.set_defaults(func=rm_server)
    parser_servers_clear = parser_servers_subparsers.add_parser('clear', help="Remove all servers")
    parser_servers_clear.set_defaults(func=clear_servers)

    parsed_args = parser.parse_args(shlex.split(command))

    if hasattr(parsed_args, 'func'):
        parsed_args.func(debugger, result, parsed_args)
    else:
        print("ERROR: Unknown command")
        parser.print_help()
    

def list_servers(debugger, result, args):
    for num, url in enumerate(client.urls):
        print(f"{num}: {url}")

def add_server(debugger, result, args):
    client.urls.append(args.url)
    dne_on_server.clear()

def rm_server(debugger, result, args):
    if int(args.index) < len(client.urls):
        del client.urls[int(args.index)]

def clear_servers(debugger, result, args):
    client.urls.clear()

def list_symbols(debugger, result, args):
    num_targets = debugger.GetNumTargets()
    for i in range(num_targets):
        target = debugger.GetTargetAtIndex(i)
        for module in target.module_iter():
            build_id = get_build_id(module)
            file_spec = module.GetFileSpec()
            symbol_file_spec = module.GetSymbolFileSpec()

            print(f"{file_spec} ({build_id}) {has_debug_symbols(module)}")


def run_command(debugger, command):
    res = lldb.SBCommandReturnObject()
    ci = debugger.GetCommandInterpreter()
    ci.HandleCommand(str(command), res, False)
    if res.Succeeded():
        output = res.GetOutput()
        return output.strip() if output else ""
    else:
        raise Exception(res.GetError().strip())


def enable_auto_load(debugger):
    global hook_idx
    output = run_command(debugger, "target stop-hook list")
    if 'dbgd' not in output:
        output = run_command(debugger, 'target stop-hook add -o \'dbgd symbols load\'')
        hook_idx = int(output.split()[2][1:])


def disable_auto_load(debugger):
    global hook_idx
    if hook_idx is not None:
        output = run_command(debugger, 'target stop-hook delete {}'.format(hook_idx))
        hook_idx = None

def autoload_symbols(debugger, result, args):
    if args.switch.lower() == 'on':
        enable_auto_load(debugger)
    elif args.switch.lower() == 'off':
        disable_auto_load(debugger)
    else:
        print("Unknown switch {}".format(args.switch))


def load_symbols(debugger, result, args):
    if args.force:
        dne_on_server.clear()

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

                if str(file_spec) in dne_on_server:
                    return

                print(f"[debuginfod] Searching for symbols from {file_spec} ({build_id})")
                debug_file = client.get_debuginfo(build_id)
                if debug_file:
                    print(f"[debuginfod] Reading symbols from {debug_file}")
                    run_command(debugger, f'target symbols add -s {file_spec} {debug_file}')
                else:
                    print(f"[debuginfod] Failed to find symbols for {file_spec}")
                    dne_on_server.add(str(file_spec))
