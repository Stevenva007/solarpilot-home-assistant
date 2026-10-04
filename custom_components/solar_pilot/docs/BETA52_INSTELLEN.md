# SolarPilot 1.0.0-beta.52 — instellen en controleren

Beta.52 onderscheidt tijdelijke bronwacht van een echte opdrachtfout. Een oude, ontbrekende of onbeschikbare toestelrapportage wordt automatisch opnieuw gelezen; de kaart vraagt hiervoor geen **Controle afronden**. Verkeerde vereiste bronkoppelingen krijgen een configuratiemelding. Echte fouten en onzekere opdrachten behouden hun bestaande controle en bescherming. De analyse-export leest effectieve read-only configuratiemappings en hun expliciet gekoppelde bronnen volledig.

## Bronbasis en gegevensbehoud

De codebasis is de werkelijk gepubliceerde beta.51 op commit `89fbec5148a759a8b961c158d494104402419fbf`, tree `fe5b74446ee3991ed8fa478355c0307181b55bfb`. Haar onveranderlijke release en gecontroleerde pakketten zijn de rollbackbasis. Updates zijn cumulatief: geldige instellingen, toestelbindingen, prioriteiten, modellen, historiek en APP-aanvragen blijven behouden. Deze diagnosecorrectie vraagt geen algemene reset, nieuwe bronheartbeat of extra fysieke toestemming.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.51-release.
2. Laat beschermde afwas- of andere cycli afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.52` via HACS zodra de release beschikbaar is, of vervang uitsluitend `custom_components/solar_pilot` met het juiste lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad daarna de webpagina; op Android stop je de Home Assistant-app volledig en open je haar opnieuw, op iOS kun je de weergave naar beneden trekken om te verversen.
5. Controleer backendversie en geladen kaart afzonderlijk. Open **Uitleg** en controleer beta.52 en hash `84be3bf69de3232c`. Een download of manifestnummer bewijst geen geladen kaartcode.

SolarPilot registreert haar gebundelde frontend zelf. Een extra Lovelace-resource, www-bestand of nieuw dashboard-YAML is niet nodig. De eerdere module-/paneelreparatie blijft behouden.

## Wat betekent de waarschuwing?

| Melding | Betekenis en juiste vervolgstap |
| --- | --- |
| Automatische herstartcontrole | Eerder beheerde toestelstatus wordt na herstart opnieuw gelezen. Wacht op echte bruikbare bronnen; de opgeslagen modus wordt daarna volgens bestaande voorwaarden hervat. |
| Automatische broncontrole | Toesteldata is tijdelijk oud, ontbrekend of onbeschikbaar. SolarPilot leest automatisch opnieuw bij gewone regelrondes. Bronherstel ruimt de wachtreden op; hiervoor is geen resetknop nodig. |
| Toestelgegevens controleren | Een vereiste koppeling of broneigenschap past niet. Controleer de genoemde bron en toestelinstellingen. Een reset repareert die configuratie niet. |
| Aandacht nodig / Opdrachtfout | Een echte opgeslagen fout of onzekere opdracht vraagt de bestaande gerichte controle. Een onbekende of nog actieve betrokken last wordt niet door een reset vrijgegeven. |

Een regelronde met ontbrekende brondata maakt geen blinde ON/OFF-, START- of boileropdracht. Minimumlooptijden, beschermde programma's en de 120 seconden bronversheid blijven behouden. Bij een directe **Controle afronden**-aanroep zonder foutjournal/herstelcontrole maar met alleen een bronprobleem meldt de backend de actuele wacht-/configuratiereden; hij claimt geen geslaagde alles-uit-reset en wist geen journal.

## Bronuitval gericht onderzoeken

De aangeleverde eerdere beta.51-export toont dat brondata tijdelijk ontbrak, terwijl geen pending opdracht of opdrachtfout was vastgelegd. De export bevatte door de read-only mappingfout onvoldoende effectieve configuratie en expliciete bronnen. Zij bewijst geen specifieke fysieke verbindingsstoring of de oorzaak van een later screenshot.

Bij een blijvende bronwacht controleer je het genoemde toestel en zijn gekoppelde HA-integratie, werkelijke beschikbaarheid en laatst ontvangen rapportage. Bij een configuratiemelding corrigeer je de genoemde koppeling. Download zo nodig een nieuwe **Export → Export samenstellen**; beta.52 bewaart effectieve configuratie en gekoppelde bronnen en registreert de probleemreden/soort in snelle analysepunten. Privacyfilters en pseudoniemen blijven behouden. Deel geen tokens, privébundels of private serveradressen en plaats de analyse-export niet op publieke GitHub.

## Behouden boiler- en toestelregels

Zonnestabiliteit en de minimumtijd sinds de laatste werkelijk verstuurde boilerdoelopdracht lopen afzonderlijk. Een voortdurend geldige afgeronde stabiliteitscontrole begint niet opnieuw alleen vanwege opdrachtrust. De standaard 1800 seconden sinds de laatste opdracht, koeling, hygiëne, eigendom, doelbevestiging en zichtbare uitvoeringswachtreden blijven gelden. Voorstel, gemeld Panasonic-doel en gemeten tanktemperatuur blijven apart.

Handmatige OFF-zones blijven uit tot expliciete gebruikers-AUTO. Beschermde afwascycli worden niet onderbroken; onzekere opdrachten krijgen geen blinde retry. De Wallbox blijft read-only. Geldige leerdata en alle bestaande actuator-, elektrische, comfort- en prioriteitsgrenzen blijven behouden. Geen Force DHW, Powerful, extra APP-aanvraag of algemene datareset.

## Teststatus en rollback

De softwaregate staat in `TESTRESULTATEN_BETA52.md`. Tests met HA-API-/DOM-doubles bewijzen de softwareclassificatie, export en kaartbediening. Zij bewijzen geen fysieke toestelverbinding, werkelijke browser-HTTP-levering of nieuwe live installatie. In deze werksessie is geen live Home Assistant-toegang of fysieke toestelactie uitgevoerd.

Voor rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.51-release of gecontroleerde volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart, actuele bronnen, eigendom en beveiligingen controleren**. Beta.51 behoudt de eerdere boiler- en paneelreparaties, maar bevat nog de algemene foutclassificatie bij tijdelijke bronwacht en onvolledige analyse-export van read-only configuratiemappings. Oude releasedocumenten blijven historie; het actuele `OVERDRACHT.md` beschrijft de huidige bron.
