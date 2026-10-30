# SolarPilot 1.0.0-beta.112 installeren

Werk na publicatie SolarPilot via HACS bij naar **1.0.0-beta.112**, herstart Home Assistant volledig en herlaad de app of browser. Controleer daarna zowel de backend- als kaartversie onder Instellingen & controle. Behoud integratie, configuratie, modellen, aanvragen en historie. Maak vooraf een volledige privéback-up inclusief opslag en userfiles.

## Wat verandert voor SG?

Een lopend automatisch algemeen SG-contact hoeft het startvermogen niet telkens opnieuw te halen. Een warmtepomp die bijvoorbeeld terugregelt naar 1300 W en volledig op zon draait, mag blijven werken terwijl zijn gezamenlijke zonnebudget lager is dan de oorspronkelijke startdrempel. Beta.111 kon dit onterecht als een tekort zien en na de buffer of minimumduur stoppen.

Beta.112 houdt de aanvraag aan zolang actueel bruikbaar P1-/HP-/EV-zonnebudget overblijft na de bestaande correcties en alle overige voorwaarden passen. De werkelijke netafname wordt apart bewaakt. De warmtepomp behoudt vaste toegang tot actueel bevestigd autonoom Wallbox-zonnelaadvermogen. De Wallbox regelt zelf terug en krijgt geen laadcommando.

Daarnaast kon het herstel van een nog actuele, wat trager rapporterende warmtepompmeting de oudste meettijd van het gezamenlijke budget terugzetten. Dat is bij verschillende rapportagesnelheden normaal. De regeling verwart dit niet meer met uitgeputte tekorttijd: bronactualiteit en voortgang van oorspronkelijke rapporten worden afzonderlijk beoordeeld.

## Hoe groot is de wolkenbuffer?

De gewone zonne- en importbuffers worden op verzoek **vijftien minuten (900 seconden)**. De zachte grens blijft **600 W** echte P1-netafname en de oorspronkelijke minimumduur blijft **twintig minuten**. Bij de update wordt de vroegere standaard van 300 seconden eenmaal omgezet naar 900 seconden. Andere bewaarde aangepaste duurtijden blijven staan; na de migratie worden ook latere bewuste eigen keuzes behouden. Een reeds vastgelegde lopende tekortdeadline wordt niet verlengd.

- Meer dan 600 W netafname begint de importbuffer. Herstel naar 600 W of minder wist die klok.
- Als het geldige gezamenlijke bruikbare zonnebudget helemaal wegvalt, begint apart de zonnebuffer. Nieuwe actuele bruikbare zon wist die klok.
- De regeling beoordeelt de betreffende buffer en de minimumduur samen; die klokken lopen tegelijk. Bij een tekort vanaf minuut 18 ligt de beleidsgrens dus op minuut 33. De korte lokale timer houdt terugmeldruimte over en kan iets vóór die grens aflopen.
- Lager moduleren met nog bruikbare zon begint geen zonnebuffer. De startdrempel geldt voor een nieuwe start, niet voor het behouden van een lopend contact.

De reken- en bronfouten zijn afzonderlijk hersteld. Daarnaast overbrugt de gevraagde vijftienminutenbuffer langere tijdelijke wolken. Bij aanhoudend tekort kan SG na de buffer en het toepasselijke minimum vrijgeven. De langere buffer kan tijdelijk meer netafname toelaten; de grens van 600 W zelf is niet verhoogd en alle harde grenzen blijven gelden.

## Wat blijft gelden?

Actuele harde net-, fase-, kwartier-, batterij-, bron-, koel-, contact- en timercontroles blijven onafhankelijk. Zij kunnen eerder ingrijpen dan een gewone wolkenbuffer. De aparte Wallboxreactietijd blijft standaard vier minuten en verruimt alleen haar bestaande softwarematige importuitzondering. Panasonic bepaalt zelfstandig compressorwerking, behoefte en fabrikantbeveiligingen; een SG-contact is geen compressorcommando.

Automatisch algemeen zonbedrijf heeft geen verplichte uurstop. Het behoudt dezelfde oorspronkelijke starttijd en korte lokaal bevestigde toestemming, standaard 300 seconden met actuele hercontrole vóór vernieuwing. Tijdelijk handmatige en andere begrensde routes behouden hun oorspronkelijke eindtijden. Onbekende of oude metingen worden geen actuele nul of verzonnen zonnebijdrage. Firmwareherstel en bescherming van fysieke handmatige UIT blijven behouden.

Er is geen nieuwe instelling of lokale herbevestiging alleen voor deze softwarecorrectie. De instelling hysteresis_w blijft uitsluitend bij de bestaande alternatieve herstartroute via een nieuwe zonneperiode horen; zij vormt geen behoudsdrempel voor een lopend automatisch algemeen contact.

## Controle na de update

Bekijk tijdens een natuurlijke zonnige periode het werkelijke SG-contact, de actuele reden, het warmtepompvermogen en de ruwe netafname. De reden benoemt nu ook een actieve zonnebuffer en de resterende minimumduur, zodat tijdelijk tekort herkenbaar is. Een modulerende warmtepomp hoort bij nog bruikbare zon door te lopen. Bij een gewone korte wolk kan een buffer aftellen en bij herstel verdwijnen, zonder nieuwe starttijd. De warmtepomptaak en het SG-contact blijven afzonderlijke zaken in de geschiedenis. Een afgeleide taak bewijst niet dat het contact voortdurend aan was.

Bij een volgende onverklaarde stop is de lokale analyse-export nodig voor het precieze stopmoment, de oorspronkelijke metingen en de beslisreden. Een screenshot van de tijdlijn alleen bewijst niet waarom het contact stopte. Exporteer geen privégegevens naar de openbare repository.

## Rollback

Rollback naar beta.111 behoudt configuratie en opslag, maar brengt de startvermogensdrempel voor een lopend contact en de fout bij terugkerende oudere bronbijdragen terug. Daardoor kan SG opnieuw stoppen terwijl nog bruikbare zon beschikbaar is. Stel vóór rollback de gewone tekortbuffer terug op een waarde die beta.111 ondersteunt, bijvoorbeeld 300 seconden: die versie accepteert maximaal 600 seconden en kan de nieuwe 900 seconden niet valideren. Gebruik vervolgens de normale HACS-versiekeuze of het exacte gepubliceerde pakket, herstart Home Assistant en herlaad de kaart. Wis de integratie of privéopslag niet.

Softwarevalidatie en de grens tussen voorbereiding, CI en publicatie staan in TESTRESULTATEN_BETA112.md. De lokale lease houdt standaard maximaal de ingestelde terugmeldmarge van 20 seconden vóór de tekort-/minimumdeadline over; de buffer is daarom geen garantie op exact 900 seconden fysieke AAN. Er is geen fysieke warmtepomp-, SG- of laadproef uitgevoerd.
