"""Condense CPI component metadata (from /api/1.0/metadata/<hash>) into compact per-component specs."""
import json, sys, os, re
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

def cond_str(c):
    if not c: return None
    t = c.get('conditionType')
    if t == 'BasicCondition':
        vals = c.get('valueList') or []
        return '%s in %s' % (c.get('key'), vals) if len(vals) != 1 else '%s == %r' % (c.get('key'), vals[0])
    subs = [cond_str(s) for s in c.get('complexSubConditions', [])]
    if t == 'AndCondition': return '(' + ' AND '.join(subs) + ')'
    if t == 'OrCondition': return '(' + ' OR '.join(subs) + ')'
    if t == 'NotCondition': return 'NOT ' + (subs[0] if len(subs) == 1 else '(' + ' AND '.join(subs) + ')')
    return json.dumps(c)

def compact_cond(c):
    """Machine-evaluable condition: ["eq", key, [values]] | ["and", ...] | ["or", ...] | ["not", ...]."""
    t = c.get('conditionType')
    if t == 'BasicCondition':
        return ['eq', c.get('key'), c.get('valueList') or []]
    subs = [compact_cond(s) for s in c.get('complexSubConditions', [])]
    return [{'AndCondition': 'and', 'OrCondition': 'or', 'NotCondition': 'not'}.get(t, 'and')] + subs


def row_spec(r, tab, sec):
    s = {'key': r.get('key'), 'label': r.get('label'), 'type': r.get('dataType'), 'tab': tab}
    if r.get('defaultValue') not in (None,): s['default'] = r['defaultValue']
    if r.get('isMandatory'): s['mandatory'] = True
    if r.get('comboMetadata'): s['values'] = [c['key'] for c in r['comboMetadata'] if c.get('isEnabled', True)]
    if r.get('condition'):
        s['visibleIf'] = cond_str(r['condition'])
        s['cond'] = compact_cond(r['condition'])
    if r.get('regexConstraint'): s['regex'] = r['regexConstraint']; s['regexMsg'] = r.get('message')
    if r.get('isReadOnly'): s['readOnly'] = True
    if not r.get('isVisible', True): s['hidden'] = True
    if r.get('isPassword'): s['password'] = True
    if r.get('isExternalizable') is False: s['notExternalizable'] = True
    if r.get('columnsMetadata'):
        s['columns'] = []
        for c in r['columnsMetadata']:
            cs = {'key': c['key'], 'label': c.get('label'), 'type': c.get('dataType')}
            if c.get('defaultValue') is not None: cs['default'] = c['defaultValue']
            if c.get('isMandatory'): cs['mandatory'] = True
            if c.get('comboMetadata'): cs['values'] = [x['key'] for x in c['comboMetadata']]
            if c.get('condition'):
                cs['visibleIf'] = cond_str(c['condition'])
                cs['cond'] = compact_cond(c['condition'])
            s['columns'].append(cs)
    return s

index = []
for j in json.load(open(src, encoding='utf-8')):
    if j.get('status') != 200: continue
    b = json.loads(j['body'])
    rows = []
    def walk_rows(rs, tab, sec):
        for r in rs:
            if r.get('key'): rows.append(row_spec(r, tab, sec))
            for ch in r.get('childSectionTO') or []:
                walk_rows(ch.get('rows', []), tab, ch.get('key'))
    for t in b.get('navigationTabs', []):
        for s in t.get('sections', []):
            walk_rows(s.get('rows', []), t.get('key'), s.get('key'))
    kind = {'shape': 'step', 'listOfSenderAdapters': 'sender', 'listOfReceiverAdapters': 'receiver', 'extra': 'config'}[j['kind']]
    name = j['key'].replace('DEFAULT_', '')
    spec = {'kind': kind, 'name': name, 'cmdVariantUri': j['uri'], 'properties': rows,
            'meta': b.get('properties', {}), 'helpUrl': b.get('helpUrl')}
    uri = dict(x.split('::',1) for x in j['uri'].split('/') if '::' in x)
    if kind in ('sender','receiver'):
        base = '%s__%s__%s__%s' % (kind, uri.get('cname','').replace('sap:',''), uri.get('tp',''), uri.get('mp',''))
    else:
        base = kind + '__' + name
    fn = re.sub(r'[^\w.-]+', '_', base)[:120] + '.json'
    json.dump(spec, open(os.path.join(out, fn), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    index.append((kind, name, j['uri'], fn, len(rows)))
with open(os.path.join(out, '_index.tsv'), 'w', encoding='utf-8') as f:
    for i in sorted(index): f.write('\t'.join(map(str, i)) + '\n')
print(len(index), 'specs')
