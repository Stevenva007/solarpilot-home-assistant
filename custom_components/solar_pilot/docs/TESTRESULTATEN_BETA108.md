# SolarPilot beta.108 — softwarevalidatie

## Actuele status

De volledige definitieve beta.108-suite slaagt lokaal met **8828 tests**, zonder fouten of overgeslagen tests. Daarvan zijn 121 nieuwe regressies voor de begrensde overdracht, echte runtime-/transportvoorwaarden, schermweergave en bewaard diagnosebewijs. Een vroege volledige loop vond drie bestaande opstartregressies: de nieuwe observatie schreef vóór het inlezen van bestaande opslag. De regeling observeert en bewaart nu pas na de geladen runtime; de oorspronkelijke tests en aanvullende opslagcontroles slagen in de volledige herhaling.

Actuele uitleg, overdracht, repositoryprivacy/structuur, SG-schrijfgrens, beide JavaScript-syntaxcontroles en de online upstreamcontrole zijn gecontroleerd. De vijf commitgebonden CI-gates en vergelijking van de vier gedownloade assets blijven voorwaarden voor geslaagde publicatie. De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) legt de uitslag per exacte commit vast.

De online upstreamhercontrole van 25 oktober 2026 is uitgevoerd: beide officiële defaultbranches, laatste stabiele releases en tagcommits zijn ongewijzigd tegenover de inhoudelijke bronreview. De pins staan in upstream_review.json; zie [UPSTREAM_BETA108.md](UPSTREAM_BETA108.md). Bronactualiteit is geen nieuwe compatibiliteitsverklaring.

## Getoetste nieuwe werking

Fictieve regressies tonen aan dat een bevestigde SG-aanvraag boven een lager geplaatste autonome zonneladende Wallbox tijdelijk binnen een begrensde netuitzondering kan blijven, ook wanneer de netpiek pas later in de SG-sessie optreedt. De actuele coherente laadmeting, SG-raming en max_takeover_w begrenzen het plafond; de eerste bijdrage mag niet door latere polls stijgen.

De oorspronkelijke episode-eindtijd mag niet worden verlengd door uitlezen, vernieuwing, klokwissel, herstart of tijdelijke dip rond de softwaregrens. Werkelijk herstel vereist ruwe P1 op of onder de SG-importdrempel, bevestigingstijd en minstens twee nieuwe bronrapporten. Een onbekende of beschadigde hersteltoestand verleent geen nieuwe reactietijd.

De gewone wolkenbuffer blijft tegelijk op de ongewijzigde ruwe P1-netafname werken. Fase-, kwartier-, batterij-, bron-, contact-, koel-, eigendoms-, voorrangs- en maximale sessievoorwaarden houden hun onafhankelijke beslissingen. Finale hercontrole na asynchrone opslag en Shelly-preflight mag geen verdwenen EV-bijdrage, verlopen termijn of gewijzigde koppeling gebruiken.

De gerenderde kaarttests controleren actuele reactietijd en vereisen passend actueel backendbewijs. Een oude, toekomstige, restored of verlopen momentopname en een aftellende browserklok creëren geen toestemming of apparaatopdracht. Bestaande prioriteitsbediening en externe SG-waarneming blijven behouden. Een exact passend actueel extern AAN-contact mag uitsluitend binnen zijn oorspronkelijke vijftien minuten door de beperkte EV-reactietijd behouden blijven; dit geeft geen eigendom, ON-opdracht, vernieuwing of nieuw minimum. De originele deadline en overnamecontrole op ruwe P1 blijven strikt gelden.

Aanvullende analysecontroles verifiëren dat oorspronkelijk overdrachtbegin, eindtijd en broncontext in snelle metingen en begrensde toestandsovergangen bewaard blijven. Herstel of latere bronupdates mogen eerder bewaard diagnosebewijs niet overschrijven. Aftelseconden maken geen gebeurtenis per regelronde; registratie verleent geen nieuwe overdrachts- of apparaatbevoegdheid.

## Verplichte publicatieprocedure

De definitieve head moet alle vijf bestaande GitHub-gates halen: repository/full-suite, HACS, Hassfest, Chromium en echte Home Assistant-startup. Main herhaalt de gates. Alleen daarna maakt dezelfde workflow beide ZIP-pakketten en beide release-documenten. De vier gedownloade assets moeten met de exacte tagbron en broncommit overeenkomen. Een oudere groene commit of losse ZIP vervangt geen mislukte gate.

## Bewijsgrenzen

Deze wijziging staat bewust tijdelijk hogere totale netafname toe binnen uitsluitend de beschreven softwarematige uitzondering. Zij verhoogt geen fysieke aansluitcapaciteit en geeft de Wallbox geen commando. Een contact-AAN, laag warmtepompvermogen of cloudrapport bewijst geen causale extra warmteopname of bevestigde fysieke laadreactie. De korte lokale SG-terugval en de softwarematige reactie-eindtijd zijn afzonderlijke mechanismen. Het vierminutenvenster geldt voor de actieve Home Assistant-regeling; een eigen aanvraag heeft een apart geprogrammeerde korte lokale lease, standaard 300 seconden. Bij HA-uitval volgt fysieke UIT dus niet gegarandeerd exact op 240 seconden. Voor extern waargenomen AAN wordt geen nieuwe lokale termijn geprogrammeerd.

Er is geen fysieke schakelproef, Wallbox-overdracht of meterkalibratie op een gebruikersinstallatie uitgevoerd. Private exports, sensorkoppelingen en identificeerbare installatiegegevens blijven buiten de openbare repository. Bestaande Panasonic-capaciteiten en beschermde afwascycli blijven behouden.
