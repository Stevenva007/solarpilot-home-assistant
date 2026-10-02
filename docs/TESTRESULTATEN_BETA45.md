# SolarPilot 1.0.0-beta.45 — testresultaten

Datum: **2026-10-02**

> **Softwarematig klaar voor publicatie:** de definitieve beta.45-bron behaalde **1773 geslaagde Python-tests in 10.05 s** en **veertien geslaagde browsercontroles**, met nul fysieke actuatoroproepen. Publicatie, nieuwe pakketten, installatie en latere livebevestiging zijn nog open. Beta.44 is werkelijk gepubliceerd, geïnstalleerd en geladen; haar resultaten blijven afzonderlijke historie.

## Exact aangetoonde oorzaak

De live Aquarea Smart Cloud **1.0.61** heeft domein `aquarea`. De geïnstalleerde water-heaterbron publiceert eerst optimistisch het gevraagde doel, doet daarna de cloudopdracht en vraagt pas na exact tien seconden geforceerd status op. Beta.44 herkende alleen `panasonic_cc`, waardoor deze echte koppeling de generieke `ha_state`-route gebruikte.

Na gecontroleerd hervatten werd een vroege bevestiging met `ha_state` vóór tien seconden waargenomen. Dit is geen livebewijs van de anti-optimistische guard. De adapterherkenning in beta.45 omvat uitsluitend exact geregistreerde `aquarea` en `panasonic_cc`, zonder naamheuristiek. Persoonlijke bedientijden en temperatuurwaarden worden niet gepubliceerd.

De geïnstalleerde Aquarea-klimaatbron gebruikt gepatchte `current_action` voor HEATING/COOLING/IDLE. De oudere `panasonic_cc`-AUTO-beperking wordt niet zonder bewijs aan deze installatie toegeschreven.

## Definitieve beta.45-softwaregate

- Volledige Python-regressiesuite: **1773 geslaagd in 10.05 s** op de definitieve samengestelde bron; geen afgeleid totaal uit losse suites.
- Gerichte regressies omvatten beide exact herkende adapterdomeinen, onbekende adapters, registratierelaties, onmiddellijke echo, latere rapportage, timeout, herstart en bestaande review-/eigendomslimits.
- Alle **veertien browsercontroles** zijn groen op fictieve gegevens, met **nul fysieke actuatoroproepen**.
- Actuele-uitlegcontrole, handoff, repositoryvalidatie en publieke preflight zijn groen; uitleg-hash **`8eb8458f093da416`**, **432 optieshulpvelden**.
- Beide JavaScript-syntaxcontroles en `git diff --check` zijn groen; versie- en documentconsistentie zijn gecontroleerd.

Deze softwaregate bewijst geen fysieke toestelactie, publicatie of geladen Home Assistant-versie. De drie tijdens tests gegenereerde cachemappen zijn herstelbaar buiten de repository geplaatst; geen gebruikersbestanden zijn verwijderd.

## Bewezen beta.44-basis

- Onveranderlijke tag `v1.0.0-beta.44`, commit `5bbfa16cbc9453a818fb825fe16c447792ed63a2`, geslaagde Validate `37022762657`.
- Werkelijk gecontroleerde release-ZIP's, HACS-installatie, volledige herstart en geladen backend/nieuwe kaart beta.44 zijn afzonderlijk bevestigd op Core 2026.9.4.
- Beta.44-softwaregate: **1760 Python-tests in 11.68 s**, **veertien browsercontroles**; hash `65b54c9797e55bb4`. Dit zijn historische resultaten voor beta.44.
- Native taakbron via gewone wizard opgeslagen: vers WATER/geen ruimtebusy en daarna vers PUMP/ruimtebusy. Geen HEAT/COOL- of compressorvermogensclaim.
- Opslaan en teruglezen van de afzonderlijke maandagdeadline zijn getest via de normale wizard, zonder APP-ticket/herarming/START. Bijvoorbeeld maandag 10:00 bij een gewone deadline 13:00 is een productkeuze, geen universele standaard of hier gepubliceerd persoonlijk schema.
- De gerichte reviewroute is gecontroleerd zonder fout of wachtende opdracht. Door de ACK-mismatch is de installatie voor beta.45-controle gepauzeerd; de vroege bevestiging bewijst geen latere ACK of fysieke opwarming.
- Afwascyclusleren bleef terecht uit: een exclusieve W-meter ontbreekt. Geen fictief volledig gemeten profiel of claim dat alle leermodules actief zijn.

## Open publicatie en liveacceptatie

Beta.45-tag, GitHub-CI, publicatie en nieuwe ZIP-checksums bestaan hier nog niet als bevestigd resultaat. Bestaande beta.44-tags/assets blijven onveranderlijk.

Na gecontroleerde installatie moeten backend én kaart beta.45 worden bevestigd. Een passende doelwaarneming na minstens tien seconden moet afzonderlijk worden gecontroleerd; zij blijft HA/cloudrapportage en geen onafhankelijk fysiek meetbewijs. De nieuwe beta.45-ACK-route is nog niet live bewezen. Een gewone review of geladen versienummer mag dat bewijs niet vervangen.

Geen fysieke AEG-START/STOP, Wallbox-opdracht, geforceerde 60 °C-proef, Powerful of leerreset uitvoeren om een test te laten slagen.

Zie `BETA45_INSTELLEN.md` voor installatie, guardgrenzen en rollback.
