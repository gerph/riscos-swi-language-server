"""
Parse the general 'swi_conditions_data' into something we can use.

The general conditions data is intended for use decoding the SWI call
parameters in a debugger. It has a little more information than we want.
Plus it's keyed by the SWI number. We need keying by the SWI name.
"""

import swi_conditions_data


def meaning_to_cname(meaning, entry):
    """
    Convert the meaning of a variable to a C variable name.
    """
    cname = []
    suffix = []
    if meaning.startswith('pointer to string '):
        cname.append('str_')
        meaning = meaning[18:]
    elif meaning.startswith('pointer to code '):
        suffix.append('_func')
        meaning = meaning[16:]
    elif meaning.startswith('pointer to '):
        if entry:
            suffix.append('p')
        meaning = meaning[11:]
    elif meaning.startswith('constant '):
        meaning = meaning[9:]
        # FIXME: Handle '<number> OR variable'
    cname.append(meaning)
    cn = ''.join(cname + suffix)
    if cn.startswith('str_str'):
        cn = cn[4:]
    return cn


def meaning_to_bname(meaning, entry):
    """
    Convert the meaning of a variable to a BASIC variable name.
    """
    cname = []
    suffix = []
    if meaning.startswith('pointer to string '):
        suffix.append('$')
        meaning = meaning[18:]
    elif meaning.startswith('pointer to code '):
        suffix.append('_func%')
        meaning = meaning[16:]
    elif meaning.startswith('pointer to '):
        if entry:
            suffix.append('p%')
        meaning = meaning[11:]
    elif meaning.startswith('constant '):
        meaning = meaning[9:]
        # FIXME: Handle '<number> OR variable'
    cname.append(meaning)
    cn = ''.join(cname + suffix)
    if cn.startswith('str_str'):
        cn = cn[4:]
    return cn


def prepare_swix():
    swix_data = {}
    for swinum, conditions in swi_conditions_data.swi_conditions.items():
        for condition in conditions:
            if 'match' in condition:
                # This is a reason code, so skip it.
                continue

            # Input registers
            inr = []
            inregs = {}
            last_reg = -2
            for reg, meaning in sorted(condition['entry'].items()):
                cname = meaning_to_cname(meaning, entry=True)
                bname = meaning_to_bname(meaning, entry=True)
                inregs[reg] = {
                    'reg': reg,
                    'dir': 'in',
                    'desc': meaning,
                    'cvar': cname,
                    'bvar': bname,
                }
                if reg == last_reg + 1:
                    inr[-1][1] = reg
                else:
                    inr.append([reg, reg])
                last_reg = reg

            # Output registers
            outr = []
            outregs = {}
            last_reg = -2
            for reg, meaning in sorted(condition['exit'].items()):
                if meaning == 'corrupted':
                    continue # Nothing to do!
                cname = meaning_to_cname(meaning, entry=False)
                bname = meaning_to_bname(meaning, entry=False)
                outregs[reg] = {
                    'reg': reg,
                    'dir': 'out',
                    'desc': meaning,
                    'cvar': '&' + cname,
                    'bvar': bname,
                }
                if reg == last_reg + 1:
                    outr[-1][1] = reg
                else:
                    outr.append([reg, reg])
                last_reg = reg

            # Contruct the flags
            flags = []
            for part in inr:
                if part[0] == part[1]:
                    flags.append("_IN(%i)" % (part[0],))
                else:
                    flags.append("_INR(%i,%i)" % (part[0], part[1]))
            for part in outr:
                if part[0] == part[1]:
                    flags.append("_OUT(%i)" % (part[0],))
                else:
                    flags.append("_OUTR(%i,%i)" % (part[0], part[1]))
            if not flags:
                flags.append('0')

            # Construct the input registers
            inparams = []
            outparams = []
            for reg, params in sorted(inregs.items()):
                inparams.append(params)
            for reg, params in sorted(outregs.items()):
                outparams.append(params)

            swi = condition['label']
            swix_data[swi] = {
                    'swi': swi,
                    'desc': condition.get('description'),
                    'flags': flags,
                    'ins': inparams,
                    'outs': outparams,
                    'inrange': describe_range([r['reg'] for r in inparams]),
                    'outrange': describe_range([r['reg'] for r in outparams]),
                }

    return swix_data


def describe_range(regs):
    lastreg = -2
    regnums = []
    for rn in regs:
        if rn == lastreg + 1:
            regnums[-1][1] = rn
        else:
            regnums.append([rn, rn])
        lastreg = rn
    regrange = ["R%i" % (rn[0],) if rn[0] == rn[1] else "R%i-R%i" % (rn[0], rn[1]) for rn in regnums]
    return ', '.join(regrange)


def lookup(swi):
    if swi.startswith('X'):
        swi = swi[1:]
    return swix_data.get(swi)


swix_data = prepare_swix()
