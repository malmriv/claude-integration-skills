# Lab log (2026-11-16, Avvale test tenant, package CPIPruebasAlmagro)

Inputs harvested
- Corpus: 24 iFlows + 1 value mapping already in the package (editor-written, versions 2024-2026).
- Palette: `/api/1.0/metadata?profileID=iflmap` → 77 shape types, 41 sender + 80 receiver adapter variants.
- 189 component definitions (`/api/1.0/metadata/<hash>`); 40 third-party adapters returned 500 (ignored).

Experiments (all artifacts are `ZZ ...` / `zz.lab.*` in the package)

| Id | What | Result |
|---|---|---|
| lab01 `zz.lab01.flowsteps` | Built in the web editor: 22 step types (splitters, gather, join, multicasts, filter, aggregator, validator, converters, XSLT + resource, XML modifier, encoders, digest, Data Store write, content enricher, terminate end) | Canonical serialization of every type; server validation list obtained via `validationResultModel` |
| T0 `zz.lab02.uploadtest` | lab01 repackaged by `package_iflow.py` without its XSLT file | Upload OK; `Mapping file 'XSLTMapping1' not found` |
| T1 `zz.lab.t1` | Generated: every step type (31 of them with inferred identity), router, multicast/join/gather, local processes, looping/idempotent calls, exception subprocess, 9 receiver adapters | Every generated shape recognised with the expected palette flavor (0 mismatches) ⇒ inferred identities confirmed. Found: UI-only collaboration keys, wrong Poll/Content Enricher wiring, Gather+PKCS, aggregator transaction, empty local process, assorted mandatory fields |
| T2 base | Clean-ish baseline | 6 problems: Content Enricher+HTTP, Poll Enrich+receiver SFTP (3 msgs), 2 empty local processes |
| T2 soft (M1,M3,M4,M5,M11,M12) | wrong activityType, old version, unknown key, bad enum, bad table cell, undefined `{{param}}` | M1,M5,M11 rejected; **M3, M4, M12 accepted silently** |
| T2 m2 | version 9.9.9 | rejected ("not supported") |
| T2 m6 | no activityType | rejected ("ctype::FlowstepVariant/version::1.6 ... not supported") |
| T2 m7 | no componentVersion | accepted |
| T2 m8 | no cmdVariantUri | accepted (rebuilt) |
| T2 m9 | no BPMNShape | **HTTP 500: model cannot be built, iFlow cannot be opened** |
| T2 m10 | no incoming/outgoing children | accepted (rebuilt from sequence flows) |
| T3 | 6 local-process variants | ErrorEnd variant OK; missing `processType` ⇒ treated as main process; others "empty sequence" |
| T4 | SAP-style ids vs custom ids; re-saved in the editor | ids irrelevant; error persists after editor save ⇒ semantic |
| T5 | local processes with CM+header / Groovy / empty CM; Content Enricher+OData; Poll Enrich+PollingSFTP sender | only the empty-CM process fails ⇒ rule "a CM without actions is empty"; enricher wiring confirmed |
| T6 `zz.lab.t6` | Generated HTTPS → CM → Router(NonXML) → Groovy → Process Call (local) / Request Reply HTTP; exception subprocess | **0 problems, deployRestricted=false; deployed → STARTED; undeployed** |

Validator calibration: on the 24 corpus iFlows `validate_iflw.py` reports 0 FATAL/0 ERROR; on T2/T5/T6 it reports
the same errors as the tenant plus the silent ones (M4, M12).

Not covered yet (candidates for the next lab): Message Mapping generation (needs .mmap), Operation Mapping,
Value Mapping step, timer schedules beyond the sample, sender adapters other than HTTPS/PollingSFTP at runtime,
runtime behaviour of each step (only design-time + one deployment were exercised).
