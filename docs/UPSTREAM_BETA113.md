# Upstreambroncontrole voor beta.113

## Aquarea en SDK — 2 november 2026

De officiële defaultbranch-HEADs, nieuwste gepubliceerde stabiele releases en opgeloste tagcommits zijn opnieuw online gecontroleerd.

| Bron | Defaultbranch en HEAD | Stabiele release en opgeloste commit |
|---|---|---|
| [Aquarea](https://github.com/wpatrik14/home-assistant-aquarea) | `main` · `76f7e84c98897a7ef354ea8f1e5a6f34d0a71b4b` | `v1.9.1` · dezelfde commit; gepubliceerd 1 november 2026, 18:52:58 UTC |
| [SDK](https://github.com/wpatrik14/aioaquarea) | `main` · `55da9428ddf43ed26f2386d79c43d50cf4d9da0c` | `v1.5.0` · dezelfde commit; gepubliceerd 23 oktober 2026, 15:00:23 UTC |

De [volledige Aquarea-vergelijking](https://github.com/wpatrik14/home-assistant-aquarea/compare/d3867f4143f7e2c15b84ed67c6e7ace2561f5f96...76f7e84c98897a7ef354ea8f1e5a6f34d0a71b4b) bevat twee commits en zeven gewijzigde bestanden. Alleen coordinator en manifest zijn productiecode. In de [vastgepinde coordinator](https://github.com/wpatrik14/home-assistant-aquarea/blob/76f7e84c98897a7ef354ea8f1e5a6f34d0a71b4b/custom_components/aquarea/coordinator.py) krijgt een geweigerde login met API_ERROR achtereenvolgens vijf, tien, twintig en maximaal dertig minuten wachttijd. Tijdens die wachttijd volgt UpdateFailed zonder nieuwe login; succes wist teller en deadline. Andere fouttypen starten deze loginwachttijd niet.

De device-, zone-, tank-, operation-status- en energieperiodecontracten veranderen niet; SDK is identiek. SolarPilot vraagt reeds een nieuwe geslaagde bronupdate. Wachten, mislukte polls en oude cache krijgen daardoor geen actuele taak-, UIT- of SG-toestemmingsbetekenis. Geen productieaanpassing aan SolarPilot of automatische upstream-update is nodig. De bestaande tests test_native_program56.py, test_cloud_energy_period91.py en test_operation_source_evidence83.py slaagden: 131 gevallen.

Het checkpoint bewaart voor Aquarea de beoordeelde basis v1.9.0 met review_result relevant_changes_processed; SDK blijft no_additional_changes. compatibility_claim blijft false. Bronreview bewijst geen lokale installatiecompatibiliteit of geïnstalleerde versie.

## Bestaande Marstek-integratie — native meetcontract

De native broncontrole is beoordeeld tegen [taurgis/has-marstek-local-api v1.12.0](https://github.com/taurgis/has-marstek-local-api/releases/tag/v1.12.0), opgelost naar commit `97e70c6959c5784c17b291a32c3ed5fe54d7215c`. Dit is een afzonderlijke community-integratie, geen door SolarPilot geïnstalleerde of bijgewerkte dependency. De gebruiker koppelt expliciet bestaande entiteiten; de werkelijk geladen bron moet het ondersteunde contract leveren.

De [sensorbeschrijvingen](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/helpers/sensor_descriptions.py) en [parser](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/pymarstek/data_parser.py) onderscheiden `ongrid_power` van `em_total_power` en `battery_power`. Voor Venus E 3.0 is de gekozen OnGrid-bron de getekende AC-poort: positief naar de woning/het net, negatief naar de batterij. Het monitorprofiel accepteert deze native power daarom uitsluitend met `discharge_positive`. SoC gebruikt `battery_soc`, afkomstig van `bat_soc`; beide bronnen worden onafhankelijk gecontroleerd.

De [coordinator](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/coordinator.py) en parser kunnen bij ontbrekende velden of mislukte deelvragen eerdere waarden blijven publiceren. Een nieuwe HA-rapporttijd of alleen een algemeen geslaagde poll bewijst daarom geen nieuwe power. SolarPilot verifieert de geladen entiteit, registrybinding en eigen coordinator, positieve `ES.GetStatus`-methodestatus, `es_status_fresh`, `has_fresh_data`, de geslaagde poll en de oorspronkelijke tijden.

De bestaande [UDP-client](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/pymarstek/udp.py) bewaart ontvangen antwoorden in zijn [ResponseRouter](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/pymarstek/response_router.py): ruwe response, bronadres en oorspronkelijke monotone ontvangsttijd. SolarPilot leest die bestaande cache uitsluitend mee. Het relevante numerieke veld moet aanwezig zijn, bij hetzelfde IP en dezelfde poort horen, met HA/coordinatordata overeenkomen en uiterlijk tijdens de voltooide poll ontvangen zijn.

De router ruimt zijn cache standaard na dertig seconden op. SolarPilot bewaart reeds passend veldbewijs daarom begrensd in geheugen, met ongewijzigde oorspronkelijke ontvangsttijd en maximaal de ingestelde bronleeftijd, standaard 120 seconden. Een gedeeltelijk antwoord zonder dit veld of HA-herpublicatie verlengt niets. Een nieuw passend antwoord met dezelfde waarde kan ook 0 W vernieuwen. Expliciete bronfouten maken de meting direct onbekend; gewijzigde binding/coordinator wist eerder bewijs. Ontbrekend bewijs bij de eerste lezing en niet-ondersteunde native vormen blijven onbekend. Expliciet gekozen onafhankelijke HA-bronnen gebruiken de gewone HA-broncontrole. Geen aanvullende RPC, polling, cachemutatie of actuatoractie; dit bronbewijs is geen onafhankelijke fysieke meetgarantie.

## Marstek-productbron

De officiële [Marstek-downloadpagina](https://marstekenergy.com/en-fr/pages/download-center) verwijst voor Venus E 3.0 naar de [EU-brochure](https://cdn.shopify.com/s/files/1/0746/1575/0952/files/MARSTEK_VENUS_E3.0_Brochure_EU_EN.pdf?v=1776130081). De specificatietabel op pagina 2 vermeldt model MARSTEK VENUS E 3.0, capaciteit 5,12 kWh en afzonderlijk 90% ontladingsdiepte. SolarPilot gebruikt de capaciteit als nominale profielinformatie, niet als gegarandeerde bruikbare AC-energie, vrije reserve of controlerecht.

Deze productbron bewijst geen specifieke Home Assistant-entiteit, API-veldnaam, polariteit of meetdekking. Het nieuwe profiel leest uitsluitend bewust geselecteerde bestaande HA-bronnen met bevestigde getekende AC-batterijbetekenis. Geen P1-/CT-woningbron, DC-waarde of absolute batteryPower zonder richting als vervanging. De bestaande Marstek-integratie blijft de gegevensbron; SolarPilot voegt geen polling of fabrikantbediening toe.

Zie [het bronregister](UPSTREAM_BRONNEN.md). De releasegate controleert de actuele Aquarea-/SDK-stand opnieuw vóór publicatie.
