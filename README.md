# RISC OS SWI Language Server

## Summary

This repository provides the implementation of a Language Server which understands RISC OS SWI interfaces. It can provide information on these SWI calls when you over over them.

Language Servers are a way that IDEs can communicate with processes to understand more about the code that is being edited. It allows the code to have operations applied to it, or to look up information or provide code completion as you write things. It can do a lot more as well, but those at the things that are most commonly known. The principle is good - that you have a LSP server which understands the language and you have your editor that can talk to it. Whatever the editor, they can benefit from the LSP’s functionality, and similarly a newly implemented LSP can give its functions to all the editors which support the protocol. No hardcoded stuff. It’s really quite clever.

There are LSPs for many languages and file formats. There’s a good chance that you’re probably using some now without even knowing it. https://github.com/Hexlet/awesome-lsp-servers has some more.

## Pre-requisites

The RISC OS SWI language server relies on information provided
by the `riscos-prm` tool. This tool must be installed on your
path.

## Installation

Installing a language server is different for each editor.

### SublimeText

To configure the language server for use with SublimeText...

* Install the `LSP` package from Package Control.
* Add a configuration in your `LSP.sublime-settings` file:

```
{
    "clients":
        {
            "riscos-swis": {
                "command": [
                    "riscos-swi-lsp",
                    "--tcp",
                    "--port", "9988"
                ],
                "selector": "source.c|source.bbcbasic|source.asm.arm",
                "tcp_port": 9988,
            },
        }
}
```

Update the `command` section to point to the source from
this repository. You will need to have the `pygls` package
installed.


## Recognised invocations

When you float over a token that looks like a SWI name,
this will be used to look up the relevant call in the PRMs.
Certain SWI calls will have different reason codes, which
determine the operation being performed. Where these are known
the language server will attempt to determine which reason
code is being called.

### C: _swix

The `_swix` form of SWI calls is recognised when you hover over
it. The server will attempt to look up the
interfaces using the flags (`_IN` and `_INR`) supplied, together
with the parameters.

If you use `_swix(<swi>,` and trigger a completion (ctrl-space
in some editors) a completion will be offered for the SWI
interface.

### BASIC: SYS

The `SYS` form of SWI calls is recognised when you hover over
it. The server will attempt to look up the interfaces using the
following parameters after the SWI name.

If you use `SYS "<swi>"` and trigger a completion (ctrl-space
in some editors) a completion will be offered for the SWI
interface.


### Assembler: SWI

The `SWI` form of SWI call will only look up the SWI name
and does not currently infer any reason codes when you hover
over it.
