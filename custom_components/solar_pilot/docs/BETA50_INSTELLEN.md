# SolarPilot 1.0.0-beta.50 — instellen en controleren

Beta.50 herstelt de herhaalde boilerstabiliteitscontrole terwijl de bestaande rust tussen doelopdrachten nog loopt. Bij voortdurend geldige zonnevoorwaarden blijft de afgeronde controle geldig. Het overzicht en de warmwaterdetailkaart tonen de echte uitvoeringswachtreden. De minimumtijd sinds een vorige doelopdracht, koelbescherming, bronversheid, eigendom en alle eerdere veiligheidsregels blijven behouden.

## Bronbasis en gegevensbehoud

De codebasis is de werkelijk gepubliceerde beta.49 op commit `ae3936749f40c0a575c8867ccaecbddf9fa61702`, tree `a9b37e533369811e8b16c285ba09864b6d7ff765`. Haar onveranderlijke release en gecontroleerde pakketten zijn de rollbackbasis. Updates zijn cumulatief: geldige instellingen, toestelbindings, centrale prioriteiten, klimaat-/PV-/faseprofielen, historiek en APP-aanvragen blijven behouden. Deze update vraagt geen algemene leerreset of nieuwe fysieke toestemming.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.49-release.
2. Laat een beschermde afwas- of andere cyclus afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.50` via HACS zodra de release beschikbaar is, of vervang uitsluitend `custom_components/solar_pilot` met het juiste lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig en controleer de backendversie en vernieuwde kaart afzonderlijk. Controleer onder **Uitleg** versie beta.50 en uitleg-hash `e4dd5ccfe591288d`.
5. Controleer actuele bronnen, herstelredenen, pending opdrachten, eigendom en apparaatbeveiligingen. Een download, versienummer of softwaretest bewijst geen fysieke opwarming.

## Twee boilerwachttijden

| Wachttijd | Betekenis | Wat beta.50 verandert |
| --- | --- | --- |
| Stabiliteitscontrole | De zonnevoorwaarden blijven gedurende de ingestelde tijd geldig; standaard 300 seconden. | Een voltooide controle begint niet opnieuw alleen omdat de opdrachtrust nog loopt. |
| Rust tussen doelopdrachten | Een extra verhoging wacht minstens de ingestelde tijd sinds de laatste werkelijk verstuurde doelopdracht; standaard 1800 seconden. | De bestaande duur en het beginpunt blijven behouden; de werkelijke uitvoeringswachtreden wordt zichtbaar. |

Die vorige doelopdracht kan ook een verlaging of herstel naar het normale doel zijn. Beide timers kunnen tegelijk lopen; zij worden geen reeks steeds nieuwe volledige zonnecontroles. Zodra beide voorwaarden voldaan zijn, kan de volgende gewone regelronde de verhoging vragen, mits alle andere guards nog passen. Werkelijk verlies van geldig zonnebewijs, koeling of een te groot meetgat kan de betrokken stabiliteitscontrole wel onderbreken. Een wachtend hoog voorstel krijgt geen eigendoms- of hysteresevrijgave alsof het doel al is toegepast.

Behoud de bestaande eigen waarden. Het inkorten van timers, uitschakelen van koelbescherming of wissen van leerdata is geen onderdeel van deze reparatie. Verlaging wegens echte netafname, nacht, koeling of Pauze en normaal doelherstel houden hun bestaande regels.

## Voorstel, gemeld doel en tanktemperatuur

Het overzicht en de warmwaterdetailkaart tonen de actuele regel- of uitvoeringswachtreden. Een gunstig zonneadvies verbergt de rust tussen doelopdrachten, wachten op een andere regelopdracht of een ongeschikt native doelbereik niet meer. Een nog niet uitgevoerde 55 °C-verhoging mag ook niet bij minder PV alsnog starten via de lagere vasthouddrempel; alleen een passend eigen werkelijk doel kan een bestaande fase vasthouden. Houd drie waarden uit elkaar:

- **SolarPilot-voorstel**: het berekende beleidsdoel; dit kan 60 °C zijn terwijl uitvoering nog wacht.
- **Panasonic-doel**: de actuele native doelrapportage; 50 °C blijft 50 °C totdat een passende terugmelding anders meldt.
- **Tanktemperatuur**: de werkelijke gekoppelde temperatuurmeting; ook een gemeld doel van 60 °C bewijst niet dat de tank die temperatuur bereikt heeft.

Voor exact geregistreerde `aquarea` en `panasonic_cc` blijft de bestaande doelbevestiging minimaal tien seconden en een passende nieuwe Home Assistant-rapportage vereisen. Een onmiddellijke optimistische echo telt niet. Die latere bronrapportage blijft HA-/cloudbewijs, geen onafhankelijke fysieke ACK of compressorstart. Een onzekere of foutieve opdracht krijgt geen blinde retry.

## Behouden bron- en veiligheidscontrole

Werkelijke koeling blijft extra warmte begrenzen. Actieve verwarming/preheating/defrosting behoudt de ingestelde ruimtecomfortvoorrang. Ontbrekende, oude, restored of onbeschikbare klimaatdata blijft beschermd. Actuele betrouwbare native `aquarea` idle/off gaat voor deze optionele DHW-guard vóór algemene PUMP-taakinfo; de oudere `panasonic_cc`-AUTO-ambiguïteit behoudt haar bestaande expliciete taakbewijs. Alleen bewezen koeling verlengt de koeluitloop.

Normaal doel standaard 50 °C, bewaakte comfortgrens 46 °C, extra overschot maximaal 60 °C en autonome fabrikantsterilisatie blijven behouden. Een groot zichtbaar overschot vervangt geen reserves, elektrische grenzen, prioriteit, eigendom of hygiënecontrole. Extra 60 °C krijgt nooit Wallboxkrediet. Panasonic bepaalt de eigen warmteproductie; SolarPilot vraagt geen Force DHW, Powerful, Force Heater of hoofdvoedingswijziging.

Handmatige OFF-zones blijven uit tot expliciete gebruikers-AUTO. Een lopende beschermde afwascyclus wordt niet onderbroken en een onzekere AEG-START wordt niet opnieuw verstuurd. Batterijopdrachten, nieuw P1-bewijs, forecastdekking, tijdroosters en veilig herladen behouden alle beta.49-regels. Een gewone herstartcontrole wordt automatisch afgewerkt zodra echte betrouwbare bronnen terugkeren; echte manual hold/fout of veranderd doel blijft beschermd.

## Installatieacceptatie en rollback

De softwaregate staat in `TESTRESULTATEN_BETA50.md`. Er is in deze werksessie geen live Home Assistant-toegang; beta.50-installatie, een nieuwe native 60 °C-doelbevestiging en fysieke tankopwarming zijn hier niet uitgevoerd. Observeer een volgende natuurlijke toegestane opdracht en passende tankrespons; gebruik geen geforceerde proefopdracht, extra APP-aanvraag of leerreset om acceptatie te claimen.

Voor rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.49-release of gecontroleerde volledige back-up herstellen → Home Assistant herstarten → backend/kaart, actuele bronnen, eigendom en beveiligingen controleren**. Beta.49 behoudt de eerdere audit- en veiligheidsregels, maar bevat nog de herhaalde boilerstabiliteitscontrole en verborgen uitvoeringswachtreden die beta.50 herstelt. Oude release-documenten blijven historische informatie; het actuele `OVERDRACHT.md` beschrijft de huidige bron.
