# SolarPilot beta.107 — softwarevalidatie

## Actuele status

De volledige beta.107-suite slaagt lokaal met **8707 tests**, zonder fouten of overgeslagen tests. Daarvan zijn 40 nieuwe regressies voor broncoherentie, effectieve voorrang, stopuitleg en snelle diagnose. De 63 gerichte kaart-/module-/UI-controles slagen eveneens. De eerste volledige loop vond een achtergebleven kaartversie; na correctie slaagde de volledige suite opnieuw.

Actuele uitleg, overdracht, repositoryprivacy/structuur, SG-schrijfgrens, beide JavaScript-syntaxcontroles en de online upstreambroncontrole zijn gecontroleerd. De vijf commitgebonden CI-gates en de downloadvergelijking blijven verplicht vóór een geslaagde publicatie. De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) registreert die uitslag per exacte commit; deze lokale uitslag claimt geen uitgevoerde fysieke installatieproef.

De online upstreamcontrole van 25 oktober 2026 vergelijkt beide officiële defaultbranches, laatste stabiele releases en tagcommits met de bestaande inhoudelijke bronreview. De pins zijn ongewijzigd; zie [UPSTREAM_BETA107.md](UPSTREAM_BETA107.md).

## Nieuwe regressies

De nieuwe SG-coherentietests gebruiken fictieve bronnen. Ze controleren een recent maar onverenigbaar Wallboxrapport, herstel met behoud van de oorspronkelijke meettijd, behoud van onafhankelijk werkelijk restoverschot, de gezamenlijke volledige warmtepomp-/EV-bijdrage rond de 250 W-tolerantie en hercontrole na een latere PV-daling. Een al toegelaten SG-vernieuwing behoudt haar bestaande importbeleid; de ruwe netgrens blijft beslissend.

Voorrangsteksttests toetsen beide effectieve volgordes en tijdelijke Wallbox-voorrang zonder apparaatopdrachten. Nieuwe analysetests toetsen begrensde bronwaarden, oorspronkelijke rapporttijden, ontbrekende of onbruikbare brongegevens en behoud van het bestaande export-/privacycontract. De nieuwe diagnose is read-only en geeft geen aanvullende start-, lease- of herstartrechten.

## Verplichte publicatieprocedure

De definitieve head moet alle vijf bestaande GitHub-gates halen: repository/full-suite, HACS, Hassfest, Chromium en echte Home Assistant-startup. Main herhaalt de gates. Alleen daarna maakt dezelfde workflow beide ZIP-pakketten en beide release-documenten. De vier gedownloade assets moeten overeenkomen met de exacte tag en broncommit. Een oudere groene commit vervangt deze controles niet.

## Bewijsgrenzen

Een langere gewone wolkenbuffer kan de afzonderlijke maximale totale netafname niet omzeilen. Deze update verandert geen ingestelde grens, bufferduur, SG-capaciteit of bronkoppeling. De coherentiecontrole weigert alleen een onverenigbare voorwaardelijke EV-startbijdrage; ze kalibreert geen meter en bewijst geen fysieke oorzaak.

Er is geen fysieke SG-schakelproef, Wallbox-overdracht of meterkalibratie op een gebruikersinstallatie uitgevoerd. Een gesloten SG-contact of compressoractiviteit bewijst geen causale extra warmteopname. Bronrapporttijden in Home Assistant zijn niet noodzakelijk de fysieke meettijdstippen. Private exports en identificeerbare installatiegegevens blijven buiten de openbare repository.
