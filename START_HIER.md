# SolarPilot beta.67 — installatie en upgrade

Panasonic blijft zelfstandig regelen. SolarPilot geeft één rustige, begrensde SG-zonneboost volgens het expliciet lokaal bevestigde toepassingsbereik. Beta.67 toont de actuele taak, elektrische hoofdactiviteit en bijverwarming apart. Verse native taakmeldingen, afleidingen en gekozen standen houden hun eigen betekenis. Het bestaande meterpaar krijgt automatisch het herkenbare Panasonic-profiel: voeding 1 warmtepomp inclusief regeling/pompen, voeding 2 elektrische bijverwarming. Dit is een weergave-aanname; eerdere bewuste afwijkingen blijven staan. Voor deze update hoef je niets nieuws te configureren of in te vullen. De ventilatoranimatie geeft verse elektrische hoofdactiviteit aan, geen bewezen compressorrotatie; bij alleen bijverwarming blijft zij stil en beweegt het verwarmingssymbool. Verminderde beweging onderdrukt animaties. SG-regels, meter-/koelbevestigingen en geldige bestaande instellingen uit beta.66 blijven behouden. Een werkelijk gewijzigde koppeling of profielkeuze houdt haar eigen voorwaarden.

**Begin met [BETA67_INSTELLEN.md](docs/BETA67_INSTELLEN.md).** Daar staan back-up, lokale profiel-/meter-/koelbeveiligingscontrole, korte acceptatie en rollback. De volledige actuele werking staat in [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Nieuwe software-/publicatiestatus: [TESTRESULTATEN_BETA67.md](docs/TESTRESULTATEN_BETA67.md).

## Installeren en behouden

1. Maak vóór upgrade een volledige privé HA-back-up, inclusief configuratie, SolarPilot-opslag, modellen en userfiles. Bewaar beta.66-code samen met de passende back-up.
2. Controleer de eigen SG-aanvraag/contactstand en geef de aanvraag vrij vóór programmavervanging. Behoud een draaiende beschermde afwascyclus; maak geen nieuw APP-ticket als updateproef.
3. Installeer via HACS exact `1.0.0-beta.67` zodra gepubliceerd, herstart HA volledig en herlaad de pagina volledig of sluit de app volledig af en open haar opnieuw. Controleer backend- en kaartversie afzonderlijk; beide moeten beta.67 tonen.
4. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`; bewaar userfiles en HA-opslag. Verwijder/herschep de bestaande entry niet.

Eerste installatie: voeg de GitHub-repository toe aan HACS als **Integration**, voeg SolarPilot toe onder **Instellingen → Apparaten & diensten** en controleer P1/PV eerst in **Alleen bekijken**. De frontend wordt automatisch geregistreerd. Er is geen aparte Lovelace-resource, dashboard-YAML of www-kopie nodig.

Beta.67 behoudt de beta.63-fix voor onveranderbare en geneste HA-opties. Een update herstelt geen toestemming door gegevens te wissen. Bestaande geldige single-meterconfig, prioriteiten, APP-tickets, geschiedenis, modellen, bewaartermijnen en de globale hervatvoorkeur blijven behouden.

## Instellingen en uitlezing controleren

Bij een ongewijzigde beta.66-installatie hoef je de SG-ingebruikname, het gekozen profiel, de meterdekking of de bestaande koelbeveiliging niet opnieuw te bevestigen wegens deze upgrade. Controleer de behouden waarden. Voor een nieuwe installatie of werkelijk gewijzigde koppeling/profielkeuze gelden de volgende voorwaarden.

Kies **Uitsluitend tapwater** of **Algemene SG-boost volgens Panasonic-bedrijf**. Bevestig het gekozen bereik bewust; SolarPilot wijzigt Panasonic-percentages/temperaturen niet. Voor extra koeling is geschikte bestaande condens-/dauwpuntbeveiliging een afzonderlijke controle. AUTO of onbekende context bewijst geen veilige extra koeling.

Koppel één echte bevestigde meter of twee volledige niet-overlappende voedingen. Split totaal bestaat alleen bij twee actuele geldige deelwaarden; bekende nul blijft nul en een ontbrekend deel geeft geen verzonnen totaal. Optionele echte compressorfrequentie en ontvangen SG-status helpen observatie. Compressorbedrijf bewijst geen SG-veroorzaakt extra verbruik.

De warmtepomp verschijnt in Overzicht en Toestellen tussen de andere blokken en in Warmtepomp. De twee vaste onderdelen tonen Taak van de warmtepomp en Elektrische bijverwarming, met afzonderlijk meter-/bronbewijs. Een verse werkelijke native taakmelding kan apart leesbaar blijven bij lage/nul/partiële of ontbrekende meting; een uit verbruik en context afgeleide functie benoemt haar gebruikte bronnen. Alleen een gekozen verwarmingsstand of WATER-route is geen afzonderlijk gemelde productie. Oude of tegenstrijdige taakcontext geeft geen eenduidige functieclaim. Het totaal blijft onvolledig als één voeding ontbreekt; nul op één voeding is geen totale rust. Compressorfrequentie blijft afzonderlijk bewijs. De animatie duidt actuele elektrische activiteit aan en creëert geen bedieningsrecht. De gemelde SG-contactstand staat prominent; de aanvraag staat in Details. Een bekende aanvraag/contactafwijking krijgt een waarschuwing. Ontvangen SG verschijnt uitsluitend met een passende actuele bevestigde bron; ontbrekend bewijs blijft technisch onbekend zonder een permanent onbekend-label op de kaart. Details tonen eigenaar, reden, lokale timer, metingen en bronnen. De lokale timer blijft standaard 300 s, vernieuwd iedere 60 s zonder fysieke UIT/AAN-cyclus. Herstart, rust of langdurig laag vermogen geeft geen pulstruc, Force-opdracht of automatische nieuwe toestemming.

Een sessie duurt standaard maximaal één uur. Tapwater-only behoudt de tankafkoelregel. Algemeen gebruikt na iedere beëindigde/onderbroken sessie rust en aantoonbaar nieuw zon-/native bewijs; een warme of ontbrekende tank is niet zelfstandig een permanente blokkering. Constante zon of dezelfde samples geeft geen eindeloze herstartlus. De volledige startvertraging en actuele guards blijven gelden.

De korte lokale controle opent geen elektrische apparatuur. Fysieke SG-/timerproef en natuurlijke automatische sessie worden uitsluitend na expliciete toestemming uitgevoerd. Zonder echte mapping-/timer-/profielbevestiging blijft automatische SG geblokkeerd; gezonde andere apparaten houden hun eigen voorwaarden. De historische stilstandoorzaak blijft onbeslist.

## Analyse en adviezen

Bij Analyse nodig maakt één klik een export van de beschikbare zeven dagen. Meetkwaliteit toont dekking/bevindingen zonder leervragen of beleidkeuzeknoppen. Onder Export download je lokaal JSON.GZ met meetgegevens en een gerichte analysevraag. Voeg het hier bewust toe; de meegeleverde analysevraag betreft warmtepompinsteltips, SolarPilot-instellingen en logische verbetervoorstellen. Je kunt een teruggegeven JSON-adviezenrapport optioneel onder Export uploaden. Het rapport toont bronbinding, bewijs en beperkingen en past niets automatisch toe. Antwoorden verwerken alleen een exact geëxporteerde én nog actuele bevindingrevisie: beoordeeld afgehandeld, meer data nodig blijft open. Sampling-/aanpassingsbeleid verandert niet. Een instellingenwijziging blijft een afzonderlijke bewuste actie; codeverbeteringen vragen een afzonderlijke geteste HACS-release. Het rapport blijft bij gewone updates bewaard; een geïnstalleerd vertrouwd implementatieregister bepaalt of een logische voorstelidentiteit uitgevoerd is. Een uploadtekst kan die status niet zelf claimen. De automatische registratie met standaard zeven dagen/vijfminutenmeetpunten vraagt geen nieuwe koppelingen of configuratie en bewijst niet iedere korte verbruikspiek. Zie de releasehandleiding.

## Rollback

Geef eerst de eigen SG-aanvraag vrij en controleer contactstand/lokale afloop. Stop de nieuwe runtime voordat beta.66 terugkomt. Herstel beta.66-code én de volledige passende privéback-up van vóór deze upgrade; een oude ZIP alleen herstelt nieuwe schema-/bewijsvelden niet exact. Laat nooit twee versies tegelijk het contact beheren.

Voor terugkeer naar de oude directe beta.61-regeling blijft de volledige passende back-up van vóór beta.62-migratie noodzakelijk. Privé herkomstarchief is geen complete HA-restore en doet geen fysieke replay. Zie de releasehandleiding voor de volledige procedure.
