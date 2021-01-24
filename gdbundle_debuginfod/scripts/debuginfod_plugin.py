import gdb

import os
import sys
from urllib.request import urlretrieve
from urllib.parse import urljoin, quote
from urllib.error import HTTPError

from progressist import ProgressBar

DEFAULT_SYMBOL_SERVER_URL="https://debuginfod.elfutils.org/"

# Default cache of symbol files is:
# ~/.cache/debuginfod/.build-id
cache_dir = os.path.join(os.environ['HOME'], '.cache', 'debuginfod')

def try_fetch_symbols(objfile, build_id, cache_dir):
    print('[debuginfod] Searching for symbols for {0}'.format(objfile.filename))

    # Check cache
    cache_key = os.path.join("buildid", build_id, "debuginfo")
    cached_file = os.path.join(cache_dir, cache_key)
    if os.path.exists(cached_file):
        return cached_file

    # File not cached, attempt to download for server
    try:
        d = os.path.dirname(cached_file)
        if not os.path.isdir(d):
            os.makedirs(d)
    except OSError:
        pass

    servers = os.getenv('DEBUGINFOD_URLS')
    if servers is None:
        servers = [DEFAULT_SYMBOL_SERVER_URL]

    url_key = f"buildid/{build_id}/debuginfo"

    for server in servers:
        url = urljoin(server, quote(url_key))
        bar = ProgressBar(template="Downloading... |{animation}| {done:B}/{total:B}")
        try:
            urlretrieve(url, cached_file, reporthook=bar.on_urlretrieve)
            return cached_file
        except HTTPError as exception:
            if exception.code == 404:
                continue
            else:
                print('[debuginfod] ' + exception)
        except:
            print("[debuginfod] Unexpected error:", sys.exc_info()[0])
            raise
    return None

def fetch_symbols_for(objfile):
    if getattr(objfile, 'owner', None) is not None or any(o.owner == objfile for o in gdb.objfiles()):
        # This is either a separate debug file or this file already
        # has symbols in a separate debug file.
        return

    build_id = objfile.build_id if hasattr(objfile, 'build_id') else None
    if build_id:
        debug_file = try_fetch_symbols(objfile, build_id, cache_dir)
        if debug_file:
            print(f"[debuginfod] Reading symbols from {debug_file}")
            objfile.add_separate_debug_file(debug_file)
        else:
            print(f"[debuginfod] Failed to find symbols for {objfile.filename}")

def new_objfile(event):
    fetch_symbols_for(event.new_objfile)

# Create our cache dir.
try:
    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)
except OSError:
    pass

gdb.events.new_objfile.connect(new_objfile)