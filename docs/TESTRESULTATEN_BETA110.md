# SolarPilot beta.110 — softwarevalidatie

## Controle

Deze release wordt getoetst op actuele P1-verdeling zonder toekomstige afwas- of thermostaatreserve, de SG-totaalraming met alleen de resterende mogelijke toename, werkelijk startklare prioriteitskandidaten, beschermde cycli, geserialiseerde opdrachten en hercontrole na opslag- en transportwachten. Nieuwe regressies controleren ook informatieve firmwareversiewijzigingen zonder blokkade of handmatige herbevestiging, automatisch herstel van de oude firmware-only-latch met geldig bewijs en de bewaarde oorspronkelijke wijzigingsdiagnose.

De begrensde SG-/Wallboxreactie omvat oorspronkelijk episodeplafond en absolute eindtijd, herstel met nieuwe lage P1-rapporten, bronverlies, herstart, klokafwijkingen, effectieve volgorde, finale transportcontrole, afzonderlijke fase-, kwartier- en batterijgrenzen, externe AAN-waarneming, UI-aftellers en exportprivacy. De beta.109-recorderregressies blijven behouden.

**Definitieve volledige testuitslag: 8949 tests geslaagd, zonder fouten of skips.** De ongewijzigde definitieve bron is volledig gecontroleerd, met 242 nieuwe regressies: 121 voor actuele lastverdeling, SG-totaalraming, broncoherentie en automatische firmwareverificatie, plus 121 voor de begrensde Wallboxreactie. De onafhankelijke adversarial review vond geen materiële fout. De verzamelde testlijst bevat eveneens exact 8949 tests; de volledige loop eindigde op 100% met exitcode 0. Actuele uitleg, veldhulp, overdracht, privacy/structuur, SG-grens, beide JavaScript-syntaxcontroles en online upstreamreview horen bij dezelfde bron.

Alle vijf bestaande commitgebonden GitHub Validate-gates blijven verplicht: repository met volledige testsuite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Main herhaalt de gates. De vier gedownloade release-assets worden vervolgens met de exacte tag en bron-SHA vergeleken. Een oudere groene commit of alleen een gemaakte ZIP voldoet niet.

Er is geen fysieke SG-, warmtepomp- of laadproef uitgevoerd. Fictieve tests bewijzen geen werkelijke terugregeling, bekabeling, lokale timerwerking of gerealiseerde besparing. Privé-exportgegevens zijn geen openbare fixtures.
