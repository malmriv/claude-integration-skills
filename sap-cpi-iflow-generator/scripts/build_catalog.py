#!/usr/bin/env python3
"""Build catalog/components.json from tenant metadata + canonical iflw samples.

Inputs (all harvested from a live tenant, see reference/harvesting.md):
  --specs DIR        condensed metadata specs (one JSON per component variant)
  --palette FILE     /api/1.0/metadata?profileID=iflmap response (palette list)
  --samples GLOB...  canonical .iflw files written by the SAP editor (corpus + labs)
  --overrides FILE   hand-maintained identity overrides verified on the tenant
Output: catalog/components.json

A component entry = what you need to emit one BPMN element correctly:
  bpmn tag, event definition, where the ifl:properties live, identity keys
  (activityType/subActivityType/...), the full property list with defaults,
  allowed values, mandatory flags and visibility conditions.
"""
import argparse, glob, json, os, re
import xml.etree.ElementTree as ET

B = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
NS = {'bpmn2': B, 'ifl': 'http:///com.sap.ifl.model/Ifl.xsd'}
EVT_DEFS = ['messageEventDefinition', 'errorEventDefinition', 'escalationEventDefinition',
            'timerEventDefinition', 'terminateEventDefinition']


def parse_uri(u):
    # cname may itself contain '/', e.g. "PKCS#7/CMS Signature-Content Splitter": split only before "key::"
    return dict(x.split('::', 1) for x in re.split(r'/(?=[A-Za-z]+::)', u) if '::' in x)


def comp_key(u):
    """Stable key for a component across versions."""
    d = parse_uri(u)
    if d.get('ctype') == 'AdapterVariant':
        return 'adapter:%s|%s|%s|%s' % (d.get('cname'), d.get('tp'), d.get('mp'), d.get('direction'))
    return d.get('cname')


def vtuple(v):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r'[.]', v or '0'))


def props_of(el):
    out = []
    for p in el.findall('bpmn2:extensionElements/ifl:property', NS):
        out.append((p.findtext('key'), p.findtext('value') or ''))
    return out


def harvest_samples(files):
    """cname -> best (highest version) canonical sample info."""
    best = {}
    for f in files:
        root = ET.parse(f).getroot()
        parent = {c: p for p in root.iter() for c in p}
        for el in root.iter():
            pr = props_of(el)
            d = dict(pr)
            cu = d.get('cmdVariantUri')
            if not cu:
                continue
            tag = el.tag.split('}')[1]
            info = {'file': os.path.basename(f), 'element': el.get('id') or (parent[el].get('id') if el in parent else None),
                    'version': parse_uri(cu).get('version', ''), 'props': pr}
            if tag in EVT_DEFS:  # properties live on the event definition
                ev = parent[el]
                info.update(bpmn=ev.tag.split('}')[1], eventDefinition=tag, propsOn='eventDefinition')
            else:
                evd = [c.tag.split('}')[1] for c in el if c.tag.split('}')[1] in EVT_DEFS]
                info.update(bpmn=tag, eventDefinition=evd[0] if evd else None, propsOn='element')
                if tag == 'callActivity' and el.find('bpmn2:standardLoopCharacteristics', NS) is not None:
                    info['loopCharacteristics'] = True
            k = comp_key(cu)
            if k not in best or vtuple(info['version']) >= vtuple(best[k]['version']):
                best[k] = info
    return best


# Fallback identity rules for components never seen in a canonical sample.
# They are marked verified=false; run the tenant validation loop before relying on them.
def inferred_identity(cname, flavor, shape_type):
    i = {}
    enc = {'Base64 Encode', 'GZIP Compress', 'ZIP Compress', 'MIME Multipart Message Encode'}
    dec = {'Base64 Decode', 'GZIP Decompress', 'ZIP Decompress', 'MIME Multipart Message Decode'}
    if cname in enc:
        i = {'activityType': 'Encoder', 'encoderType': cname}
    elif cname in dec:
        i = {'activityType': 'Decoder', 'encoderType': cname}
    elif flavor and flavor.startswith('Splitter_'):
        i = {'activityType': 'Splitter', 'splitType': cname}
    elif cname in ('put', 'get', 'select', 'delete'):
        i = {'activityType': 'DBstorage', 'operation': cname}
    elif cname in ('GroovyScript', 'JavaScript'):
        i = {'activityType': 'Script', 'subActivityType': cname}
    elif cname in ('MessageMapping', 'OperationMapping'):
        i = {'activityType': 'Mapping', 'mappingType': cname}
    elif cname == 'XSLTMapping':
        i = {'activityType': 'Mapping', 'subActivityType': 'XSLTMapping'}
    elif cname in ('NonLoopingProcess', 'LoopingProcess'):
        i = {'activityType': 'ProcessCallElement', 'subActivityType': cname}
    elif shape_type == 'Gateway' and flavor == 'parallel':
        i = {'activityType': cname, 'subActivityType': 'parallel'}
    else:
        i = {'activityType': flavor or cname}
    return i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--specs', required=True)
    ap.add_argument('--palette', required=True)
    ap.add_argument('--samples', nargs='+', required=True)
    ap.add_argument('--overrides')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    files = []
    for g in a.samples:
        files += glob.glob(g)
    samples = harvest_samples(files)
    overrides = json.load(open(a.overrides, encoding='utf-8')) if a.overrides else {}

    palette = json.load(open(a.palette, encoding='utf-8'))[0]
    shape_by_cname = {}
    for k, v in palette['shapeMetadataTOMap'].items():
        at = v[0]['attributes']
        if at.get('cmdURI'):
            shape_by_cname[parse_uri(at['cmdURI']).get('cname')] = (k, at)

    comps = {}
    for f in sorted(glob.glob(os.path.join(a.specs, '*.json'))):
        s = json.load(open(f, encoding='utf-8'))
        uri = s['cmdVariantUri']
        d = parse_uri(uri)
        if d.get('vendor') not in (None, 'SAP'):
            continue  # third-party adapters: out of scope
        key = comp_key(uri)
        version = d.get('version', '')
        spec_keys = [p['key'] for p in s['properties']]
        e = {'key': key, 'kind': s['kind'], 'cmdVariantUri': uri, 'version': version,
             'componentVersion': '.'.join(version.split('.')[:2]) if version else None,
             'properties': s['properties'], 'helpUrl': s.get('helpUrl')}
        if s['kind'] in ('sender', 'receiver'):
            e.update(bpmn='messageFlow', propsOn='element', display=s['name'].split('|')[0],
                     adapter={'ComponentType': d['cname'].split(':')[-1], 'TransportProtocol': d.get('tp'),
                              'MessageProtocol': d.get('mp'), 'direction': d.get('direction'),
                              'ComponentNS': d['cname'].split(':')[0] if ':' in d['cname'] else (d.get('vendor') or 'sap'),
                              'vendor': d.get('vendor')})
        else:
            sk, at = shape_by_cname.get(d.get('cname'), (s['name'], {}))
            e['display'] = at.get('displayName') or at.get('name') or s['name']
            e['paletteKey'] = sk
            e['shapeType'] = at.get('type')
            e['flavor'] = at.get('flavor')
        smp = samples.get(key)
        if smp:
            ident = [(k, v) for k, v in smp['props'] if k not in spec_keys]
            e['identity'] = {k: v for k, v in ident if k not in ('cmdVariantUri', 'componentVersion')}
            for k in ('bpmn', 'eventDefinition', 'propsOn'):
                if smp.get(k) and not (e.get('bpmn') == 'messageFlow' and k == 'bpmn'):
                    e[k] = smp[k]
            if smp.get('loopCharacteristics'):
                e['loopCharacteristics'] = True
            e['verified'] = 'sample'
            e['sample'] = '%s#%s (v%s)' % (smp['file'], smp['element'], smp['version'])
            if not version and smp['version']:
                # palette URI is version-less (e.g. MessageStartEvent) but the editor writes a versioned one
                cu = dict(smp['props']).get('cmdVariantUri')
                e['cmdVariantUri'], e['version'] = cu, smp['version']
                e['componentVersion'] = '.'.join(smp['version'].split('.')[:2])
                version = smp['version']
            e['propertyOrderInSample'] = [k for k, _ in smp['props']]
            sample_keys = {k for k, _ in smp['props']}
            if smp['version'] == version:
                # Same version as the tenant palette: metadata keys the editor did NOT write are UI-only
                # (e.g. IFlowConfiguration name/bundleId/productProfiles live in MANIFEST.MF, not in the .iflw).
                ui_only = [k for k in spec_keys if k not in sample_keys]
                if ui_only:
                    e['uiOnlyKeys'] = ui_only
            else:
                e['sampleVersionDiffers'] = True
        elif s['kind'] not in ('sender', 'receiver'):
            e['identity'] = inferred_identity(d.get('cname'), e.get('flavor'), e.get('shapeType'))
            e['verified'] = 'inferred'
        else:
            e['verified'] = 'metadata-only'
        if key in overrides:
            e.update(overrides[key])
        comps[key] = e

    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(comps, open(a.out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    n = {}
    for c in comps.values():
        n[c['verified']] = n.get(c['verified'], 0) + 1
    print(len(comps), 'components', n)


if __name__ == '__main__':
    main()
