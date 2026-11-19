// Paste into the Integration Suite UI page (same origin) - e.g. via a browser automation "execute JS" tool.
// Set _ws to the package workspace id: (await (await fetch('/api/1.0/workspace?pkgId=<Package>')).json())
window._ws = window._ws || '<workspace id>';

window._arts = async () =>
  (await fetch(`/api/1.0/workspace/${_ws}/artifacts`, { headers: { Accept: 'application/json' } })).json();

// Server-side validation of an uploaded iFlow (what the editor shows as red/yellow markers)
window._validate = async (bundleId) => {
  const a = (await _arts()).find((x) => x.tooltip === bundleId);
  if (!a) return 'NO ARTIFACT ' + bundleId;
  const r = await fetch(
    `/api/1.0/workspace/${_ws}/artifacts/${a.id}/entities/${a.entityID}/iflows/${encodeURIComponent(bundleId)}`,
    { headers: { Accept: 'application/json' } });
  if (r.status !== 200) return 'HTTP ' + r.status; // 500 = model cannot be built (e.g. missing BPMNShape)
  const j = await r.json();
  window._lastModel = j; // j.bpmnModel.shapes[].attributes.flavor tells how each element was recognised
  const v = j.validationResultModel || {};
  return {
    deployRestricted: v.isDeployRestricted,
    n: (v.problems || []).length,
    problems: (v.problems || []).map((p) =>
      `${p.severity[0]} ${p.elementId}${p.attributeId ? '.' + p.attributeId : ''}: ${p.message}`),
  };
};

// Minimal zip reader (stored + deflate) using the browser's DecompressionStream
window._unzip = async (buf) => {
  const b = new Uint8Array(buf), dv = new DataView(buf);
  let e = b.length - 22;
  while (dv.getUint32(e, true) !== 0x06054b50) e--;
  const n = dv.getUint16(e + 10, true);
  let p = dv.getUint32(e + 16, true);
  const out = {};
  for (let i = 0; i < n; i++) {
    const m = dv.getUint16(p + 10, true), cs = dv.getUint32(p + 20, true), fl = dv.getUint16(p + 28, true),
      xl = dv.getUint16(p + 30, true), cl = dv.getUint16(p + 32, true), lo = dv.getUint32(p + 42, true);
    const name = new TextDecoder().decode(b.subarray(p + 46, p + 46 + fl));
    p += 46 + fl + xl + cl;
    const lfl = dv.getUint16(lo + 26, true), lxl = dv.getUint16(lo + 28, true);
    const data = b.subarray(lo + 30 + lfl + lxl, lo + 30 + lfl + lxl + cs);
    out[name] = m === 0 ? new TextDecoder().decode(data)
      : await new Response(new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).text();
  }
  return out;
};

// Files of an artifact without downloading: {'src/main/resources/scenarioflows/integrationflow/X.iflw': '...', ...}
window._files = async (bundleId) => {
  const a = (await _arts()).find((x) => x.tooltip === bundleId);
  const r = await fetch(`/api/1.0/workspace/${_ws}/artifacts/${a.id}/entities/${a.entityID}`);
  return _unzip(await r.arrayBuffer());
};

// Save any JSON-able object as ONE download (the browser may ask where to save each file)
window._download = (name, obj) => {
  const l = document.createElement('a');
  l.href = URL.createObjectURL(new Blob([JSON.stringify(obj)], { type: 'application/json' }));
  l.download = name; document.body.appendChild(l); l.click(); l.remove();
};

// Harvest every component definition of the palette (steps + SAP adapters) into one file
window._harvestMetadata = async () => {
  const list = await (await fetch('/api/1.0/metadata?profileID=iflmap', { headers: { Accept: 'application/json' } })).json();
  const d = list[0], jobs = [];
  for (const [k, v] of Object.entries(d.shapeMetadataTOMap)) {
    const at = v[0].attributes; if (at.hashedCmdURI) jobs.push({ kind: 'shape', key: k, uri: at.cmdURI, h: at.hashedCmdURI });
  }
  for (const dir of ['listOfSenderAdapters', 'listOfReceiverAdapters'])
    for (const ad of d.adapterMetadata[dir]) for (const det of ad.adapterDetails)
      jobs.push({ kind: dir, key: ad.name + '|' + det.name, uri: det.adapterVariantURI, h: det.adapterVariantHashURI });
  const cfg = 'ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.4'; // adjust to the current version
  jobs.push({ kind: 'extra', key: 'IFlowConfiguration', uri: cfg, h: btoa(cfg) });
  await Promise.all(Array.from({ length: 6 }, async (_, w) => {
    for (let i = w; i < jobs.length; i += 6) {
      const j = jobs[i];
      const r = await fetch('/api/1.0/metadata/' + j.h.replace(/=+$/, '') +
        '?profile=iflmap&bundleType=IntegrationFlow&stepId=X_1', { headers: { Accept: 'application/json' } });
      j.status = r.status; j.body = await r.text();
    }
  }));
  _download('cpi_metadata_list.json', list);
  setTimeout(() => _download('cpi_metadata_details.json', jobs), 1500);
  return jobs.length + ' definitions';
};

// Pointer-event "press" for UI5 controls (element.click() is not enough)
window._press = (el) => {
  const r = el.getBoundingClientRect();
  const o = { bubbles: true, cancelable: true, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2, button: 0, view: window };
  for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'])
    el.dispatchEvent(t.startsWith('pointer') ? new PointerEvent(t, { ...o, pointerType: 'mouse', isPrimary: true }) : new MouseEvent(t, o));
};
window._sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// Package page in edit mode: open Add > Integration Flow > Upload (then set the file input with the browser tool)
window._openUpload = async () => {
  const add = [...document.querySelectorAll('button')].find((b) => b.getAttribute('aria-label') === 'Add artifact' || b.title === 'Add artifact');
  if (!add) return 'no add button (is the package in edit mode?)';
  _press(add); await _sleep(900);
  const mi = [...document.querySelectorAll('[role=menuitem],li,button')].find((e) => e.innerText && e.innerText.trim() === 'Integration Flow' && e.offsetParent);
  if (!mi) return 'no menu item'; _press(mi); await _sleep(1500);
  const up = [...document.querySelectorAll('[role=radio]')].find((e) => /Upload/.test(e.innerText || e.getAttribute('aria-label') || '') && e.offsetParent);
  if (!up) return 'no upload radio'; _press(up); await _sleep(800);
  return 'ok';
};
window._clickAdd = async () => {
  const dlg = [...document.querySelectorAll('[role=dialog]')].find((d) => /Add Integration Flow/.test(d.innerText));
  if (!dlg) return 'no dialog';
  const b = [...dlg.querySelectorAll('button')].find((x) => x.innerText.trim() === 'Add');
  _press(b); await _sleep(5000); return 'clicked';
};
