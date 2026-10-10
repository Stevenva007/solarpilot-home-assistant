"""Evaluate the bundled ES module and panel lifecycle with Node DOM doubles.

This exercises JavaScript evaluation, registration and construction, not a real
browser, HTTP delivery, WebView caching or a live Home Assistant installation.
"""
import json
from pathlib import Path
import shutil
import subprocess
import re

import pytest

from custom_components.solar_pilot.const import VERSION


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


MODULE_PROBE = r"""
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const definitions = new Map(), listeners = new Map(), intervalTimers = new Set();
let nextTimerId = 0;
let writes = 0, defineCalls = 0;
class NodeDouble {
  constructor() { this.innerHTML = ''; this.children = []; }
  appendChild(node) { this.children.push(node); return node; }
  append(node) { this.children.push(node); }
  addEventListener() {}
  removeEventListener() {}
  querySelectorAll() { return []; }
  querySelector() { return null; }
}
class ElementDouble extends NodeDouble {
  attachShadow() { return this.shadowRoot = new NodeDouble(); }
}
class LegacySolarPilotCard extends ElementDouble {
  constructor() { super(); this.legacySolarPilotCard = true; }
}
if (input.scenario === 'existing_old_stable_class') {
  definitions.set('solar-pilot-card', LegacySolarPilotCard);
}
const firstForeign = {type: 'foreign-card', name: 'Other integration', extension: {keep: true}};
const secondForeign = {type: 'foreign-card', name: 'Other duplicate deliberately retained'};
const catalog = input.dirtyCatalog ? [
  firstForeign,
  {type: 'solar-pilot-card', name: 'Outdated SolarPilot'},
  secondForeign,
  {type: 'solar-pilot-card', name: 'Duplicate SolarPilot'},
  {type: 'solar-pilot-guide-card', name: 'Outdated guide'},
  {type: 'solar-pilot-guide-card', name: 'Duplicate guide'}
] : [firstForeign, secondForeign];
const sandbox = {
  HTMLElement: ElementDouble,
  window: {
    customCards: catalog,
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: name => listeners.delete(name)
  },
  customElements: {
    get: name => definitions.get(name),
    define: (name, constructor) => {
      assert(!definitions.has(name), `Repeated custom element definition: ${name}`);
      defineCalls++;
      definitions.set(name, constructor);
    }
  },
  document: {createElement: name => definitions.has(name) ? new (definitions.get(name))() : new NodeDouble()},
  setTimeout, clearTimeout, queueMicrotask, requestAnimationFrame: callback => callback(),
  setInterval: () => { const id = ++nextTimerId; intervalTimers.add(id); return id; },
  clearInterval: id => intervalTimers.delete(id)
};
vm.createContext(sandbox);
async function compileModule(url) {
  const module = new vm.SourceTextModule(source, {context: sandbox, identifier: url});
  await module.link(() => { throw new Error('The card must not import external code at load time'); });
  return module;
}
async function run() {
  if (input.scenario === 'legacy_classic_to_module') {
    vm.runInContext(source, sandbox, {filename: 'legacy-card.js'});
  }
  const module = await compileModule('/solar_pilot_static/solar-pilot-card.js?v=current');
  await module.evaluate();
  if (input.scenario === 'module_same_url_twice') {
    // SourceTextModule re-evaluation uses the same evaluated module record,
    // modelling the browser's already loaded module URL. No HTTP cache is tested.
    await module.evaluate();
  }
  if (input.scenario === 'module_next_url') {
    const next = await compileModule('/solar_pilot_static/solar-pilot-card.js?v=next');
    await next.evaluate();
  }
  assert.equal(definitions.size, 8);
  assert.equal(defineCalls, input.scenario === 'existing_old_stable_class' ? 7 : 8);
  assert(definitions.has(input.panelName), 'Current release has its own panel constructor');
  if (input.scenario === 'existing_old_stable_class') {
    assert.equal(definitions.get('solar-pilot-card'), LegacySolarPilotCard,
      'An already registered Lovelace compatibility class must remain intact');
    assert.notEqual(definitions.get(input.panelName), LegacySolarPilotCard,
      'The current sidebar must never instantiate the retained old card');
  }
  assert.equal(sandbox.window.customCards, catalog, 'Preserve the shared catalog array');
  for (const type of ['solar-pilot-card', 'solar-pilot-guide-card']) {
    assert.equal(catalog.filter(item => item.type === type).length, 1, `One catalog entry for ${type}`);
  }
  assert.equal(catalog.find(item => item.type === 'solar-pilot-card').name, 'SolarPilot · Control Center');
  assert.equal(catalog.find(item => item.type === 'solar-pilot-guide-card').name, 'SolarPilot · Actuele uitleg');
  assert.equal(catalog.filter(item => item.type === 'foreign-card').length, 2);
  assert(catalog.includes(firstForeign) && catalog.includes(secondForeign));
  assert(catalog.indexOf(firstForeign) < catalog.indexOf(secondForeign));
  assert.equal(firstForeign.extension.keep, true);
  // HA custom panels receive properties directly, without Lovelace setConfig().
  const card = sandbox.document.createElement(input.panelName);
  assert(!card.legacySolarPilotCard, 'Sidebar construction uses the current release');
  card.panel = {url_path: 'solar-pilot'};
  card.narrow = true;
  card.route = {path: ''};
  card.hass = {
    states: {'sensor.solar_pilot': {attributes: {
      solar_pilot: true, integration_version: input.backendVersion, mode: 'solar', devices: []
    }}},
    callService: () => { writes++; }
  };
  card.connectedCallback();
  assert(card._content.innerHTML.includes('SolarPilot'));
  assert(card._content.innerHTML.includes('Automatisch regelen'));
  assert(card._content.innerHTML.includes(input.backendVersion), 'Show backend version independently');
  assert(card._content.innerHTML.includes(input.cardVersion), 'Show the loaded card version independently');
  assert(card._content.innerHTML.includes('Integratie en kaart hebben verschillende versies'),
    'Explain a backend/card mismatch rather than presenting the backend version as the loaded UI');
  assert.equal(listeners.size, 1);
  assert.equal(intervalTimers.size, 1, 'One read-only freshness timer while the panel is connected');
  card.disconnectedCallback();
  assert.equal(listeners.size, 0);
  assert.equal(intervalTimers.size, 0, 'Release the freshness timer when leaving the panel');
  assert.equal(writes, 0);
  const guide = sandbox.document.createElement('solar-pilot-guide-card');
  guide.hass = {states: {'sensor.guide': {attributes: {
    solar_pilot_guide: true, title: 'Actuele regels', version: 'probe',
    sections: [{title: 'Boiler', paragraphs: ['Panasonic regelt zelf'], bullets: []}]
  }}}};
  assert(guide.shadowRoot.innerHTML.includes('Panasonic regelt zelf'));
  process.stdout.write(JSON.stringify({registered: definitions.size, catalogEntries: catalog.length, writes}));
}
run().catch(error => { process.stderr.write(error.stack); process.exitCode = 1; });
"""


def run_module_probe(scenario, *, dirty_catalog=False):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for ES module and panel lifecycle checks")
    result = subprocess.run(
        [node, "--experimental-vm-modules", "--no-warnings", "-e", MODULE_PROBE, str(CARD)],
        input=json.dumps({"scenario": scenario, "dirtyCatalog": dirty_catalog,
                          "panelName": "solar-pilot-panel-" + re.sub(r"[^a-z0-9]+", "-", VERSION.lower()).strip("-"),
                          "cardVersion": VERSION, "backendVersion": "99.0.0-beta.1"}),
        text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("scenario", [
    "module_once", "module_same_url_twice", "module_next_url", "legacy_classic_to_module",
    "existing_old_stable_class",
])
def test_actual_module_loading_keeps_single_registration_and_constructs_ha_panel(scenario):
    assert run_module_probe(scenario) == {"registered": 8, "catalogEntries": 4, "writes": 0}


def test_actual_module_repairs_only_its_own_existing_catalog_duplicates():
    assert run_module_probe("module_next_url", dirty_catalog=True) == {
        "registered": 8, "catalogEntries": 4, "writes": 0,
    }
