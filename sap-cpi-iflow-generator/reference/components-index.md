# Components index (generated from catalog/components.json)

verified: `sample` = identity copied from an iFlow written by the SAP editor; `tenant-upload` = identity inferred, then confirmed by uploading a generated iFlow (server recognised the palette flavor, lab T1); `inferred` = NOT yet confirmed, run the tenant validation loop before relying on it; `metadata-only` = adapter variant whose properties come from tenant metadata but never seen in a real iFlow (identity follows the generic adapter rule, see adapters.md).

## Flow steps, events, gateways, processes

| key (`type` in iflowgen) | palette name | BPMN element | event definition / props on | identity properties | tenant version | verified |
|---|---|---|---|---|---|---|
| `Aggregator` | Aggregator | callActivity |  | activityType=Aggregator | 1.2.0 | sample |
| `Base64 Decode` | Base64 Decode | callActivity |  | activityType=Decoder, encoderType=Base64 Decode | 1.0.1 | tenant-upload |
| `Base64 Encode` | Base64 Encode | callActivity |  | activityType=Encoder, encoderType=Base64 Encode | 1.0.1 | sample |
| `Camel` | Iterating Splitter | callActivity |  | splitType=Camel, activityType=Splitter | 1.6.0 | sample |
| `contentEnricherWithLookup` | Content Enricher | serviceTask |  | activityType=contentEnricherWithLookup | 1.2.0 | sample |
| `CsvToXmlConverter` | CSV To XML Converter | callActivity |  | activityType=CsvToXmlConverter | 1.4.0 | sample |
| `Decrypt` | PKCS7/CMS Decryptor | callActivity |  | activityType=Decrypt | 1.2.0 | tenant-upload |
| `delete` | Delete | callActivity |  | activityType=DBstorage, operation=delete | 1.7.1 | tenant-upload |
| `EDIExtractor` | EDI Extractor | callActivity |  | activityType=EDIExtractor | 2.3.0 | tenant-upload |
| `EDISplitter` | EDI Splitter | callActivity |  | activityType=Splitter, splitType=EDISplitter | 2.13.0 | tenant-upload |
| `EDItoXMLConverter` | EDI to XML Converter | callActivity |  | activityType=EDItoXMLConverter | 2.10.0 | tenant-upload |
| `EDIValidator` | EDI Validator | callActivity |  | activityType=EDIValidator | 1.7.0 | tenant-upload |
| `Encrypt` | PKCS7/CMS Encryptor | callActivity |  | activityType=Encrypt | 1.3.0 | tenant-upload |
| `EndEvent` | End Event | endEvent |  | activityType=EndEvent | - | sample |
| `Enricher` | Content Modifier | callActivity |  | activityType=Enricher | 1.6.6 | sample |
| `ErrorEndEvent` | Error End Event | endEvent | errorEventDefinition (props on definition) | activityType=EndErrorEvent | - | sample |
| `ErrorEventSubProcessTemplate` | Exception Subprocess | subProcess |  | activityType=ErrorEventSubProcessTemplate | 1.1.0 | sample |
| `ErrorStartEvent` | Error Start Event | startEvent | errorEventDefinition (props on definition) | activityType=StartErrorEvent | - | sample |
| `EscalationEndEvent` | Escalation End Event | endEvent | escalationEventDefinition (props on definition) | activityType=EscalationEndEvent | 1.0.0 | sample |
| `ExclusiveGateway` | Router | exclusiveGateway |  | activityType=ExclusiveGateway | 1.2.0 | sample |
| `ExternalCall` | Request Reply | serviceTask |  | activityType=ExternalCall | 1.0.4 | sample |
| `Filter` | Filter | callActivity |  | activityType=Filter | 1.1.0 | sample |
| `GatewayRoute` | Route | sequenceFlow |  | expressionType=NonXML | 1.0.3 | sample |
| `Gather` | Gather | callActivity |  | activityType=Gather | 1.2.0 | sample |
| `GeneralSplitter` | General Splitter | callActivity |  | activityType=Splitter, splitType=GeneralSplitter | 1.6.0 | sample |
| `get` | Get | callActivity |  | activityType=DBstorage, operation=get | 1.7.1 | sample |
| `GroovyScript` | Groovy Script | callActivity |  | activityType=Script, subActivityType=GroovyScript | 1.1.2 | sample |
| `GZIP Compress` | GZIP Compress | callActivity |  | activityType=Encoder, encoderType=GZIP Compress | 1.0.1 | tenant-upload |
| `GZIP Decompress` | GZIP Decompress | callActivity |  | activityType=Decoder, encoderType=GZIP Decompress | 1.0.1 | tenant-upload |
| `IdempotentProcessCall` | Idempotent Process Call | callActivity |  | activityType=IdempotentProcessCall | 1.1.2 | tenant-upload |
| `IDMapper` | ID Mapping | callActivity |  | activityType=IDMapper | 1.0.0 | tenant-upload |
| `IDoc` | IDoc Splitter | callActivity |  | activityType=Splitter, splitType=IDoc | 1.1.0 | tenant-upload |
| `IFlowConfiguration` | IFlowConfiguration | collaboration |  |  | 1.2.4 | sample |
| `IntegrationProcess` | Integration Process | process |  |  | 1.2.1 | sample |
| `intermediatetimer` | Timer Start | startEvent | timerEventDefinition (props on definition) | scheduleKey=<row><cell>dateType</cell><cell>SIMPL..., activityType=StartTimerEvent | 1.4.0 | sample |
| `JavaScript` | JavaScript | callActivity |  | activityType=Script, subActivityType=JavaScript | 1.1.2 | tenant-upload |
| `Join` | Join | parallelGateway |  | activityType=Join, subActivityType=parallel | 1.0.0 | sample |
| `JsonToXmlConverter` | JSON To XML Converter | callActivity |  | activityType=JsonToXmlConverter | 1.1.2 | sample |
| `LocalIntegrationProcess` | Local Integration Process | process |  | processType=directCall | 1.1.3 | sample |
| `LoopingProcess` | Looping Process Call | callActivity |  | loopId=StandardLoopCharacteristics_173798540..., activityType=ProcessCallElement, subActivityType=LoopingProcess | 1.3.0 | sample |
| `MessageDigest` | Message Digest | callActivity |  | activityType=MessageDigest | 1.1.1 | sample |
| `MessageEndEvent` | End Message | endEvent | messageEventDefinition |  | 1.1.0 | sample |
| `MessageMapping` | Message Mapping | callActivity |  | mappingType=MessageMapping, activityType=Mapping | 1.3.1 | sample |
| `MessageStartEvent` | Start Message | startEvent | messageEventDefinition |  | 1.0 | sample |
| `MIME Multipart Message Decode` | MIME Multipart Decoder | callActivity |  | activityType=Decoder, encoderType=MIME Multipart Message Decode | 1.0.2 | tenant-upload |
| `MIME Multipart Message Encode` | MIME Multipart Encoder | callActivity |  | activityType=Encoder, encoderType=MIME Multipart Message Encode | 1.2.0 | tenant-upload |
| `Multicast` | Parallel Multicast | parallelGateway |  | activityType=Multicast, subActivityType=parallel | 1.1.1 | sample |
| `NonLoopingProcess` | Process Call | callActivity |  | activityType=ProcessCallElement, subActivityType=NonLoopingProcess | 1.0.4 | sample |
| `OperationMapping` | Operation Mapping | callActivity |  | activityType=Mapping, mappingType=OperationMapping | 1.1.0 | inferred |
| `Persist` | Persist Message | callActivity |  | activityType=Persist | 1.0.2 | tenant-upload |
| `PgpDecrypt` | PGP Decryptor | callActivity |  | activityType=PgpDecrypt | 1.2.0 | tenant-upload |
| `PgpEncrypt` | PGP Encryptor | callActivity |  | activityType=PgpEncrypt | 1.3.1 | tenant-upload |
| `PKCS#7/CMS Signature-Content Splitter` | PKCS#7/CMS Splitter | callActivity |  | activityType=Splitter, splitType=PKCS#7/CMS Signature-Content Splitter | 1.1.1 | tenant-upload |
| `PollEnrich` | Poll Enrich | serviceTask |  | activityType=PollEnrich | 1.1.0 | sample |
| `put` | Write | callActivity |  | activityType=DBstorage, operation=put | 1.7.1 | sample |
| `select` | Select | callActivity |  | activityType=DBstorage, operation=select | 1.7.1 | tenant-upload |
| `Send` | Send | serviceTask |  | activityType=Send | 1.0.4 | sample |
| `SequentialMulticast` | Sequential Multicast | parallelGateway |  | activityType=SequentialMulticast, subActivityType=parallel | 1.1.0 | sample |
| `SignMessage` | PKCS7/CMS Signer | callActivity |  | activityType=SignMessage | 1.5.0 | tenant-upload |
| `SimpleSignMessage` | Simple Signer | callActivity |  | activityType=SimpleSignMessage | 1.3.0 | tenant-upload |
| `StartEvent` | Start Event | startEvent |  | activityType=StartEvent | - | sample |
| `TarSplitter` | Tar Splitter | callActivity |  | activityType=Splitter, splitType=TarSplitter | 1.0.0 | tenant-upload |
| `TerminateEndEvent` | Terminate Message | endEvent | terminateEventDefinition | activityType=TerminateEvent | - | sample |
| `Variables` | Write Variables | callActivity |  | visibility=local, encrypt=true, expire=90, activityType=Variables | 1.2.0 | sample |
| `VerifySign` | PKCS7 Signature Verifier | callActivity |  | activityType=VerifySign | 1.2.0 | tenant-upload |
| `XMLDigitalSignMessage` | XML Signer | callActivity |  | activityType=XMLDigitalSignMessage | 1.3.3 | tenant-upload |
| `XMLDigitalVerifySign` | XML Signature Verifier | callActivity |  | activityType=XMLDigitalVerifySign | 1.1.0 | tenant-upload |
| `XmlModifier` | XML Modifier | callActivity |  | activityType=XmlModifier | 1.1.0 | sample |
| `XmlToCsvConverter` | XML To CSV Converter | callActivity |  | activityType=XmlToCsvConverter | 1.2.0 | sample |
| `XMLtoEDIConverter` | XML to EDI Converter | callActivity |  | activityType=XMLtoEDIConverter | 2.10.0 | tenant-upload |
| `XmlToJsonConverter` | XML To JSON Converter | callActivity |  | activityType=XmlToJsonConverter | 1.0.8 | sample |
| `XmlValidator` | XML Validator | callActivity |  | activityType=XmlValidator | 2.2.3 | sample |
| `XSLTMapping` | XSLT Mapping | callActivity |  | mappinguri=dir://mapping/xslt/src/main/resources..., mappingname=XSLTMapping1, activityType=Mapping, subActivityType=XSLTMapping | 1.2.0 | sample |
| `ZIP Compress` | ZIP Compress | callActivity |  | activityType=Encoder, encoderType=ZIP Compress | 1.0.1 | sample |
| `ZIP Decompress` | ZIP Decompress | callActivity |  | activityType=Decoder, encoderType=ZIP Decompress | 1.0.2 | tenant-upload |
| `ZipSplitter` | Zip Splitter | callActivity |  | activityType=Splitter, splitType=ZipSplitter | 1.0.0 | tenant-upload |

## Adapters (messageFlow)

| key | direction | ComponentType | TransportProtocol | MessageProtocol | tenant version | verified |
|---|---|---|---|---|---|---|
| `adapter:AdvancedEventMesh|TCP|SMF|Receiver` | Receiver | AdvancedEventMesh | TCP | SMF | 1.3.3 | metadata-only |
| `adapter:AdvancedEventMesh|TCP|SMF|Sender` | Sender | AdvancedEventMesh | TCP | SMF | 1.3.3 | metadata-only |
| `adapter:AS2|HTTP|AS2 MDN|Sender` | Sender | AS2 | HTTP | AS2 MDN | 1.11.0 | metadata-only |
| `adapter:AS2|HTTP|AS2|Receiver` | Receiver | AS2 | HTTP | AS2 | 1.11.1 | metadata-only |
| `adapter:AS2|HTTP|AS2|Sender` | Sender | AS2 | HTTP | AS2 | 1.17.1 | metadata-only |
| `adapter:AS4|HTTPS|ebMS3 Pull|Receiver` | Receiver | AS4 | HTTPS | ebMS3 Pull | 1.5.0 | metadata-only |
| `adapter:AS4|HTTPS|ebMS3 Pull|Sender` | Sender | AS4 | HTTPS | ebMS3 Pull | 1.3.0 | metadata-only |
| `adapter:AS4|HTTPS|ebMS3 Push|Receiver` | Receiver | AS4 | HTTPS | ebMS3 Push | 1.6.0 | metadata-only |
| `adapter:AS4|HTTPS|ebMS3 Push|Sender` | Sender | AS4 | HTTPS | ebMS3 Push | 1.4.1 | metadata-only |
| `adapter:AS4|HTTPS|ebMS3 Receipt|Sender` | Sender | AS4 | HTTPS | ebMS3 Receipt | 1.1.0 | metadata-only |
| `adapter:AzureStorage|HTTPS|BLOB Storage|Receiver` | Receiver | AzureStorage | HTTPS | BLOB Storage |  | metadata-only |
| `adapter:AzureStorage|HTTPS|BLOB Storage|Sender` | Sender | AzureStorage | HTTPS | BLOB Storage |  | metadata-only |
| `adapter:AzureStorage|HTTPS|Fileshare Storage|Receiver` | Receiver | AzureStorage | HTTPS | Fileshare Storage |  | metadata-only |
| `adapter:AzureStorage|HTTPS|Fileshare Storage|Sender` | Sender | AzureStorage | HTTPS | Fileshare Storage |  | metadata-only |
| `adapter:AzureStorage|HTTPS|Queue Storage|Receiver` | Receiver | AzureStorage | HTTPS | Queue Storage |  | metadata-only |
| `adapter:AzureStorage|HTTPS|Queue Storage|Sender` | Sender | AzureStorage | HTTPS | Queue Storage |  | metadata-only |
| `adapter:AzureStorage|HTTPS|Table Storage|Receiver` | Receiver | AzureStorage | HTTPS | Table Storage |  | metadata-only |
| `adapter:AzureStorage|HTTPS|Table Storage|Sender` | Sender | AzureStorage | HTTPS | Table Storage |  | metadata-only |
| `adapter:JDBC|JDBC|JDBC|Receiver` | Receiver | JDBC | JDBC | JDBC | 1.7.0 | sample |
| `adapter:MicrosoftSharePoint|HTTP|REST|Receiver` | Receiver | MicrosoftSharePoint | HTTP | REST |  | metadata-only |
| `adapter:MicrosoftSharePoint|HTTP|REST|Sender` | Sender | MicrosoftSharePoint | HTTP | REST |  | metadata-only |
| `adapter:OpenConnectors|HTTP|REST|Receiver` | Receiver | OpenConnectors | HTTP | REST |  | metadata-only |
| `adapter:ProcessDirect|Not Applicable|Not Applicable|Receiver` | Receiver | ProcessDirect | Not Applicable | Not Applicable | 1.1.1 | sample |
| `adapter:ProcessDirect|Not Applicable|Not Applicable|Sender` | Sender | ProcessDirect | Not Applicable | Not Applicable | 1.1.2 | metadata-only |
| `adapter:RabbitMQ|TCP|AMQP 0-9-1|Receiver` | Receiver | RabbitMQ | TCP | AMQP 0-9-1 |  | metadata-only |
| `adapter:RabbitMQ|TCP|AMQP 0-9-1|Sender` | Sender | RabbitMQ | TCP | AMQP 0-9-1 |  | metadata-only |
| `adapter:RNIF20|https|rnif20|Receiver` | Receiver | RNIF20 | https | rnif20 | 1.2.0 | metadata-only |
| `adapter:RNIF20|sap-rnif20|sap-rnif20|Sender` | Sender | RNIF20 | sap-rnif20 | sap-rnif20 | 1.2.0 | metadata-only |
| `adapter:sap:AMQP|TCP|AMQP1.0|Receiver` | Receiver | AMQP | TCP | AMQP1.0 | 1.5.1 | metadata-only |
| `adapter:sap:AMQP|TCP|AMQP1.0|Sender` | Sender | AMQP | TCP | AMQP1.0 | 1.8.1 | metadata-only |
| `adapter:sap:AMQP|WS|AMQP1.0|Receiver` | Receiver | AMQP | WS | AMQP1.0 | 1.4.2 | metadata-only |
| `adapter:sap:AMQP|WS|AMQP1.0|Sender` | Sender | AMQP | WS | AMQP1.0 | 1.7.2 | sample |
| `adapter:sap:Ariba|HTTPS|cXML|Receiver` | Receiver | Ariba | HTTPS | cXML | 1.0.5 | metadata-only |
| `adapter:sap:Ariba|HTTPS|cXML|Sender` | Sender | Ariba | HTTPS | cXML | 1.3.2 | metadata-only |
| `adapter:sap:DataStoreConsumer|JDBC|None|Sender` | Sender | DataStoreConsumer | JDBC | None | 1.0.0 | metadata-only |
| `adapter:sap:ELSTER|HTTP|None|Receiver` | Receiver | ELSTER | HTTP | None | 1.2.1 | metadata-only |
| `adapter:SAP:Facebook|HTTP|Not Applicable|Receiver` | Receiver | Facebook | HTTP | Not Applicable | 1.2.1 | metadata-only |
| `adapter:sap:FTP|FTP|File|Receiver` | Receiver | FTP | FTP | File | 1.2.1 | metadata-only |
| `adapter:sap:FTP|FTP|File|Sender` | Sender | FTP | FTP | File | 1.4.2 | metadata-only |
| `adapter:sap:HCIOData|HTTP|OData V2|Receiver` | Receiver | HCIOData | HTTP | OData V2 | 1.32.1 | metadata-only |
| `adapter:sap:HCIOData|HTTP|OData V4|Receiver` | Receiver | HCIOData | HTTP | OData V4 | 1.23.1 | metadata-only |
| `adapter:sap:HTTPS|HTTPS|None|Sender` | Sender | HTTPS | HTTPS | None | 1.5.3 | sample |
| `adapter:sap:HTTP|HTTP|None|Receiver` | Receiver | HTTP | HTTP | None | 1.22.1 | sample |
| `adapter:sap:IDOC|HTTP|IDoc SOAP|Receiver` | Receiver | IDOC | HTTP | IDoc SOAP | 1.8.3 | metadata-only |
| `adapter:sap:IDOC|HTTP|IDoc SOAP|Sender` | Sender | IDOC | HTTP | IDoc SOAP | 1.4.5 | metadata-only |
| `adapter:sap:JMS|Not Applicable|Not Applicable|Receiver` | Receiver | JMS | Not Applicable | Not Applicable | 1.6.3 | metadata-only |
| `adapter:sap:JMS|Not Applicable|Not Applicable|Sender` | Sender | JMS | Not Applicable | Not Applicable | 1.5.0 | metadata-only |
| `adapter:sap:Kafka|TCP|Kafka|Receiver` | Receiver | Kafka | TCP | Kafka | 1.1.0 | metadata-only |
| `adapter:sap:Kafka|TCP|Kafka|Sender` | Sender | Kafka | TCP | Kafka | 1.1.0 | metadata-only |
| `adapter:sap:LDAP|TCP|LDAP|Receiver` | Receiver | LDAP | TCP | LDAP | 1.4.1 | metadata-only |
| `adapter:sap:Mail|IMAP|Not Applicable|Sender` | Sender | Mail | IMAP | Not Applicable | 1.14.0 | metadata-only |
| `adapter:sap:Mail|POP3|Not Applicable|Sender` | Sender | Mail | POP3 | Not Applicable | 1.12.0 | metadata-only |
| `adapter:sap:Mail|SMTP|None|Receiver` | Receiver | Mail | SMTP | None | 1.13.0 | metadata-only |
| `adapter:sap:MDI|HTTP|Not Applicable|Receiver` | Receiver | MDI | HTTP | Not Applicable | 1.0.0 | metadata-only |
| `adapter:sap:ODataSender|HTTP|OData V2|Sender` | Sender | ODataSender | HTTP | OData V2 | 1.3.1 | metadata-only |
| `adapter:sap:ODC|HTTPS|Not Applicable|Receiver` | Receiver | ODC | HTTPS | Not Applicable | 1.2.0 | metadata-only |
| `adapter:sap:PollingFTP|FTP|File|Sender` | Sender | PollingFTP | FTP | File | 1.0.1 | metadata-only |
| `adapter:sap:PollingSFTP|SFTP|File|Sender` | Sender | PollingSFTP | SFTP | File | 1.10.0 | sample |
| `adapter:sap:RFC|RFC|Synchronous RFC|Receiver` | Receiver | RFC | RFC | Synchronous RFC | 1.3.0 | metadata-only |
| `adapter:sap:SFTP|SFTP|File|Receiver` | Receiver | SFTP | SFTP | File | 1.14.0 | sample |
| `adapter:sap:SFTP|SFTP|File|Sender` | Sender | SFTP | SFTP | File | 1.21.0 | sample |
| `adapter:sap:SOAP|HTTP|Plain SOAP|Receiver` | Receiver | SOAP | HTTP | Plain SOAP | 1.10.4 | metadata-only |
| `adapter:sap:SOAP|HTTP|Plain SOAP|Sender` | Sender | SOAP | HTTP | Plain SOAP | 1.4.1 | metadata-only |
| `adapter:sap:SOAP|HTTP|SOAP 1.x|Receiver` | Receiver | SOAP | HTTP | SOAP 1.x | 1.14.1 | sample |
| `adapter:sap:SOAP|HTTP|SOAP 1.x|Sender` | Sender | SOAP | HTTP | SOAP 1.x | 1.9.4 | sample |
| `adapter:sap:SuccessFactors|HTTP|OData V2|Receiver` | Receiver | SuccessFactors | HTTP | OData V2 | 1.21.2 | metadata-only |
| `adapter:sap:SuccessFactors|HTTP|OData V4|Receiver` | Receiver | SuccessFactors | HTTP | OData V4 | 1.11.0 | metadata-only |
| `adapter:sap:SuccessFactors|HTTP|REST|Receiver` | Receiver | SuccessFactors | HTTP | REST | 1.1.4 | metadata-only |
| `adapter:sap:SuccessFactors|HTTP|REST|Sender` | Sender | SuccessFactors | HTTP | REST | 1.1.4 | metadata-only |
| `adapter:sap:SuccessFactors|HTTP|SOAP|Receiver` | Receiver | SuccessFactors | HTTP | SOAP | 1.7.2 | metadata-only |
| `adapter:sap:SuccessFactors|HTTP|SOAP|Sender` | Sender | SuccessFactors | HTTP | SOAP | 1.5.2 | metadata-only |
| `adapter:SAP:Twitter|HTTP|Not Applicable|Receiver` | Receiver | Twitter | HTTP | Not Applicable | 1.1.3 | metadata-only |
| `adapter:sap:XI|HTTP|XI|Receiver` | Receiver | XI | HTTP | XI | 1.20.0 | metadata-only |
| `adapter:sap:XI|HTTP|XI|Sender` | Sender | XI | HTTP | XI | 1.21.0 | metadata-only |
