# SolarPilot beta.96 — presentatie en Home Assistant-apparaatkoppeling

Versie: **1.0.0-beta.96** · Bouwbasis: gepubliceerde beta.95.

## Installeren

Maak eerst een actuele volledige privéback-up van Home Assistant. Installeer de gepubliceerde beta.96 via HACS zodra de vijf verplichte controles en de pakketverificatie geslaagd zijn. Herstart Home Assistant volledig en herlaad de browser/app. Verwijder de SolarPilot-configuratie-entry niet; behoud instellingen, userfiles, modellen en historie.

Een eerder lokaal aangepaste beta.95 kan rechtstreeks worden vervangen door de volledige beta.96. Dezelfde functionele correcties staan dan onder één herkenbaar versienummer in GitHub, de releasepakketten en HACS. Controleer backend- en kaartversie afzonderlijk. Een codewijziging in de Home Assistant-map wordt niet vanzelf naar GitHub gestuurd.

## Wat verandert

- De Panasonic-sensoren delen hun zware presentatieberekening per publicatie. Sensorwaarde en attributen gebruiken hetzelfde frame. De regelaar en exports kunnen rechtstreeks actuele gegevens blijven lezen; SG-contactwaarnemingen worden niet gecachet.
- De bestaande virtuele hub wordt vóór zijn kinderen geregistreerd. Op moderne Home Assistant-versies verwijzen kinderen naar de HA-hub-id en worden apparaten binnen de eigen configuratie-entry opgezocht. Identiteiten en gebruikersnamen blijven behouden. Oudere ondersteunde versies houden hun bestaande terugvalroute.
- De Aquarea 1.6.0-bronwijziging is beoordeeld: de vroegere dagsensoren leveren nu intervaldelta's. Deze tellen niet als dagelijks energie- of periodebewijs. De maandmeters en de oorspronkelijke bron-/actualiteitscontroles blijven apart. SolarPilot installeert of wijzigt de Aquarea-provider niet.

De update verandert geen regelgrenzen, bronactualiteitsgrens, fysieke bevoegdheden, rusttijd, lokale timer, AEG-startticket of PV-kalibratiefactor. De presentatiecache vernieuwt geen oorspronkelijke rapporttijd. Zij geeft geen extra stuur- of leerbewijs.

## Controleren

Controleer na de volledige herstart de SolarPilot-versie, de bestaande verbruikers en hun koppeling aan de hub. Bekijk of de Panasonic-sensoren actuele oorspronkelijke brongegevens tonen. Een gelijkblijvende waarde is niet automatisch verouderd; ontbrekende echte ontvangst blijft onbekend. Controleer nieuwe logmeldingen afzonderlijk van oude meldingen vóór de update.

De generieke integratiecorrecties staan in deze release. Privé YAML-sensoren, andere integraties en apparaatspecifieke instellingen horen bij de lokale installatie en worden niet naar deze repository gekopieerd.

## Rollback

Bewaar vóór herstel een volledige privéback-up. Geef een eigen SG-aanvraag alleen veilig vrij waar betrouwbaar mogelijk en onderbreek geen beschermde cyclus. Herstel zo nodig de oorspronkelijke beta.95-code met behoud van entry, userfiles en opslag; herstart Home Assistant volledig. Gebruik geen twee runtimes tegelijk.

De oorspronkelijke beta.95 kan de dubbele presentatieberekeningen en verouderde apparaatkoppeling opnieuw tonen. Het opslagschema verandert in beta.96 niet. Een oude onzekere of al verbruikte afwasaanvraag mag nooit door rollback opnieuw worden bewapend.

[Actuele werking](ACTUELE_WERKING.md) · [Testverslag](TESTRESULTATEN_BETA96.md) · [Overdracht](../OVERDRACHT.md)
