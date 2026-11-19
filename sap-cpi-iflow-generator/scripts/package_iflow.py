#!/usr/bin/env python3
"""Package an iFlow (.iflw + resources) into an importable SAP Cloud Integration zip.

Usage:
  python package_iflow.py --iflw path/to/Flow.iflw --id my.bundle.id --name "My Flow" \
      [--version 1.0.0] [--resources dir] [--description "..."] --out MyFlow.zip

--resources: directory whose content is copied under src/main/resources/
             (e.g. script/x.groovy, mapping/y.xsl, mapping/z.mmap, xsd/a.xsd, wsdl/b.wsdl, json/...).
The .iflw is placed at src/main/resources/scenarioflows/integrationflow/<iflw basename>.
"""
import argparse, os, zipfile, time

IMPORT_PACKAGE = ("com.sap.esb.application.services.cxf.interceptor,com.sap.esb.security,com.sap.it.op.agent.api,"
    "com.sap.it.op.agent.collector.camel,com.sap.it.op.agent.collector.cxf,com.sap.it.op.agent.mpl,javax.jms,javax.jws,"
    "javax.wsdl,javax.xml.bind.annotation,javax.xml.namespace,javax.xml.ws,org.apache.camel,org.apache.camel.builder,"
    "org.apache.camel.component.cxf,org.apache.camel.model,org.apache.camel.processor,org.apache.camel.processor.aggregate,"
    "org.apache.camel.spring.spi,org.apache.commons.logging,org.apache.cxf.binding,org.apache.cxf.binding.soap,"
    "org.apache.cxf.binding.soap.spring,org.apache.cxf.bus,org.apache.cxf.bus.resource,org.apache.cxf.bus.spring,"
    "org.apache.cxf.buslifecycle,org.apache.cxf.catalog,org.apache.cxf.configuration.jsse,org.apache.cxf.configuration.spring,"
    "org.apache.cxf.endpoint,org.apache.cxf.headers,org.apache.cxf.interceptor,org.apache.cxf.management.counters,"
    "org.apache.cxf.message,org.apache.cxf.phase,org.apache.cxf.resource,org.apache.cxf.service.factory,"
    "org.apache.cxf.service.model,org.apache.cxf.transport,org.apache.cxf.transport.common.gzip,org.apache.cxf.transport.http,"
    "org.apache.cxf.transport.http.policy,org.apache.cxf.workqueue,org.apache.cxf.ws.rm.persistence,org.apache.cxf.wsdl11,"
    "org.osgi.framework,org.slf4j,org.springframework.beans.factory.config,com.sap.esb.camel.security.cms,org.apache.camel.spi,"
    "com.sap.esb.webservice.audit.log,com.sap.esb.camel.endpoint.configurator.api,com.sap.esb.camel.jdbc.idempotency.reorg,"
    "javax.sql,org.apache.camel.processor.idempotent.jdbc,org.osgi.service.blueprint")

def manifest_line(key, value):
    """MANIFEST.MF lines are max 72 bytes; continuation lines start with one space."""
    raw = (key + ': ' + value).encode('utf-8')
    out, first = [], True
    while raw:
        n = 72 if first else 71
        out.append((b'' if first else b' ') + raw[:n]); raw = raw[n:]; first = False
    return b'\r\n'.join(out) + b'\r\n'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iflw', required=True); ap.add_argument('--id', required=True)
    ap.add_argument('--name', required=True); ap.add_argument('--version', default='1.0.0')
    ap.add_argument('--resources'); ap.add_argument('--description', default='')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if any(c in a.id for c in ' /\\:*?"<>|'):
        raise SystemExit('Bundle ID must not contain spaces or path characters: %r' % a.id)
    mf = b''.join([manifest_line('Manifest-Version', '1.0'), manifest_line('Bundle-ManifestVersion', '2'),
        manifest_line('Bundle-Name', a.name), manifest_line('Bundle-SymbolicName', a.id + '; singleton:=true'),
        manifest_line('Bundle-Version', a.version), manifest_line('SAP-BundleType', 'IntegrationFlow'),
        manifest_line('SAP-NodeType', 'IFLMAP'), manifest_line('SAP-RuntimeProfile', 'iflmap'),
        manifest_line('Import-Package', IMPORT_PACKAGE), manifest_line('Origin-Bundle-Name', a.name),
        manifest_line('Origin-Bundle-SymbolicName', a.id)]) + b'\r\n'
    project = ('<?xml version="1.0" encoding="UTF-8"?><projectDescription>\n   <name>%s</name>\n   <comment/>\n   <projects/>\n'
        '   <buildSpec>\n      <buildCommand>\n         <name>org.eclipse.jdt.core.javabuilder</name>\n         <arguments/>\n'
        '      </buildCommand>\n   </buildSpec>\n   <natures>\n      <nature>org.eclipse.jdt.core.javanature</nature>\n'
        '      <nature>com.sap.ide.ifl.project.support.project.nature</nature>\n      <nature>com.sap.ide.ifl.bsn</nature>\n'
        '   </natures>\n</projectDescription>') % a.id
    stamp = time.strftime('%a %b %d %H:%M:%S UTC %Y', time.gmtime())
    # java.util.Properties style: non-ASCII as \uXXXX
    desc = ''.join(c if ord(c) < 128 else '\\u%04X' % ord(c) for c in a.description)
    with zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('META-INF/MANIFEST.MF', mf)
        z.writestr('.project', project)
        z.writestr('metainfo.prop', '#Store metainfo properties\n#%s\ndescription=%s\n' % (stamp, desc))
        has = lambda f: bool(a.resources) and os.path.isfile(os.path.join(a.resources, f))
        if not has('parameters.prop'):
            z.writestr('src/main/resources/parameters.prop', '#%s\n' % stamp)
        if not has('parameters.propdef'):
            z.writestr('src/main/resources/parameters.propdef',
                       '<?xml version="1.0" encoding="UTF-8" standalone="no"?><parameters><param_references/></parameters>')
        z.write(a.iflw, 'src/main/resources/scenarioflows/integrationflow/' + os.path.basename(a.iflw))
        if a.resources:
            for root, _, files in os.walk(a.resources):
                for f in files:
                    p = os.path.join(root, f)
                    rel = os.path.relpath(p, a.resources).replace(os.sep, '/')
                    z.write(p, 'src/main/resources/' + rel)
    print('written', a.out)

if __name__ == '__main__':
    main()
