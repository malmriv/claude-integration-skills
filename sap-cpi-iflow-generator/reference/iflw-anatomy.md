# iFlow anatomy (.zip and .iflw)

All snippets are copied from iFlows written by the SAP editor or from generated iFlows that the tenant validated
with zero problems and deployed (lab T6). `...` = the remaining catalog properties.

## 1. The importable zip

```
META-INF/MANIFEST.MF                                     OSGi manifest (see below)
.project                                                 Eclipse project, <name> = bundle id
metainfo.prop                                            description=... (java .properties, non-ASCII as \uXXXX)
src/main/resources/parameters.prop                       externalized parameter values (name=value)
src/main/resources/parameters.propdef                    externalized parameter definitions (XML)
src/main/resources/scenarioflows/integrationflow/<Name>.iflw   the BPMN model (exactly one)
src/main/resources/script/*.groovy|*.js                  Script steps (property script = file name only)
src/main/resources/mapping/*.xsl|*.mmap|*.opmap          XSLT / message / operation mappings
src/main/resources/xsd/  wsdl/  json/  edmx/  lib/       schemas, service definitions, archives
```
`scripts/package_iflow.py` writes all of it. MANIFEST essentials (lines wrap at 72 bytes, continuation lines
start with one space, CRLF):
```
Manifest-Version: 1.0
Bundle-ManifestVersion: 2
Bundle-Name: <iFlow name>
Bundle-SymbolicName: <bundle.id>; singleton:=true
Bundle-Version: 1.0.0
SAP-BundleType: IntegrationFlow
SAP-NodeType: IFLMAP
SAP-RuntimeProfile: iflmap
Import-Package: ... (fixed list, copy from package_iflow.py)
Origin-Bundle-Name / Origin-Bundle-SymbolicName
```
The upload dialog reads Name/ID/Description from MANIFEST + metainfo.prop. The bundle id must be unique in the
tenant and contain no spaces. When modifying an existing iFlow keep its `Bundle-SymbolicName`.

`parameters.propdef` (one `<parameter>` per `{{name}}`):
```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?><parameters><parameter>
    <key/>
    <name>S4HANA_Timeout</name>
    <type>xsd:string</type>
    <isRequired>false</isRequired>
    <constraint/>
    <description/>
    <additionalMetadata/>
  </parameter><param_references/></parameters>
```
`parameters.prop`: `S4HANA_Timeout=60000` (escape `:` and `=` as `\:` `\=` as java .properties does).

## 2. .iflw skeleton

```xml
<?xml version="1.0" encoding="UTF-8"?><bpmn2:definitions xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:ifl="http:///com.sap.ifl.model/Ifl.xsd"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="Definitions_1">
  <bpmn2:collaboration id="Collaboration_1" name="Default Collaboration">
     <bpmn2:extensionElements> ...IFlowConfiguration properties... </bpmn2:extensionElements>
     <bpmn2:participant .../>  (senders, receivers, one per process)
     <bpmn2:messageFlow .../>  (one per adapter channel)
  </bpmn2:collaboration>
  <bpmn2:process id="Process_1" ...> main Integration Process </bpmn2:process>
  <bpmn2:process id="Process_2" ...> Local Integration Process(es) </bpmn2:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1" name="Default Collaboration Diagram">
    <bpmndi:BPMNPlane bpmnElement="Collaboration_1" id="BPMNPlane_1"> shapes + edges </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn2:definitions>
```
Note the namespace `http:///com.sap.ifl.model/Ifl.xsd` (three slashes). Every `ifl:property` is
`<ifl:property><key>K</key><value>V</value></ifl:property>`; empty value = `<value/>`.

### Collaboration (iFlow-level configuration, `IFlowConfiguration` 1.2.4)
Properties: `namespaceMapping` (`xmlns:p1=urn:a;xmlns:p2=urn:b`), `httpSessionHandling` (None|...),
`accessControlMaxAge`, `returnExceptionToSender` (false), `log` (All events | ...), `corsEnabled` (false),
`exposedHeaders`, `allowedHeaderList`, `ServerTrace` (false), `allowedOrigins`, `accessControlAllowCredentials`,
`allowedHeaders`, `allowedMethods`, `componentVersion`=1.2, `cmdVariantUri`=`ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.4`.
Never write `name`, `bundleId`, `Description`, `productProfiles` here (UI-only; tenant error
"Invalid value 'iflmap' entered in 'Runtime Profile' field").

### Participants
```xml
<bpmn2:participant id="Participant_1" ifl:type="EndpointSender" name="Sender">
  <bpmn2:extensionElements>
    <ifl:property><key>enableBasicAuthentication</key><value>false</value></ifl:property>
    <ifl:property><key>ifl:type</key><value>EndpointSender</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:participant>
<bpmn2:participant id="Participant_2" ifl:type="EndpointRecevier" name="Backend">   <!-- "Recevier" sic -->
  <bpmn2:extensionElements>
    <ifl:property><key>ifl:type</key><value>EndpointRecevier</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:participant>
<bpmn2:participant id="Participant_Process_1" ifl:type="IntegrationProcess" name="Integration Process" processRef="Process_1">
  <bpmn2:extensionElements/>
</bpmn2:participant>
```
Local processes also use `ifl:type="IntegrationProcess"`; what makes them local is the process's
`cmdVariantUri` + `processType=directCall`.

### Message flow (adapter channel)
```xml
<bpmn2:messageFlow id="MessageFlow_1" name="HTTPS" sourceRef="Participant_1" targetRef="StartEvent_1">
  <bpmn2:extensionElements>
    <ifl:property><key>ComponentType</key><value>HTTPS</value></ifl:property>
    <ifl:property><key>Description</key><value/></ifl:property>
    <ifl:property><key>ComponentNS</key><value>sap</value></ifl:property>
    <ifl:property><key>Name</key><value>HTTPS</value></ifl:property>            <!-- = messageFlow name -->
    <ifl:property><key>TransportProtocolVersion</key><value>1.5.3</value></ifl:property>
    <ifl:property><key>ComponentSWCVName</key><value>external</value></ifl:property>
    <ifl:property><key>system</key><value>Sender</value></ifl:property>        <!-- = participant name -->
    <ifl:property><key>TransportProtocol</key><value>HTTPS</value></ifl:property>
    <ifl:property><key>MessageProtocol</key><value>None</value></ifl:property>
    <ifl:property><key>MessageProtocolVersion</key><value>1.5.3</value></ifl:property>
    <ifl:property><key>ComponentSWCVId</key><value>1.5.3</value></ifl:property>
    <ifl:property><key>direction</key><value>Sender</value></ifl:property>
    ... adapter properties (urlPath, senderAuthType, userRole, clientCertificates, xsrfProtection, maximumBodySize)
    <ifl:property><key>componentVersion</key><value>1.5</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.3</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:messageFlow>
```
Adapters with `vendor::SAP` in the URI (ProcessDirect, JDBC) also carry `<key>Vendor</key><value>SAP</value>`.
Direction rules: `reference/adapters.md`.

### Processes
```xml
<bpmn2:process id="Process_1" name="Integration Process">
  <bpmn2:extensionElements>
    <ifl:property><key>transactionalHandling</key><value>Not Required</value></ifl:property> <!-- Required|Not Required|Required JMS -->
    <ifl:property><key>transactionTimeout</key><value>30</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.2</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.1</value></ifl:property>
  </bpmn2:extensionElements>
  ... flow nodes, subProcesses, then sequenceFlows ...
</bpmn2:process>

<bpmn2:process id="Process_2" name="Local Process">
  <bpmn2:extensionElements>
    <ifl:property><key>processType</key><value>directCall</value></ifl:property>   <!-- mandatory identity -->
    <ifl:property><key>transactionalHandling</key><value>From Calling Process</value></ifl:property> <!-- |Required|Required JMS -->
    <ifl:property><key>transactionTimeout</key><value>30</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowElementVariant/cname::LocalIntegrationProcess/version::1.1.3</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:process>
```

### Flow steps (generic shape)
```xml
<bpmn2:callActivity id="CallActivity_1" name="Set Kind">          <!-- serviceTask for ExternalCall, Send, PollEnrich, contentEnricherWithLookup -->
  <bpmn2:extensionElements>
    <ifl:property><key>activityType</key><value>Enricher</value></ifl:property>   <!-- identity keys first -->
    <ifl:property><key>headerTable</key><value>&lt;row&gt;&lt;cell id='Action'&gt;Create&lt;/cell&gt;...&lt;/row&gt;</value></ifl:property>
    <ifl:property><key>propertyTable</key><value/></ifl:property>
    <ifl:property><key>bodyType</key><value>constant</value></ifl:property>
    <ifl:property><key>wrapContent</key><value/></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.6</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::Enricher/version::1.6.6</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:incoming>SequenceFlow_1</bpmn2:incoming>
  <bpmn2:outgoing>SequenceFlow_2</bpmn2:outgoing>
</bpmn2:callActivity>
```
Property order does not matter (the editor itself writes them in arbitrary order).
Gateways: `bpmn2:exclusiveGateway` (Router) and `bpmn2:parallelGateway` (Multicast, Sequential Multicast, Join;
identity `subActivityType=parallel`).

### Events
```xml
<!-- Message Start (main process, target of the sender message flow) -->
<bpmn2:startEvent id="StartEvent_1" name="Start">
  <bpmn2:extensionElements>
    <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::MessageStartEvent/version::1.0</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:outgoing>SequenceFlow_1</bpmn2:outgoing>
  <bpmn2:messageEventDefinition/>
</bpmn2:startEvent>
<!-- Message End: same pattern, MessageEndEvent/version::1.1.0, componentVersion 1.1, <bpmn2:messageEventDefinition/> -->
<!-- Local process Start / End: no event definition -->
<bpmn2:startEvent id="StartEvent_2" name="Start">
  <bpmn2:extensionElements>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::StartEvent</value></ifl:property>
    <ifl:property><key>activityType</key><value>StartEvent</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:outgoing>SequenceFlow_21</bpmn2:outgoing>
</bpmn2:startEvent>
<!-- EndEvent: cname::EndEvent + activityType EndEvent, no definition -->
<!-- Terminate: props on the event + empty definition -->
<bpmn2:endEvent id="EndEvent_5" name="End 1">
  <bpmn2:extensionElements>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::TerminateEndEvent</value></ifl:property>
    <ifl:property><key>activityType</key><value>TerminateEvent</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:incoming>SequenceFlow_9</bpmn2:incoming>
  <bpmn2:terminateEventDefinition/>
</bpmn2:endEvent>
<!-- Error Start / Error End / Escalation End / Timer Start: props on the DEFINITION, none on the event -->
<bpmn2:endEvent id="EndEvent_80508966" name="Escalation End 2">
  <bpmn2:incoming>SequenceFlow_80508969</bpmn2:incoming>
  <bpmn2:escalationEventDefinition>
    <bpmn2:extensionElements>
      <ifl:property><key>ErrorCode</key><value>ReceiverNotFound</value></ifl:property>
      <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
      <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::EscalationEndEvent/version::1.0.0</value></ifl:property>
      <ifl:property><key>activityType</key><value>EscalationEndEvent</value></ifl:property>
    </bpmn2:extensionElements>
  </bpmn2:escalationEventDefinition>
</bpmn2:endEvent>
```
Error Start: `errorEventDefinition` with `cmdVariantUri=ctype::FlowstepVariant/cname::ErrorStartEvent`,
`activityType=StartErrorEvent`. Error End: `cname::ErrorEndEvent`, `activityType=EndErrorEvent`.
Timer Start: `timerEventDefinition id="TimerEventDefinition_N"` with `scheduleKey`, `componentVersion` 1.4,
`cname::intermediatetimer/version::1.4.0`, `activityType=StartTimerEvent` (see serialization-rules.md §Timer).

### Exception Subprocess (inside a process, not in the collaboration)
```xml
<bpmn2:subProcess id="SubProcess_1" name="Exception Subprocess">
  <bpmn2:extensionElements>
    <ifl:property><key>activityType</key><value>ErrorEventSubProcessTemplate</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.1.0</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:startEvent id="StartEvent_9" name="Error Start"> ... errorEventDefinition ... </bpmn2:startEvent>
  ... steps ...
  <bpmn2:endEvent .../>    <!-- Message End, Error End or Escalation End -->
  <bpmn2:sequenceFlow .../> (flows of the subprocess live INSIDE the subProcess)
</bpmn2:subProcess>
```
It has no incoming/outgoing flows. Lab-verified in the main Integration Process (SAP also allows it in local
processes; not exercised in the lab).

### Sequence flow
`<bpmn2:sequenceFlow id="SequenceFlow_2" sourceRef="CallActivity_1" targetRef="ExclusiveGateway_1"/>`
Multicast branches may carry `name="Branch 1"`. Router routes: serialization-rules.md §Router.
A sequence flow must stay inside its container (process or subProcess).

## 3. Diagram (`bpmndi`)
```xml
<bpmndi:BPMNShape bpmnElement="CallActivity_1" id="BPMNShape_CallActivity_1">
  <dc:Bounds height="60.0" width="100.0" x="430.0" y="100.0"/>
</bpmndi:BPMNShape>
<bpmndi:BPMNEdge bpmnElement="SequenceFlow_2" id="BPMNEdge_SequenceFlow_2"
     sourceElement="BPMNShape_CallActivity_1" targetElement="BPMNShape_ExclusiveGateway_1">
  <di:waypoint x="480.0" xsi:type="dc:Point" y="130.0"/>
  <di:waypoint x="560.0" xsi:type="dc:Point" y="130.0"/>
</bpmndi:BPMNEdge>
```
- Mandatory: one `BPMNShape` per participant (sender/receiver pools 100x140, process pools = their bounds),
  per flow node and per subProcess. Missing shape ⇒ HTTP 500, the iFlow cannot be opened.
- Coordinates are absolute (not relative to the pool). Keep each node inside its process pool and each
  subprocess node inside the subprocess box (membership comes from the XML nesting, but nodes drawn outside
  their pool are confusing and get moved when someone edits the iFlow).
- Sizes used by the editor: activities 100x60, events 32x32, gateways 40x40.
- Edges: two waypoints (centre to centre) are enough.
