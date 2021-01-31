# Debuginfod Plugins

![PyPI](https://img.shields.io/pypi/v/gdbundle-debuginfod)
![Build](https://github.com/schultetwin1/gdbundle-debuginfod/workflows/CI/badge.svg)


This repo contains both a GDB and LLDB plugin to support
[debuginfod](https://www.mankier.com/8/debuginfod#) in the versions of GDB and
LLDB which not do have debuginfod built in.

WARNING: Currently these plugins only support downloading symbols/ These
plugin **do not** support sources.

## Supported Environments

This works in both LLDB and GDB. As of GDB 10.1, debuginfod support is built
into GDB and so this plugin is not needed.


## Installation

These plugins can be installed in two different ways:

* Using [gdbundle](https://github.com/memfault/gdbundle). A GDB/LLDB plugin
  manager from [MemFault](https://interrupt.memfault.com/blog/gdbundle-plugin-manager). (Preferred method)

* Manual

### Using gdbundle

First follow gdbundle's install [steps](https://github.com/memfault/gdbundle#quickstart).

Then install the debuginfod plugins with the following command:

```shell
pip install gdbundle-debuginfod-plugin
```
### Manual Install

Instructions to come...

## Usage

Once installed, you will have access to the `dbgd` command in both GDB and
LLDB. Run `dbgd --help` to see the full list of commands. Normal usage will
be covered here.

By default, symbols will load automatically. :warning: This feature is not
yet implemented on LLDB! :warning:

### Load symbols manually

```
debugger> dbgd symbols load
```

### Turn on / off auto loading of symbols

```
debugger> dbgd symbols autoload on
debugger> dbgd symbols autoload off
```

### List loaded symbols

```
debugger> dbgd symbols list
```

### List all debuginfod servers

```
debugger> dbgd servers list
```

### Add a debuginfod server

```
debugger> dbgd servers add [url]
```

### Remove a debuginfod server

```
debugger> dbgd servers rm [index]
```