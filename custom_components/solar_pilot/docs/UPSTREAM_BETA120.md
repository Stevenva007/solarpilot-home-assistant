# Upstreambroncontrole voor beta.120

## Aquarea, prerelease en werkelijk vereiste SDK — 25 november 2026

De officiële publieke repositorymetadata, defaultbranch-HEADs, nieuwste gepubliceerde stabiele releases en opgeloste stabiele releasetags zijn opnieuw gecontroleerd. Daarnaast is de nieuwe Aquarea-prerelease afzonderlijk beoordeeld, zonder haar als stabiele release of geïnstalleerde dependency te behandelen.

| Bron | Actuele publieke stand | Gepubliceerde releases |
|---|---|---|
| [Aquarea](https://github.com/wpatrik14/home-assistant-aquarea) | `main` op `8d5180c5323ff25cd9eab3baf39261ad25969d9f` | Stabiel: [v2.0.1](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v2.0.1), commit `2ff80459a219330daf8c38341221075aaf9bfef8`, gepubliceerd 10 november 2026 om 20:08:44 UTC. Prerelease: [v3.0.0](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v3.0.0), commit `c804a96ac0017f72ef381b3798713a836d987b80`, gepubliceerd 25 november 2026 om 12:41:56 UTC. |
| [aioaquarea-ng](https://github.com/wpatrik14/aioaquarea) | `main` op `58bdd9bc3662950225fc1afc35ab7d084d5789b8` | Stabiel: [v1.6.0](https://github.com/wpatrik14/aioaquarea/releases/tag/v1.6.0), dezelfde commit, gepubliceerd 9 november 2026 om 00:33:45 UTC. |

Zowel Aquarea v2.0.1 als de v3.0.0-prerelease declareren `aioaquarea-ng>=1.6.0`. Dat bereik is geen bewijs van de werkelijk geladen versie op een Home Assistant-installatie. De gepubliceerde SDK v1.6.0 is ongewijzigd sinds het beta.117-checkpoint; taakparser, `operation_status`, `current_action` en LIVE/CACHED-contract hebben geen nieuwe diff.

## Commit-, PR-, issue- en releasestatus

PR189 verplaatste de integratie van `custom_components/aquarea` naar `custom_components/aquarea_smart_cloud` en voegde een entrymigratie toe; PR190 publiceerde v3.0.0. Beide zijn gemerged en hun code staat in de gepubliceerde prereleasetag. PR191 over aanvullende HACS-uitleg is zonder merge gesloten. PR192 heeft de domeinwijziging vervolgens op `main` volledig teruggedraaid. PR193 voegde alleen elf README-regels toe over handmatig naast Heishamon installeren. Daarom bevat de exacte diff van stabiele v2.0.1 naar de actuele defaultbranch geen productiecodewijziging.

De v3-tag blijft publiek en handmatig selecteerbaar als prerelease, maar is niet de nieuwste stabiele release en staat niet meer op de defaultbranch. Aquarea heeft geen open PR's. Alleen issue 165 over een gemelde HTTP-403 blijft open; zij bevat geen nieuwe gepubliceerde implementatie. De SDK heeft geen open issue of PR. Open of teruggedraaide code verleent geen bronactualiteit, installatiebewijs of controlerecht.

## Inhoudelijke compatibiliteitsverwerking

De v3-productiecode behoudt de v2.0.1-sensoren en dezelfde SDK-afhankelijkheid; de relevante runtimewijziging voor SolarPilot is de officiële pakket-/registrydomeinnaam. SolarPilot controleerde voorheen uitsluitend `aquarea` en zou een daadwerkelijk geladen v3-provider daardoor als onbekend behandelen, ook wanneer zijn getypeerde SDK-semantiek ongewijzigd is.

Beta.120 accepteert daarom `aquarea` en `aquarea_smart_cloud` als gesloten officiële domeinset. De keuze komt uit de werkelijk geladen provider en wordt niet uit een versienummer, entiteitsnaam of configuratievoorstel afgeleid. Registryplatform, config-entrydomein, apparaatidentifier, coordinator-module, unique-id, daadwerkelijk geladen module, geverifieerde SDK-capability, LIVE-status, bronwaarde en oorspronkelijke rapporttijd moeten allemaal hetzelfde domein en apparaat bewijzen. Twee geladen domeinen, een gemengde identiteit of een onbekende handmatige domeinnaam blijft onbekend. De bestaande pompstatusmigratie, periodebetekenis en alle conflictregels blijven gelden.

De energieperiodelezer accepteert onder hetzelfde exacte v3-domein alleen de reeds beoordeelde native dag-/maandklassen en behoudt hun oorspronkelijke UTC-periode en fetch-/rapporttijden. Nieuwe today/lifetime-entiteiten worden niet als oude perioden herlabeld. De analyse-export vermeldt uitsluitend één werkelijk geladen vaste provider en zijn lokale manifest-/pakketmetadata; parallel geladen kopieën zijn ambigu en worden niet gekozen.

## Grenzen

SolarPilot installeert, verwijdert, migreert of hernoemt Aquarea niet. De v3-prerelease wordt niet automatisch geselecteerd. Deze wijziging geeft geen nieuwe sensorbinding, providerpoll, dependency-monkeypatch, Panasonic-cloudopdracht, Wallboxbediening of ander actuatorrecht. Panasonic blijft SG-only via de bestaande afzonderlijke uitgang; de overige Panasonic- en Wallboxbronnen blijven read-only. Publieke broncontrole kan niet aantonen wat lokaal is geïnstalleerd en is geen garantie voor toekomstige, nog onbekende wijzigingen.
