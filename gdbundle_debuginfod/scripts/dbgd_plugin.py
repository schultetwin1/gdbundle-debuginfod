import argparse
import pydebuginfod

class DbgdPlugin:
    """ Abstracts GDB and LLDB functionality"""

    def __init__(self) -> None:
        self._client = pydebuginfod.Client()
        self._dne = []
        pass

    def run_command(self, args):
        parser = argparse.ArgumentParser()

        main_subparsers = parser.add_subparsers()

        parser_symbols = main_subparsers.add_parser('symbols', help="Commands to interact with symbols")

        symbols_subparsers = parser_symbols.add_subparsers()

        parser_symbols_load = symbols_subparsers.add_parser('load', help="Load Symbols")
        parser_symbols_load.add_argument("-f", "--force", help="Force re-load symbols", action="store_true")
        parser_symbols_load.set_defaults(func=self.load_symbols)
        parser_symbols_autoload = symbols_subparsers.add_parser('autoload', help="Turn symbol load on / off")
        parser_symbols_autoload.add_argument("switch", choices=["on", "off"])
        parser_symbols_autoload.set_defaults(func=self.autoload_symbols)
        parser_symbols_list = symbols_subparsers.add_parser('list', help="List loaded symbols")
        parser_symbols_list.set_defaults(func=self.list_symbols)

        parser_servers = main_subparsers.add_parser('servers', help="Add/Remove/View debuginfod servers")

        parser_servers_subparsers = parser_servers.add_subparsers()

        parser_servers_list = parser_servers_subparsers.add_parser('list', help="List urls")
        parser_servers_list.set_defaults(func=self.list_servers)
        parser_servers_add = parser_servers_subparsers.add_parser('add', help="Add a server")
        parser_servers_add.add_argument("url", help="URL of debuginfod server")
        parser_servers_add.set_defaults(func=self.add_server)
        parser_servers_rm = parser_servers_subparsers.add_parser('rm', help="Remove a server")
        parser_servers_rm.add_argument("index", help="Index of server")
        parser_servers_rm.set_defaults(func=self.rm_server)
        parser_servers_clear = parser_servers_subparsers.add_parser('clear', help="Remove all servers")
        parser_servers_clear.set_defaults(func=self.clear_servers)

        parsed_args = parser.parse_args(args)

        if hasattr(parsed_args, 'func'):
            parsed_args.func(parsed_args)
        else:
            print("ERROR: Unknown command")
            parser.print_help()

    #
    # Servers
    # 
    def list_servers(self, _args):
        for num, url in enumerate(self._client.urls):
            print(f"{num}: {url}")

    def add_server(self, args):
        self._client.urls.append(args.url)
        self._dne.clear()

    def rm_server(self, args):
        idx = int(args.index)
        if idx < len(self._client.urls):
            del self._client.urls[idx]

    def clear_servers(self, args):
        self._client.urls.clear()

    #
    # Symbols
    #
    def load_symbols(self, args):
        pass

    def autoload_symbols(self, args):
        pass

    def list_symbols(self, args):
        pass
