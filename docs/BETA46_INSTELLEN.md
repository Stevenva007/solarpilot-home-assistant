# SolarPilot 1.0.0-beta.46 — instellen en controleren

Beta.46 corrigeert een onnodige blokkering van extra sanitair warm water. In beta.45 kon een algemene Panasonic-taakmelding `PUMP` of de AUTO-modus zwaarder wegen dan een actuele native `aquarea`-klimaatactie `idle/off`. Daardoor kon de extra zonnebuffer op het gewone doel blijven wachten, ook als de klimaatbron geen actieve verwarming of koeling meldde.

Een groot getoond overschot geeft op zichzelf geen opdrachtvrijgave. Beta.46 herstelt de volgorde van bronbewijs; de bestaande zonnevoorwaarden, prioriteiten en beveiligingen blijven daarnaast nodig.

Een vóór beta.46 opgeslagen koel-/onzekerheidstijd wordt conservatief behouden: de oorspronkelijke oorzaak is niet betrouwbaar te reconstrueren. Een bestaande koeluitloop of bescherming tijdens een native warmwatertaak kan daarom nog tijdelijk gelden. De upgrade wist geen herinnerde echte koeling.

## Bronbasis en wijziging

De bronbasis is de bestaande beta.45-hoofdbranch op commit `9cddb043f4e6b1547eaa9487e057692ffb1d1a5b`. De gepubliceerde beta.45-tag blijft onveranderd op commit `507f74183f51b3517b077d05a455e4f169824f69`.

| Bronbewijs | Gevolg voor een nieuwe extra zonnebuffer |
| --- | --- |
| Exact geregistreerde `aquarea`, actuele native `hvac_action=idle/off` | De klimaatguard kan vrijgeven, ook in AUTO/HEAT_COOL en bij een algemene `PUMP`-taak. |
| Werkelijke `cooling` | Koellimiet en ingestelde rusttijd hebben voorrang. |
| Werkelijke `heating/preheating/defrosting` | Met ruimtecomfortvoorrang aan wacht een nieuwe extra buffer. |
| Ontbrekende, restored, oude of onbeschikbare klimaatbron | Extra buffer blijft beschermd; een taakmelding vervangt de ontbrekende klimaatbron niet. |
| Oudere `panasonic_cc` in AUTO/HEAT_COOL met `idle/off` | Blijft onduidelijk zonder een actuele expliciete `IDLE/WATER`-taak. `PUMP` geeft geen vrijgave. |
| Onbekende informatie die later betrouwbaar wordt | Geen nieuw verzonnen halfuur koelrust; alleen eerder bewezen koeling blijft haar bestaande uitloop volgen. |

De ruwe taak en `space_activity_status` blijven afzonderlijke diagnostiek en leerinformatie. `PUMP` bewijst geen verwarmrichting, koelrichting of compressorvermogen en wordt niet als een normale rustsample aangeleerd alleen omdat de DHW-guard mag vrijgeven.

## Voor de upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.45-release voor rollback.
2. Laat een beschermde afwas- of andere cyclus afwerken; gebruik geen STOPRESET voor de update.
3. Noteer modus, gemeld boilerdoel, eventuele manual hold/pending opdracht en bestaande bronkoppelingen. Bestaande instellingen en leerdata worden behouden.
4. Laat afzonderlijke concurrerende boilerautomatiseringen uit zolang SolarPilot de regeling uitvoert.

## Upgrade

1. Installeer exact `1.0.0-beta.46` via HACS zodra die release beschikbaar is, of vervang met het lokale pakket uitsluitend `custom_components/solar_pilot`. Bewaar bestaande `userfiles` en Home Assistant-opslag.
2. Herstart Home Assistant volledig. Controleer daarna de backendversie en vernieuwde kaart afzonderlijk; alleen een manifestnummer of HACS-download bewijst geen geladen code.
3. Controleer tijdens **Alleen bekijken** of **Pauze** de echte bronherkomst, klimaatversheid, ruwe `hvac_action`, taakmelding, P1/PV, tankmeting, handmatige functies, hygiëne en pending opdrachten.
4. Voor de native Aquarea Smart Cloud-koppeling moet de klimaatbron exact uit `aquarea` geregistreerd zijn. Een naam of label met Panasonic of Aquarea erin geeft geen vertrouwen.
5. Gebruik alleen waar nodig de bestaande gerichte boilerreview buiten **Automatisch regelen** en zonder pending opdracht. Zij schrijft zelf geen temperatuur; deze update heft een bestaande beschermende pauze niet automatisch op.
6. Hervat gewone automatische regeling na broncontrole. Observeer een natuurlijke toegestane doelopdracht; forceer geen 60 °C-proef of Powerful-actie om een diagnoseveld te vullen.

## Wat te controleren bij voldoende zon

Bij een verse native `aquarea`-actie `idle/off` mag een algemene `PUMP`-taak de klimaatguard niet langer op ruimtebedrijf laten wachten. De totale warmwaterreden kan nog een andere geldige wachtrede tonen: zonnestabiliteit, rust tussen opdrachten, onvoldoende overschot na reserves, koeluitloop na echte koeling, manual hold, hygiëne of elektrische grenzen.

Het normale doel blijft standaard 50 °C met een bewaakte comfortgrens van 46 °C. Extra overschot blijft maximaal 60 °C en krijgt geen Wallboxkrediet. Een lopende AEG-beurt behoudt haar conservatieve reserve; echte ruimteverwarming behoudt haar ingestelde voorrang. Er ontstaat geen automatisch 55 °C-tussenprofiel.

De beta.45-doelbevestiging blijft intact: voor exact geregistreerde `aquarea` en `panasonic_cc` telt de onmiddellijke optimistische doelweergave niet. Een passende nieuwe Home Assistant-rapportage na minstens tien seconden is vereist. Ook die rapportage bewijst geen onafhankelijke fysieke meting of bereikte tanktemperatuur.

## Test- en installatiestatus

De definitieve softwaregate en eventuele publicatie-/pakketcontrole staan in `TESTRESULTATEN_BETA46.md`. In deze werksessie is geen live Home Assistant-verbinding beschikbaar; een beta.46-installatie of fysieke opwarming is hier niet bevestigd.

## Rollback

Kies **Pauze**, laat beschermde cycli afwerken en herstel de onveranderlijke beta.45-release of een gecontroleerde volledige back-up. Herstart Home Assistant en bevestig backend/kaart en beveiligingen. Beta.45 behoudt de vertraagde `aquarea`-doelbevestiging maar bevat nog de te brede taak-/AUTO-blokkering die beta.46 corrigeert. Laat automatische regeling gepauzeerd als de relevante bron-/reviewcontrole niet slaagt.

Zie `ACTUELE_WERKING.md`, `TESTRESULTATEN_BETA46.md` en het actuele `OVERDRACHT.md`.
