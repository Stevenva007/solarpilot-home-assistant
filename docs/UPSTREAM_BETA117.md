# Upstreambroncontrole voor beta.117

## Aquarea en werkelijk vereiste SDK — 11 november 2026

De acht officiële GitHub-records zijn opnieuw gecontroleerd: repository-identiteit, defaultbranch, HEAD, nieuwste gepubliceerde stabiele release en opgeloste releasetag van beide bronnen. Beide repositories zijn publiek, gebruiken `main`, hebben geen open pull requests en hun nieuwste stabiele tag wijst rechtstreeks naar de actuele HEAD.

| Bron | Actuele publieke stand | Gepubliceerde stabiele release |
|---|---|---|
| [Aquarea](https://github.com/wpatrik14/home-assistant-aquarea) | `main` op `2ff80459a219330daf8c38341221075aaf9bfef8` | [v2.0.1](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v2.0.1), dezelfde commit, gepubliceerd 10 november 2026 om 20:08:44 UTC |
| [aioaquarea-ng](https://github.com/wpatrik14/aioaquarea) | `main` op `58bdd9bc3662950225fc1afc35ab7d084d5789b8` | [v1.6.0](https://github.com/wpatrik14/aioaquarea/releases/tag/v1.6.0), dezelfde commit, gepubliceerd 9 november 2026 om 00:33:45 UTC |

Het Aquarea-manifest v2.0.1 gebruikt `aioaquarea-ng>=1.6.0`. Dat is een runtimebereik, geen bewijs welke versie op een Home Assistant-installatie geladen is. Voor deze review is de werkelijk gepubliceerde SDK v1.6.0 exact op bovenstaande commit beoordeeld. SolarPilot installeert of upgradet Aquarea en de SDK niet.

## Inhoudelijke verschillen sinds het beta.116-checkpoint

De [Aquarea-diff v1.10.0→v2.0.1](https://github.com/wpatrik14/home-assistant-aquarea/compare/5d6a5a1fcdd36df5baf077741901e95357fc9bdc...2ff80459a219330daf8c38341221075aaf9bfef8) bevat v1.11.0, v2.0.0 en v2.0.1. PR171 voegt lokale vandaag-energie en opgebouwde lifetime-energie toe op basis van cloudhistorie. Dit zijn nieuwe eigen entiteittypen met andere reset-/volledigheidssemantiek; SolarPilot neemt ze niet automatisch over als de bestaande interval- of maandperiodebronnen.

De brekende PR181 verplaatst pompstatus met dezelfde unieke id van `sensor` naar `binary_sensor` en maakt pomprichting een enum met kleine waarden `idle`, `pump` en `water`. De Aquarea-entrymigratie behoudt waar mogelijk object-id en gebruikersaanpassingen, verwijdert daarna de oude sensor en laat Recorder-historie onder het oude entity-id staan. Bij een botsing blijft de migratie bewust open voor een volgende poging. SolarPilot zocht deze native rol alleen onder `sensor` en verloor daardoor na een geslaagde v2-migratie zijn aanvullende read-only taakcontext.

Beta.117 herkent voor exact dezelfde `*_pump_status`-unique-id zowel de historische sensor als de nieuwe binaire sensor. De bestaande Aquarea-config-entry, apparaatidentiteit, getypeerde SDK-pompwaarde, LIVE-statuspoll, oorspronkelijke rapporttijd en waardeovereenkomst blijven verplicht. Kleine richtingwaarden werden al genormaliseerd zonder hun getypeerde bron te vervangen. Als oude en nieuwe pompstatus tegelijk aanwezig zijn, wordt niet gekozen en blijft het contract onbekend. Dit voegt geen automatische sensorbinding of actuator toe.

V2.0.1 verwerkt PR184: privacy van accountgebonden clients, reconfiguregedrag, herhaalbare migratie en vertaalde fouten. De overige v2-wijzigingen omvatten seriële cloudcommando's per platform, vertalingen, iconen, kwaliteitsdocumentatie en foutafhandeling. SolarPilot neemt geen nieuwe cloudcommandoroute over. De twee nog open Aquarea-issues zijn [#165](https://github.com/wpatrik14/home-assistant-aquarea/issues/165), een gemelde provider/IP-403, en [#41](https://github.com/wpatrik14/home-assistant-aquarea/issues/41), een oudere migratiefout. Zij zijn geen gepubliceerde nieuwe code en geven geen bronactualiteit of compatibiliteitsbewijs. De SDK heeft geen open issues of pull requests.

De [SDK-diff v1.5.0→v1.6.0](https://github.com/wpatrik14/aioaquarea/compare/55da9428ddf43ed26f2386d79c43d50cf4d9da0c...58bdd9bc3662950225fc1afc35ab7d084d5789b8) komt uit PR26. Zij voegt `raise_on_error` en `retry_login` toe aan consumptierapporten en verandert alleen consumptiemanager, core/decorators, documentatie en tests. De door SolarPilot gecontroleerde taakparser, `operation_status`, `current_action`, LIVE/CACHED-kwaliteit en zoneopbouw zijn inhoudelijk ongewijzigd. De bestaande geladen-codecontrole blijft daarom capability-gebonden in plaats van een versienummer-allowlist.

## Grenzen

Deze verwerking herstelt alleen read-only taakpresentatie bij de nieuwe geregistreerde entiteitsvorm. Nieuwe lifetime/vandaag-energie wordt niet als oud dag-/maandbewijs gelabeld. Open issues, gemergede PR's, releases en lokale installatie blijven afzonderlijk. Er is geen claim dat v2.0.1 lokaal geïnstalleerd is, geen toekomstige compatibiliteitsgarantie en geen Panasonic-, Wallbox- of andere nieuwe schrijfbevoegdheid.
