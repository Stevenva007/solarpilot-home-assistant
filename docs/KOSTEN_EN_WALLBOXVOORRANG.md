# SolarPilot beta.24 — kosten en Wallbox-voorrang

Deze handleiding vult de actuele werking aan met de concrete instelroute. De volledige, releasegebonden uitleg staat in `ACTUELE_WERKING.md` en in Home Assistant onder **Uitleg**.

## Eén cumulatieve update

Deze volledige versie bevat beta.22 (eerste batterijopdracht bij korte systeem-uptime), beta.23 (opengeklapte dashboarddelen behouden), de twee onderstaande functies en de correctie waarbij een toestel zonder dagdoel niet permanent door forecast-uitstel wordt geblokkeerd. Vanaf beta.21 mag rechtstreeks naar beta.24 worden bijgewerkt. Tussenliggende versies hoeven niet gepubliceerd of geïnstalleerd te worden.

Publiceer dit pakket via de bestaande Git-repository en behoud die `.git`-map. Publiceer niet de omhullende ZIP-map als extra submap. Maak de nieuwe tag pas na een geslaagde Validate-run. De meegeleverde code publiceert niets zelfstandig naar GitHub.

Bijwerken in Home Assistant: eerst **Pauze**, dan eigen lasten met behoud van minimumlooptijd laten vrijgeven, daarna via HACS bijwerken en Home Assistant herstarten. Configuratie, lokale leerdata en `userfiles` blijven behouden bij de normale update. Verwijder de integratie of privébundel niet. Controleer de toestand na de herstart en kies bewust opnieuw Zonnestroom.

## Elektriciteitskost vandaag

**Overzicht** toont de netto elektriciteitskost vandaag tot nu toe. **Planning** en **Energie** tonen de uitsplitsing in netafname, injectie, rechtstreeks verbruikte PV en vermeden aankoop.

De aparte tegel **Geschatte energiekost · planhorizon** blijft bestaan. Die berekening hield al rekening met voorspelde PV en injectie; ze was geen bedrag voor vandaag. De uitsplitsing ervan is nu open te klappen.

Netto variabele kost vandaag = som(netafname per meetinterval × toen geldende afnameprijs) − som(injectie per meetinterval × toen geldende injectievergoeding).

Rechtstreekse PV vermindert de netafname en is daardoor al verwerkt. Het informatieve bedrag **Vermeden netaankoop door zon** wordt NIET nogmaals van de netto kost afgetrokken. De productie heeft hier geen berekende investerings-/onderhoudskost. Vaste kosten, capaciteitstarief en niet in het ingestelde kWh-tarief opgenomen factuurposten worden niet toegevoegd.

Fictief voorbeeld: 10 kWh netafname tegen €0,30 = €3,00. 6 kWh injectie tegen €0,03 = €0,18 vergoeding. Netto kost = €2,82. Daarnaast 5 kWh direct gebruikte zon = €1,50 vermeden netaankoop, niet een tweede aftrek.

Metingen: de eigen dagboekhouding gebruikt bestaande P1-/PV-vermogensmetingen. Ze integreert alleen bruikbare intervallen, bewaart totalen en begint een nieuwe dag om lokale middernacht. Een herstart overbrugt geen ontbrekende meetperioden. Meetdekking wordt getoond. Bij de eerste upgrade kunnen beschikbare bestaande SolarPilot-dagtotalen eenmalig tegen het ingestelde tarief worden overgenomen; dat wordt als tariefschatting aangeduid. Historische kwartierprijzen vóór die upgrade worden niet verzonnen. De nieuwe intervalregistratie herprijst eerder verbruik niet wanneer het actuele tarief verandert.

Zonder prijsgegevens is de kost onbekend, niet nul. Bij een gekoppelde thuisbatterij is rechtstreeks gebruikte zon niet zonder meer uit P1/PV afleidbaar; de nieuwe directe-PV-uitsplitsing wordt dan als onbekend getoond. Netto P1-kost blijft wel berekenbaar.

## Wallbox-voorrang per verbruiker instellen

1. Kies **Pauze** en wacht tot eigen lasten veilig zijn vrijgegeven.
2. Open **Configureren → Opslag & laden → Wallbox**.
3. Behoud de bestaande vermogens-, status- en Full Solar-bronnen. Vul **Minimum voor autonome zonnelaadstart** in op basis van de werkelijk gebruikte laadfasen. Bij eenfasig Full Solar is circa 1380 W een gebruikelijk minimum; bij driefasig circa 4140 W. Dit volgt NIET automatisch uit de hoofdzekering of huisaansluiting. Bij faseoptimalisatie gebruik je het minimum van de werkelijk actieve zonnelaadmodus. De standaard 0 betekent nog te bevestigen en voorkomt een ongefundeerde aanname.
4. Een auto-aangesloten-sensor is optioneel. Gebruik uitsluitend een bron die aansluiting op déze Wallbox bevestigt. Een algemene kabelsensor van een voertuig bewijst de laadlocatie niet. Een herkende Wallbox-laadvraag kan ook zonder extra sensor voldoende zijn.
5. Open **Verbruikers & prioriteiten → Toestel aanpassen → 4/4 Planning & energie**.
6. Kies bij **Voorrang ten opzichte van de Wallbox**: **Wallbox eerst; klein restoverschot benutten**. Laat **Mag gecontroleerd vermogen van Wallbox overnemen** uit voor dit lagere toestel. Andere toestellen kunnen **Dit toestel eerst** of **Globale voorkeur volgen** behouden.
7. Sla op, controleer de keuzes en kies bewust opnieuw Zonnestroom.

Bestaande verbruikers behouden hun globale voorkeur en bestaande beschermtijden. Alleen deze update installeren geeft de Wallbox dus niet automatisch voorrang op een bestaand toestel.

## Gedrag bij de nieuwe keuze

Zonder actieve laadvraag (geen auto, vol, pauze of een herkende niet-vragende toestand) blijft het gewone zonneoverschot voor de lage verbruiker bruikbaar. Kabelaanwezigheid alleen is onvoldoende. Onbekende of verouderde bronnen geven geen vrijbrief voor nieuwe starts.

Bij wachtende Full Solar-laadvraag en te weinig overschot voor de Wallbox mag de lagere last het kleine overschot benutten. Om te bepalen wanneer de Wallbox zou kunnen starten, telt SolarPilot netto-injectie, actueel EV-verbruik en het werkelijk gemeten vermogen van eigen lagere lasten dat kan worden vrijgegeven samen, verminderd met batterijontlading. Dit is uitsluitend een voorrangsbeslissing: het verhoogt nooit vrije injectie of elektrische netruimte voor nieuwe lasten.

Bij voldoende potentieel worden nieuwe lagere starts direct tegengehouden. Na standaard 120 seconden stabiel boven minimum + 150 W krijgen eigen lagere lasten een stopverzoek. Hun minimumlooptijd en beschermde cyclus blijven gelden. Voor een compressor met 30 minuten minimumlooptijd kan de auto dus nog moeten wachten. Na de minimumlooptijd wordt niet nog eens de gewone 15-minuten-tekortvertraging toegevoegd. De ingestelde minimumrust vóór een herstart blijft bestaan.

Fictief driefasevoorbeeld: 4000 W injectie + 350 W eigen lager verbruik = 4350 W beschikbaar ná stoppen. Dat ligt boven 4140 + 150 W. Zodra stabiliteit en toestelbescherming dat toelaten, geeft SolarPilot die 350 W vrij en laat de Wallbox zelfstandig reageren.

Start de auto na daadwerkelijk vrijgeven niet binnen standaard 10 minuten, dan wordt niet eindeloos vermogen gereserveerd. De lagere last komt opnieuw in aanmerking; standaard 30 minuten later mag opnieuw worden beoordeeld. Bij 5 minuten onder minimum − 300 W vervalt de startreserve ook. Deze timers staan onder de geavanceerde Wallbox-instellingen.

Tijdens werkelijk laden mag een lagere last alleen stabiel écht restoverschot gebruiken. Een mogelijke EV-vermogensdaling na zo'n start kan tot veilig teruggeven leiden. Door cloudvertraging en veranderlijke zon is dit geen garantie op onmiddellijk of exact watt-voor-watt gedrag. Er volgen geen extra cloudoproepen en geen Wallbox-schrijfopdrachten.

De tab **Verbruikers** toont de gekozen lagere lasten, het ingestelde laadminimum, het berekende potentieel, wachttijd en reden. Deze voorkeur wijzigt geen warmtepompdoelen, sterilisatie of fysieke batterijtoestemming.

## Validatie

De nieuwe pure beslislaag, rekeningmodule, runtime-adapters en sensoreigenschappen zijn met lokale tests gecontroleerd. Browsercontroles gebruiken de echte kaartcode met uitdrukkelijk fictieve data. Dit is geen hardwaretest met een echte auto, laadpaal of compressor. GitHub Actions/HACS/hassfest moeten na publicatie nog op de nieuwe commit slagen.
