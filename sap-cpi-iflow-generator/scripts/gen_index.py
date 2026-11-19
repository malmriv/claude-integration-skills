#!/usr/bin/env python3
"""Regenerate reference/components-index.md from catalog/components.json."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
cat = json.load(open(os.path.join(HERE, '..', 'catalog', 'components.json'), encoding='utf-8'))
L = ['# Components index (generated from catalog/components.json)', '',
     'verified: `sample` = identity copied from an iFlow written by the SAP editor; `tenant-upload` = identity inferred, '
     'then confirmed by uploading a generated iFlow (server recognised the palette flavor, lab T1); `inferred` = NOT yet '
     'confirmed, run the tenant validation loop before relying on it; `metadata-only` = adapter variant whose properties '
     'come from tenant metadata but never seen in a real iFlow (identity follows the generic adapter rule, see adapters.md).', '',
     '## Flow steps, events, gateways, processes', '',
     '| key (`type` in iflowgen) | palette name | BPMN element | event definition / props on | identity properties | tenant version | verified |',
     '|---|---|---|---|---|---|---|']
for k, c in sorted(cat.items(), key=lambda kv: kv[0].lower()):
    if c['kind'] in ('sender', 'receiver'):
        continue
    ident = ', '.join('%s=%s' % (a, b if len(str(b)) < 40 else str(b)[:37] + '...') for a, b in (c.get('identity') or {}).items())
    ev = (c.get('eventDefinition') or '') + (' (props on definition)' if c.get('propsOn') == 'eventDefinition' else '')
    L.append('| `%s` | %s | %s | %s | %s | %s | %s |' % (k, c.get('display', ''), c.get('bpmn') or 'callActivity',
                                                        ev, ident, c.get('version') or '-', c.get('verified')))
L += ['', '## Adapters (messageFlow)', '',
      '| key | direction | ComponentType | TransportProtocol | MessageProtocol | tenant version | verified |',
      '|---|---|---|---|---|---|---|']
for k, c in sorted(cat.items(), key=lambda kv: kv[0].lower()):
    if c['kind'] not in ('sender', 'receiver'):
        continue
    a = c['adapter']
    L.append('| `%s` | %s | %s | %s | %s | %s | %s |' % (k, a['direction'], a['ComponentType'], a['TransportProtocol'],
                                                        a['MessageProtocol'], c['version'], c['verified']))
open(os.path.join(HERE, '..', 'reference', 'components-index.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('ok', len(L))
