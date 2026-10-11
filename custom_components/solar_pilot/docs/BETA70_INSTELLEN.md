# SolarPilot 1.0.0-beta.70 — warmtepompgeschiedenis

Beta.70 voegt een afzonderlijke lokale warmtepompgeschiedenis toe. Je ziet een gekozen dag, geregistreerde activiteit, starts/stops, taken, gemeten elektrische dagenergie en afzonderlijke SG-lagen. Panasonic blijft zelfstandig regelen. De beta.69-SG-startbijdrage en alle bestaande elektrische-/voorrangsbeveiligingen blijven behouden.

## Update met behoud van gegevens

1. Maak een volledige privé Home Assistant-back-up, inclusief configuratie, SolarPilot-opslag, modellen, tickets, bestaande historie en userfiles. Bewaar gecontroleerde beta.69-code voor rollback.
2. Geef een eigen SG-aanvraag vrij vóór codevervanging en controleer gemelde contactstand/lokale afloop. Behoud beschermde apparaatcycli.
3. Update via HACS naar exact `1.0.0-beta.70` na publicatie en herstart Home Assistant volledig. Herlaad de browserpagina volledig of sluit de app volledig af en open haar opnieuw.
4. Controleer backend- én geladen kaartversie onder Instellingen & controle: beide moeten `1.0.0-beta.70` zijn. Een integratieherlading alleen vervangt geen al geladen kaartcode.
5. Controleer behouden instellingen, volgorde, APP-tickets, modellen, geschiedenis en userfiles. Ongewijzigde geldige SG-/profiel-/split-/koelbevestigingen blijven staan. Er zijn geen nieuwe verplichte sensoren, configuratiestappen of leervragen.

Lokaal vervangen: uitsluitend `custom_components/solar_pilot` uit het local-ZIP. Behoud `userfiles` en alle Home Assistant-opslag. Verwijder of herschep de bestaande integratie niet. Eerste installatie blijft HACS Integration, HA-herstart en toevoegen onder Apparaten & diensten. De kaart wordt automatisch geregistreerd; een aparte Lovelace-resource is niet nodig.

## Geschiedenis bekijken

Open **Geschiedenis** bij de warmtepomp in **Overzicht**, **Toestellen** of **Warmtepomp**. De popup **Warmtepompgeschiedenis** heeft een datumkiezer, Vorige/Volgende dag, Vandaag en Vernieuwen. Ze blijft tijdens de gewone dashboardupdates open.

| Onderdeel | Betekenis |
| --- | --- |
| Geregistreerde draaitijd, Starts en Stops | Waargenomen activiteit en overgangen uit passend vers native taakbewijs of complete actuele elektrische meting. Dit is geen afzonderlijke compressorlooptijd. |
| Dagtijdlijn en taakperioden | Activiteitsperioden met de beschikbare taken. Bevestigd, Afgeleid en Taak onbekend blijven herkenbaar. |
| Zeven/dertig dagen | Balken voor geregistreerde activiteit en gemeten elektrische dagenergie. Ontbrekende dagen tonen geen registratie. |
| Gemeten verbruik en meetdekking | Geregistreerde elektrische energie van de hele warmtepomp uit bruikbare complete actuele bevestigde metingen. Alleen de gedekte periode telt mee. |
| SG-aanvraag | De door SolarPilot geregistreerde eigen aanvraag. |
| SG-contact | De daadwerkelijk gemelde verse relaisstand. |
| Panasonic SG-ontvangst | Uitsluitend de passende verse gekoppelde ontvangen-SG-bron; een aanvraag of contact AAN bewijst dit niet. |

De warmtepompgeschiedenis begint na installatie van beta.70. Er worden geen eerdere dagen, taken, starten of stopoorzaken uit modellen, oude export of andere verbruikerhistorie gegokt. Die bestaande gegevens blijven behouden. De nieuwe registratie werkt in Alleen bekijken, Automatisch regelen en Pauze, onafhankelijk van de analysedetailregistratie.

## Metingen en grenzen

Een echte bevestigde totaalmeter of twee complete actuele bevestigde niet-overlappende voedingen kunnen elektrische energie leveren. W/kW worden genormaliseerd; nul is gemeten nul. Ontbrekende, negatieve, geschatte, oude of onvolledige meting geeft geen energie over dat interval. Een bekende deelwaarde vormt geen compleet totaal.

De energie-integratie gebruikt twee complete bruikbare eindpunten van dezelfde meterbinding, maximaal dertig seconden uit elkaar. Een ongewijzigde waarde is alleen bruikbaar zolang haar echte rapportagetijd actueel blijft; de regelcyclus maakt haar niet vers. Herstart, reload/unload, meetgat of gewijzigde meterbinding onderbreekt de integraal. De popup toont meetdekking naast kWh, zodat een gedeeltelijke dag niet volledig lijkt.

Activiteit kan uit een verse native taak of uit complete actuele elektrische activiteit blijken. Het bestaande elektrische weergavecriterium is alleen observatie en verandert geen SG-vrijgave. Onbekende tijd is geen bewezen UIT; registratiegrenzen krijgen geen verzonnen fysieke stopoorzaak. Sessies worden verdeeld over lokale kalenderdagen, ook bij 23/25 uur. Detailaantallen zijn begrensd; dagtotalen blijven met een onvolledigheidslabel bestaan als details worden afgekapt.

Alleen **totale warmtepompenergie** wordt berekend. De geschiedenis claimt geen energie per thermische taak, warmteproductie, COP, compressorlooptijd, extra SG-kWh of causale besparing. Samenloop van SG en verbruik blijft een waarneming. De nieuwe popup bedient geen apparaat en wijzigt geen instelling.

## Opslag en privacy

De nieuwe geschiedenis gebruikt afzonderlijke lokale HA-opslag `solar_pilot.<entry>.heatpump_history`, met maximaal dertig lokale kalenderdagen. Bestaande verbruikerhistorie, modellen, tickets en analysedata worden niet vervangen. Activiteits-/SG-sessies en taaksegmenten hebben vaste detailgrenzen; ontbrekend of afgekapt detail wordt zichtbaar vermeld. De laatste nog niet opgeslagen waarnemingen kunnen bij abrupte uitval ontbreken.

Details worden alleen op aanvraag gelezen met de bestaande Home Assistant-leesrechten op de betrokken actuele en historische bronnen. Ze worden niet als zware herhaalde Recorder-attributen opgeslagen. Een onleesbare of niet ondersteunde opslagversie wordt niet stil overschreven. Er is geen automatische upload. Geschiedenis, echte entitybindings, huishoudelijke metingen en back-ups horen niet in publieke bron of release-assets.

## Behouden SG-werking

De bestaande SG-startdrempel telt werkelijk restoverschot plus de extra afgeleide bijdrage uit een complete actuele bevestigde warmtepompmeting, begrensd door gemeten PV en gecorrigeerd voor netafname, batterijontlading en reserves. Bestaand warmtepompvermogen blijft in P1 en vergroot geen elektrische ruimte. De aparte mogelijke extra SG-vraag, net-/fase-/kwartiergrenzen, Wallboxvoorrang, start-/stopvertraging, rust, sessielimiet en lokale lease blijven behouden.

Panasonic-percentages, koelwaarden, temperaturen, programma's, compressor, elektrische ondersteuning en sterilisatie worden niet geschreven. Eén bestaande toegewezen SG-uitgang blijft de enige warmtepompactuator. De historie geeft geen nieuwe bediening of automatische ingebruiknamerechten. Softwaretests bewijzen geen fysieke meterbedrading, Shelly-afloop, condensbeveiliging of Panasonic-reactie.

## Rollback naar beta.69

Geef de eigen SG-aanvraag vrij, controleer contactstand/lokale afloop en stop de nieuwe runtime. Zet gecontroleerde beta.69-code terug met behoud van instellingen, userfiles en bestaande HA-opslag. Beta.69 leest de nieuwe afzonderlijke warmtepompgeschiedenis niet; bewaar die opslag als je later weer naar beta.70 wilt. Een periode zonder beta.70-registratie blijft bij terugkeer een gat.

Voor exact herstel van de toestand vóór de upgrade zet je beta.69-code én de volledige passende privéback-up terug. Dat herstelt ook instellingen of andere gegevens die sinds de upgrade bewust veranderd zijn en kan nieuwe historie verwijderen; bewaar gewenste nieuwe gegevens eerst privé. Alleen een oudere ZIP brengt niet de hele installatie terug naar een eerder tijdstip. Laat nooit twee runtimes tegelijk het SG-contact beheren en verwijder de entry niet als rollbackstap.

Terugkeer naar de oude directe beta.61-regeling blijft de volledige pre-beta.62-migratieback-up vereisen. Actuele software-/publicatiestatus: `TESTRESULTATEN_BETA70.md`. Volledige actuele werking: `ACTUELE_WERKING.md`.
