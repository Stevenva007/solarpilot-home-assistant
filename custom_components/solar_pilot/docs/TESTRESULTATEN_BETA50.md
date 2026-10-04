# SolarPilot 1.0.0-beta.50 — testresultaten

Datum: **2026-10-04**

## Bronbasis en gebruikersbewijs

Beta.49 op commit `ae3936749f40c0a575c8867ccaecbddf9fa61702`, tree `a9b37e533369811e8b16c285ba09864b6d7ff765` is de codebasis. Beta.49 is werkelijk gepubliceerd en haar pakketten zijn gecontroleerd; oudere tags en releasebestanden blijven onveranderd. De historische 2464 beta.49-tests worden niet als nieuwe beta.50-uitvoering opgevoerd.

De aangeleverde beta.49-schermen tonen circa 5 kW vrije injectie, geen gemelde actieve/onzekere koeling, een voorstel van 60 °C naast een native tankdoel van 50 °C en daarna opnieuw een stabiliteitscontrole van 60 seconden. De gebruiker bevestigt dat de wachttijd telkens opnieuw begint. Deze schermen tonen geen volledige opdracht-/timerhistorie, nieuwe doelbevestiging of fysieke tankopwarming.

## Definitieve softwaregate

De volledige samengestelde suite is uitgevoerd op de definitieve beta.50-bronboom: **2511 geslaagd in 17.08 s**, nul fouten en nul overgeslagen tests. Dit is 47 testgevallen meer dan de historische beta.49-suite van 2464: 29 beleids-/runtimegevallen en achttien echte boilerkaartweergaven in Node VM. De oude resultaten zijn geen nieuwe uitvoering.

| Controle | Resultaat |
| --- | --- |
| Volledige software-suite | 2511 geslaagd, 17.08 s |
| Werkelijke Node VM-kaartweergaven | 31 geslaagd: achttien boiler en dertien klimaat, opgenomen in de volledige suite |
| Python-bronsyntax | 65 modules geslaagd |
| JSON-syntax | Vier bestanden geslaagd |
| JavaScript-syntax | Kaart en optieshulp geslaagd |
| Actuele uitleg en gegenereerde hulp | Versie beta.50, hash `e4dd5ccfe591288d`, 432 hulpvelden consistent |
| Handoff, publieke preflight, repositoryvalidatie en diffcontrole | Geslaagd |
| Offline voorbeeld | Met fictieve gegevens opnieuw opgebouwd; geen HA-verbinding of toestelopdracht |

Gerichte regressies controleren de blijvende stabiliteitskandidaat tijdens opdrachtrust, het behouden minimuminterval sinds de laatste werkelijk verstuurde doelopdracht, geen extra volledige zonne-wachttijd bij verlopen opdrachtrust en geen start-hysterese of eigendom voor een onuitgevoerd voorstel. Onuitgevoerde 55 °C-voorstellen tijdens observatie, wachten op andere opdrachten of een geweigerd native doelbereik mogen niet bij minder PV alsnog starten via de vasthouddrempel; een passend eigen werkelijk doel behoudt zijn legitieme hold. Werkelijk verloren zonnebewijs, koeling, ontbrekende gegevens of te grote meetgaten behouden hun bestaande bescherming en vereisen waar nodig een nieuwe stabiliteitsperiode.

De achttien boilerkaartproeven voeren de echte Node VM-rendercode uit voor actuele opdrachtrust, serialisatie en native doelgrenzen in zowel overzicht als warmwaterdetailkaart. Voorstel, native doel en tankmeting blijven afzonderlijk; zonder runtime-status blijft het bestaande beschermende terugvalbericht beschikbaar. De dertien behouden klimaatkaartgevallen blijven in dezelfde suite opgenomen. Er zijn geen volledige browserproeven opnieuw uitgevoerd. Dit is softwarebewijs, geen geladen live kaart of fysieke apparaatrespons.

## Publicatie en installatie

De afzonderlijke publicatiecontrole staat bij de [beta.50-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.50) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. Beide pakketten worden afzonderlijk tegen die exacte tag gecontroleerd; beta.49-publicatiebewijs is geen beta.50-publicatiebewijs.

Geen live Home Assistant-installatie of fysieke toestelactie is in deze werksessie uitgevoerd. Softwaretests en HA-doubles bewijzen geen compressorstart, bereikte tanktemperatuur of gemeten energievoordeel. Er worden geen geforceerde AUTO/OFF-/DHW-/Wallbox-/AEG-opdrachten of algemene leerreset gebruikt om acceptatie te claimen.
