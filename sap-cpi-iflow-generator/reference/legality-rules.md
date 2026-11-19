# Legality rules: valid XML that the tenant rejects (or silently misreads)

Three layers decide whether an iFlow is legal:
1. **Model build** (opening the iFlow): the server converts .iflw → editor model. Failure = HTTP 500, nothing opens.
2. **Design-time validation** (`validationResultModel` returned with the model; same list the editor shows as red
   markers): errors set `isDeployRestricted=true` and the Deploy action is refused.
3. **Deployment/runtime** (bundle build + start): not observable at design time; verified only for the lab T6
   iFlow (deployed, STARTED, undeployed).

`scripts/validate_iflw.py` implements every rule below (codes = severity it reports).

## A. Fatal (HTTP 500 on open)

| Cause | Lab |
|---|---|
| A flow node / participant / subProcess without `bpmndi:BPMNShape` | T2 M9 |
| Not well-formed XML, wrong root/namespace, duplicate ids, dangling `sourceRef`/`targetRef`/`processRef` (validator treats as FATAL; never send these) | - |

## B. Rejected by design-time validation (blocks deploy)

| Rule | Tenant message (verbatim) | Lab |
|---|---|---|
| `activityType` wrong or missing | `This component Enrichr with version 1.6 is not supported in Cloud Integration profile.` / `This component ctype::FlowstepVariant/version::1.6 ...` | T2 M1, M6 |
| Version higher than the tenant's | `This component Enricher with version 9.9 is not supported ...` | T2 M2 |
| Invalid enum value | `Invalid value 'banana' entered in 'Type' field` | T2 M5 |
| Invalid table cell / empty mandatory cell | `Invalid value 'wrongtype' entered in 'Source Type' field in 'Headers' table`, `Header name not defined in row 1 for Content Modifier step` | T2 M11 |
| UI-only key written on the collaboration | `Invalid value 'iflmap' entered in 'Runtime Profile' field` | T1 |
| Local process without `processType=directCall` (parsed as main process) | `Invalid value 'From Calling Process' entered in 'Transaction Handling' field` | T3 Pf |
| Local process whose only step(s) do nothing (Content Modifier with no header, property or body) | `Local Integration Process cannot have an empty sequence` (on `Participant_<process>`) | T3/T4/T5 |
| Mandatory field empty (only when visible per its condition) | `Attribute 'X' is mandatory`, `Mandatory property 'X' not set`, `'Data Store Name' cannot be empty`, `XPath is not defined for Splitter step`, `Token is not defined for Splitter step`, `Enter an address in XI Receiver` ... | T1 |
| Table with at least one required row is empty | `The table 'Schemas' has a constraint that it should contain at least one row but no row is configured.` | T1 |
| Field regex/format | `Only the following characters are allowed: ...` (SFTP username), `StepID should use only characters (aA-zZ, 0-9) without any whitespaces` (Persist) | T1 |
| XPath with `//` in CSV↔XML converters | `"//" of xPath is not supported` | lab01, T1 |
| Aggregator in a process without transaction | `The process requires a transaction because aggregator is used. Set transaction handling to Required for JDBC.` | lab01, T1 |
| Gather after a PKCS#7 splitter | `Gather not supported with splitter of type PKCS` | T1 |
| Content Enricher with HTTP (or other) adapter | `Content Enricher supports SuccessFactors, Soap1.x, and OData adapter types` | T2 |
| Content Enricher / Poll Enrich without inbound message flow (or flow in the wrong direction) | `Content Enricher 1 does not have incoming connector from external system`, `Poll Enrich does not have incoming connector from external system` | lab01, T1 |
| Poll Enrich wired to a receiver-direction adapter | `Poll file must have incoming connector from sender system only`, `SFTP Sender doesn't support the Trigger Option null`, `Timer is not configured. Please set a schedule` | T2 |
| Mapping/script resource missing | `Mapping file 'XSLTMapping1' not found` | T0 |
| Security steps without key aliases | `Private Key Alias not specified for Signer step`, `Public Key Alias not specified for Verifier step`, `No Encryptor Key User ID specified`, `Receiver Public Key Alias not specified for Content Encryptor step` | T1 |
| Content Enricher / Request Reply / step without outgoing sequence flow | `Content Enricher 1 does not have an outgoing sequence flow` | lab01 |

## C. Accepted silently — the dangerous ones ("valid but illegal")

| Deviation | What the tenant does | Lab | Validator |
|---|---|---|---|
| Unknown / misspelled property key | Ignores it: the step runs with the default value of the key you meant | T2 M4 | ERROR |
| `{{param}}` not defined in parameters.prop/.propdef | No design-time error; breaks configuration/deploy | T2 M12 | ERROR |
| `cmdVariantUri` missing | Rebuilt from activityType/componentVersion (version may not be what you expect) | T2 M8 | ERROR |
| `componentVersion` missing | Tolerated | T2 M7 | WARN |
| `<incoming>/<outgoing>` children missing or wrong | Rebuilt from the sequence flows | T2 M10 | WARN |
| Older component version | Accepted; newer properties simply absent | T2 M3 | WARN |
| Disconnected steps (no incoming/outgoing flow) | Mostly not reported (only some step types are) — dead code | lab01 | ERROR |
| Missing `BPMNEdge` | Tolerated | - | WARN |

## D. Structural / semantic rules (write them right the first time)

Processes
- Main Integration Process: exactly one start event: Message Start (target of a sender adapter) or Timer Start.
  No plain Start Event. Ends with Message End, Terminate, Error End or Escalation End.
- Local Integration Process: `processType=directCall`; starts with a plain Start Event, ends with a plain End
  Event (or Error/Escalation End); `transactionalHandling` ∈ {From Calling Process, Required, Required JMS};
  must contain at least one effective step.
- Exception Subprocess: inside a process; starts with Error Start; ends with Message End / Error End /
  Escalation End; no flows in or out.
- Process Call / Looping Process Call / Idempotent Process Call: `processId` must be a Local Integration Process.
  Looping: `standardLoopCharacteristics` with `loopMaximum` + `loopCondition`; `loopId` = its id.
- Process with Aggregator: `transactionalHandling=Required`.

Flow
- Every non-start node has ≥1 incoming, every non-end node ≥1 outgoing sequence flow; flows never cross
  container boundaries (process ↔ subprocess ↔ other process).
- Router: ≥2 outgoing; exactly one default route via the gateway `default` attribute; every other route has a
  `conditionExpression` and `expressionType` XML|NonXML matching the expression language.
- Multicast branches converge in one Join; Join has ≥2 incoming and 1 outgoing; Gather follows Join or a splitter
  (not a PKCS#7 splitter).
- Request Reply and Send: exactly one receiver message flow each.

Adapters / message flows: see adapters.md. In short: sender adapters only from EndpointSender participants into
a Message Start Event (or a Poll Enrich step); receiver adapters only from Request Reply, Send or a Message End
Event into an EndpointRecevier participant; Content Enricher / Poll Enrich receive the flow from the participant.

Content-type warnings (W, do not block deploy but are real smells): `Content Modifier may not pass XML message to
XSLT Mapping. XSLT Mapping supports XML input only.` The tenant reasons about the payload type step by step
(XML / non-XML / binary). After Base64/ZIP/GZIP/encryption steps the payload is binary; after a JSON converter it
is not XML; follow conversions accordingly.

## E. Mapping tenant messages to fixes

| Message contains | Fix |
|---|---|
| `is not supported in Cloud Integration profile` | identity keys or version wrong → copy from catalog |
| `Invalid value '...' entered in '...' field` | enum value: use catalog `values` (keys, not labels) |
| `cannot have an empty sequence` | the local process needs an effective step (add a real header/property/body or another step) |
| `does not have incoming connector from external system` | missing message flow or wrong direction (participant → step) |
| `must have incoming connector from sender system only` | Poll Enrich needs a sender-direction polling adapter |
| `requires a transaction because aggregator` | set `transactionalHandling=Required` on that process |
| `Mapping file ... not found` | add the file under `src/main/resources/mapping/` with the `mappingpath` name |
| HTTP 500 when opening | missing BPMNShape or broken references |
