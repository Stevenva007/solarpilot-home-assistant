# SolarPilot 1.0.0-beta.107 installeren

Werk SolarPilot bij via HACS naar **1.0.0-beta.107**, herstart Home Assistant volledig en herlaad de app of browser. Backend en geladen kaart moeten allebei beta.107 tonen. Toestellen, koppelingen, voorrang, timers, lokaal bevestigde SG-capaciteiten, modellen en historie blijven behouden.

## Wat verbetert

Een nog recent Wallbox-cloudrapport kan achterlopen op een snelle verandering van de zonneproductie. Beta.107 laat voorwaardelijk laadvermogen voor een SG-start alleen meetellen wanneer het samen met een complete actuele warmtepompmeting binnen de uit actuele PV, getekende P1 en batterijontlading afgeleide totale belasting past, met 250 W tolerantie voor kleine tijdverschillen. Een tegenstrijdig rapport geeft geen voorwaardelijke laadbijdrage. Werkelijk gemeten restoverschot blijft bruikbaar en een reeds toegelaten SG-aanvraag krijgt hierdoor geen nieuwe stopvoorwaarde.

De SG-redenen volgen de effectieve centrale volgorde, inclusief tijdelijke Wallbox-voorrang. De uitleg suggereert niet langer dat de Wallbox hoger staat wanneer SG vooraan staat. Snelle analysewaarnemingen en nieuwe SG-toestandsovergangen bewaren daarnaast afzonderlijk oorspronkelijk bronbewijs voor net, PV en Wallbox. Oude ontbrekende gegevens worden niet gereconstrueerd.

## Helpt een langere wolkenbuffer?

De gewone wolkenbuffer blijft standaard **600 W gedurende vijf minuten**, naast het ingestelde SG-minimum. Deze buffer overbrugt een gewoon tijdelijk tekort zolang de afzonderlijke grenzen het toelaten.

De maximale totale netafname is een aparte directe grens. Fictief voorbeeld: bij een ingestelde grens van 4.500 W geeft een actuele netafname van 4.620 W SG direct vrij, ook als de minimumduur of wolkenbuffer nog loopt. Een langere wolkenbuffer voorkomt die stop niet. De Wallbox regelt zelfstandig; SolarPilot verstuurt geen laadcommando en kan haar niet dwingen eerst terug te regelen. Het vrijgeven van SG bewijst evenmin dat op dat moment warmtepompvermogen wegvalt.

Verleng de buffer of bronouderdom niet om een dergelijk incident te verbergen. De update verhoogt geen grens en verandert geen bestaande instelling op basis van een diagnose-export. De vijfminutenbuffer blijft de passende standaard voor korte gewone tekorten; lang aanhoudende import en echte grensoverschrijdingen houden hun afzonderlijke beleid.

## Controle na de update

Open **Voorrang** en controleer de gewenste volgorde. Bekijk onder Warmtepomp de actuele reden, de aparte netgrens en de SG-stopinformatie. Laat nieuwe metingen tijdens normaal gebruik verzamelen. Maak bij een volgende onverwachte stop een nieuwe analyse-export; die bevat vanaf deze versie meer oorspronkelijke brongegevens. Een ontvangen Wallboxrapport is nog geen bewezen fysieke meetwaarde op het SG-stopmoment.

De bestaande externe SG-overname na vijftien minuten, handmatige UIT-bescherming en tijdelijke Aan-/Uit-bediening blijven gelden. Panasonic bepaalt comfort, normaal warm water, koeling en sterilisatie zelfstandig. Een PV-voorspelfout of ontbrekende exclusieve toestelmeter vraagt eigen bronbewijs en wordt niet door een gewijzigde SG-uitleg opgelost.

## Terugzetten

Maak vóór update of rollback een volledige privéback-up, inclusief SolarPilot-opslag en userfiles. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk veilig vrij en controleer de lokale terugval. Installeer beta.106 met behoud van entry en gegevens, herstart Home Assistant volledig en herlaad de kaart. Beta.106 behoudt de centrale volgorde en externe overname, maar mist de nieuwe coherentiecontrole en aanvullende diagnose. Gebruik geen twee runtimes tegelijk en verwijder de integratie niet als migratiemethode.

[Actuele werking](ACTUELE_WERKING.md) · [Softwarebewijs en beperkingen](TESTRESULTATEN_BETA107.md)
