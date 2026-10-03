# SolarPilot 1.0.0-beta.48 — testresultaten

Datum: **2026-10-03**

## Bronbasis

Beta.47 op commit `468291ad4a1f8050e71d2a842e434d93ecb8a104` is de absolute codebasis. Beta.47 en oudere tags en releasebestanden blijven onveranderd. Historische testaantallen worden niet als beta.48-resultaat gebruikt.

## Definitieve softwaregate

De volledige samengestelde suite is uitgevoerd op de definitieve beta.48-bronboom: **2170 geslaagd in 8.72 s**, exitcode 0. Dit is 286 testgevallen meer dan de historische beta.47-suite van 1884; de oudere resultaten worden niet als nieuwe uitvoering opgevoerd.

| Controle | Resultaat |
| --- | --- |
| Volledige Python-suite | 2170 geslaagd, 8.72 s |
| Werkelijke Node VM-kaartweergaven | Acht geslaagd, opgenomen in de volledige suite |
| Python-bronsyntax | 65 bestanden geslaagd |
| JSON-syntax | Vier bestanden geslaagd |
| JavaScript-syntax | Kaart en optieshulp geslaagd |
| Actuele uitleg en gegenereerde hulp | Versie beta.48, hash `7e00ab66b2698a93`, 432 hulpvelden consistent |
| Handoff, publieke preflight, repositoryvalidatie en diffcontrole | Geslaagd |
| Offline voorbeeld | Met fictieve gegevens opnieuw opgebouwd; geen HA-verbinding of toestelopdracht |

De regressiedekking bewaakt blijvende handmatige OFF-bescherming, vaste HEAT/COOL, eigen coast en harde comfortgrenzen, per-zone herstel, geen replay van onzekere opdrachten of vrijgave door late AUTO-echo, latere HA-bevestiging en timeout. Zij controleert confidence voor werkelijk benodigde respons, transparante modelstatus/aantallen, forecasturen zonder gaten en feedback uitsluitend na bevestigde opdrachten. Ontbrekende acties worden geen idle-leerbewijs; geldige leerdata en instellingen blijven behouden.

Ook behouden herstartherstel, operationele bronversheid/restored/ongeldige waarden, nieuw post-START-fasebewijs, fout/interlock boven handmatige toestelvraag, dynamische-prijsgaten/vaste terugval, geïsoleerd faseleren en selectief opslagherstel zijn gedekt. Opdrachtjournalen en wederzijdse DHW-/klimaat-/batterijserialisatie worden gecontroleerd, inclusief read-only afhandeling van pending opdrachten wanneer een module uitstaat en veilige verwijdering. Alle bestaande DHW-/AEG-/prioriteits-/Wallboxgrenzen blijven onderdeel van de samengestelde suite.

Er zijn geen volledige browserproeven opnieuw uitgevoerd. De acht Node VM-gevallen voeren de echte kaart-rendercode uit en zijn geen bewijs van een geladen live Home Assistant-kaart of fysieke apparaatrespons.

## Publicatie en installatie

De publicatiecontrole staat bij de [beta.48-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.48) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. Pakketverificatie wordt afzonderlijk tegen die exacte tag uitgevoerd.

Geen live Home Assistant-installatie of fysieke toestelactie is in deze werksessie uitgevoerd. Softwaretests bewijzen geen bereikte temperatuur, fysieke verwarm-/koelrespons of gemeten energievoordeel. Er worden geen geforceerde AUTO/OFF-/DHW-/Wallbox-/AEG-opdrachten of leerreset gebruikt om acceptatie te claimen.
