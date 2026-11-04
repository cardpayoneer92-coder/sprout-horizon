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


def main():
    files = (glob.glob('sections/*.liquid') + glob.glob('blocks/*.liquid')
             + glob.glob('snippets/*.liquid'))
    checked = 0
    for f in files:
        src = open(f, encoding='utf-8').read()
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
            json.loads(raw)
        except json.JSONDecodeError as e:
            problems.append(f'{t}: not valid JSON — {e}')

    for p in problems:
        print(p)
    print(f'{checked} schemas checked: ' + ('clean' if not problems else f'{len(problems)} problem(s)'))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
