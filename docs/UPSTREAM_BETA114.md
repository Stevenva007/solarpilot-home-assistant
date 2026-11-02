# Upstreambroncontrole voor beta.114

## Aquarea en SDK — 2 november 2026

De officiële defaultbranch-HEADs, nieuwste gepubliceerde stabiele releases en opgeloste tagcommits zijn opnieuw online gecontroleerd.

| Bron | Defaultbranch en HEAD | Stabiele release en opgeloste commit |
|---|---|---|
| [Aquarea](https://github.com/wpatrik14/home-assistant-aquarea) | `main` · `76f7e84c98897a7ef354ea8f1e5a6f34d0a71b4b` | `v1.9.1` · dezelfde commit; gepubliceerd 1 november 2026, 18:52:58 UTC |
| [SDK](https://github.com/wpatrik14/aioaquarea) | `main` · `55da9428ddf43ed26f2386d79c43d50cf4d9da0c` | `v1.5.0` · dezelfde commit; gepubliceerd 23 oktober 2026, 15:00:23 UTC |

Beide HEADs en stabiele tagcommits zijn identiek aan het inhoudelijk beoordeelde beta.113-checkpoint. Er is geen nieuwe upstreamdiff te verwerken. De daar volledig beoordeelde Aquarea v1.9.0→v1.9.1-loginbackoff verandert geen apparaat-, zone-, tank-, taak- of energieperiodecontract. Een wachtende of mislukte bronpoll geeft geen nieuwe actuele meting.

Het machineleesbare checkpoint behoudt de opgeloste commits, `review_result=no_additional_changes` en `compatibility_claim=false`. De nieuwe controledatum is geen claim van een nieuwe providerfix, geslaagde fysieke proef of reeds geïnstalleerde upstreamversie. Deze release installeert of wijzigt de bronintegraties niet.

## Marstek — bronbetekenis en diagnostiek

Het bestaande native contract blijft [taurgis/has-marstek-local-api v1.12.0](https://github.com/taurgis/has-marstek-local-api/releases/tag/v1.12.0), opgelost naar `97e70c6959c5784c17b291a32c3ed5fe54d7215c`. De vastgepinde [sensorbeschrijvingen](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/helpers/sensor_descriptions.py) en [parser](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/pymarstek/data_parser.py) onderscheiden batterij-AC `ongrid_power`, DC `battery_power` en woning-CT `em_total_power`. Voor de ondersteunde native OnGrid-bron betekent positief ontladen naar huis/net en negatief laden. SoC gebruikt het afzonderlijke `battery_soc` uit ontvangen `bat_soc`.

Beta.114 gebruikt dit bestaande onderscheid voor een duidelijke fout bij een bekend verkeerde native meetsoort of tekenkeuze. Geen apparaatsnaam, integratiedomein of modelnaam alleen bewijst een AC-meetrol. Een bronbevestiging wordt niet uit een export of update afgeleid. De gebruiker kiest en controleert de bestaande meting bewust.

De [coordinator](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/coordinator.py), bestaande [UDP-client](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/pymarstek/udp.py) en [ResponseRouter](https://github.com/taurgis/has-marstek-local-api/blob/97e70c6959c5784c17b291a32c3ed5fe54d7215c/custom_components/marstek/pymarstek/response_router.py) blijven het ontvangen veldbewijs en de oorspronkelijke tijden leveren. De al bestaande beta.113-controles op bronkwaliteit, veldpresence, oorspronkelijke ontvangsttijd, cachegrens en gewijzigde binding blijven gelden. Een extra diagnostische code verruimt deze voorwaarden niet en levert geen nieuwe actuele watt.

De diagnostiek publiceert alleen noodzakelijke categorische broninformatie, waaronder verwacht en aangetroffen native veld. Zij neemt geen ruwe antwoordcache, IP-adres, MAC-adres of private apparaatidentiteit over. Geen extra RPC, polling, cachemutatie of fabrikantbediening. De AC-bevestiging verleent geen actuatorrecht.

De nominale Marstek-capaciteit van 5,12 kWh blijft fabrikantinformatie uit de in UPSTREAM_BETA113.md vermelde officiële brochure. Die capaciteit bewijst geen actuele vermogensmeting, meetdekking of beschikbare reserve.

Zie [het bronregister](UPSTREAM_BRONNEN.md). De releasegate controleert de actuele Aquarea-/SDK-stand opnieuw vóór publicatie.
