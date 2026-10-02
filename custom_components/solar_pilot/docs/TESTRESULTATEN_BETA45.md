# SolarPilot 1.0.0-beta.45 — testresultaten

Datum: **2026-10-02**

> **Gepubliceerd, geïnstalleerd en geladen:** de definitieve beta.45-bron behaalde **1773 geslaagde Python-tests in 10.05 s** en **veertien geslaagde browsercontroles**, met nul fysieke actuatoroproepen. Validate, onveranderlijke tag/release en beide gedownloade ZIP's zijn afzonderlijk gecontroleerd. HACS-installatie, volledige herstart, geladen backend én kaart beta.45 en gecontroleerd hervatten van Auto zijn bevestigd. Een nieuwe latere doelbevestiging blijft nog open; een oude beta.44-ACK is daarvoor geen bewijs.

## Exact aangetoonde oorzaak

De live Aquarea Smart Cloud **1.0.61** heeft domein `aquarea`. De geïnstalleerde water-heaterbron publiceert eerst optimistisch het gevraagde doel, doet daarna de cloudopdracht en vraagt pas na exact tien seconden geforceerd status op. Beta.44 herkende alleen `panasonic_cc`, waardoor deze echte koppeling de generieke `ha_state`-route gebruikte.

In beta.44 werd na gecontroleerd hervatten een vroege bevestiging met `ha_state` vóór tien seconden waargenomen. Dit is geen livebewijs van de anti-optimistische guard. De adapterherkenning in beta.45 omvat uitsluitend exact geregistreerde `aquarea` en `panasonic_cc`, zonder naamheuristiek. Persoonlijke bedientijden en temperatuurwaarden worden niet gepubliceerd.

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

## Bewezen publicatie en pakketcontrole

De [Validate-workflow 37029502122](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/37029502122) is geslaagd, inclusief alle vier jobs. De [beta.45-prerelease](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.45) is gepubliceerd op **2 oktober 2026 om 15:48:55 UTC**, onder onveranderlijke tag `v1.0.0-beta.45` op commit `507f74183f51b3517b077d05a455e4f169824f69`.

Beide gedownloade ZIP's zijn gecontroleerd tegen die tag: verifier `errors=[]`, **254 repositorybestanden** en **100 integratiebestanden**, integratie-inhoud bytegelijk aan de tag. Manifestversie, padveiligheid en afwezigheid van private/cachebestanden zijn gecontroleerd.

- `SolarPilot-v1.0.0-beta.45-GitHub-HACS.zip`: **1797247 bytes**; SHA-256 `d4e81596b92b164e646db5e7a0f904c389c837de98bb5a5cfb35d31fa7a1d32e`.
- `SolarPilot-v1.0.0-beta.45-local.zip`: **709748 bytes**; SHA-256 `0ec3b6bdb19584bd55c4068306ca98c3c9463beda13c3cf6660332deda525916`.

Beta.45 en oudere tags, ZIP-assets en release-documentassets blijven onveranderlijk. Deze latere hoofdbranch-documentatie wordt niet teruggeschreven naar bestaande releasebestanden. Een nieuwe versleutelde volledige NAS-back-up voor beta.45 is gereed bevestigd; geen herstelproef is uitgevoerd.

## Bewezen installatie en gecontroleerd hervatten

- HACS bevestigde geïnstalleerd én beschikbaar beta.45 en **Up-to-date**.
- Na een normale volledige Home Assistant-herstart op Core **2026.9.4** zijn backend/actuele uitleg en vernieuwde kaart afzonderlijk als **1.0.0-beta.45** bevestigd.
- De nieuwe boilerstatus meldt `target_adapter_domains=['aquarea']`, `ack_poll_min_s=10` en contract `later_ha_report_at_or_after_adapter_delay`. Dit bewijst de nieuwe adapterherkenning en ingestelde wachttijd, geen voltooide nieuwe ACK.
- De verse native taakbron is geldig; gemeld ruimtebedrijf houdt de extra zonnebuffer beschermd. Dit is geen onafhankelijke HEAT/COOL-, compressor- of vermogensmeting.
- Powerful, Force DHW en Force Heater stonden uit. Review/manual hold, fout en wachtende opdracht waren afwezig; een extra reviewhandeling was niet nodig.
- **Automatisch regelen** is na die controles via de normale Home Assistant-bediening hervat en teruggelezen. Het bestaande passende normale doel vereiste geen nieuwe doelopdracht. Er is geen proefstart, geforceerde opwarming of Powerful-activering voor acceptatie uitgevoerd.

## Nieuwe latere opdrachtbevestiging nog open

De bewaarde laatste succesvolle opdracht betreft nog de oudere beta.44-`ha_state` en is geen nieuwe `delayed_ha_state`-bevestiging. Observeer een volgende natuurlijke, toegestane doelopdracht: een passende rapportage na minstens tien seconden blijft afzonderlijk vereist. Forceer geen doelwijziging alleen om dit bewijs te verkrijgen.

Ook een latere rapportage blijft HA/cloudinformatie en geen onafhankelijk LIVE apparaatbericht, compressoractiviteit of bereikte tanktemperatuur. Gecontroleerd hervatten en geladen versie vervangen dit toekomstige ACK-bewijs niet.

Geen fysieke AEG-START/STOP, Wallbox-opdracht, geforceerde 60 °C-proef, Powerful of leerreset uitvoeren om een test te laten slagen.

Zie `BETA45_INSTELLEN.md` voor installatie, guardgrenzen en rollback.
