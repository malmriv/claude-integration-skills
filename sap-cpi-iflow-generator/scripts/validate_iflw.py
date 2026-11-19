#!/usr/bin/env python3
"""Static validator for SAP Cloud Integration iFlows (.iflw or the importable .zip).

Catches what makes an iFlow syntactically valid XML but *illegal* for the tenant. Every rule below was
either observed in tenant validation (GET .../iflows/<id> -> validationResultModel) during the lab runs,
or derived from the tenant's own component metadata (catalog/components.json).

Severity:
  FATAL  the tenant cannot even build the editor model (HTTP 500, iFlow will not open)
  ERROR  the tenant reports an error and blocks deployment (isDeployRestricted=true) -- or the tenant
         would silently ACCEPT it but the result is not what the XML says (e.g. unknown property keys)
  WARN   tenant warning or bad practice
Exit code: 2 if any FATAL/ERROR, else 0.

Usage: python validate_iflw.py Flow.iflw [--resources dir] [--catalog ../catalog/components.json] [--json]
       python validate_iflw.py MyFlow.zip
"""
import argparse, io, json, os, re, sys, zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
B = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
DI = 'http://www.omg.org/spec/BPMN/20100524/DI'
DC = 'http://www.omg.org/spec/DD/20100524/DC'
IFL = 'http:///com.sap.ifl.model/Ifl.xsd'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
NS = {'bpmn2': B, 'ifl': IFL, 'bpmndi': DI, 'dc': DC}
EVT_DEFS = ['messageEventDefinition', 'errorEventDefinition', 'escalationEventDefinition',
            'timerEventDefinition', 'terminateEventDefinition']
FLOW_NODES = {'callActivity', 'serviceTask', 'startEvent', 'endEvent', 'exclusiveGateway', 'parallelGateway',
              'subProcess', 'intermediateCatchEvent', 'intermediateThrowEvent'}
IDENTITY_KEYS = {'cmdVariantUri', 'componentVersion', 'activityType', 'subActivityType', 'encoderType', 'splitType',
                 'operation', 'mappingType', 'processType', 'loopId', 'mappinguri', 'mappingname', 'scheduleKey',
                 'expressionType', 'visibility', 'encrypt', 'expire',
                 # adapter identity
                 'ComponentType', 'Description', 'ComponentNS', 'Name', 'TransportProtocolVersion', 'ComponentSWCVName',
                 'system', 'TransportProtocol', 'MessageProtocol', 'MessageProtocolVersion', 'ComponentSWCVId',
                 'direction', 'Vendor'}
CONTENT_ENRICHER_ADAPTERS = {'SuccessFactors', 'SOAP', 'HCIOData'}   # tenant: "supports SuccessFactors, Soap1.x, and OData"


def tag(el):
    return el.tag.split('}')[1] if '}' in el.tag else el.tag


def parse_uri(u):
    return dict(x.split('::', 1) for x in re.split(r'/(?=[A-Za-z]+::)', u or '') if '::' in x)


def vtuple(v):
    return tuple(int(x) if x.isdigit() else 0 for x in (v or '0').split('.'))


def comp_key(u):
    d = parse_uri(u)
    if d.get('ctype') == 'AdapterVariant':
        return 'adapter:%s|%s|%s|%s' % (d.get('cname'), d.get('tp'), d.get('mp'), d.get('direction'))
    return d.get('cname')


def props(el):
    ext = el.find('bpmn2:extensionElements', NS)
    out = {}
    if ext is None:
        return out
    for p in ext.findall('ifl:property', NS):
        out[p.findtext('key')] = p.findtext('value') or ''
    return out


def eval_cond(cond, values):
    if not cond:
        return True
    op = cond[0]
    if op == 'eq':
        return values.get(cond[1], '') in cond[2]
    if op == 'and':
        return all(eval_cond(c, values) for c in cond[1:])
    if op == 'or':
        return any(eval_cond(c, values) for c in cond[1:])
    if op == 'not':
        return not all(eval_cond(c, values) for c in cond[1:])
    return True


NCNAME = r'[A-Za-z_][\w.\-]*'


def java_regex(r):
    """Metadata constraints: 'Constraint.isValidRegex(<java regex>)', 'Constraint.isValidNCName' or a bare regex."""
    m = re.match(r'^Constraint\.isValidRegex\((.*)\)$', r, re.S)
    if m:
        return m.group(1)
    if r.startswith('Constraint.isValidNCName'):
        return NCNAME
    if r.startswith('Constraint.'):
        return None  # unknown constraint function: do not guess
    return r


def parse_table(v):
    """'<row><cell id='A'>x</cell>...</row>...' -> list of dicts (positional cells -> '#0', '#1'...)."""
    rows = []
    try:
        root = ET.fromstring('<t>%s</t>' % v)
    except ET.ParseError:
        return None
    for r in root.findall('row'):
        d = {}
        for i, c in enumerate(r.findall('cell')):
            d[c.get('id', '#%d' % i)] = c.text or ''
        rows.append(d)
    return rows


class V:
    def __init__(self, catalog, resources, params):
        self.cat = catalog
        self.res = resources  # set of relative paths under src/main/resources, or None
        self.params = params  # dict of externalized params or None
        self.out = []

    def add(self, sev, eid, msg):
        self.out.append((sev, eid or '-', msg))

    # ------------------------------------------------------------------
    def check_component(self, el, owner_id, kind_hint=None):
        """Validate identity + properties of one element carrying ifl properties."""
        p = props(el)
        cu = p.get('cmdVariantUri')
        if not cu:
            self.add('ERROR', owner_id, 'no cmdVariantUri: the tenant rebuilds it from activityType/componentVersion '
                                        '(possibly an old version). Always write it.')
            return None, p
        key = comp_key(cu)
        c = self.cat.get(key)
        if not c:
            self.add('ERROR', owner_id, 'unknown component %r (cmdVariantUri %s) - not in the tenant palette' % (key, cu))
            return None, p
        ver = parse_uri(cu).get('version')
        if c.get('version') and ver:
            if vtuple(ver) > vtuple(c['version']):
                self.add('ERROR', owner_id, 'version %s of %s does not exist on the tenant (max %s): "component ... is not supported"'
                         % (ver, key, c['version']))
            elif vtuple(ver) < vtuple(c['version']):
                self.add('WARN', owner_id, '%s uses old version %s (tenant current %s); accepted, but properties added in newer '
                                           'versions are absent' % (key, ver, c['version']))
        cv = p.get('componentVersion')
        if cv is None and c.get('componentVersion'):
            self.add('WARN', owner_id, 'componentVersion missing (tenant tolerates it, the editor always writes it)')
        elif cv and ver and cv != '.'.join(ver.split('.')[:2]):
            self.add('ERROR', owner_id, 'componentVersion %s does not match cmdVariantUri version %s' % (cv, ver))
        for k, v in (c.get('identity') or {}).items():
            if k in ('activityType', 'subActivityType', 'encoderType', 'splitType', 'operation', 'mappingType', 'processType'):
                if k not in p:
                    self.add('ERROR', owner_id, 'identity property %s=%s missing (missing activityType => "component ... not '
                                                'supported"; missing processType on a local process => treated as main process)'
                             % (k, v))
                elif p[k] != v:
                    self.add('ERROR', owner_id, 'identity property %s=%r but %s requires %r' % (k, p[k], key, v))
        # ---- properties ----
        spec = {q['key']: q for q in c['properties']}
        ui_only = set(c.get('uiOnlyKeys') or [])
        for k, v in p.items():
            if k in IDENTITY_KEYS:
                continue
            if k in ui_only:
                self.add('ERROR', owner_id, 'property %r is UI-only for %s and must not be written in the .iflw '
                                            '(tenant: e.g. "Invalid value \'iflmap\' entered in \'Runtime Profile\'")' % (k, key))
                continue
            if k not in spec:
                self.add('ERROR', owner_id, 'unknown property %r for %s: the tenant SILENTLY IGNORES it (typo => default '
                                            'behaviour). Known: %s' % (k, key, ', '.join(sorted(spec))[:300]))
        values = {k: v for k, v in p.items()}
        for k, q in spec.items():
            if k in ui_only:
                continue
            visible = eval_cond(q.get('cond'), values)
            v = p.get(k)
            if v is None:
                if visible and not c.get('sampleVersionDiffers') and not (ver and vtuple(ver) < vtuple(c.get('version', '0'))):
                    self.add('WARN', owner_id, 'property %r not written (editor always writes every property; default %r applies)'
                             % (k, q.get('default', '')))
                continue
            if '{{' in v:
                for name in re.findall(r'\{\{([^}]+)\}\}', v):
                    if self.params is not None and name not in self.params:
                        self.add('ERROR', owner_id, 'externalized parameter {{%s}} (property %s) is not defined in '
                                                    'parameters.prop/.propdef - tenant accepts it silently at design time' % (name, k))
                continue
            if not visible:
                continue
            if q.get('mandatory') and v.strip() == '' and q.get('type') != 'isTable':
                sev = 'WARN' if q.get('type') == 'xsd:boolean' else 'ERROR'   # empty boolean is read as false
                self.add(sev, owner_id, 'mandatory property %r (%s) is empty' % (k, q.get('label')))
            if v and q.get('values') and q.get('type') != 'isTable' and v not in q['values']:
                self.add('ERROR', owner_id, 'invalid value %r for %r; allowed: %s' % (v, k, q['values']))
            if v and q.get('type') == 'xsd:boolean' and v not in ('true', 'false', '0', '1'):
                self.add('ERROR', owner_id, '%r must be boolean (true/false or 1/0 as the component uses), got %r' % (k, v))
            if v and q.get('type') in ('xsd:integer', 'xsd:long') and not re.fullmatch(r'-?\d+', v) and '${' not in v:
                self.add('ERROR', owner_id, '%r must be an integer, got %r' % (k, v))
            if v and q.get('regex') and '${' not in v and java_regex(q['regex']):
                try:
                    if not re.fullmatch(java_regex(q['regex']), v, re.S):
                        self.add('ERROR', owner_id, 'value %r of %r violates constraint %s (%s)' % (v, k, q['regex'], q.get('regexMsg')))
                except re.error:
                    pass
            if q.get('type') == 'isTable' and v:
                rows = parse_table(v)
                if rows is None:
                    self.add('ERROR', owner_id, 'table property %r is not a valid <row><cell id=..> list' % k)
                    continue
                cols = {cc['key']: cc for cc in q.get('columns', [])}
                for i, r in enumerate(rows, 1):
                    for ck, cvv in r.items():
                        if ck.startswith('#'):
                            continue
                        if ck not in cols:
                            self.add('ERROR', owner_id, 'table %r row %d: unknown column %r (known %s)' % (k, i, ck, list(cols)))
                            continue
                        col = cols[ck]
                        if col.get('values') and cvv and cvv not in col['values'] and '{{' not in cvv:
                            self.add('ERROR', owner_id, 'table %r row %d: invalid %s=%r; allowed %s' % (k, i, ck, cvv, col['values']))
                    for ck, col in cols.items():
                        if col.get('mandatory') and not r.get(ck) and eval_cond(col.get('cond'), r) and not any(x.startswith('#') for x in r):
                            self.add('ERROR', owner_id, 'table %r row %d: mandatory column %r empty' % (k, i, ck))
            if q.get('type') == 'isTable' and not v and q.get('mandatory') and visible:
                self.add('WARN', owner_id, 'table %r is empty; the tenant may require at least one row' % k)
        return c, p

    # ------------------------------------------------------------------
    def run(self, xml_text):
        try:
            root = ET.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)
        except ET.ParseError as e:
            self.add('FATAL', '-', 'XML not well-formed: %s' % e)
            return self.out
        if tag(root) != 'definitions' or root.tag.split('}')[0][1:] != B:
            self.add('FATAL', '-', 'root must be bpmn2:definitions in namespace %s' % B)
        for pfx, uri in (('ifl', IFL),):
            if IFL not in xml_text:
                self.add('FATAL', '-', 'namespace xmlns:ifl="%s" missing' % uri)
        ids = {}
        for el in root.iter():
            i = el.get('id')
            if i:
                if i in ids:
                    self.add('FATAL', i, 'duplicate id %r' % i)
                ids[i] = el
        collab = root.find('bpmn2:collaboration', NS)
        if collab is None:
            self.add('FATAL', '-', 'no bpmn2:collaboration')
            return self.out
        self.check_component(collab, collab.get('id'))
        participants = {p.get('id'): p for p in collab.findall('bpmn2:participant', NS)}
        processes = {p.get('id'): p for p in root.findall('bpmn2:process', NS)}
        ptype = {pid: p.get('{%s}type' % IFL) for pid, p in participants.items()}
        for pid, p in participants.items():
            t = ptype[pid]
            if t not in ('EndpointSender', 'EndpointRecevier', 'IntegrationProcess'):
                self.add('ERROR', pid, 'participant ifl:type %r invalid (EndpointSender | EndpointRecevier [sic] | IntegrationProcess)' % t)
            if t == 'IntegrationProcess':
                if p.get('processRef') not in processes:
                    self.add('FATAL', pid, 'processRef %r does not resolve to a bpmn2:process' % p.get('processRef'))
            pp = props(p)
            if t in ('EndpointSender', 'EndpointRecevier') and pp.get('ifl:type') != t:
                self.add('WARN', pid, 'participant should carry <ifl:property> ifl:type=%s (editor writes it)' % t)
        # ---- diagram ----
        shapes = {s.get('bpmnElement'): s for s in root.iter('{%s}BPMNShape' % DI)}
        edges = {s.get('bpmnElement'): s for s in root.iter('{%s}BPMNEdge' % DI)}
        for i, el in ids.items():
            t = tag(el)
            if t in FLOW_NODES or (t == 'participant'):
                if i not in shapes:
                    self.add('FATAL', i, 'no BPMNShape for %s %r: tenant answers HTTP 500, iFlow cannot be opened' % (t, i))
            if t in ('sequenceFlow', 'messageFlow') and i not in edges:
                self.add('WARN', i, 'no BPMNEdge for %s (add one; the editor always writes it)' % t)
        for k in list(shapes) + list(edges):
            if k not in ids:
                self.add('ERROR', k, 'diagram references unknown element %r' % k)
        # ---- message flows ----
        local_procs = set()
        proc_kind = {}
        for pid, pr in processes.items():
            c, p = self.check_component(pr, pid)
            cname = parse_uri(p.get('cmdVariantUri', '')).get('cname')
            proc_kind[pid] = cname
            if cname == 'LocalIntegrationProcess':
                local_procs.add(pid)
        node_proc = {}
        for pid, pr in processes.items():
            for el in pr.iter():
                if el.get('id') and el is not pr:
                    node_proc[el.get('id')] = pid
        mf_by_node = {}
        for mf in collab.findall('bpmn2:messageFlow', NS):
            mid = mf.get('id')
            s, t = mf.get('sourceRef'), mf.get('targetRef')
            for r in (s, t):
                if r not in ids:
                    self.add('FATAL', mid, 'messageFlow reference %r does not exist' % r)
            c, p = self.check_component(mf, mid)
            if not c:
                continue
            d = p.get('direction')
            ad = c.get('adapter', {})
            mf_by_node.setdefault(s, []).append((mid, c, p))
            mf_by_node.setdefault(t, []).append((mid, c, p))
            if d == 'Sender':
                if ptype.get(s) != 'EndpointSender':
                    self.add('ERROR', mid, 'sender adapter must start at an EndpointSender participant (sourceRef %r)' % s)
                tgt = ids.get(t)
                tp = props(tgt) if tgt is not None else {}
                tcname = parse_uri(tp.get('cmdVariantUri', '')).get('cname')
                if tgt is not None and not (tag(tgt) == 'startEvent' and tgt.find('bpmn2:messageEventDefinition', NS) is not None) \
                        and tcname != 'PollEnrich':
                    self.add('ERROR', mid, 'sender adapter must target a Message Start Event (or a Poll Enrich step), not %s %r'
                             % (tag(tgt), t))
                if tcname == 'PollEnrich' and ad.get('ComponentType') not in ('SFTP', 'PollingSFTP', 'FTP', 'PollingFTP', 'Mail',
                                                                              'DataStoreConsumer'):
                    self.add('WARN', mid, 'Poll Enrich normally uses a polling sender adapter (SFTP/FTP/Mail)')
            elif d == 'Receiver':
                src, tgt_ = ids.get(s), ids.get(t)
                enricher_like = None
                for r in (s, t):
                    e = ids.get(r)
                    if e is not None:
                        cn = parse_uri(props(e).get('cmdVariantUri', '')).get('cname')
                        if cn in ('contentEnricherWithLookup', 'PollEnrich'):
                            enricher_like = (r, cn)
                if enricher_like:
                    r, cn = enricher_like
                    if t != r:
                        self.add('ERROR', mid, '%s message flow must go FROM the participant TO the step (targetRef=%s): tenant '
                                               'reports "does not have incoming connector from external system"' % (cn, r))
                    if cn == 'contentEnricherWithLookup' and ad.get('ComponentType') not in CONTENT_ENRICHER_ADAPTERS:
                        self.add('ERROR', mid, 'Content Enricher supports only SuccessFactors, SOAP 1.x and OData adapters '
                                               '(got %s)' % ad.get('ComponentType'))
                    if cn == 'PollEnrich':
                        self.add('ERROR', mid, 'Poll Enrich needs a SENDER-direction polling adapter (e.g. sap:PollingSFTP/Sender) '
                                               'from an EndpointSender participant, not a receiver adapter')
                else:
                    if ptype.get(t) != 'EndpointRecevier':
                        self.add('ERROR', mid, 'receiver adapter must target an EndpointRecevier participant (targetRef %r)' % t)
                    sp = props(src) if src is not None else {}
                    scname = parse_uri(sp.get('cmdVariantUri', '')).get('cname')
                    if src is not None and scname not in ('ExternalCall', 'Send', 'MessageEndEvent'):
                        self.add('ERROR', mid, 'receiver message flow must start at Request Reply, Send or a Message End Event '
                                               '(got %s/%s)' % (tag(src), scname))
        # ---- processes ----
        for pid, pr in processes.items():
            self.check_container(pr, pid, proc_kind.get(pid), processes, local_procs, mf_by_node, ids, top=True)
        return self.out

    def check_container(self, cont, pid, pkind, processes, local_procs, mf_by_node, ids, top=False):
        is_local = pkind == 'LocalIntegrationProcess'
        is_sub = tag(cont) == 'subProcess'
        nodes = [e for e in cont if tag(e) in FLOW_NODES]
        flows = [e for e in cont if tag(e) == 'sequenceFlow']
        node_ids = {n.get('id') for n in nodes}
        inc, out = {}, {}
        for f in flows:
            s, t = f.get('sourceRef'), f.get('targetRef')
            for r in (s, t):
                if r not in node_ids:
                    self.add('FATAL' if r not in ids else 'ERROR', f.get('id'),
                             'sequenceFlow %s %r is not a node of the same container %r' % ('end', r, cont.get('id')))
            out.setdefault(s, []).append(f)
            inc.setdefault(t, []).append(f)
        starts, ends = [], []
        meaningful = 0
        has_aggregator = False
        for n in nodes:
            nid = n.get('id')
            t = tag(n)
            if t == 'subProcess':
                c, p = self.check_component(n, nid)
                inner_start = [e for e in n if tag(e) == 'startEvent']
                if not any(e.find('bpmn2:errorEventDefinition', NS) is not None for e in inner_start):
                    self.add('ERROR', nid, 'Exception Subprocess must begin with an Error Start Event')
                self.check_container(n, pid, pkind, processes, local_procs, mf_by_node, ids)
                continue
            evd = [e for e in n if tag(e) in EVT_DEFS]
            carrier = evd[0] if (evd and props(evd[0]).get('cmdVariantUri')) else n
            if evd and props(n).get('cmdVariantUri') and props(evd[0]):
                self.add('WARN', nid, 'properties duplicated on event and event definition')
            if t in ('startEvent', 'endEvent') and evd and tag(evd[0]) in ('errorEventDefinition', 'escalationEventDefinition',
                                                                         'timerEventDefinition') and carrier is n:
                self.add('ERROR', nid, 'properties of %s must be on the <bpmn2:%s> child, not on the event' % (t, tag(evd[0])))
            c, p = self.check_component(carrier, nid)
            cname = parse_uri(p.get('cmdVariantUri', '')).get('cname')
            # incoming/outgoing children consistency
            ch_in = [x.text for x in n.findall('bpmn2:incoming', NS)]
            ch_out = [x.text for x in n.findall('bpmn2:outgoing', NS)]
            if sorted(ch_in) != sorted(f.get('id') for f in inc.get(nid, [])) or \
                    sorted(ch_out) != sorted(f.get('id') for f in out.get(nid, [])):
                self.add('WARN', nid, '<incoming>/<outgoing> children do not match the sequenceFlows (tenant rebuilds them, '
                                      'but write them consistently)')
            if t == 'startEvent':
                starts.append((n, cname))
                if not out.get(nid):
                    self.add('ERROR', nid, 'start event without outgoing sequence flow')
            elif t == 'endEvent':
                ends.append((n, cname))
                if not inc.get(nid):
                    self.add('ERROR', nid, 'end event without incoming sequence flow')
            else:
                if not inc.get(nid):
                    self.add('ERROR', nid, '%s has no incoming sequence flow' % (cname or t))
                if not out.get(nid):
                    self.add('ERROR', nid, '%s has no outgoing sequence flow' % (cname or t))
            # ---- step specific rules ----
            if cname == 'Enricher':
                if p.get('headerTable', '') or p.get('propertyTable', '') or p.get('wrapContent', ''):
                    meaningful += 1
            elif t not in ('startEvent', 'endEvent'):
                meaningful += 1
            if cname == 'Aggregator':
                has_aggregator = True
            if cname in ('NonLoopingProcess', 'LoopingProcess', 'IdempotentProcessCall'):
                tgt = p.get('processId')
                if tgt not in processes:
                    self.add('ERROR', nid, 'processId %r does not reference a process' % tgt)
                elif tgt not in local_procs:
                    self.add('ERROR', nid, 'processId %r must reference a Local Integration Process' % tgt)
            if cname == 'LoopingProcess':
                slc = n.find('bpmn2:standardLoopCharacteristics', NS)
                if slc is None:
                    self.add('ERROR', nid, 'Looping Process Call needs <bpmn2:standardLoopCharacteristics loopMaximum=".."> with '
                                           '<bpmn2:loopCondition xsi:type="bpmn2:tFormalExpression">')
                elif p.get('loopId') and p.get('loopId') != slc.get('id'):
                    self.add('ERROR', nid, 'loopId %r must equal standardLoopCharacteristics id %r' % (p.get('loopId'), slc.get('id')))
            if cname in ('ExternalCall', 'Send'):
                mfs = [m for m in mf_by_node.get(nid, [])]
                if len(mfs) != 1:
                    self.add('ERROR', nid, '%s needs exactly one receiver message flow (has %d)' % (cname, len(mfs)))
            if cname in ('contentEnricherWithLookup', 'PollEnrich') and not mf_by_node.get(nid):
                self.add('ERROR', nid, '%s needs a message flow from a participant' % cname)
            if cname == 'ExclusiveGateway':
                outs = out.get(nid, [])
                dflt = n.get('default')
                if len(outs) < 2:
                    self.add('ERROR', nid, 'Router needs at least 2 routes')
                if not dflt or dflt not in [f.get('id') for f in outs]:
                    self.add('ERROR', nid, 'Router must name exactly one default route in its default="SequenceFlow_x" attribute')
                for f in outs:
                    fp = props(f)
                    ce = f.find('bpmn2:conditionExpression', NS)
                    if f.get('id') != dflt:
                        if ce is None or not (ce.text or '').strip():
                            self.add('ERROR', f.get('id'), 'non-default route needs <bpmn2:conditionExpression xsi:type='
                                                           '"bpmn2:tFormalExpression">')
                        if fp.get('expressionType') not in ('XML', 'NonXML'):
                            self.add('ERROR', f.get('id'), 'route expressionType must be XML or NonXML (property key '
                                                           '"expressionType", not "conditionType")')
                        if ce is not None and fp.get('expressionType') == 'XML' and '${' in (ce.text or ''):
                            self.add('WARN', f.get('id'), 'route uses ${...} expression but expressionType=XML (use NonXML)')
            if cname in ('Multicast', 'SequentialMulticast') and len(out.get(nid, [])) < 2:
                self.add('WARN', nid, 'multicast with fewer than 2 branches')
            if cname == 'Join':
                if len(inc.get(nid, [])) < 2 or len(out.get(nid, [])) != 1:
                    self.add('WARN', nid, 'Join should have multiple incoming branches and one outgoing branch')
            if cname == 'Gather':
                prev = [ids.get(f.get('sourceRef')) for f in inc.get(nid, [])]
                for pv in prev:
                    if pv is not None and parse_uri(props(pv).get('cmdVariantUri', '')).get('cname') == 'PKCS#7/CMS Signature-Content Splitter':
                        self.add('ERROR', nid, 'Gather not supported with splitter of type PKCS')
            if cname in ('GroovyScript', 'JavaScript') and self.res is not None:
                s = p.get('script', '')
                if not p.get('scriptBundleId') and ('script/' + s) not in self.res:
                    self.add('ERROR', nid, 'script %r not found in src/main/resources/script/' % s)
            if cname in ('XSLTMapping', 'MessageMapping', 'OperationMapping') and self.res is not None and p.get('mappingSource', 'mappingSrcIflow') == 'mappingSrcIflow':
                mp = p.get('mappingpath', '')
                ext = {'XSLTMapping': '.xsl', 'MessageMapping': '.mmap', 'OperationMapping': '.opmap'}[cname]
                rel = mp.replace('src/main/resources/', '') + ext
                if mp and rel not in self.res and not p.get('messageMappingBundleId'):
                    self.add('ERROR', nid, 'mapping file %r not found (tenant: "Mapping file ... not found")' % rel)
        # ---- container rules ----
        if top and not is_sub:
            if is_local:
                bad = [n.get('id') for n, cn in starts if cn != 'StartEvent']
                if bad:
                    self.add('ERROR', pid, 'Local Integration Process must start with a plain Start Event (got %s)' % bad)
                if meaningful == 0 and not any(cn == 'ErrorEndEvent' for n, cn in ends):
                    self.add('ERROR', 'Participant_' + pid if ('Participant_' + pid) in ids else pid,
                             'Local Integration Process cannot have an empty sequence (a Content Modifier with no header/'
                             'property/body counts as empty)')
            else:
                if len(starts) != 1:
                    self.add('ERROR', pid, 'Integration Process must have exactly one start event (has %d)' % len(starts))
                for n, cn in starts:
                    if cn == 'StartEvent':
                        self.add('ERROR', n.get('id'), 'Integration Process cannot use a plain Start Event (use Message Start or '
                                                       'Timer Start)')
                    if cn == 'MessageStartEvent' and not mf_by_node.get(n.get('id')):
                        self.add('WARN', n.get('id'), 'Start event should have an incoming message flow (sender adapter)')
                if has_aggregator:
                    pp = props(processes[pid])
                    if pp.get('transactionalHandling') != 'Required':
                        self.add('ERROR', pid, 'process with Aggregator needs transactionalHandling=Required (JDBC)')
        if is_sub and not starts:
            self.add('ERROR', cont.get('id'), 'subprocess without start event')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--resources', help='directory equivalent to src/main/resources (for .iflw input)')
    ap.add_argument('--catalog', default=os.path.join(HERE, '..', 'catalog', 'components.json'))
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    cat = json.load(open(a.catalog, encoding='utf-8'))
    res, params, xml = None, None, None
    if a.path.lower().endswith('.zip'):
        z = zipfile.ZipFile(a.path)
        names = z.namelist()
        iflws = [n for n in names if n.endswith('.iflw')]
        if len(iflws) != 1:
            raise SystemExit('zip must contain exactly one .iflw (found %d)' % len(iflws))
        xml = z.read(iflws[0]).decode('utf-8')
        res = {n[len('src/main/resources/'):] for n in names if n.startswith('src/main/resources/')}
        params = {}
        if 'src/main/resources/parameters.prop' in names:
            for line in z.read('src/main/resources/parameters.prop').decode('utf-8').splitlines():
                if '=' in line and not line.startswith('#'):
                    params[line.split('=', 1)[0].strip()] = line.split('=', 1)[1]
        for req in ('META-INF/MANIFEST.MF', '.project', 'metainfo.prop'):
            if req not in names:
                print('ERROR  -  zip lacks %s' % req)
    else:
        xml = open(a.path, encoding='utf-8').read()
        if a.resources:
            res = set()
            for r, _, fs in os.walk(a.resources):
                for f in fs:
                    res.add(os.path.relpath(os.path.join(r, f), a.resources).replace(os.sep, '/'))
            pp = os.path.join(a.resources, 'parameters.prop')
            params = {}
            if os.path.exists(pp):
                for line in open(pp, encoding='utf-8'):
                    if '=' in line and not line.startswith('#'):
                        params[line.split('=', 1)[0].strip()] = line.split('=', 1)[1]
    v = V(cat, res, params)
    findings = v.run(xml)
    order = {'FATAL': 0, 'ERROR': 1, 'WARN': 2}
    findings.sort(key=lambda f: (order.get(f[0], 3), f[1]))
    if a.json:
        print(json.dumps([{'severity': s, 'element': e, 'message': m} for s, e, m in findings], indent=1))
    else:
        for s, e, m in findings:
            print('%-5s  %-28s %s' % (s, e, m))
        n = {k: sum(1 for f in findings if f[0] == k) for k in order}
        print('\nSummary: %d fatal, %d error, %d warn' % (n['FATAL'], n['ERROR'], n['WARN']))
    sys.exit(2 if any(f[0] in ('FATAL', 'ERROR') for f in findings) else 0)


if __name__ == '__main__':
    main()
