# Adapters (message flows)

## Direction and wiring rules (lab-verified)

| Situation | sourceRef | targetRef | adapter variant |
|---|---|---|---|
| Inbound call/event that starts the iFlow | sender participant (`ifl:type="EndpointSender"`) | Message Start Event | `direction::Sender` |
| Request Reply (synchronous call) | `serviceTask` ExternalCall | receiver participant (`EndpointRecevier`) | `direction::Receiver` |
| Send (asynchronous, fire-and-forget) | `serviceTask` Send | receiver participant | `direction::Receiver` |
| Message End Event that delivers the result | Message End Event | receiver participant | `direction::Receiver` |
| Content Enricher (lookup + merge) | receiver participant | `serviceTask` contentEnricherWithLookup | `direction::Receiver`; **only OData (HCIOData), SOAP 1.x or SuccessFactors** |
| Poll Enrich (read a file/mail mid-flow) | sender participant (`EndpointSender`) | `serviceTask` PollEnrich | **sender** polling adapter, e.g. `sap:PollingSFTP/.../direction::Sender` |
| Timer-started iFlow | none | - | - |

- One message flow per Request Reply / Send / enricher step.
- `system` = name of the sender/receiver participant, `Name` = message flow name.
- Each main Integration Process has exactly one start event. An iFlow may hold several Integration Processes,
  each with its own sender channel (seen in a real iFlow: `HTTPS_P1` → `StartEvent_2`, `HTTPS_P2` → `StartEvent_17`).
- The SFTP sender (`sap:SFTP` Sender) is a polling *start* adapter (scheduler inside the adapter); for mid-flow
  reads use Poll Enrich + `sap:PollingSFTP`.
- ProcessDirect: receiver `address` (e.g. `/my/target`) must match the `address` of a ProcessDirect sender in
  the called iFlow.

## Choosing the variant

Adapters are resolved by ComponentType + direction (+ TransportProtocol/MessageProtocol when ambiguous):
`SOAP` (SOAP 1.x | Plain SOAP), `HCIOData` (OData V2 | OData V4), `Mail` sender (IMAP | POP3),
`AMQP` (TCP | WS), `SuccessFactors` (OData V2 | OData V4 | REST | SOAP). In `iflowgen.py` pass
`"messageProtocol"`/`"transportProtocol"` for those.

## Always-mandatory keys of common adapters (tenant catalog, 2026-11-16)

Only unconditional mandatory keys are listed; many more become mandatory depending on other values
(e.g. `credentialName` when `authenticationMethod=Basic`). The validator evaluates those conditions.

| Adapter | Direction | TP/MP | Version | Always-mandatory keys (default) |
|---|---|---|---|---|
| JDBC | Receiver | JDBC/JDBC | 1.7.0 | `alias`; `connectionTimeout`=3; `queryTimeout`=3 |
| ProcessDirect | Receiver | Not Applicable/Not Applicable | 1.1.1 | `address` |
| ProcessDirect | Sender | Not Applicable/Not Applicable | 1.1.2 | `address` |
| AMQP | Receiver | TCP/AMQP1.0 | 1.5.1 | `host`; `port`; `destinationName` |
| AMQP | Sender | TCP/AMQP1.0 | 1.8.1 | `host`; `port`; `destinationName`; `NumberConcurrentProcesses`=1; `queuePrefetch`=5 |
| AMQP | Receiver | WS/AMQP1.0 | 1.4.2 | `host`; `port`; `destinationName` |
| AMQP | Sender | WS/AMQP1.0 | 1.7.2 | `host`; `port`; `destinationName`; `NumberConcurrentProcesses`=1; `queuePrefetch`=5 |
| DataStoreConsumer | Sender | JDBC/None | 1.0.0 | `storageName`; `PollDelay`=10; `RetryInterval`=1; `ExponentialBackoff`=1; `file_lock_timeout`=10 |
| HCIOData | Receiver | HTTP/OData V2 | 1.32.1 | `address`; `clearStaleConnection`=false; `operation`=Query(GET) (Create(POST)/Merge(MERGE)/Update(PUT)/Query(GET)/Read(GET)/Delete(DELETE)); `receiveTimeOut`=1; `retryOnException`=false; `retryOnFailure`=false |
| HCIOData | Receiver | HTTP/OData V4 | 1.23.1 | `address`; `proxyType`=default (default/sapcc/default/manual); `authenticationMethod`=None (None/Basic/Client Certificate/OAuth2ClientCredentials); `receiveTimeOut`=1 |
| HTTPS | Sender | HTTPS/None | 1.5.3 | `urlPath`; `senderAuthType`=RoleBased (RoleBased/ClientCertificate/NoAuthorization); `xsrfProtection`=1 |
| HTTP | Receiver | HTTP/None | 1.22.1 | `httpAddressWithoutQuery` |
| IDOC | Receiver | HTTP/IDoc SOAP | 1.8.3 | `address`; `proxyType`=default (default/sapcc/default/manual); `KeepConnectionAlive`=1; `CompressMessage` |
| IDOC | Sender | HTTP/IDoc SOAP | 1.4.5 | `address`; `senderAuthType`=RoleBased (RoleBased/ClientCertificate) |
| JMS | Receiver | Not Applicable/Not Applicable | 1.6.3 | `QueueName_outbound`; `RetentionThresholdAlerting`=2; `ExpirationPeriod`=30; `UseMessageCompression`=1; `EncryptMessage`=1; `TransferExchangeProperties`=0 |
| JMS | Sender | Not Applicable/Not Applicable | 1.5.0 | `QueueName_inbound`; `RetryInterval`=1; `ExponentialBackoff`=1 |
| Kafka | Receiver | TCP/Kafka | 1.1.0 | `authentication`=SASL (ClientCertificate/SASL); `topic`; `acknowledgement`=RequiredByAll (RequiredByAll/RequiredByLeader/NotRequired); `maxRequestSize`=1024; `maxInflightRequests`=5; `retries`=0; `retryBackoff`=1000; `compression`=none (none/gzip/lz4/snappy/zstd); `requestTimeout`=30; `maxBlockTime`=30; `reconnectBackoff`=1 |
| Kafka | Sender | TCP/Kafka | 1.1.0 | `authentication`=SASL (ClientCertificate/SASL); `topic`; `parallelConsumers`=1; `errorHandling`=retry (retry/skip); `minFetchSize`=1; `maxFetchSize`=52428800; `maxPartitionFetchSize`=1048576; `maxWaitFetch`=500; `maxPollRecords`=500; `requestTimeout`=30; `retryBackoff`=1000; `reconnectBackoff`=1; `heartbeatInterval`=3; `sessionTimeout`=10 |
| Mail | Sender | IMAP/Not Applicable | 1.14.0 | `server`; `timeout`=3000; `folder`=INBOX; `maxMessagesPerPoll`=20; `lockDuration`=60 |
| Mail | Sender | POP3/Not Applicable | 1.12.0 | `server`; `timeout`=3000; `maxMessagesPerPoll`=20; `lockDuration`=60 |
| Mail | Receiver | SMTP/None | 1.13.0 | `server`; `timeout`=30000; `from`; `to`; `keep_attachments`=0 |
| ODataSender | Sender | HTTP/OData V2 | 1.3.1 | `authentication`=basic (basic/certificate); `edmxPath`; `operation`=GET_FEED (GET_FEED/GET_ENTRY/CREATE_ENTRY/UPDATE_ENTRY/DELETE_ENTRY/FUNCTION_IMPORT); `entitySet` |
| PollingSFTP | Sender | SFTP/File | 1.10.0 | `host` |
| RFC | Receiver | RFC/Synchronous RFC | 1.3.0 | `destination` |
| SFTP | Receiver | SFTP/File | 1.14.0 | `host`; `sftpSecEnabled`=1 |
| SFTP | Sender | SFTP/File | 1.21.0 | `host`; `useClusterLock`=0; `file_lock_timeout`=15; `noop`=delete (delete/mark/test/move) |
| SOAP | Receiver | HTTP/Plain SOAP | 1.10.4 | `address`; `KeepConnectionAlive`=1; `CompressMessage` |
| SOAP | Sender | HTTP/Plain SOAP | 1.4.1 | `address`; `senderAuthType`=RoleBased (RoleBased/ClientCertificate) |
| SOAP | Receiver | HTTP/SOAP 1.x | 1.14.1 | `address`; `KeepConnectionAlive`=1; `CompressMessage`=0 |
| SOAP | Sender | HTTP/SOAP 1.x | 1.9.4 | `address` |
| XI | Receiver | HTTP/XI | 1.20.0 | `Address`; `KeepConnectionAlive`=1; `CompressMessage`=0; `CommunicationComponentSender`; `CommunicationComponentReceiver`; `ServiceInterfaceReceiver`; `ServiceInterfaceNamespaceReceiver`; `keepOriginalPayloadReceiver`=0 |
| XI | Sender | HTTP/XI | 1.21.0 | `Address_inbound`; `keepOriginalPayloadSender`=0 |

Notes from the lab:
- HTTP receiver `authenticationMethod` defaults to `Client Certificate` in the metadata; set it explicitly
  (`None`, `Basic`, `OAuth2ClientCredentials`, ...). Same for OData V4 `authenticationMethod`.
- Mail receiver: `to` is mandatory; empty `subject` only warns.
- XI receiver needs communication components, interface and namespace even in a test.
- SFTP receiver `username` is mandatory and validated by regex; `host` is `host:port`.
- Every adapter catalog entry lists `properties[]` with `default`, `values`, `mandatory`, `visibleIf`/`cond`
  and `regex`: read it instead of guessing.
