#!/usr/bin/env python3
import logging
import re
import subprocess

from lsprotocol import types

from pygls.cli import start_server
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

server = LanguageServer("riscos-swis", "v1")

#print = lambda msg: server.log_trace(params=types.LogTraceParams(msg))
#print = lambda msg: server.window_log_message(params=types.LogMessageParams(types.MessageType.Info,msg))
#print = lambda msg: logging.info(msg)

swi_match_left_re = re.compile(r'X?[A-Z][A-Za-z0-9_]*$')
swi_match_right_re = re.compile(r'^[A-Za-z0-9_]*')

# _swix(swi, flags, ...)
swix_before_re = re.compile(r'_swix?\s*\(\s*$')
swix_after_re = re.compile(r'\s*, ((?:_INR?\(\s*[\d,]+\s*\)|_OUTR?\(\s*[\d,]+\s*\)|\d+|0x[0-9A-Fa-f]+|[+|]|\s+)+)(,\s*|\))')
swix_inout_re = re.compile(r'_(?:IN|OUT)\(\s*(\d+)\s*\)')
swix_inoutr_re = re.compile(r'_(?:IN|OUT)R\(\s*(\d+)\s*,\s*(\d+)\s*\)')
swix_params_nobrackets_re = re.compile(r'^\s*([^(),]+?)\s*([,)])(.*)')
swix_params_simplebrackets_re = re.compile(r'^\s*\(\s*([^(),]+?)\s*\)\s*([,)])(.*)')

# SYS "swi", regs... TO regs
sys_before_re = re.compile(r'SYS *"?$')
sys_after_re = re.compile(r'^"')
sys_params_nobrackets_re = re.compile(r'^\s*([^(),:;]*?)\s*([,:;]|TO|$)(.*)')
sys_params_simplebrackets_re = re.compile(r'^\s*\(\s*([^(),:;]*?)\s*\)\s*([,:;]|TO|$)(.*)')

# SWI swi
swi_before_re = re.compile(r'(^|\s)SWI(EQ|NE|CS|CC|MI|PL|VS|VC|HI|LS|GE|LT|GT|LE|AL|NV)?\s+$')
swi_asm_re = re.compile(r'^(?:(\$?[A-Za-z0-9_]+):?)?\s+([A-Za-z_]+)(.*)')
swi_comment_re = re.compile(r'^(.*) (;|//) ?(.*)')

class SWICall:
    # Seconds to get the PRM information
    process_timeout = 5

    def __init__(self, name):
        self.name = name
        self.rin_supplied = {}
        self.rin_value = {}
        self.rout_expect = {}

    def decode(self, document: TextDocument, pos: types.Position, line: str, start_pos: int, end_pos: int):
        before = line[:start_pos]
        after = line[end_pos:]

        logging.info("Text before SWI: '%s'" % (before,))
        logging.info("Text after SWI: '%s'" % (after,))
        if swix_before_re.search(before):
            self.decode_swix(document, before, after)
        if sys_before_re.search(before):
            self.decode_sys(document, before, after)
        if swi_before_re.search(before):
            self.decode_swi(document, pos, before, after)

    def decode_swi(self, document: TextDocument, pos: types.Position, before: str, after: str):
        # We can extract the registers that were supplied and those returned
        # but we will ignore any flags.
        logging.info("Is a SWI call (assembler)")
        nlines = 20
        for linenum in range(pos.line - 1, pos.line - nlines, -1):
            line = document.lines[linenum].rstrip()
            logging.info("Line #%i: %s" % (linenum, line))
            match = swi_comment_re.search(line)
            comment = None
            if match:
                line = match.group(1)
                comment = match.group(2)
            match = swi_asm_re.search(line)
            if match:
                label = match.group(1)
                mnemonic = match.group(2)
                rest = match.group(3).strip()
                logging.info("  Mnemonic = %s" % (mnemonic,))

    def decode_sys(self, document: TextDocument, before: str, after: str):
        # We can extract the registers that were supplied and those returned
        # but we will ignore any flags.
        logging.info("Is a SYS call (BASIC)")
        if after and after[0] == '"':
            after = after[1:]
        params = after.lstrip()
        if params and params[0] == ',':
            logging.info("We know the parameters")
            params = params[1:].lstrip()
            rn = 0
            type_input = True
            while params:
                if params.startswith('TO'):
                    type_input = False
                    params = params[2:]
                    rn = 0
                    continue
                if params.startswith(';'):
                    # Ignore the flags return for simplicity
                    break
                match = sys_params_nobrackets_re.match(params)
                if not match:
                    match = sys_params_simplebrackets_re.match(params)
                if match:
                    expr = match.group(1)
                    sep = match.group(2)
                    params = match.group(3)
                    if type_input:
                        if expr:
                            self.rin_supplied[rn] = True
                        else:
                            expr = '0'
                        self.rin_value[rn] = expr
                        logging.info("  In: r%i = %s" % (rn, expr))
                    else:
                        if expr:
                            self.rout_expect[rn] = expr
                            logging.info(" Out: %s = r%i" % (expr, rn))
                    rn += 1
                    if sep == ':' or sep == ';':
                        break
                    if sep == 'TO':
                        type_input = False
                        rn = 0
                        continue
                else:
                    break

    def decode_swix(self, document: TextDocument, before: str, after: str):
        # We can extract the registers that were supplied and those returned
        # but we will ignore any flags or block usage. At present we only handle
        # a single line of statement.
        logging.info("Is a _swix/_swi call")
        match = swix_after_re.search(after)
        if match:
            logging.info("We know the parameters")
            flags = match.group(1)
            logging.info("Flags: %s" % (flags,))
            params_pos = match.end()
            params = after[params_pos:]
            logging.info("Params: %s" % (params,))
            self.rin_supplied = {}
            self.rout_supplied = {}
            for part in re.split('[|+]', flags):
                part = part.strip()

                if part.isdigit() or part.startswith('0x'):
                    # Simple numbers for the flags
                    if part.startswith('0x'):
                        n = int(part, 16)
                    else:
                        n = int(part)
                    rn = 0
                    for rn in range(10):
                        if n & (1<<rn):
                            self.rin_supplied[rn] = True
                        if n & (1<<(31 - rn)):
                            self.rout_supplied[rn] = True
                    continue

                match = swix_inout_re.search(part)
                if match:
                    # _IN/_OUT specifications
                    rn = int(match.group(1))
                    if part.startswith('_IN'):
                        self.rin_supplied[rn] = True
                    else:
                        self.rout_supplied[rn] = True
                    continue

                match = swix_inoutr_re.search(part)
                if match:
                    # _INR/_OUTR specifications
                    rnlo = int(match.group(1))
                    rnhi = int(match.group(2))
                    for rn in range(rnlo, rnhi + 1):
                        if part.startswith('_IN'):
                            self.rin_supplied[rn] = True
                        else:
                            self.rout_supplied[rn] = True
                    continue

                logging.info("Not recognised: '%s'" % (part,))

            logging.info("InRegs: %s" % (sorted(self.rin_supplied.keys()),))
            logging.info("OutRegs: %s" % (sorted(self.rout_supplied.keys()),))

            # Now work out what the parameters are...
            args = []
            while params:
                match = swix_params_nobrackets_re.match(params)
                if not match:
                    match = swix_params_simplebrackets_re.match(params)
                if match:
                    expr = match.group(1)
                    sep = match.group(2)
                    params = match.group(3)
                    args.append(expr)
                    if sep == ')':
                        break
                else:
                    break
            logging.info("Args: %s" % (args,))
            for r in sorted(self.rin_supplied.keys()):
                if args:
                    value = args.pop(0)
                    self.rin_value[r] = value
                    logging.info("  In: r%i = %s" % (r, value))
                else:
                    break
            for r in sorted(self.rout_supplied.keys()):
                if args:
                    value = args.pop(0)
                    if value[0] == '&':
                        value = value[1:]
                    else:
                        value = '*' + value
                    self.rout_expect[r] = value
                    logging.info("  Out: %s = r%i" % (value, r))
                else:
                    break

    def markdown(self):
        """
        Return the markdown text to use for this SWI call.

        Here we invoke `riscos-prm` to get its summary.

        @return:    None if no content could be read
                    markdown text for the SWI
        """
        proc = subprocess.run(["riscos-prm", "--summary", "--no-tables", self.name],
                              timeout=self.process_timeout,
                              capture_output=True,
                              encoding='utf-8')
        if proc.returncode != 0:
            return None
        return proc.stdout


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(ls: LanguageServer, params: types.HoverParams):
    pos = params.position
    document_uri = params.text_document.uri
    document = ls.workspace.get_text_document(document_uri)

    try:
        line = document.lines[pos.line].rstrip()
        logging.info("Line: %s" %(line,))
    except IndexError:
        logging.info("No line")
        return None

    # We want to try to find the position within the line.
    logging.info("pos=%r" % (pos,))
    try:
        word = document.word_at_position(pos, swi_match_left_re, swi_match_right_re)
        logging.info("word=%r" % (word,))
    except IndexError:
        logging.info("No word")
        return None

    if '_' not in word:
        logging.info("Not a SWI call (no _ in word)")
        return None

    try:
        start_pos = line.index(word)
        end_pos = start_pos + len(word)
    except IndexError:
        logging.info("Cannot get range of word")
        return None

    if word.startswith('X'):
        word = word[1:]
    parts = word.split('_')
    if len(parts) > 2:
        logging.info("Not a SWI call (multiple _ in word)")
        return None

    swi_name = word

    swicall = SWICall(swi_name)
    swicall.decode(document, pos, line, start_pos, end_pos)

    markdown = swicall.markdown()
    if markdown is None:
        return None

    return types.Hover(
        contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value=markdown,
        ),
        range=types.Range(
            start=types.Position(line=pos.line, character=start_pos),
            end=types.Position(line=pos.line, character=end_pos),
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    start_server(server)
