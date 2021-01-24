# Debuginfod Plugins

This repo contains both a GDB and LLDB plugin to support
[debuginfod](https://www.mankier.com/8/debuginfod#) in the versions of GDB and
LLDB which not do have debuginfod built in.

## Supported Environments

| Debuggger | Versions              |
|-----------|-----------------------|
| gdb*      | <10.1                 |
| lldb*     | Support in the works  |

\* Debuggers must have python API enabled

## Getting Started

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