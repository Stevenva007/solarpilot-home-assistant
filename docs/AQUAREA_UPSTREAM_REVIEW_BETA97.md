# Aquarea-bronreview voor beta.97

Gecontroleerd op **18 oktober 2026 om 13:09:46 UTC**, via de officiële publieke GitHub-repositories. Defaultbranches, actuele HEADs, nieuwste gepubliceerde stabiele releases en hun opgeloste tagcommits zijn afzonderlijk gecontroleerd. Dit document bevat geen gegevens uit een particuliere installatie en bewijst niet welke provider lokaal is geïnstalleerd.

| Bron | Defaultbranch en HEAD | Nieuwste stabiele release |
|---|---|---|
| [Aquarea](https://github.com/wpatrik14/home-assistant-aquarea) | `main`, `3151d7f196e45b671f3136c9220244fb8c10f2df`; commit van 18 oktober 2026 09:49:11 UTC | [v1.7.0](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.7.0), dezelfde commit; gepubliceerd 18 oktober 2026 09:49:22 UTC |
| [aioaquarea-ng](https://github.com/wpatrik14/aioaquarea) | `main`, `d859f3727556c8a07964affd61a038edfd2d353a`; commit van 10 oktober 2026 11:49:13 UTC | [v1.3.1](https://github.com/wpatrik14/aioaquarea/releases/tag/v1.3.1), dezelfde commit; gepubliceerd 10 oktober 2026 11:49:16 UTC |

## Verschillen sinds beta.96

De volledige [vergelijking Aquarea 1.6.0–1.7.0](https://github.com/wpatrik14/home-assistant-aquarea/compare/f127489774c61c1e97ee5eb5097257748d55d510...3151d7f196e45b671f3136c9220244fb8c10f2df) bevat twee commits: toevoeging van `auto_mode` (`8ba51a059f3b98ba9b4e38b07f3809f153d50887`) en de versieverhoging. De gewijzigde bestanden zijn `climate.py`, het manifest, README, documentatie en klimaatmappertests.

De [klimaatentiteit op de vaste nieuwe commit](https://github.com/wpatrik14/home-assistant-aquarea/blob/3151d7f196e45b671f3136c9220244fb8c10f2df/custom_components/aquarea/climate.py) voegt `auto_mode` toe: `heat` bij `AUTO_HEAT`, `cool` bij `AUTO_COOL`, uitsluitend wanneer de zone `hvac_mode: auto` heeft; anders `null`. Dit vertelt ook tijdens stilstand aan welke kant AUTO staat. `hvac_mode` en `hvac_action` veranderen niet. De getypeerde coordinatorpoll, tankstatus, schrijfopdrachten, energiesensoren en dependency `aioaquarea-ng>=1.3.1` veranderen evenmin.

De SDK-vergelijking met het eerdere checkpoint bevat nul commits of gewijzigde bestanden. De [parser van SDK 1.3.1](https://github.com/wpatrik14/aioaquarea/blob/d859f3727556c8a07964affd61a038edfd2d353a/aioaquarea/device_manager.py) koppelt globale `operation_status` nog aan `specialStatus`; [de getters en `current_action`](https://github.com/wpatrik14/aioaquarea/blob/d859f3727556c8a07964affd61a038edfd2d353a/aioaquarea/data.py) behouden hun bestaande betekenis. [PR12](https://github.com/wpatrik14/aioaquarea/pull/12) blijft open en niet gemerged, met head `ebe561274e1d79160814474c175cfdb3469f61e5` en laatste update 10 oktober 2026 12:44:17 UTC. Dit voorstel is geen vrijgegeven parsercorrectie.

## Beoordeling voor SolarPilot

SolarPilot onderscheidt de gekozen verwarmings-/koelrichting al via `ExtendedOperationMode.AUTO_HEAT` en `AUTO_COOL` van het gebonden native apparaat. Een nieuwe geslaagde providerpoll en de bestaande oorspronkelijke tijden blijven vereist. Het extra HA-attribuut verhelpt daardoor geen ontbrekende geselecteerde-programmainformatie waarvoor een nieuwe terugval nodig is.

Er komt geen productielogica voor dit attribuut bij. `auto_mode` bewijst geen actieve taak, compressorbedrijf, leerbare waarneming of SG-/koelvrijgave; ook een gewijzigd attribuut vernieuwt geen native polltijd. De runtimecontrole blijft gebaseerd op daadwerkelijk geladen parser-/gettersemantiek, zonder versie-allowlist. Historische onbekende gegevens krijgen geen nieuw bewijs achteraf.

De speciale regressies in `tests/test_aquarea_auto_mode97.py` controleren de nieuwe klimaatvorm met een getypeerde AUTO-poll en bewaken dat het attribuut geen ontbrekend of verlopen bronbewijs vervangt. De bestaande beta.96-regressie voor intervaldelta's blijft van toepassing: de Aquarea-verbruiksinterval van 15 minuten is geen SolarPilot SG-rusttijd en levert geen actuele vermogensmeting.

De nieuwe [melding bij issue132](https://github.com/wpatrik14/home-assistant-aquarea/issues/132#issuecomment-6248603978) over `hvac_action: off` bevat geen vrijgegeven oplossing; zij verandert de bovenstaande bronbeoordeling niet. De actuele uitkomst staat machineleesbaar in `docs/upstream_review.json`. De publicatiegate moet de upstreamstand opnieuw controleren voordat de release wordt gepubliceerd.
