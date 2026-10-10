# SolarPilot beta.65 — installatie en upgrade

Panasonic blijft zelfstandig regelen. SolarPilot geeft één rustige, begrensde SG-zonneboost warmtepomp volgens het expliciet lokaal bevestigde toepassingsbereik. Beta.65 herstelt de warmtepompweergave en toont haar naast de andere toestellen, met grafische bedrijfsindicatie en afzonderlijke SG-bewijslagen. Geldige bestaande instellingen en lokale bevestigingen uit beta.64 blijven behouden. Een gewijzigde koppeling of profielkeuze houdt haar eigen bevestigingsvoorwaarden.

**Begin met [BETA65_INSTELLEN.md](docs/BETA65_INSTELLEN.md).** Daar staan back-up, lokale profiel-/meter-/koelbeveiligingscontrole, korte acceptatie en rollback. De volledige actuele werking staat in [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Nieuwe software-/publicatiestatus: [TESTRESULTATEN_BETA65.md](docs/TESTRESULTATEN_BETA65.md).

## Installeren en behouden

1. Maak vóór upgrade een volledige privé HA-back-up, inclusief configuratie, SolarPilot-opslag, modellen en userfiles. Bewaar beta.64-code samen met de passende back-up.
2. Controleer de eigen SG-aanvraag/contactstand en geef de aanvraag vrij vóór programmavervanging. Behoud een draaiende beschermde afwascyclus; maak geen nieuw APP-ticket als updateproef.
3. Installeer via HACS exact `1.0.0-beta.65` zodra gepubliceerd, herstart HA volledig en herlaad de pagina volledig of sluit de app volledig af en open haar opnieuw. Controleer backend- en kaartversie afzonderlijk; beide moeten beta.65 tonen.
4. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`; bewaar userfiles en HA-opslag. Verwijder/herschep de bestaande entry niet.

Eerste installatie: voeg de GitHub-repository toe aan HACS als **Integration**, voeg SolarPilot toe onder **Instellingen → Apparaten & diensten** en controleer P1/PV eerst in **Alleen bekijken**. De frontend wordt automatisch geregistreerd. Er is geen aparte Lovelace-resource, dashboard-YAML of www-kopie nodig.

Beta.65 behoudt de beta.63-fix voor onveranderbare en geneste HA-opties. Een update herstelt geen toestemming door gegevens te wissen. Bestaande geldige single-meterconfig, prioriteiten, APP-tickets, geschiedenis, modellen, bewaartermijnen en de globale hervatvoorkeur blijven behouden.

## Instellingen en uitlezing controleren

Bij een ongewijzigde beta.64-installatie hoef je de SG-ingebruikname, het gekozen profiel, de meterdekking of de bestaande koelbeveiliging niet opnieuw te bevestigen wegens deze upgrade. Controleer de behouden waarden. Voor een nieuwe installatie of werkelijk gewijzigde koppeling/profielkeuze gelden de volgende voorwaarden.

Kies **Uitsluitend tapwater** of **Algemene SG-boost volgens Panasonic-bedrijf**. Bevestig het gekozen bereik bewust; SolarPilot wijzigt Panasonic-percentages/temperaturen niet. Voor extra koeling is geschikte bestaande condens-/dauwpuntbeveiliging een afzonderlijke controle. AUTO of onbekende context bewijst geen veilige extra koeling.

Koppel één echte bevestigde meter of twee volledige niet-overlappende voedingen. Split totaal bestaat alleen bij twee actuele geldige deelwaarden; bekende nul blijft nul en een ontbrekend deel geeft geen verzonnen totaal. Optionele echte compressorfrequentie en ontvangen SG-status helpen observatie. Compressorbedrijf bewijst geen SG-veroorzaakt extra verbruik.

De warmtepomp verschijnt in Overzicht en Toestellen tussen de andere blokken. Het tabblad Warmtepomp toont dezelfde actuele warmtepompuitleg; vervallen boiler-/klimaatregelingen worden niet meer als ontbrekende configuratie getoond. Een activiteitssymbool markeert bevestigd bedrijf. Een apart SG-label onderscheidt de aanvraag, de gemelde Shelly-stand en de werkelijk ontvangen SG-status. Actuele compressorfrequentie is het primaire bewijs. Alleen zonder gekoppelde compressorbron kan een verse passende native hvac_action bedrijf of rust aangeven; vermogen, WATER of alleen een gekozen HEAT-programma bewijst dit niet. Oude of onbeschikbare bronnen blijven onbekend. Details tonen eigenaar, reden, lokale timer, metingen en bronbewijs. De lokale timer blijft standaard 300 s, vernieuwd iedere 60 s zonder fysieke UIT/AAN-cyclus. Herstart, rust of langdurig laag vermogen geeft geen pulstruc, Force-opdracht of automatische nieuwe toestemming.

Een sessie duurt standaard maximaal één uur. Tapwater-only behoudt de tankafkoelregel. Algemeen gebruikt na iedere beëindigde/onderbroken sessie rust en aantoonbaar nieuw zon-/native bewijs; een warme of ontbrekende tank is niet zelfstandig een permanente blokkering. Constante zon of dezelfde samples geeft geen eindeloze herstartlus. De volledige startvertraging en actuele guards blijven gelden.

De korte lokale controle opent geen elektrische apparatuur. Fysieke SG-/timerproef en natuurlijke automatische sessie worden uitsluitend na expliciete toestemming uitgevoerd. Zonder echte mapping-/timer-/profielbevestiging blijft automatische SG geblokkeerd; gezonde andere apparaten houden hun eigen voorwaarden. De historische stilstandoorzaak blijft onbeslist.

## Rollback

Geef eerst de eigen SG-aanvraag vrij en controleer contactstand/lokale afloop. Stop de nieuwe runtime voordat beta.64 terugkomt. Herstel beta.64-code én de volledige passende privéback-up van vóór deze upgrade; een oude ZIP alleen herstelt nieuwe schema-/bewijsvelden niet exact. Laat nooit twee versies tegelijk het contact beheren.

Voor terugkeer naar de oude directe beta.61-regeling blijft de volledige passende back-up van vóór beta.62-migratie noodzakelijk. Privé herkomstarchief is geen complete HA-restore en doet geen fysieke replay. Zie de releasehandleiding voor de volledige procedure.
