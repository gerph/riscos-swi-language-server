# Configuration for Sublime Text

To configure the language server for use with SublimeText, add a 
configuration in your `LSP.sublime-settings` file:

```
{
    "clients":
        {
            "riscos-swis": {
                "command": [
                    "...path-to.../riscos-swi-ls.py",
                    "--tcp",
                    "--port", "9988"
                ],
                "selector": "source.c|source.bbcbasic|source.asm.arm",
                "tcp_port": 9988,
            },
        }
}
```

