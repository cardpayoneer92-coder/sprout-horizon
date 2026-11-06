#!/usr/bin/env python3
"""Catch the schema mistakes Shopify's GitHub sync rejects silently.

Run before every push:  python3 tools/sp_validate.py

Each rule here cost real debugging time on the Sera theme — a rejected file
never appears in the theme and Shopify shows no error on the storefront.
"""
import glob
import json
import re
import sys

# Shopify units are short plain tokens ("px", "%", "sec"). "/1000em" was rejected.
UNIT_OK = re.compile(r'[A-Za-z%]{0,4}')
RESERVED_IDS = {'per_page'}

problems = []


def check(path, schema, is_section):
    # A section rendered with "tag": null is rejected silently. Horizon's own
    # sections either name a real tag or leave the key out; only blocks use null.
    if is_section and 'tag' in schema and schema['tag'] is None:
        problems.append(f'{path}: section has "tag": null — name a real tag or drop the key')

    def settings_of(obj):
        out = list(obj.get('settings') or [])
        for b in obj.get('blocks', []) or []:
            if isinstance(b, dict):
                out += list(b.get('settings') or [])
        return out

    for st in settings_of(schema):
        if not isinstance(st, dict):
            continue
        sid = st.get('id')

        if sid in RESERVED_IDS:
            problems.append(f'{path}: setting id "{sid}" is reserved — rename it')

        unit = st.get('unit')
        if unit is not None and not UNIT_OK.fullmatch(str(unit)):
            problems.append(f'{path}: {sid} has unit {unit!r} — use a short plain unit')

        if st.get('type') == 'range':
            if 'min' not in st or 'max' not in st:
                problems.append(f'{path}: range {sid} is missing min or max')
                continue
            lo, hi = st['min'], st['max']
            step = st.get('step', 1)  # Shopify defaults step to 1
            if step <= 0:
                problems.append(f'{path}: range {sid} has a step of {step}')
                continue
            steps = (hi - lo) / step
            if steps < 2 or steps > 101:
                problems.append(
                    f'{path}: range {sid} has {steps:g} steps (Shopify needs 2..101) — use a select instead')
            default = st.get('default')
            if default is not None:
                if not (lo <= default <= hi) or (default - lo) % step != 0:
                    problems.append(f'{path}: range {sid} default {default} is off the step grid')

        if st.get('type') in ('text', 'textarea') and '{{' in str(st.get('default', '')):
            problems.append(f'{path}: {sid} has Liquid in its default — move it to a Liquid fallback')


BLOCK_TAGS = {'if', 'unless', 'for', 'case', 'capture', 'form', 'paginate', 'tablerow',
              'comment', 'raw', 'schema', 'stylesheet', 'javascript', 'doc'}
TAG_RE = re.compile(r'\{%-?\s*(\w+)')


def check_liquid_balance(path, src):
    """An unclosed or stray if/for/endif makes Shopify reject the file with
    no error (sp-collection lost a whole release this way)."""
    stack = []
    # Skip raw/comment/schema/doc bodies so their contents are not parsed.
    src = re.sub(r'\{%-?\s*(comment|raw|schema|doc|stylesheet|javascript)\s*-?%\}.*?\{%-?\s*end\1\s*-?%\}', '', src, flags=re.S)
    # Inside {% liquid %} blocks every line is a tag.
    def expand(m):
        return '\n'.join('{% ' + ln.strip() + ' %}' for ln in m.group(1).splitlines() if ln.strip())
    src = re.sub(r'\{%-?\s*liquid\b(.*?)-?%\}', expand, src, flags=re.S)
    for m in TAG_RE.finditer(src):
        tag = m.group(1)
        line = src.count('\n', 0, m.start()) + 1
        if tag in BLOCK_TAGS:
            stack.append((tag, line))
        elif tag.startswith('end') and tag[3:] in BLOCK_TAGS:
            want = tag[3:]
            if not stack or stack[-1][0] != want:
                opened = f'{stack[-1][0]} from line ~{stack[-1][1]}' if stack else 'nothing'
                problems.append(f'{path}: "{tag}" near line {line} but the open block is {opened}')
                return
            stack.pop()
    if stack:
        problems.append(f'{path}: "{stack[-1][0]}" opened near line {stack[-1][1]} is never closed')


_schemas = {}


def schema_for(kind, name):
    """Schema of sections/<name>.liquid or blocks/<name>.liquid, or None."""
    key = (kind, name)
    if key not in _schemas:
        _schemas[key] = None
        try:
            src = open(f'{kind}/{name}.liquid', encoding='utf-8').read()
            m = re.search(r'\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}', src, re.S)
            if m:
                _schemas[key] = json.loads(m.group(1))
        except (OSError, json.JSONDecodeError):
            pass
    return _schemas[key]


def check_values(where, defs, values):
    """A template value outside a select's options or a range's grid rejects
    the whole template file, silently (page.gifting.json, art: blanket)."""
    by_id = {d['id']: d for d in defs if isinstance(d, dict) and 'id' in d}
    for sid, val in (values or {}).items():
        d = by_id.get(sid)
        if d is None:
            continue
        if d.get('type') == 'select' and val not in [o.get('value') for o in d.get('options', [])]:
            problems.append(f'{where}: {sid} = {val!r} is not one of the select options')
        if d.get('type') == 'range' and isinstance(val, (int, float)):
            lo, hi, step = d.get('min'), d.get('max'), d.get('step', 1)
            if lo is not None and hi is not None and (not lo <= val <= hi or (val - lo) % step):
                problems.append(f'{where}: {sid} = {val} is outside {lo}..{hi} step {step}')


def check_blocks(where, parent_schema, blocks):
    local = {b.get('type'): b for b in (parent_schema or {}).get('blocks', []) or [] if isinstance(b, dict)}
    for bid, blk in (blocks or {}).items():
        btype = blk.get('type', '')
        if btype.startswith('@'):
            continue
        sch = local.get(btype) if btype in local and local[btype].get('settings') else schema_for('blocks', btype)
        if sch is None:
            continue
        check_values(f'{where} › {btype}', sch.get('settings') or [], blk.get('settings'))
        check_blocks(f'{where} › {btype}', sch, blk.get('blocks'))


def check_template_values(path, tpl):
    for sid, sec in (tpl.get('sections') or {}).items():
        stype = sec.get('type', '')
        if stype.startswith('_') or stype in ('apps',):
            continue
        sch = schema_for('sections', stype)
        if sch is None:
            continue
        check_values(f'{path} › {stype}', sch.get('settings') or [], sec.get('settings'))
        check_blocks(f'{path} › {stype}', sch, sec.get('blocks'))


def main():
    files = (glob.glob('sections/*.liquid') + glob.glob('blocks/*.liquid')
             + glob.glob('snippets/*.liquid'))
    checked = 0
    for f in files:
        src = open(f, encoding='utf-8').read()
        if '/sp-' in f or '/_sp-' in f:
            check_liquid_balance(f, src)
        m = re.search(r'\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}', src, re.S)
        if not m:
            continue
        checked += 1
        try:
            schema = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            problems.append(f'{f}: schema is not valid JSON — {e}')
            continue
        check(f, schema, f.startswith('sections/'))

    # settings_data.json values must sit inside the ranges settings_schema.json
    # declares — one out-of-range value rejects the WHOLE file, silently.
    try:
        schema_raw = re.sub(r'^\s*/\*.*?\*/', '', open('config/settings_schema.json', encoding='utf-8').read(), flags=re.S)
        data_raw = re.sub(r'^\s*/\*.*?\*/', '', open('config/settings_data.json', encoding='utf-8').read(), flags=re.S)
        groups = json.loads(schema_raw)
        current = json.loads(data_raw).get('current', {})
    except (OSError, json.JSONDecodeError):
        groups, current = [], {}
    bounds = {}
    for grp in groups:
        if isinstance(grp, dict):
            for st in grp.get('settings') or []:
                if isinstance(st, dict) and st.get('type') == 'range' and 'id' in st:
                    bounds[st['id']] = (st.get('min'), st.get('max'))
    if isinstance(current, dict):
        for key, val in current.items():
            if key in bounds and isinstance(val, (int, float)):
                lo, hi = bounds[key]
                if lo is not None and val < lo:
                    problems.append(f'config/settings_data.json: {key} is {val}, below the minimum {lo}')
                if hi is not None and val > hi:
                    problems.append(f'config/settings_data.json: {key} is {val}, above the maximum {hi}')

    for t in glob.glob('templates/*.json') + glob.glob('sections/*-group.json'):
        raw = re.sub(r'/\*.*?\*/', '', open(t, encoding='utf-8').read(), flags=re.S)
        try:
            tpl = json.loads(raw)
        except json.JSONDecodeError as e:
            problems.append(f'{t}: not valid JSON — {e}')
            continue
        check_template_values(t, tpl)

    for p in problems:
        print(p)
    print(f'{checked} schemas checked: ' + ('clean' if not problems else f'{len(problems)} problem(s)'))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
