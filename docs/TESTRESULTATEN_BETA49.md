# SolarPilot 1.0.0-beta.49 — testresultaten

Datum: **2026-10-04**

## Bronbasis

Beta.48 op commit `a7df7688806ee128242058631a000c640e1243dd`, tree `11ade811d25f296ab84d6e0209776a615ab0099d` is de codebasis. Beta.48 is werkelijk gepubliceerd en haar pakketten zijn gecontroleerd; oudere tags en releasebestanden blijven onveranderd. De historische 2170 beta.48-tests worden niet als nieuwe beta.49-uitvoering opgevoerd.

## Definitieve softwaregate

De volledige samengestelde suite is uitgevoerd op de definitieve beta.49-bronboom: **2464 geslaagd in 13.90 s**, nul fouten en nul overgeslagen tests. Dit is 294 testgevallen meer dan de historische beta.48-suite van 2170; oudere resultaten worden niet als nieuwe uitvoering opgevoerd.

| Controle | Resultaat |
| --- | --- |
| Volledige software-suite | 2464 geslaagd, 13.90 s |
| Werkelijke Node VM-klimaatkaartweergaven | Dertien geslaagd, opgenomen in de volledige suite |
| Python-bronsyntax | 65 modules geslaagd |
| JSON-syntax | Vier bestanden geslaagd |
| JavaScript-syntax | Kaart en optieshulp geslaagd |
| Actuele uitleg en gegenereerde hulp | Versie beta.49, hash `8b9a30084c8ddf0f`, 432 hulpvelden consistent |
| Handoff, publieke preflight, repositoryvalidatie en diffcontrole | Geslaagd |
| Offline voorbeeld | Met fictieve gegevens opnieuw opgebouwd; geen HA-verbinding of toestelopdracht |

De regressiedekking omvat batterijserialisatie met gewone lasten, AEG-deadline/vermogensoverdracht en klimaatverwijdering; nieuw P1-bewijs; duurzame commandointentie, verse postissue power-ACK, SoC-eenheden/versheid, neutraal setpoint én vermogen bij verwijderen, native-neutraalrepresentatie en directe pre-call hercontrole na opslag. Fouten, tussentijdse veranderingen of ontbrekende bronnen veroorzaken geen retry, fysieke aanroep of onterechte klaarstatus. Veilige Observe/Pauze-vrijgave en vervangende batterijtargets behouden handmatige doelen, echte eigen flow, readonly-/foutstromen en native grenzen.

Forecaststaart/gaten blijven onbekend; actuele ontbrekende PV wordt geen nul-leerbewijs. Een volledig gemeenschappelijk evaluatievenster behoudt ontbrekende staart buiten de beoordeling en weigert binnengaten. UTC/DST-roosters, volledige 92/96/100-kwartierreplay, echte nulprijzen en veilige vaste terugval bij ongeldige prijs/tijd zijn gedekt. Gestructureerde pseudonimisering bewaart schema/eenheden/enums, korte en historische labels, gewone en batterij-IDs en hun joins, ook bij botsingen met machinevelden. Setup/unload/startafbreking, ongeldige afzonderlijke records met geldig-sibling-behoud en klimaatdeactivatie/bindingswijziging bij eigen OFF/pending/onbereikbare zone blijven onder regressiecontrole. Alle beta.48-grenzen blijven onderdeel van de samengestelde suite.

De dertien Node VM-gevallen voeren de echte klimaatkaart-rendercode uit, inclusief een werkelijk geëvalueerde horizon van acht uur tegenover 48 ingestelde uren en ontbrekend/nulbewijs zonder volledige-dekkingsclaim. Er zijn geen volledige browserproeven opnieuw uitgevoerd. Softwaretests en deze rendergevallen bewijzen geen geladen live Home Assistant-kaart of fysieke apparaatrespons.

## Publicatie en installatie

De publicatiecontrole staat bij de [beta.49-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.49) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. Pakketverificatie wordt afzonderlijk tegen die exacte tag uitgevoerd; beta.48-publicatiebewijs is geen beta.49-publicatiebewijs.

Geen live Home Assistant-installatie of fysieke toestelactie is in deze werksessie uitgevoerd. Softwaretests en HA-doubles bewijzen geen fysieke batterijrespons, bereikte temperatuur of gemeten energievoordeel. Er worden geen geforceerde AUTO/OFF-/DHW-/Wallbox-/AEG-opdrachten of algemene leerreset gebruikt om acceptatie te claimen.
