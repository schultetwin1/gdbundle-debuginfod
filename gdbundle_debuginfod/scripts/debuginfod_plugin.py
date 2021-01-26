import gdb

from elftools.elf.elffile import ELFFile
import os
from pathlib import Path
import requests
import shutil
import sys
import tempfile
import time
from urllib.request import urlretrieve
from urllib.parse import urljoin, quote
from urllib.error import HTTPError


DEFAULT_SYMBOL_SERVER_URL="https://debuginfod.elfutils.org/"

# Default cache of symbol files is:
# ~/.cache/debuginfod/.build-id
cache_dir = os.path.join(os.environ['HOME'], '.cache', 'debuginfod')
env_cache_dir = os.getenv("DEBUGINFOD_CACHE_PATH")
if env_cache_dir is not None:
    cache_dir = env_cache_dir
env_timeout_secs = os.getenv("DEBUGINFOD_TIMEOUT")
timeout_secs = 90 if env_timeout_secs is None else int(env_timeout_secs)
verbose = os.getenv("DEBUGINFOD_VERBOSE") is not None

def symbols_in_objfile(objfile):
    path = objfile.filename if hasattr(objfile, 'filename') else None
    if not Path(path).exists():
        return False

    with open(path, 'rb') as f:
        elf = ELFFile(f)
        return bool(elf.get_section_by_name('.debug_info') or
                    elf.get_section_by_name('.zdebug_info'))

    return False

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def download_file(url, destination):
    if verbose:
        print("[debuginfod] Downloading {0} to {1}".format(url, destination))
    # Download to a temporary file first
    temp = tempfile.NamedTemporaryFile()

    response = requests.get(url, stream=True, timeout=timeout_secs)
    if response.status_code != 200:
        if response.status_code == 404:
            return None
        else:
            raise RuntimeError(f"Request to {url} returned status code {response.status_code}")

    bytes_downloaded = 0
    start_time = time.time()

    for data in response.iter_content(chunk_size=None):
        temp.write(data)
        current_time = time.time()
        bytes_downloaded += len(data)
        sys.stdout.write('\r[debuginfod] Downloading... {} bytes'.format(sizeof_fmt(bytes_downloaded)))
        sys.stdout.flush()
    sys.stdout.write("\n")
    temp.flush()

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy(temp.name, str(destination))

    return str(destination)

    

def try_fetch_symbols(objfile, build_id, cache_dir):
    print('[debuginfod] Searching for symbols for {0}'.format(objfile.filename))

    # Check cache
    cache_key = os.path.join("buildid", build_id, "debuginfo")
    cached_file = os.path.join(cache_dir, cache_key)
    if os.path.exists(cached_file):
        return cached_file

    # File not cached, attempt to download for server
    servers = os.getenv('DEBUGINFOD_URLS')
    if servers is None:
        servers = [DEFAULT_SYMBOL_SERVER_URL]

    url_key = f"buildid/{build_id}/debuginfo"

    for server in servers:
        url = urljoin(server, quote(url_key))
        dest_file = download_file(url, cached_file)
        if dest_file is not None:
            return dest_file
    return None

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