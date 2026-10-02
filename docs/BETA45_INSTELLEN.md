# SolarPilot 1.0.0-beta.45 — instellen en controleren

Beta.45 corrigeert uitsluitend de exacte adapterherkenning voor latere Panasonic-boilerdoelbevestiging. De live koppeling is **Aquarea Smart Cloud 1.0.61**, met domein `aquarea`. Zij schrijft eerst optimistisch het gevraagde doel in Home Assistant en vraagt pas na tien seconden geforceerd op. Beta.44 herkende alleen `panasonic_cc`; haar live `ha_state`-bevestiging na vijf seconden was geen bewijs voor de vertraagde beveiliging.

## Bewezen uitgangspunt

Beta.44 is gepubliceerd onder de onveranderlijke tag `v1.0.0-beta.44`, commit `5bbfa16cbc9453a818fb825fe16c447792ed63a2`. Validate `37022762657`, beide ZIP's, HACS-installatie en geladen backend/kaart op Core 2026.9.4 zijn gecontroleerd. De beta.44-softwaregate behaalde 1760 Python-tests en veertien browsercontroles; dit is niet het beta.45-totaal.

De normale wizard en native taakguard zijn gecontroleerd. Verse WATER en PUMP zijn gelezen; PUMP maakte `space_climate_busy=true`. Dit meldt een taak en bewijst geen HEAT/COOL of exclusief compressorvermogen. Opslaan en teruglezen van de afzonderlijke maandagdeadline zijn getest zonder APP-ticket, herarming of START. Bijvoorbeeld maandag 10:00 naast een gewone deadline 13:00 is een optionele productkeuze; hier wordt geen persoonlijk schema gepubliceerd. Gemeten afwascyclusleren blijft uit zonder geschikte exclusieve W-meter.

De gerichte reviewroute is gecontroleerd, maar een vroege `ha_state`-bevestiging vóór tien seconden gebruikte de verkeerde adapterroute. De installatie is daarom voor beta.45-controle gepauzeerd. Beta.45 is nog niet gepubliceerd of geïnstalleerd; een latere doelwaarneming is nog niet live bevestigd. Persoonlijke bedientijden en tank-/doelwaarden worden niet gepubliceerd.

## Softwarecontrole en voorbereiding

De definitieve beta.45-softwaregate is groen: **1773 Python-tests in 10.05 s**, **veertien browsercontroles** met nul fysieke actuatoroproepen, actuele uitleg (`8eb8458f093da416`), handoff, validatie, publieke preflight, beide JavaScript-syntaxcontroles en diffcontrole. Publicatie en liveacceptatie blijven afzonderlijke stappen.

1. Behoud de gecontroleerde beta.45-bron en het volledige testverslag; zie `TESTRESULTATEN_BETA45.md`. Herhaal de gate bij verdere bronwijzigingen.
2. Publiceer een nieuwe onveranderlijke tag `v1.0.0-beta.45`; wijzig beta.44 of oudere tags/assets niet.
3. Controleer de werkelijk gedownloade release-ZIP's tegen die tag en leg SHA-256 vast.
4. Maak vóór installatie een actuele volledige Home Assistant-back-up. Een eerdere versleutelde volledige NAS-back-up vóór beta.44 is bevestigd, maar is geen herstelproef en bevat niet vanzelf later opgeslagen instellingen.
5. Laat een actieve beschermde cyclus afwerken. Gebruik geen STOPRESET of nieuwe APP-aanvraag om updateacceptatie af te dwingen.
6. Noteer modus, boilerstatus, native taakbron, maandagdeadline en toesteltoestanden.

## Upgrade zodra beta.45 is gepubliceerd

1. Installeer exact `1.0.0-beta.45` via HACS en herstart Home Assistant volledig.
2. Controleer backendversie en vernieuwde kaart afzonderlijk. Een HACS-download of manifestnummer bewijst niet dat nieuwe code geladen is.
3. Houd **Alleen bekijken** of **Pauze** tijdens bron-/reviewcontrole.
4. Controleer de geregistreerde adapterherkomst van het native water-heaterdoel: exact `aquarea` of `panasonic_cc`, geen afleiding uit een naam of label.
5. Controleer tankmeting, gemeld doel, handmatige/krachtige functies, fabrikant-hygiëne, koel-/ruimteactie, P1/PV en eventuele wachtende opdracht.
6. Gebruik alleen waar vereist de bestaande gerichte boilerreview buiten **Automatisch regelen** en zonder pending opdracht. De knop schrijft zelf geen temperatuur.
7. Hervat Auto alleen na bruikbare bronnen en gecontroleerde beveiligingen. Forceer geen 60 °C- of Powerful-proef.

## Latere doelbevestiging

Voor een herkende adapter telt een onmiddellijke lokale echo niet als bevestiging. Er moet minstens tien seconden na de opdracht een passende nieuwe Home Assistant-rapportage beschikbaar zijn. De status kan dat tonen als `delayed_ha_state`; een oude `ha_state` vóór die grens is geen bewijs voor deze route.

Ook een latere rapportage kan cloudcache zijn. De guard bewijst geen onafhankelijk LIVE apparaatbericht, compressoractiviteit of bereikte tanktemperatuur. Timeout, afwijkend doel en handmatige overname blijven beschermd; onzekerheid veroorzaakt geen blinde herhaalopdrachten.

Andere water-heateradapters houden hun bestaande contract. Native ruimteactie en expliciete taakbron blijven afzonderlijke read-only informatie. De geïnstalleerde Aquarea-klimaatadapter gebruikt gepatchte `current_action`; zij wordt niet als altijd verkeerde AUTO-weergave beschreven.

## Wat niet verandert

- Wallbox blijft volledig read-only; extra 60 °C krijgt geen Wallboxkrediet.
- AEG-startveiligheid, deadlines, beschermde cycli en proportionele reserves blijven behouden.
- Normaal warmwatercomfort, avondvoorraad, koeling, eigendom, hygiëne en elektrische grenzen blijven leidend.
- Powerful wordt niet automatisch als boilerboost gebruikt; de afzonderlijke installateursinstelling DHW capacity blijft ongewijzigd.
- Geen leerreset of stille activering van gemeten cyclusleren zonder geschikte exclusieve meter.

## Rollback

Kies **Pauze**, laat beschermde cycli afwerken en herstel de onveranderlijke beta.44-release of een gecontroleerde volledige back-up. Herstart Home Assistant en bevestig backend/kaart. Beta.44 bevat nog de gemiste `aquarea`-ACK-herkenning; gebruik daarom geen vroege doelweergave als beveiligingsbewijs en hervat niet onbeoordeeld Auto.

Zie `TESTRESULTATEN_BETA45.md` en `ACTUELE_WERKING.md`.
