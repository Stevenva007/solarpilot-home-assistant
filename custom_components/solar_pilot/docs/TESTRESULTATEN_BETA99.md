# SolarPilot beta.99 — test- en publicatieverslag

Versie: **1.0.0-beta.99** · 18 oktober 2026

Bouwbasis: gepubliceerde beta.98 `b79d06bbe7950538a317ccf060828c5fb65111bb`, tree `7004dbdfe145d445738e3e034a8d24d7d9cdcd09`. Alle regressies gebruiken fictieve toestellen, bronnen en waarnemingen. De aangeleverde afbeeldingen onderbouwen de onleesbare weergave; zij bewijzen geen specifieke oorzaak van historische brononderbrekingen.

## Getoetst gedrag

De compacte sessieweergave behoudt de geregistreerde taakperioden en hun bewijsniveau. Oorspronkelijke chronologie is uitklapbaar. Ondersteuning blijft een afzonderlijke gelijktijdige waarneming. Een periode met positieve fractieseconden mag niet verdwijnen doordat API-kloktijden tot seconden zijn geformatteerd. Een echt meetpunt zonder duur krijgt geen fictieve looptijd. Parent-/daggrenzen, DST, ongeldige data, onbekende tijd, leesrechten en uitsluitend leesbare bediening blijven vereist. Geen nieuw dagtotaal, achteraf opgetelde energie of taakclassificatie.

De native bronregressies moeten een nieuwe provider-generatie vóór haar echte bevestiging uitlezen: die uitlezing is eerst onbekend maar mag het daaropvolgende echte bericht niet verbruiken. Alleen dat werkelijk nieuwe geldige bericht kan de weergave, actie- of programmalezing herstellen. Een uitlezing zelf, mislukte callback, teruggezette flag, cachegeneratie die in-place naar LIVE is veranderd, hergebruik van een afgekeurd statusobject en een gewijzigde binding mogen geen nieuw bewijs geven. Alle oorspronkelijke bron-, mode-, tijd-, koel- en actuatorgrenzen blijven behouden.

De uitgebreide historiecontrole omvat gewone en gearchiveerde switch-/number-/script-/afwastoestellen, Wallbox-laadperioden, bestaande SG-lagen en huidige gekoppelde bronhistorie voor batterijen en overige sturingen. De nieuwe broncatalogus is alleen leesbaar, beperkt tot expliciet geconfigureerde bronrollen en filtert op de leesrechten van de aanvrager. Hij geeft geen archiefwaarden of private historische ACL-identiteiten terug. De bestaande apparaathistorie blijft haar volledige historische leesrechten controleren. Het openen van de native Home Assistant-historyweergave vereist opnieuw de eigen HA-bronrechten en kent de eigen recorderdekking.

De huidige boilertemperatuur en het ingestelde doel openen rechtstreeks hun exacte toegestane bron. De gesloten routekeuze onderscheidt ingestelde bronnen van de bestaande gecontroleerde native tankdetectie. Bronherbinding, ingetrokken leesrechten, meerdere rollen op dezelfde entiteit en een ontbrekende of tegenstrijdige bron mogen geen andere grafiek openen. Een berekend SG-doel en historische waarden zonder bijbehorende bron blijven gewone tekst. De catalogus leest ook voor deze route uitsluitend configuratie en gecontroleerde registratiegegevens, geen bronwaarden of historie.

De oorspronkelijke conservatieve status-only-afwijzing blijft voor de legacy-route behouden, naast de moderne bronvolgordecorrectie. Bestaande koelregressies zijn niet versoepeld. De DOM-doubles en exacte constructorlijst zijn uitgebreid voor de nieuwe echte dialoog; de oorspronkelijke lifecycle-, define-once- en no-write-asserties blijven vereist.

## Actuele upstreamcontrole

Op 18 oktober 2026 om **18:42:20 UTC** zijn alle acht GitHub-records opnieuw gecontroleerd. Aquarea v1.8.0/main/tag `8722cf22e5a5752406aea1ba79b2cf48d4deedf3` en SDK v1.4.0/main/tag `893065a81c014cb9aa1d3350446d61c01bccf3b9` zijn ongewijzigd sinds beta.98. Het nieuwe checkpoint vergelijkt dezelfde commits en vermeldt `no_additional_changes`. De historische inhoudelijke review staat in `AQUAREA_UPSTREAM_REVIEW_BETA98.md`; de huidige bronregistratie staat in `UPSTREAM_BRONNEN.md` en `upstream_review.json`.

## Uitgevoerde validatie

- Volledige suite op de definitieve productiebron met Python 3.13.16: **7737 geslaagd in 169,66 seconden**; geen mislukte of overgeslagen tests.
- Gerichte frontendregressies: **177 geslaagd**, met compacte toestelreadout, oorspronkelijke details, nauwkeurige warmtepompperioden, bron-/gebruikerswissels en directe boilerlinks. De afzonderlijke onafhankelijke UI-/navigatiecontrole bevat **91** gevallen; aantallen overlappen en worden niet opgeteld.
- Gerichte backend-/bron-/geschiedenistests: **265 geslaagd**. De onafhankelijke bronrechtencontrole bevat **106** gevallen over beide schema-engines; geen blokkades gevonden.
- Beide echte Chromium-gates geslaagd op de definitieve kaart: gewone toestelgeschiedenis/bronkeuze en warmtepompgeschiedenis. Inclusief 320/390-pixel touch, muis, toetsenbord, herweergave en vertraagde antwoorden; exacte `hass-more-info`-historyweergave; directe temperatuur-/doelbron; geen stuuropdrachten. De compacte toestelreadout is aanvullend geometrisch en met hit-test gecontroleerd zodat balk en cursor bereikbaar blijven. Screenshotcontrole bevestigt dit op 320 pixels.
- Echte **Home Assistant Core 2026.10.0 / Python 3.14.2**: normale én actuele-SG-fixture slagen voor setup, reload en unload. De werkelijke geregistreerde broncatalogus/schema, echte Core-gebruikersgroepen en READ-rechten, injectie-/unloadafwijzing en configuratiebehoud zijn gecontroleerd; `source_history_registered_current_read_only_acl=true`, **0 fysieke serviceaanroepen**.
- Python-syntaxis van **94** componentbestanden, Node-syntaxis, privacy-/structuurcontrole, overdracht, actuele uitleg en Panasonic-/SG-grenzen slagen. Actuele gids: **038485ea5df510d9**. `git diff --check` is schoon.

## Publicatievoorwaarden

Alle vijf Validate-gates moeten op de definitieve PR-bron slagen vóór merge: repository/privacy/documentatie, PowerShell en volledige testsuite; HACS; Hassfest; echte Home Assistant setup/reload/unload; Chromium. Dezelfde main-bron doorloopt de gates opnieuw vóór automatische publicatie.

De immutable annotated tag `v1.0.0-beta.99` moet naar de geteste main-commit wijzen. Vier releasebestanden worden vóór upload en na opnieuw downloaden bytegelijk met die bron gecontroleerd, inclusief grootte en SHA-256:

- `SolarPilot-v1.0.0-beta.99-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.99-local.zip`
- `BETA99_INSTELLEN.md`
- `TESTRESULTATEN_BETA99.md`

Bestaande tags en assets worden niet overschreven. Privé-export, woningwaarden en bronidentiteiten worden niet gepubliceerd. De softwaretests bewijzen geen fysieke Panasonic-/Shelly-reactie of live installatie.
