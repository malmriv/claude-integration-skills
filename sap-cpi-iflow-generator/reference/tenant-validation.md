# Tenant validation loop and catalog refresh

Static validation (`validate_iflw.py`) encodes what we learned; the tenant is the authority. When a browser
session on the Integration Suite UI is available (e.g. Claude in Chrome on
`https://<tenant>.integrationsuite.cfapps.<region>.hana.ondemand.com/shell/design/contentpackage/<Package>`), use
the internal design-time API the UI itself uses. It works with the browser session cookies; write calls need an
`X-CSRF-Token` (fetch it with header `X-CSRF-Token: Fetch` on any GET, e.g. `/api/1.0/user`).
Use a sandbox package and `ZZ`-prefixed ids. Never deploy or delete without the owner's go-ahead.

## Endpoints (internal API, observed 2026-11)

| Purpose | Call |
|---|---|
| Package (workspace) by technical name | `GET /api/1.0/workspace?pkgId=<Package>` → list; pick `technicalName` |
| Artifacts of a package | `GET /api/1.0/workspace/<wsId>/artifacts` → `id`, `entityID`, `tooltip` (= bundle id), `semanticVersion` |
| Download artifact zip | `GET /api/1.0/workspace/<wsId>/artifacts/<id>/entities/<entityID>` (application/octet-stream) |
| Editor model **+ server-side validation** | `GET /api/1.0/workspace/<wsId>/artifacts/<id>/entities/<entityID>/iflows/<bundleId>` → JSON `{bpmnModel, validationResultModel:{hasValidationIssues,isDeployRestricted,problems[]}}`; HTTP 500 = model cannot be built |
| Palette + adapter list (current versions) | `GET /api/1.0/metadata?profileID=iflmap` |
| Component metadata (properties, defaults, values, conditions) | `GET /api/1.0/metadata/<base64(cmdVariantUri) without '='>?profile=iflmap&bundleType=IntegrationFlow&stepId=X_1` |
| Runtime status | `GET /api/v1/IntegrationRuntimeArtifacts('<bundleId>')` (404 = not deployed; `Status` STARTING/STARTED/ERROR/STOPPING) |
| Undeploy | `DELETE /api/v1/IntegrationRuntimeArtifacts('<bundleId>')` (CSRF) → 202 |
| Upload (UI) | Add > Integration Flow > Upload (zip) — the UI chains `PUT .../manifest/<zip>`, `PUT .../properties/metainfo.prop`, `POST /api/1.0/artifacts/<id>/accesspolicy`, `POST /api/1.0/workspace/<wsId>/iflows` (multipart) |
| Deploy (UI) | iFlow page → Deploy → Deploy (refused when `isDeployRestricted=true`) |

The public OData API (`/api/v1/IntegrationDesigntimeArtifacts`) is not exposed on the UI host; use the internal
calls above from the UI session, or the tenant's API host with OAuth if you have a service key.

## Browser helpers

`scripts/harvest/browser_helpers.js` (paste into the UI page): `_validate(bundleId)`, `_files(bundleId)` (read an
artifact's zip in-page, no download), `_download(name, obj)`, `_harvestMetadata()` (catalog refresh),
`_openUpload()` / `_clickAdd()` (upload dialog automation). Helpers are lost on every page navigation.
Tool output from the browser may be truncated (~1 KB per call): page through long problem lists, and strip
`=`, `&`, `?`, `${...}` from texts if an output filter blocks them. Downloads trigger a save dialog when the
browser asks where to save each file: bundle several results in one JSON blob per download.

UI upload automation that worked: open the dialog by dispatching pointer events
(`pointerdown, mousedown, pointerup, mouseup, click`) on the "Add artifact" button, the "Integration Flow" menu item
and the "Upload" radio; set the file with the browser tool's file-upload on the `Single File` input; press the
dialog's "Add" button the same way. Plain `element.click()` does not trigger UI5 controls.

## The loop

1. `validate_iflw.py` clean (no FATAL/ERROR).
2. Upload the zip (new bundle id per attempt, e.g. `zz.lab.<topic>.<n>`).
3. `_validate('<bundleId>')`:
   - `HTTP 500` → model build failure (missing BPMNShape / broken references) — fix before anything else;
   - `problems` with `E` → fix; `W` → review (payload-type warnings are common and legitimate);
   - `deployRestricted=false` → deployable.
4. Optional runtime proof: Deploy from the iFlow page, poll `IntegrationRuntimeArtifacts('<id>')` until
   `STARTED` (or `ERROR`, then read the error in Monitor > Manage Integration Content), then undeploy (`DELETE`).
5. Fold every new tenant message into `legality-rules.md` and, if it is checkable offline, into the validator.

## Refreshing the catalog (new tenant or new release)

1. In the UI session: `GET /api/1.0/metadata?profileID=iflmap` → save as `cpi_metadata_list.json`.
2. For every `shapeMetadataTOMap[*][0].attributes.hashedCmdURI` and every adapter
   `adapterDetails[].adapterVariantHashURI`, `GET /api/1.0/metadata/<hash without '='>?profile=iflmap&bundleType=IntegrationFlow&stepId=X_1`;
   also `IFlowConfiguration` (base64 of `ctype::IFlowVariant/cname::IFlowConfiguration/version::<v>`).
   Save `[{kind, key, uri, h, status, body}]` as `cpi_metadata_details.json` (third-party adapters return 500: fine).
3. Download a corpus of editor-written iFlows (all artifacts of a few packages) for canonical samples.
4. `python scripts/harvest/condense_meta.py cpi_metadata_details.json specs/`
5. `python scripts/build_catalog.py --specs specs --palette cpi_metadata_list.json --samples "corpus/*/*.iflw" --overrides catalog/overrides.json --out catalog/components.json`
6. `python scripts/gen_index.py`, then re-run `examples/good/*.json` through generator + validator + tenant loop.
7. Components still `inferred` must go through an upload test (like `examples/smoke/all-components.json`):
   the server model must show the expected palette `flavor` for each shape (`bpmnModel.shapes[].attributes.flavor`).
