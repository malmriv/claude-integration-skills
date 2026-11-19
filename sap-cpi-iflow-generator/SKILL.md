---
name: sap-cpi-iflow-generator
description: Generate, modify, repair or review SAP Cloud Integration (CPI / Integration Suite) iFlows as code - the .iflw BPMN2 XML and the importable zip - without the web editor. Use it whenever the task is to write or change an .iflw, add/remove/rewire steps (Content Modifier, Script, mappings, Router, Splitter, Gather, Join, Multicast, Request Reply, Send, Poll/Content Enricher, Data Store, converters, security steps), events (start/end/error/escalation/terminate/timer), processes (Local Integration Process, Process Call, Looping/Idempotent Process Call, Exception Subprocess) or adapters (HTTPS, HTTP, SOAP, OData, SFTP, JMS, ProcessDirect, Mail, IDoc, XI, AMQP, JDBC...), or to package and validate an iFlow before upload. Also use it to explain why an uploaded iFlow fails to open, shows errors or cannot be deployed. It carries the tenant's real component catalog (property keys, defaults, allowed values, conditions, versions) and the rules observed on a live tenant, so the generated XML is not only well-formed but legal.
---

# SAP CPI iFlow generator

The `.iflw` is BPMN 2.0 XML plus SAP `ifl:property` key/value extensions. Being well-formed XML is the easy
part. Most of what breaks an iFlow is **legal-looking XML the tenant interprets differently**: unknown property keys
are silently dropped, a missing `BPMNShape` makes the iFlow impossible to open, a Content Modifier with no action
makes a local process "empty", a missing `processType` turns a local process into a main process, and so on.
Everything in this skill was harvested from, and tested against, a live tenant (see `reference/lab-log.md`).

## Golden rules (read before writing any XML)

1. **Never invent a component, property key or value.** Every step/adapter/event comes from
   `catalog/components.json` (keys = tenant metadata keys = XML keys). If something is not in the catalog, say so;
   do not guess. Unknown keys are accepted by the tenant **and ignored**, so the step silently runs with defaults.
2. **Write every property the editor writes**: identity keys + all catalog properties (default when not set) +
   `componentVersion` + `cmdVariantUri`. Never write `uiOnlyKeys` (e.g. `productProfiles`, `bundleId` on the
   collaboration).
3. **Use the tenant's current version** (`version` in the catalog). Older versions are accepted (with fewer
   properties); versions above the tenant's make the step "not supported".
4. **Every flow node, participant and subprocess needs a `bpmndi:BPMNShape`**: without one, the editor model
   cannot be built (HTTP 500) and nobody can open the iFlow. Give every sequence/message flow a `BPMNEdge`.
5. **Identity keys decide what a step *is*.** A wrong or missing `activityType` makes the step "not supported";
   a local process without `processType=directCall` is treated as a main Integration Process.
6. **Events keep their properties on the event definition** for Error Start/End, Escalation End and Timer Start;
   Message Start/End and Terminate keep them on the event itself (see `reference/serialization-rules.md`).
7. **Router routes are special**: the default route is the gateway's `default="SequenceFlow_x"` attribute;
   the other routes need `<bpmn2:conditionExpression xsi:type="bpmn2:tFormalExpression">` plus the
   `expressionType` (`XML`|`NonXML`) property. The metadata names `conditionType/conditionValue/defaultBranch`
   are **not** XML keys.
8. **Message-flow direction is semantic**: sender adapters go Participant(EndpointSender) → Message Start Event;
   receiver adapters go Request Reply/Send/Message End Event → Participant(EndpointRecevier); Poll Enrich and
   Content Enricher receive the flow **from** the participant. Content Enricher accepts only OData, SOAP 1.x or
   SuccessFactors; Poll Enrich needs a *sender*-direction polling adapter (e.g. `sap:PollingSFTP`).
9. **Every `{{param}}` must exist in `parameters.prop` and `parameters.propdef`**; the tenant does not complain
   at design time.
10. **Every referenced resource must be in the zip** (`script/x.groovy`, `mapping/y.xsl|.mmap`, `xsd/`, `wsdl/`).
11. Keep SAP-style ids (`StartEvent_1`, `CallActivity_3`, `ServiceTask_2`, `ExclusiveGateway_1`,
    `ParallelGateway_4`, `EndEvent_2`, `SequenceFlow_7`, `MessageFlow_5`, `Participant_1`, `Process_1`,
    `Participant_Process_1`, `SubProcess_1`). The tenant does not require them, but humans and diff tools expect them.
12. **Validate before you hand anything over**: `scripts/validate_iflw.py` (static), then, when a tenant is
    reachable, the tenant validation loop (`reference/tenant-validation.md`). A clean static run is necessary,
    not sufficient.

## Workflow

**A. New iFlow (preferred path: spec → generator)**
1. Write a JSON flow spec (format in the docstring of `scripts/iflowgen.py`; examples in `examples/good/`).
   Choose step `type`s from `reference/components-index.md`; look up property keys/allowed values in
   `catalog/components.json` (`properties[].key/default/values/mandatory/visibleIf`).
2. `python scripts/iflowgen.py flow.json -o "My Flow.iflw"` (fills all defaults, identities, diagram).
3. Put scripts/mappings in a resources folder (`script/`, `mapping/`, ...).
4. `python scripts/validate_iflw.py "My Flow.iflw" --resources res` → fix every FATAL/ERROR.
5. `python scripts/package_iflow.py --iflw "My Flow.iflw" --id my.bundle.id --name "My Flow" --resources res --out my.zip`
6. `python scripts/validate_iflw.py my.zip` again (checks resources + parameters inside the zip).
7. Import (Add > Integration Flow > Upload) and run the tenant validation loop; deploy only with
   `isDeployRestricted=false`.

**B. Modify an existing iFlow (hand edit)**
1. Unzip; read the `.iflw`; locate elements by id. Keep every property you do not intend to change.
2. For new elements copy the canonical skeleton from `reference/iflw-anatomy.md` and the property list from the
   catalog; add `incoming`/`outgoing` children, the `sequenceFlow`s and the `BPMNShape`/`BPMNEdge`s.
3. When rewiring, update **both** the `sequenceFlow` (`sourceRef/targetRef`) and the `<incoming>/<outgoing>`
   children of both ends; remove orphaned flows and their edges.
4. Validate, repackage (keep the original MANIFEST `Bundle-SymbolicName` and bump `Bundle-Version`), re-validate.

**C. Review / explain errors**: run the validator; map tenant messages with `reference/legality-rules.md`.

## Reference map

| File | Use it for |
|---|---|
| `reference/iflw-anatomy.md` | zip layout, MANIFEST, namespaces, skeletons for every element family, diagram |
| `reference/serialization-rules.md` | the non-obvious encodings (events, router, loops, tables, mappings, timer, params, adapters) |
| `reference/legality-rules.md` | what the tenant rejects, what it silently accepts, structural/semantic rules, tenant messages |
| `reference/adapters.md` | adapter direction rules, which steps accept which adapters, mandatory keys per adapter |
| `reference/components-index.md` | every step/event/process/adapter: key, BPMN tag, identity, tenant version |
| `reference/tenant-validation.md` | upload + server-side validation loop, deploy/undeploy check, refreshing the catalog |
| `reference/lab-log.md` | the experiments behind every rule (T0-T6) |
| `catalog/components.json` | machine catalog (properties, defaults, allowed values, conditions, regex, versions) |

## Catalog freshness

The catalog reflects the palette of the tenant it was harvested from (Avvale test tenant, 2026-11-16). Component
versions move: if a tenant reports "component X with version Y is not supported" or new mandatory fields, refresh
the catalog with `reference/tenant-validation.md` → *Refreshing the catalog*. Groovy code inside Script steps is
out of scope here (use the `sap-cpi-groovy` skill if available).
