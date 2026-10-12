# SolarPilot beta.80 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.80** · 12 oktober 2026

De volledige lokale suite op de definitieve productiebron is geslaagd: **5247 tests in 102.49 seconden**, waaronder **122 nieuwe regressiegevallen**. De wijzigingen zijn afzonderlijk beoordeeld. Een naburige zone/tank mag geen native bewijs leveren; die gevonden grens is hersteld en opnieuw gecontroleerd.

## Concrete wijziging

De ondersteunde oudere Aquarea-provider bewaart een coordinator in de native HA-entry en vernieuwt een getypeerde `DeviceStatus` binnen hetzelfde `DeviceImpl`. De bestaande moderne adapter wachtte op een vervangen toestelobject en herkende deze andere echte poll niet. Beta.80 leest beide geverifieerde contracten; exacte entry-, device-, zone- en tankidentiteit blijven vereist. Alleen een werkelijk nieuwe geslaagde providerpoll maakt de terugmelding actueel.

De oorspronkelijke koeltoestemming is behouden: het algemene SG-profiel vraagt lokale condensbevestiging óf verse betrouwbare native context die mogelijke koeling uitsluit. De nieuwe diagnose toont welke bestaande bron ontbreekt, oud is, AUTO niet kan duiden, een conflict geeft of koelbedrijf meldt. Diagnostiek, tankopwarming, sterilisatie, watts en automatisch gevonden displaybronnen geven geen nieuwe koeltoestemming.

Gecontroleerde primaire upstream-contracten: [native coordinator](https://github.com/cjaliaga/home-assistant-aquarea/blob/main/custom_components/aquarea/coordinator.py), [native entry-opslag](https://github.com/cjaliaga/home-assistant-aquarea/blob/main/custom_components/aquarea/__init__.py), [gepinde aioaquarea 0.7.2 implementatie](https://github.com/cjaliaga/aioaquarea/blob/v0.7.2/aioaquarea/core.py) en [getypeerde gegevens](https://github.com/cjaliaga/aioaquarea/blob/v0.7.2/aioaquarea/data.py). Er is geen extra gebruikersdependency geïnstalleerd of in het manifest toegevoegd.

## Uitgevoerde lokale controles

| Controle | Resultaat |
|---|---|
| Volledige pytest-suite | 5247 geslaagd; 0 mislukt; Python 3.12.14 |
| Nieuwe native adaptergevallen | 59 |
| Nieuwe monitor-/SG-/frontenddiagnosegevallen | 43 |
| Sterilisatie als niet-blokkerende SG-status | 20 |
| Beide frontendmodules | Node-syntax gecontroleerd; Node v24.19.0 |
| Productie-Python, Python-tools en component-JSON | AST/JSON parsebaar |
| Actuele uitleg, optiehulp en mirrors | Versie 1.0.0-beta.80; 345 optievelden; gelijk |
| Handoff, openbare privacy-preflight en SG-opdrachtgrens | Geslaagd |
| Diffcontrole | `git diff --check` geslaagd |

De definitieve lokale volledige run gebruikte `python -B -m pytest -q -p no:cacheprovider`. Testgegevens zijn fictief; eigen huislabels, screenshots, bron-ID’s en exports zijn niet naar de publieke bron gekopieerd. Gerichte suites overlappen en worden niet bovenop het volledige testaantal opgeteld.

De native regressies toetsen werkelijke statusvervanging, listener-/enumcontract, dezelfde oude status, optimistische en geneste mutatie, mislukte poll, ongeobserveerde vervanging, herladen, ontbrekende/verkeerde entry, naburige zone en losgekoppelde/naburige tank. SG-tests toetsen START en verlenging met geplande/actieve/onbekende sterilisatiemelding en behoud van de werkelijke bron-, fase-, voorrangs- en elektrische guards. UI-tests toetsen oorspronkelijke meldtijden, verval zonder nieuw HA-bericht, details, escape en begrensde diagnose.

## CI op de exacte releasebron

De definitieve bron wordt daarna via [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) beoordeeld. Alleen dezelfde exacte commit met alle vijf geslaagde gates mag publiceren:

1. Repositorycontroles, volledige suite, syntax en 29 daadwerkelijke native PowerShell-publisherproeven.
2. HACS-validatie.
3. Hassfest.
4. Echte Home Assistant Core 2026.10.0: setup, platforms, reload, unload, behoud van immutable configuratie/privéarchief en echte optionele bronselectoren.
5. Echte Chromium: alle bestaande beta.79-browserproeven plus `check_cooling_ui80.py` met 72 scenario’s over drie schermen en vier breedtes, oorspronkelijke bronverval, behoud van uitleg/invoer, escape, 12 SG-configuratieroutes en geen instellingenopslag of toestelcommando.

Chromium en PowerShell ontbreken lokaal; die echte proeven zijn uitsluitend via de bijhorende brongebonden CI-run bewezen zodra zij slagen. Lokale frontend-unitproeven gebruiken Node en HA-doubles. Oudere geslaagde runs vormen geen beta.80-bewijs.

## Pakket- en publicatiebewijs

De immutable annotated tag `v1.0.0-beta.80` benoemt de exacte releasecommit waarvan dit verslag onderdeel is. De workflow vergelijkt vóór upload de hele bestandsset en inhoud met die bron. Na publicatie downloadt hij alle vier bestanden opnieuw en vergelijkt bron-SHA, bytes en SHA-256:

- `SolarPilot-v1.0.0-beta.80-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.80-local.zip`
- `BETA80_INSTELLEN.md`
- `TESTRESULTATEN_BETA80.md`

Succes vereist de stap **Download and verify published four assets against the exact tag** met `download_verified: true`. Bekijk de exacte tagcommit en bijhorende push-run bij [release beta.80](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.80). Dit bronverslag claimt vooraf geen toekomstig run-ID of geslaagde fysieke test.

## Behouden gegevens en bewijsgrenzen

Alle beta.79-auditcorrecties, geldige instellingen, bronbindings, prioriteiten, lokale Panasonic SG-percentages/koelwaarde, APP-aanvragen/deadlines, modellen en historie blijven behouden. Panasonic blijft SG-only, Wallbox read-only en AEG één native START per geldige belading. Geen automatische condensbevestiging, reset, tweede regeling of nieuwe hardware.

De softwarecorrectie herkent beschikbare echte providerinformatie; zij repareert geen weggevallen cloudbron en bewijst geen aanwezige fysieke condensbeveiliging. Bestaande harde guards kunnen SG daarom bij werkelijk ontbrekend of onveilig bewijs blijven begrenzen. Upgrade en rollback naar beta.79 staan in [BETA80_INSTELLEN.md](BETA80_INSTELLEN.md).

Bouwbasis: gepubliceerde beta.79 commit `1aab2043fa7a446e3f814bf515e4e9480a1cd6a2`, tree `c3025c593ac2185d2b9c8062dcf7d0e4d3dfe169`, main-run `38256645498`. Dat is uitsluitend herkomstbewijs; beta.80 heeft haar eigen brongebonden controles en pakketverificatie.
