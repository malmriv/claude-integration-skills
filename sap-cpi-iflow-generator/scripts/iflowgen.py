#!/usr/bin/env python3
"""Generate a SAP Cloud Integration .iflw (BPMN2 + ifl extensions) from a compact JSON flow spec.

Every element is emitted from catalog/components.json, so it carries:
  * the right BPMN tag / event definition and where the ifl:properties live,
  * identity keys (activityType, subActivityType, encoderType, splitType, operation...),
  * cmdVariantUri + componentVersion of the tenant's CURRENT palette version,
  * ALL properties the editor would write, with tenant defaults unless you override them.

Usage:  python iflowgen.py flow.json -o "My Flow.iflw" [--catalog ../catalog/components.json]

Spec (JSON):
{
  "name": "My Flow",
  "participants": [ {"id": "Sender", "name": "Sender", "role": "sender"},
                    {"id": "S4", "name": "S4HANA", "role": "receiver"} ],
  "collaboration": {"namespaceMapping": "xmlns:p1=urn:x", "log": "All events"},   # optional overrides
  "processes": [
    {"id": "Process_1", "name": "Integration Process", "type": "IntegrationProcess",   # or LocalIntegrationProcess
     "props": {"transactionalHandling": "Not Required"},
     "steps": [
        {"id": "Start", "type": "MessageStartEvent", "name": "Start"},
        {"id": "CM", "type": "Enricher", "name": "Set headers",
         "props": {"headerTable": [{"Action": "Create", "Type": "constant", "Name": "X", "Value": "1", "Datatype": "", "Default": ""}]}},
        {"id": "GW", "type": "ExclusiveGateway", "name": "Route?"},
        {"id": "Call", "type": "NonLoopingProcess", "name": "Call local", "props": {"processId": "Process_2"}},
        {"id": "End", "type": "MessageEndEvent", "name": "End"}
     ],
     "flows": [ ["Start", "CM"], ["CM", "GW"],
                {"from": "GW", "to": "Call", "name": "Yes", "condition": "${header.X} = '1'", "expressionType": "NonXML"},
                {"from": "GW", "to": "End", "name": "No", "default": true},
                ["Call", "End"] ],
     "subprocesses": [ {"id": "Exc", "type": "ErrorEventSubProcessTemplate", "name": "Exception Subprocess",
                        "steps": [...], "flows": [...]} ]
    }
  ],
  "messageFlows": [
     {"id": "MF_in", "adapter": "HTTPS", "direction": "Sender", "from": "Sender", "to": "Start",
      "name": "HTTPS", "props": {"urlPath": "/my/path"}},
     {"id": "MF_out", "adapter": "HTTP", "direction": "Receiver", "from": "Call", "to": "S4", "props": {...}}
  ]
}
Step "type" = catalog key (cname), e.g. Enricher, GroovyScript, XSLTMapping, MessageMapping, GeneralSplitter,
Camel (=Iterating Splitter), Gather, Join, Multicast, SequentialMulticast, ExclusiveGateway, ExternalCall
(Request Reply), Send, PollEnrich, contentEnricherWithLookup, put/get/select/delete (Data Store), Variables,
NonLoopingProcess, LoopingProcess, MessageStartEvent, MessageEndEvent, StartEvent, EndEvent, ErrorStartEvent,
ErrorEndEvent, EscalationEndEvent, TerminateEndEvent, intermediatetimer (Timer start) ...
Table-typed properties accept a list of dicts (column key -> value) or a pre-serialized string.
"""
import argparse, json, os, sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CATALOG = os.path.join(HERE, '..', 'catalog', 'components.json')

EVENT_TYPES = {'MessageStartEvent', 'MessageEndEvent', 'StartEvent', 'EndEvent', 'ErrorStartEvent',
               'ErrorEndEvent', 'EscalationEndEvent', 'TerminateEndEvent', 'intermediatetimer'}
SIZE = {'event': (32, 32), 'gateway': (40, 40), 'activity': (100, 60)}
# Identity keys that are pure type markers (always fixed per component).
FIXED_IDENTITY = {'activityType', 'subActivityType', 'encoderType', 'splitType', 'operation', 'mappingType',
                  'processType'}


class GenError(Exception):
    pass


def esc(v):
    return escape('' if v is None else str(v))


def table_to_string(rows):
    out = []
    for r in rows:
        out.append('<row>' + ''.join("<cell id='%s'>%s</cell>" % (k, escape(str(v))) for k, v in r.items()) + '</row>')
    return ''.join(out)


def variables_to_string(rows):
    """Write Variables table is positional: name, datatype, type, value, scope (observed in tenant output)."""
    out = []
    for r in rows:
        cells = [r.get('name', ''), r.get('datatype', ''), r.get('type', ''), r.get('value', ''), r.get('scope', 'local')]
        out.append('<row>' + ''.join('<cell>%s</cell>' % escape(str(c)) for c in cells) + '</row>')
    return ''.join(out)


class Gen:
    def __init__(self, spec, catalog):
        self.spec = spec
        self.cat = catalog
        self.ids = set()
        self.shapes = {}  # id -> (x, y, w, h)
        self.edges = []   # (id, src, tgt)
        self.lines = []

    # ---------- helpers ----------
    def comp(self, key):
        if key not in self.cat:
            raise GenError('Unknown component type %r (not in catalog). Use a catalog key.' % key)
        c = self.cat[key]
        if c.get('verified') == 'inferred':
            sys.stderr.write('WARNING: %s identity is inferred, not verified on a tenant sample.\n' % key)
        return c

    def adapter(self, mf):
        name, direction = mf['adapter'], mf['direction']
        cands = []
        for k, c in self.cat.items():
            if c['kind'] not in ('sender', 'receiver'):
                continue
            ad = c['adapter']
            if ad['direction'] != direction:
                continue
            if name in (k, ad['ComponentType'], c.get('display')):
                if mf.get('transportProtocol') and ad['TransportProtocol'] != mf['transportProtocol']:
                    continue
                if mf.get('messageProtocol') and ad['MessageProtocol'] != mf['messageProtocol']:
                    continue
                cands.append(c)
        if len(cands) != 1:
            opts = ['%s tp=%s mp=%s' % (c['key'], c['adapter']['TransportProtocol'], c['adapter']['MessageProtocol']) for c in cands]
            raise GenError('Adapter %r/%s resolves to %d variants; add transportProtocol/messageProtocol. %s'
                           % (name, direction, len(cands), opts))
        return cands[0]

    def uid(self, i):
        if i in self.ids:
            raise GenError('Duplicate id %r' % i)
        self.ids.add(i)
        return i

    def props_xml(self, c, user, ind, extra_identity=None):
        """Emit identity + all catalog properties (defaults unless overridden)."""
        user = dict(user or {})
        out = []
        emitted = set()

        def put(k, v):
            if isinstance(v, list):
                v = variables_to_string(v) if (c['key'] == 'Variables' and k == 'variable') else table_to_string(v)
            if isinstance(v, bool):
                v = 'true' if v else 'false'
            out.append('%s<ifl:property>\n%s    <key>%s</key>\n%s    %s\n%s</ifl:property>' % (
                ind, ind, esc(k), ind, ('<value>%s</value>' % esc(v)) if str(v) != '' else '<value/>', ind))
            emitted.add(k)

        ident = dict(c.get('identity') or {})
        ident.update(extra_identity or {})
        for k, v in ident.items():
            if k in FIXED_IDENTITY:
                put(k, v)
            elif k in user:
                put(k, user.pop(k))
            else:
                put(k, v)
        ui_only = set(c.get('uiOnlyKeys') or [])
        for p in c['properties']:
            k = p['key']
            if k in emitted or (k in ui_only and k not in user):
                continue
            if k in user:
                put(k, user.pop(k))
            else:
                put(k, p.get('default', ''))
        if c.get('componentVersion'):
            put('componentVersion', c['componentVersion'])
        put('cmdVariantUri', c['cmdVariantUri'])
        for k, v in user.items():  # unknown keys: emit but warn (validator will flag them)
            sys.stderr.write('WARNING: property %r is not defined for %s; emitted anyway.\n' % (k, c['key']))
            put(k, v)
        return '\n'.join(out)

    # ---------- layout ----------
    def layout_process(self, proc, x0, y0):
        """Simple left-to-right layered layout; returns (width, height)."""
        steps = proc['steps']
        flows = [self.norm_flow(f) for f in proc.get('flows', [])]
        succ = {s['id']: [] for s in steps}
        indeg = {s['id']: 0 for s in steps}
        for f in flows:
            if f['from'] in succ and f['to'] in indeg:
                succ[f['from']].append(f['to'])
                indeg[f['to']] += 1
        layer = {}
        queue = [s['id'] for s in steps if indeg[s['id']] == 0]
        for q in queue:
            layer.setdefault(q, 0)
        seen = set()
        while queue:
            n = queue.pop(0)
            if n in seen:
                continue
            seen.add(n)
            for m in succ[n]:
                layer[m] = max(layer.get(m, 0), layer[n] + 1)
                queue.append(m)
        for s in steps:
            layer.setdefault(s['id'], 0)
        rows = {}
        for s in steps:
            L = layer[s['id']]
            r = rows.get(L, 0)
            rows[L] = r + 1
            w, h = self.size_of(s['type'])
            cx = x0 + 60 + L * 150
            cy = y0 + 70 + r * 110
            self.shapes[s['id']] = (cx - w / 2, cy - h / 2, w, h)
        width = 120 + (max(layer.values()) + 1) * 150 if steps else 300
        height = 60 + max(rows.values()) * 110 if rows else 140
        return width, height

    def size_of(self, t):
        if t in EVENT_TYPES:
            return SIZE['event']
        c = self.cat.get(t, {})
        if c.get('bpmn') in ('parallelGateway', 'exclusiveGateway'):
            return SIZE['gateway']
        return SIZE['activity']

    @staticmethod
    def norm_flow(f):
        if isinstance(f, list):
            return {'from': f[0], 'to': f[1]}
        return f

    # ---------- emitters ----------
    def emit_step(self, s, ind):
        c = self.comp(s['type'])
        tag = c.get('bpmn') or 'callActivity'
        sid = self.uid(s['id'])
        name = s.get('name', c.get('display', s['type']))
        incoming = [f['id'] for f in self.cur_flows if f['to'] == sid]
        outgoing = [f['id'] for f in self.cur_flows if f['from'] == sid]
        attrs = 'id="%s" name="%s"' % (esc(sid), esc(name))
        default_flow = [f['id'] for f in self.cur_flows if f['from'] == sid and f.get('default')]
        if tag == 'exclusiveGateway' and default_flow:
            attrs = 'default="%s" ' % default_flow[0] + attrs
        lines = []
        props = dict(s.get('props') or {})
        extra = {}
        if s['type'] == 'XSLTMapping' and 'mappingname' in props:
            n = props['mappingname']
            extra = {'mappinguri': 'dir://mapping/xslt/src/main/resources/mapping/%s.xsl' % n, 'mappingname': n}
            props.setdefault('mappingpath', 'src/main/resources/mapping/%s' % n)
        if s['type'] == 'MessageMapping' and 'mappingname' in props:
            n = props['mappingname']
            extra = {'mappinguri': 'dir://mmap/src/main/resources/mapping/%s.mmap' % n, 'mappingname': n}
            props.setdefault('mappingpath', 'src/main/resources/mapping/%s' % n)
        loop = None
        if s['type'] == 'LoopingProcess':
            loop = {'id': 'StandardLoopCharacteristics_%s' % sid,
                    'max': props.pop('loopMaximum', '10'),
                    'cond': props.pop('expressionValue', props.pop('condition', ''))}
            extra['loopId'] = loop['id']
        lines.append('%s<bpmn2:%s %s>' % (ind, tag, attrs))
        if c.get('propsOn') == 'eventDefinition':
            pass  # the editor writes no extensionElements on the event itself; they live on the *EventDefinition
        else:
            lines.append('%s    <bpmn2:extensionElements>' % ind)
            lines.append(self.props_xml(c, props, ind + '        ', extra))
            lines.append('%s    </bpmn2:extensionElements>' % ind)
        for i in incoming:
            lines.append('%s    <bpmn2:incoming>%s</bpmn2:incoming>' % (ind, i))
        for o in outgoing:
            lines.append('%s    <bpmn2:outgoing>%s</bpmn2:outgoing>' % (ind, o))
        if loop:
            lines.append('%s    <bpmn2:standardLoopCharacteristics id="%s" loopMaximum="%s">' % (ind, loop['id'], esc(loop['max'])))
            lines.append('%s        <bpmn2:loopCondition id="FormalExpression_%s" xsi:type="bpmn2:tFormalExpression">%s</bpmn2:loopCondition>'
                         % (ind, sid, esc(loop['cond'])))
            lines.append('%s    </bpmn2:standardLoopCharacteristics>' % ind)
        ed = c.get('eventDefinition')
        if ed:
            if c.get('propsOn') == 'eventDefinition':
                lines.append('%s    <bpmn2:%s>' % (ind, ed))
                lines.append('%s        <bpmn2:extensionElements>' % ind)
                lines.append(self.props_xml(c, props, ind + '            '))
                lines.append('%s        </bpmn2:extensionElements>' % ind)
                lines.append('%s    </bpmn2:%s>' % (ind, ed))
            else:
                lines.append('%s    <bpmn2:%s/>' % (ind, ed))
        lines.append('%s</bpmn2:%s>' % (ind, tag))
        return '\n'.join(lines)

    def emit_flow(self, f, ind):
        attrs = 'id="%s"' % f['id']
        if f.get('name'):
            attrs += ' name="%s"' % esc(f['name'])
        attrs += ' sourceRef="%s" targetRef="%s"' % (f['from'], f['to'])
        src_type = self.step_type.get(f['from'])
        if src_type == 'ExclusiveGateway':
            et = f.get('expressionType', 'NonXML')
            body = ['%s<bpmn2:sequenceFlow %s>' % (ind, attrs),
                    '%s    <bpmn2:extensionElements>' % ind,
                    '%s        <ifl:property>\n%s            <key>expressionType</key>\n%s            <value>%s</value>\n%s        </ifl:property>'
                    % (ind, ind, ind, esc(et), ind),
                    '%s    </bpmn2:extensionElements>' % ind]
            if not f.get('default'):
                if not f.get('condition'):
                    raise GenError('Router route %s needs "condition" (or "default": true)' % f['id'])
                body.append('%s    <bpmn2:conditionExpression id="FormalExpression_%s" xsi:type="bpmn2:tFormalExpression">%s</bpmn2:conditionExpression>'
                            % (ind, f['id'], esc(f['condition'])))
            body.append('%s</bpmn2:sequenceFlow>' % ind)
            return '\n'.join(body)
        return '%s<bpmn2:sequenceFlow %s/>' % (ind, attrs)

    def emit_container(self, cont, ind, is_sub=False):
        flows = []
        for n, f in enumerate(cont.get('flows', [])):
            f = dict(self.norm_flow(f))
            f.setdefault('id', 'SequenceFlow_%s_%d' % (cont['id'], n + 1))
            self.uid(f['id'])
            flows.append(f)
            self.edges.append((f['id'], f['from'], f['to']))
        self.cur_flows = flows
        out = []
        for s in cont['steps']:
            self.step_type[s['id']] = s['type']
        for s in cont['steps']:
            self.cur_flows = flows
            out.append(self.emit_step(s, ind))
        for sp in cont.get('subprocesses', []):
            c = self.comp(sp.get('type', 'ErrorEventSubProcessTemplate'))
            self.uid(sp['id'])
            out.append('%s<bpmn2:subProcess id="%s" name="%s">' % (ind, sp['id'], esc(sp.get('name', 'Exception Subprocess'))))
            out.append('%s    <bpmn2:extensionElements>' % ind)
            out.append(self.props_xml(c, sp.get('props'), ind + '        '))
            out.append('%s    </bpmn2:extensionElements>' % ind)
            out.append(self.emit_container(sp, ind + '    ', True))
            out.append('%s</bpmn2:subProcess>' % ind)
            self.cur_flows = flows
        for f in flows:
            out.append(self.emit_flow(f, ind))
        return '\n'.join(out)

    def build(self):
        sp = self.spec
        self.step_type = {}
        L = ['<?xml version="1.0" encoding="UTF-8"?><bpmn2:definitions xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL" '
             'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
             'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:ifl="http:///com.sap.ifl.model/Ifl.xsd" '
             'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="Definitions_1">']
        L.append('    <bpmn2:collaboration id="Collaboration_1" name="Default Collaboration">')
        L.append('        <bpmn2:extensionElements>')
        L.append(self.props_xml(self.comp('IFlowConfiguration'), sp.get('collaboration'), '            '))
        L.append('        </bpmn2:extensionElements>')
        # --- layout first (needs all ids) ---
        y = 60
        proc_bounds = {}
        maxw = 0
        for p in sp['processes']:
            w, h = self.layout_process(p, 250, y)
            sub_y = y + h
            for sub in p.get('subprocesses', []):
                sw, shh = self.layout_process(sub, 280, sub_y + 10)
                self.shapes[sub['id']] = (270, sub_y, sw + 20, shh + 20)
                sub_y += shh + 40
                w = max(w, sw + 60)
            h = sub_y - y + 20
            proc_bounds[p['id']] = (250, y, max(w, 400), h)
            maxw = max(maxw, w)
            y += h + 60
        senders = [x for x in sp.get('participants', []) if x['role'] == 'sender']
        receivers = [x for x in sp.get('participants', []) if x['role'] == 'receiver']
        for i, s in enumerate(senders):
            self.shapes[s['id']] = (40, 100 + i * 180, 100, 140)
        for i, r in enumerate(receivers):
            self.shapes[r['id']] = (250 + maxw + 120, 60 + i * 180, 100, 140)
        # --- participants ---
        for s in senders:
            self.uid(s['id'])
            L.append('        <bpmn2:participant id="%s" ifl:type="EndpointSender" name="%s">' % (s['id'], esc(s.get('name', s['id']))))
            L.append('            <bpmn2:extensionElements>\n                <ifl:property>\n                    <key>enableBasicAuthentication</key>\n'
                     '                    <value>false</value>\n                </ifl:property>\n                <ifl:property>\n'
                     '                    <key>ifl:type</key>\n                    <value>EndpointSender</value>\n                </ifl:property>\n'
                     '            </bpmn2:extensionElements>')
            L.append('        </bpmn2:participant>')
        for r in receivers:
            self.uid(r['id'])
            # NOTE: "EndpointRecevier" (sic) is the value SAP itself writes.
            L.append('        <bpmn2:participant id="%s" ifl:type="EndpointRecevier" name="%s">' % (r['id'], esc(r.get('name', r['id']))))
            L.append('            <bpmn2:extensionElements>\n                <ifl:property>\n                    <key>ifl:type</key>\n'
                     '                    <value>EndpointRecevier</value>\n                </ifl:property>\n            </bpmn2:extensionElements>')
            L.append('        </bpmn2:participant>')
        for p in sp['processes']:
            pid = 'Participant_' + p['id']
            self.uid(pid)
            L.append('        <bpmn2:participant id="%s" ifl:type="IntegrationProcess" name="%s" processRef="%s">'
                     % (pid, esc(p['name']), p['id']))
            L.append('            <bpmn2:extensionElements/>')
            L.append('        </bpmn2:participant>')
            self.shapes[pid] = proc_bounds[p['id']]
        # --- message flows ---
        part_name = {x['id']: x.get('name', x['id']) for x in sp.get('participants', [])}
        for mf in sp.get('messageFlows', []):
            c = self.adapter(mf)
            self.uid(mf['id'])
            nm = mf.get('name', c['adapter']['ComponentType'])
            sysname = part_name.get(mf['from'] if mf['direction'] == 'Sender' else mf['to'], '')
            ad = c['adapter']
            ident = {'ComponentType': ad['ComponentType'], 'Description': mf.get('description', ''),
                     'ComponentNS': ad['ComponentNS'], 'Name': nm,
                     'TransportProtocolVersion': c['version'], 'ComponentSWCVName': 'external',
                     'system': sysname, 'TransportProtocol': ad['TransportProtocol'],
                     'MessageProtocol': ad['MessageProtocol'], 'MessageProtocolVersion': c['version'],
                     'ComponentSWCVId': c['version'], 'direction': ad['direction']}
            if ad.get('vendor'):
                ident['Vendor'] = ad['vendor']
            cc = dict(c)
            cc['identity'] = {}
            L.append('        <bpmn2:messageFlow id="%s" name="%s" sourceRef="%s" targetRef="%s">' % (mf['id'], esc(nm), mf['from'], mf['to']))
            L.append('            <bpmn2:extensionElements>')
            L.append(self.props_xml(cc, mf.get('props'), '                ', ident))
            L.append('            </bpmn2:extensionElements>')
            L.append('        </bpmn2:messageFlow>')
            self.edges.append((mf['id'], mf['from'], mf['to']))
        L.append('    </bpmn2:collaboration>')
        # --- processes ---
        for p in sp['processes']:
            ptype = p.get('type', 'IntegrationProcess')
            c = self.comp(ptype)
            self.uid(p['id'])
            L.append('    <bpmn2:process id="%s" name="%s">' % (p['id'], esc(p['name'])))
            L.append('        <bpmn2:extensionElements>')
            L.append(self.props_xml(c, p.get('props'), '            '))
            L.append('        </bpmn2:extensionElements>')
            L.append(self.emit_container(p, '        '))
            L.append('    </bpmn2:process>')
        # --- diagram ---
        L.append('    <bpmndi:BPMNDiagram id="BPMNDiagram_1" name="Default Collaboration Diagram">')
        L.append('        <bpmndi:BPMNPlane bpmnElement="Collaboration_1" id="BPMNPlane_1">')
        for i, (x, yy, w, h) in self.shapes.items():
            L.append('            <bpmndi:BPMNShape bpmnElement="%s" id="BPMNShape_%s">\n                <dc:Bounds height="%.1f" width="%.1f" x="%.1f" y="%.1f"/>\n'
                     '            </bpmndi:BPMNShape>' % (i, i, h, w, x, yy))
        for eid, s, t in self.edges:
            sx, sy, sw, sh = self.shapes[s]
            tx, ty, tw, th = self.shapes[t]
            L.append('            <bpmndi:BPMNEdge bpmnElement="%s" id="BPMNEdge_%s" sourceElement="BPMNShape_%s" targetElement="BPMNShape_%s">\n'
                     '                <di:waypoint x="%.1f" xsi:type="dc:Point" y="%.1f"/>\n                <di:waypoint x="%.1f" xsi:type="dc:Point" y="%.1f"/>\n'
                     '            </bpmndi:BPMNEdge>' % (eid, eid, s, t, sx + sw / 2, sy + sh / 2, tx + tw / 2, ty + th / 2))
        L.append('        </bpmndi:BPMNPlane>')
        L.append('    </bpmndi:BPMNDiagram>')
        L.append('</bpmn2:definitions>')
        return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--catalog', default=DEFAULT_CATALOG)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    cat = json.load(open(a.catalog, encoding='utf-8'))
    try:
        xml = Gen(spec, cat).build()
    except GenError as e:
        raise SystemExit('ERROR: %s' % e)
    open(a.out, 'w', encoding='utf-8').write(xml)
    print('written', a.out)


if __name__ == '__main__':
    main()
