# SolarPilot beta.117 — installatie en rollback

## Wat deze versie oplost

Aquarea v2.0.1 verplaatst de bestaande pompstatus van `sensor` naar `binary_sensor` en publiceert pomprichting als kleine enumwaarde. Beta.116 herkende de nieuwe pompstatus niet als native read-only rol. Daardoor kon SolarPilot na een providerupgrade de aanvullende warmtepomptaak als onbekend tonen, ook wanneer de onderliggende getypeerde status bruikbaar was.

Beta.117 volgt beide officiële entiteitsvormen op dezelfde unieke id, config-entry en Aquarea-apparaatbinding. De getypeerde LIVE-poll, pompwaarde, richting, zones, tankcontext en oorspronkelijke rapporttijden blijven noodzakelijk. Bij een dubbele of half afgemaakte migratie kiest SolarPilot niet. Dit wijzigt geen SG-regel, Panasonic-instelling of actuatorrecht.

## Bijwerken

1. Maak een volledige privé Home Assistant-back-up met SolarPilot-configuratie en -opslag.
2. Werk na gepubliceerde release via HACS bij naar **1.0.0-beta.117**.
3. Herstart Home Assistant volledig en herlaad browser of app zodat backend en kaart dezelfde versie gebruiken.
4. Behoud bestaande SolarPilot- en Aquarea-configuratie. Voeg geen nieuwe pompstatussensor toe en wijzig geen entity-id om deze update te laten werken.
5. Controleer de warmtepompkaart na een natuurlijke nieuwe Aquarea-poll. Een ontbrekende taak kan nog terecht wijzen op cachedata, oude rapporten, tegenstrijdige waarden, een open Aquarea-migratie of ontbrekende overige context.

SolarPilot installeert Aquarea v2.0.1 of SDK v1.6.0 niet. De upstreamversie die werkelijk op Home Assistant staat blijft een afzonderlijke lokale HACS-/integratiekeuze. Nieuwe Aquarea lifetime- en vandaag-energiesensoren worden niet automatisch gekoppeld of als oude SolarPilot-periodebron gebruikt.

## Rollback

Rollback naar beta.116 behoudt instellingen, modellen en historie, maar herkent na een voltooide Aquarea v2-migratie alleen de oude `sensor`-vorm. De read-only taakcontext kan dan opnieuw onbekend worden. Zet geen binaire sensor handmatig terug naar het oude domein en maak geen duplicaat; herstel voor een volledige rollback de passende privéback-up van provider én SolarPilot als ook Aquarea zelf wordt teruggezet.

De beta.116 SG-bronherstelwacht, Marstek-grenzen, twintigminutenminimum, vijftienminutenbuffers en alle overige veiligheidsvoorwaarden blijven in beta.117 ongewijzigd. Zie [TESTRESULTATEN_BETA117.md](TESTRESULTATEN_BETA117.md) en [UPSTREAM_BETA117.md](UPSTREAM_BETA117.md).
