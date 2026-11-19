# Serialization rules (the non-obvious encodings)

The tenant metadata (`/api/1.0/metadata/<hash>`) describes each component as UI rows. **Row key = XML property
key** for almost everything (checked against 24 real iFlows + lab iFlows). The exceptions and extra keys are listed
here. When in doubt, copy what the editor writes (the catalog `sample` field points to a canonical example).

## 1. Which keys an element carries

| Group | Keys | Where they come from |
|---|---|---|
| Identity (fixed per component) | `activityType`, `subActivityType`, `encoderType` (also on Decoders), `splitType`, `operation` (Data Store), `mappingType` (Message/Operation Mapping), `processType` (local process) | catalog `identity` |
| Version | `componentVersion` (= major.minor of the URI version), `cmdVariantUri` | catalog `cmdVariantUri` / `componentVersion` |
| Configuration | every `properties[].key` of the catalog entry, default when not set | catalog `properties` |
| Derived (value depends on other config) | XSLT: `mappinguri`, `mappingname`; Message Mapping: `mappinguri`, `mappingname`; Looping Process Call: `loopId`; Timer: `scheduleKey`; Write Variables: `visibility`, `encrypt`, `expire` | §5-§9 |
| Adapter identity | `ComponentType`, `Description`, `ComponentNS`, `Name`, `TransportProtocolVersion`, `ComponentSWCVName`=external, `system`, `TransportProtocol`, `MessageProtocol`, `MessageProtocolVersion`, `ComponentSWCVId`, `direction` (+`Vendor`=SAP for vendor::SAP adapters) | §10 |
| UI-only (never write) | collaboration: `name`, `bundleId`, `Description`, `productProfiles`; Looping Process Call: `expressionValue`, `loopMaximum` (they go into `standardLoopCharacteristics`); Router: `conditionTable`; route: `conditionType`, `conditionValue`, `defaultBranch` (see §3) | catalog `uiOnlyKeys` |

What the tenant does with deviations (lab T2):
- unknown key ⇒ **accepted silently and ignored** (the step runs with its default) — always a bug;
- missing `componentVersion` ⇒ tolerated; missing `cmdVariantUri` ⇒ tolerated (rebuilt, maybe to an old version);
- missing/wrong `activityType` ⇒ error "This component ... is not supported in Cloud Integration profile";
- version above the tenant's ⇒ same error; older real version ⇒ accepted.
The generator writes everything; when hand-editing write everything too.

## 2. Boolean and enum spelling

Use exactly the catalog spelling. Booleans are **not uniform**: most steps use `true`/`false`, many adapters use
`1`/`0` (`xsrfProtection`, `KeepConnectionAlive`, `sftpSecEnabled`...). Look at the property `default`.
Enum values are keys, not labels (`bodyType=expression`, `senderAuthType=RoleBased`, `transactionalHandling=Not Required`).
Some enums contain spaces (`Non XML` in Looping Process Call vs `NonXML` in Router routes!).

## 3. Router (Exclusive Gateway) and routes

```xml
<bpmn2:exclusiveGateway default="SequenceFlow_4" id="ExclusiveGateway_1" name="Kind?">
  ... activityType=ExclusiveGateway, throwException=false, conditionTable (empty), componentVersion 1.2, cmdVariantUri ...
  <bpmn2:incoming>SequenceFlow_2</bpmn2:incoming>
  <bpmn2:outgoing>SequenceFlow_3</bpmn2:outgoing>
  <bpmn2:outgoing>SequenceFlow_4</bpmn2:outgoing>
</bpmn2:exclusiveGateway>
<bpmn2:sequenceFlow id="SequenceFlow_3" name="A" sourceRef="ExclusiveGateway_1" targetRef="CallActivity_2">
  <bpmn2:extensionElements>
    <ifl:property><key>expressionType</key><value>NonXML</value></ifl:property>   <!-- XML (XPath) | NonXML (Camel simple) -->
  </bpmn2:extensionElements>
  <bpmn2:conditionExpression id="FormalExpression_SequenceFlow_3" xsi:type="bpmn2:tFormalExpression">${header.Kind} = 'A'</bpmn2:conditionExpression>
</bpmn2:sequenceFlow>
<bpmn2:sequenceFlow id="SequenceFlow_4" name="Other" sourceRef="ExclusiveGateway_1" targetRef="ServiceTask_1">
  <bpmn2:extensionElements>
    <ifl:property><key>expressionType</key><value>NonXML</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:sequenceFlow>   <!-- default route: no conditionExpression; it is the gateway's default="" -->
```
`throwException` is the router-level "Throw Exception" flag (default false; its runtime semantics were not
exercised in the lab). XML conditions are XPath (`/root/kind = 'A'`), NonXML are Camel simple (`${header.X} = 'A'`, `${property.p} > 3`).
The XML text is escaped (`&lt;`, `&gt;`, `&amp;`).

## 4. Multicast / Join / Gather / Splitter

- Multicast, Sequential Multicast and Join are `parallelGateway` with `subActivityType=parallel`.
- Branches are plain sequence flows from the multicast; the editor names them `Branch 1`, `Branch 2`...
- Sequential Multicast order: `routingSequenceTable` rows `<row><cell id='branchName'>Branch 1</cell></row>`.
- Every multicast branch should end in the same Join (tenant warning "All multicast branches do not meet at the
  join"), and Join → Gather is the normal pattern. Join needs ≥2 incoming and exactly 1 outgoing.
- Splitters (`GeneralSplitter`, `Camel` = Iterating, `ZipSplitter`, `TarSplitter`, `IDoc`, `EDISplitter`,
  `PKCS#7/CMS Signature-Content Splitter`) are `callActivity` with `activityType=Splitter` and
  `splitType=<cname>`. General/Iterating need `splitExprValue` (XPath) when `exprType=XPath`, or `tokenValue`
  when `exprType=Token`. The CSV↔XML converters reject XPaths starting with `//` ("'//' of xPath is not
  supported"); use absolute paths (`/root/item`).
- Gather after a PKCS#7 splitter is illegal ("Gather not supported with splitter of type PKCS").

## 5. Process calls

```xml
<bpmn2:callActivity id="CallActivity_3" name="Call local">
  ... processId=Process_2, activityType=ProcessCallElement, subActivityType=NonLoopingProcess,
      componentVersion 1.0, cmdVariantUri ...NonLoopingProcess/version::1.0.4
</bpmn2:callActivity>
<bpmn2:callActivity id="CallActivity_30" name="Compile data">
  <bpmn2:extensionElements>
    processId=Process_33, expressionType=Non XML (XML|Non XML), postProcessing=end (end|throwException),
    loopId=StandardLoopCharacteristics_CallActivity_30, activityType=ProcessCallElement,
    subActivityType=LoopingProcess, componentVersion 1.3, cmdVariantUri ...LoopingProcess/version::1.3.0
  </bpmn2:extensionElements>
  <bpmn2:incoming>..</bpmn2:incoming><bpmn2:outgoing>..</bpmn2:outgoing>
  <bpmn2:standardLoopCharacteristics id="StandardLoopCharacteristics_CallActivity_30" loopMaximum="100">
    <bpmn2:loopCondition id="FormalExpression_CallActivity_30" xsi:type="bpmn2:tFormalExpression">${property.CamelLoopIndex} &lt; ${property.MaxIter}</bpmn2:loopCondition>
  </bpmn2:standardLoopCharacteristics>
</bpmn2:callActivity>
```
`loopId` must equal the `standardLoopCharacteristics` id. Idempotent Process Call: `activityType=IdempotentProcessCall`,
`processId`, `sourceMessageID` (expression, mandatory), `skipOnDuplicate`. All three must point to a **Local
Integration Process** (`processType=directCall`).

## 6. Mappings and scripts

| Step | Properties |
|---|---|
| Groovy / JavaScript | `script`=file name in `src/main/resources/script/` (e.g. `t6.groovy`), `scriptFunction` (empty = processData), `scriptBundleId` (Script Collection id; then the file is not in the zip) |
| XSLT | `mappingSource`=mappingSrcIflow, `mappingpath`=`src/main/resources/mapping/<Name>` (no extension), `mappinguri`=`dir://mapping/xslt/src/main/resources/mapping/<Name>.xsl`, `mappingname`=`<Name>`, `mappingoutputformat`=Bytes, `mappingHeaderNameKey` (only for mappingSrcHeader) |
| Message Mapping | `mappingType`=MessageMapping, `mappingReference`=static, `mappingpath`=`src/main/resources/mapping/<Name>`, `mappinguri`=`dir://mmap/src/main/resources/mapping/<Name>.mmap`, `mappingname`, `messageMappingBundleId` (set when the mapping is a separate package artifact), `mappingSourceValue` (dynamic) |

A missing mapping file gives "Mapping file '<Name>' not found". `.mmap` files are binary-ish XML produced by the
mapping editor: do not hand-write them; reference an existing one or use XSLT/Groovy.

## 7. Tables

Table properties are an escaped list of rows: `<row><cell id='Col'>value</cell>...</row>` (inside `<value>` the `<`
become `&lt;`). Column ids = catalog `columns[].key`. Content Modifier (`headerTable`, `propertyTable`) rows:
`Action` (Create|Delete), `Type` (constant|header|xpath|expression|property|persisted variables|global persisted
variables|numberRange), `Value`, `Default`, `Name`, `Datatype` (java class, used with xpath/expression).
**Write Variables (`variable`) is positional**, without ids, cells in this order: name, datatype, type, value,
scope (local|global) — observed in a tenant sample; prefer generating it with `iflowgen.py`.

## 8. Timer Start (`intermediatetimer` 1.4.0)
`scheduleKey` holds the scheduler as escaped rows of `<row><cell>key</cell><cell>value</cell></row>`; it may also
be an externalized `{{Timer}}`. Example (run once, from a tenant sample, unescaped):
```
<row><cell>dateType</cell><cell>SIMPLE</cell></row><row><cell>hourValue</cell><cell>11</cell></row>
<row><cell>minutesValue</cell><cell>33</cell></row><row><cell>timeType</cell><cell>ON_TIME</cell></row>
<row><cell>timeZone</cell><cell>( UTC 0:00 ) Greenwich Mean Time(Etc/GMT)</cell></row>
<row><cell>throwExceptionOnExpiry</cell><cell>true</cell></row><row><cell>second</cell><cell>0</cell></row>
<row><cell>minute</cell><cell>0/5</cell></row><row><cell>hour</cell><cell>*</cell></row>
<row><cell>day_of_month</cell><cell>?</cell></row><row><cell>month</cell><cell>*</cell></row>
<row><cell>dayOfWeek</cell><cell>*</cell></row><row><cell>year</cell><cell>*</cell></row>
<row><cell>startAt</cell><cell></cell></row><row><cell>endAt</cell><cell></cell></row>
<row><cell>attributeBehaviour</cell><cell>isThrowExceptionOnExpiryVisible,...</cell></row>
<row><cell>triggerType</cell><cell>cron</cell></row><row><cell>noOfSchedules</cell><cell>1</cell></row>
<row><cell>schedule1</cell><cell>simple.repeat=NONE&amp;trigger.timeZone=Etc/GMT</cell></row>
```
Timer schedules are easy to get subtly wrong: prefer externalizing (`{{Timer}}`) and configuring in the tenant,
or copy a schedule written by the editor. A timer-started process has no sender message flow.

## 9. Externalized parameters
Any property value (or table cell) may be `{{Name}}`; the name must exist in `parameters.prop` (value) and in
`parameters.propdef` (definition). Partial use is allowed (`/path/{{Folder}}/in`). The tenant does not report an
undefined parameter at design time (lab T2 M12) — the validator does.

## 10. Adapters
- `cmdVariantUri` = `ctype::AdapterVariant/cname::<ns:Name>[/vendor::SAP]/tp::<TP>/mp::<MP>/direction::<Sender|Receiver>/version::<v>`.
- `ComponentType` = cname without namespace (`HTTPS`, `HCIOData`, `PollingSFTP`, `ProcessDirect`);
  `ComponentNS`=sap; `TransportProtocol`/`MessageProtocol` copy tp/mp; the three `*Version`/`ComponentSWCVId` =
  full version; `componentVersion` = major.minor; `Name` = the messageFlow `name`; `system` = name of the sender or
  receiver participant; `direction` = Sender|Receiver; `Description` = free text.
- Then every catalog property of that adapter variant (defaults included).

## 11. Events
See iflw-anatomy.md §Events. Summary: Message Start/End, plain Start/End and Terminate carry their properties
on the event; Error Start, Error End, Escalation End and Timer Start carry them on the `*EventDefinition` child
and the event has no `extensionElements`. Escalation End: `ErrorCode` property.

## 12. IDs and names
Ids must be unique across the whole file (participants, processes, flows, event definitions with ids, loop
characteristics, formal expressions). Names are free text (shown in the editor and monitoring) and do not need to
be unique. The tenant does not depend on id prefixes (lab T4), but keep SAP's style.
