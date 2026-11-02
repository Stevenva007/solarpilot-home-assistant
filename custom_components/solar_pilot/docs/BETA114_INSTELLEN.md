# SolarPilot 1.0.0-beta.114 installeren

Werk na publicatie SolarPilot via HACS bij naar **1.0.0-beta.114**, herstart Home Assistant volledig en herlaad de app of browser. Controleer de backend- en kaartversie onder Instellingen & controle. Behoud de integratie, koppelingen, modellen en historie. Maak vooraf een volledige privéback-up inclusief SolarPilot-opslag en userfiles.

## Een batterijbron herstellen

Een ontbrekende AC-meetbevestiging krijgt nu een eigen melding. SolarPilot noemt ook een verkeerde native meetsoort of ontbrekend actueel veldbewijs. De update bevestigt of vervangt geen bestaande bron automatisch. Een eerder opgeslagen onvoltooid profiel kan daarom ook na de update nog om een bewuste correctie vragen.

1. Open **Batterijbron controleren** bij de bronmelding, of open SolarPilot-instellingen → **Batterijen**.
2. Kies het bestaande Marstek-profiel onder **Batterij aanpassen**. Maak geen tweede profiel voor dezelfde vermogenssensor.
3. Selecteer de bestaande sensor voor het getekende AC-vermogen van de batterij zelf. Bij de ondersteunde native Marstek-koppeling is dit **Vermogen netaansluiting (AC OnGrid)**. De CT-sensor **Totaal vermogen** meet de woning; DC-batterijvermogen of een absolute waarde zonder richting is geen vervanging.
4. Kies voor deze native AC-bron **Positief = ontladen naar huis**. Controleer de bronbetekenis en bevestig de AC-meetdekking.
5. Sla op en controleer de actuele bronmelding opnieuw. Een ontbrekende bevestiging, een verkeerde meetsoort en ontbrekend actueel veldbewijs kunnen opeenvolgende oorzaken zijn. Een vinkje alleen maakt een onbruikbare meting niet geldig.

Een actief Marstek-profiel wordt zonder de expliciete AC-bevestiging niet meer opgeslagen. Een bekende verkeerde native AC-meetsoort of strijdige bekende tekenrichting krijgt een veldfout. De bevestiging verleent geen bedieningstoestemming. Het profiel blijft uitsluitend monitoren; laden, ontladen, modus en reserve blijven onder Marstek-regie.

SoC blijft optioneel en wordt afzonderlijk beoordeeld. Onbekende SoC maakt een bewezen AC-vermogensmeting niet onbruikbaar. Een werkelijke verse 0 W blijft nul; een oude, ontbrekende of onbewezen waarde blijft onbekend. Voor de ondersteunde native bron blijven de ontvangen velden, eigen coordinator en oorspronkelijke ontvangsttijden vereist. Er komt geen extra RPC, poll of verbinding bij.

De diagnostiek kan het verwachte en aangetroffen native veld noemen. Zij neemt geen ruwe providerantwoorden, netwerkadres of private apparaatidentiteit over. Een diagnose is geen fysieke meetkalibratie.

## Basislastleren met een batterij

Een ingeschakelde batterijvloot wordt niet meer alleen wegens haar aanwezigheid uitgesloten. Iedere actieve batterij moet afzonderlijk een volledige, expliciet bevestigde getekende AC-vermogensmeting leveren. De energiebalans is net + PV + getekend batterijvermogen − gemeten Wallbox − werkelijk gemeten beheerde lasten. Ontladen is positief, laden negatief; dezelfde stroom telt eenmaal mee.

Alle noodzakelijke bronnen moeten betrouwbaar, niet overlappend en maximaal 120 seconden oud zijn. De oorspronkelijke batterijontvangsttijd blijft gelden en de rapporten moeten onderling passen. Ontbrekende, geschatte, herstelde, afgeleide of dubbele bronnen maken de leerwaarneming onbekend. Een andere centrale batterijmeter met onbekende dekking wordt niet opgeteld of stil weggelaten. Een generiek batterijprofiel zonder expliciete AC-bevestiging blijft voor deze nieuwe fleetcorrectie onbekend; zijn bestaande overige voorwaarden blijven gelden.

Dit verbetert toekomstige geldige leerwaarnemingen en planning. Oude historie krijgt geen nieuwe meetdekking en een model creëert geen actuele vrije zonnestroom of nieuwe toesteltoestemming. Er worden geen nieuwe PV-aftrek, reserve of apparaatinstellingen uit een analyse automatisch toegepast.

## SG en herstel

De SG-zonne- en importbuffer blijven standaard vijftien minuten bij hun bestaande geldige meetvoorwaarden. Minimumduur, korte lokale Shelly-toestemming, vaste SG-zonnevoorrang, fase-/kwartiergrenzen en handmatige eindtijden blijven afzonderlijk. Een wolkenbuffer verleent geen toestemming op ontbrekende noodzakelijke bronmetingen.

Een batterijbronmelding herstel je in het betreffende profiel. **Controle afronden** blijft de bestaande actie voor echte fout-/overnamecontrole en bevestigt geen batterijmeetdekking. Onzekere opdrachten of een oude herstelwacht worden door de softwareupdate niet automatisch gewist.

## Rollback

Beta.113 kan het bestaande Marstek-profiel blijven lezen, maar mist de nieuwe formuliervalidatie, concrete bronredenen en basislast-fleetcorrectie. Controleer na rollback de bestaande bronkoppeling en AC-bevestiging opnieuw. Een generieke meetmelding kan dan terugkomen; wis geen configuratie, modellen of historie om die melding te verbergen.

Een rollback naar beta.112 of ouder vereist bovendien de eerdere profiel- en buffercompatibiliteitsstappen uit BETA113_INSTELLEN.md. Native Marstek blijft autonoom. Geen fysieke batterij-, SG-, warmtepomp- of laadproef is onderdeel van de softwarepublicatie.

De commitgebonden softwarecontrole en het publicatiemechanisme staan in TESTRESULTATEN_BETA114.md.
