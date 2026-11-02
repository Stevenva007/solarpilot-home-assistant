# SolarPilot beta.114 — softwarevalidatie

## Wijzigingen die worden gecontroleerd

Een actief Marstek-profiel vraagt vóór opslaan een letterlijke bevestiging van zijn AC-meetdekking. Een bekende verkeerde native meetsoort of strijdige bekende tekenrichting krijgt een veldfout. Een reeds opgeslagen onvoltooide koppeling wordt niet automatisch bevestigd of vervangen.

Batterijoverzicht, algemene bronmelding, SG en analyse-export benoemen concrete bronoorzaken. De diagnostiek onderscheidt ontbrekende AC-bevestiging, verkeerde native veldbetekenis en ontbrekend actueel veldbewijs. Veilige metadata kan het verwachte en aangetroffen native veld tonen. Ruwe providerantwoorden, netwerkidentiteit en privé-installatiegegevens horen niet in publieke fixtures of documentatie.

De meetvoorwaarden blijven behouden: complete afzonderlijke bronnen, juiste eenheden en tekens, oorspronkelijke rapporttijden, daadwerkelijk native veldbewijs, afzonderlijke SoC en geen onbekende waarde als nul. Geen automatisch aangezet bevestigingsvinkje, nieuwe bronbinding, polling of batterijbediening.

Basislastleren kan een ingeschakelde vloot gebruiken wanneer alle actieve batterijen afzonderlijk volledige expliciet bevestigde getekende AC-metingen leveren. Getekende sommen, laden, ontladen, gemengde profielen, onbekende SoC bij een monitor, oorspronkelijke native tijd, onderlinge bronalignment, dubbele rollen en centrale-meteroverlap moeten worden getoetst. Onbekende of gedeeltelijke bronnen verlenen geen leerbewijs. Generieke profielen behouden hun bestaande voorwaarden en vragen voor deze fleetcorrectie eveneens expliciete AC-bevestiging.

De bestaande SG-buffer-, eigendoms-, Wallbox-, tijd-, firmware-, fase-, kwartier-, afwas-, opslag- en commandogrensregressies blijven vereist. Basislastleren wijzigt geen realtime vrij vermogen, instelling, controlerecht of oudere meetdekking. Nieuwe fixtures gebruiken uitsluitend fictieve bronnen.

## Upstreamcontrole

De officiële Aquarea-/SDK-defaultbranch-HEADs, nieuwste gepubliceerde stabiele releases en opgeloste tagcommits zijn op 2 november 2026 opnieuw online gecontroleerd. Aquarea v1.9.1 en SDK v1.5.0 zijn identiek aan het inhoudelijk beoordeelde beta.113-checkpoint. Er is geen nieuwe upstreamwijziging te verwerken en geen automatische providerupgrade. Het afzonderlijk beoordeelde native Marstek-contract blijft vastgepind op v1.12.0. Zie UPSTREAM_BETA114.md.

## Commitgebonden validatie en publicatie

De actuele uitleg en optiehulp worden uit dezelfde canonieke bron gegenereerd. Het overdrachtsdossier, privacy/structuur, bronreview, commandogrenzen, JavaScript-syntax en passende nieuwe regressies worden samen met de volledige testsuite gecontroleerd.

Alle vijf Validate-gates moeten op de exacte PR-HEAD groen zijn vóór samenvoegen: repository/full-suite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. De Chromium-gate bevat ook het herstel van batterijbronnen en monitorweergave met fictieve data. De volledige-suiteuitslag en HA-startup worden bewezen door de Actions-run voor die commit; een oudere groene head of een uitslag tijdens nog veranderende bron is geen vervanging.

Main herhaalt de volledige suite en de overige gates op de uiteindelijke broncommit vóór automatische publicatie. Daarna worden de vier gedownloade release-assets opnieuw tegen de exacte tag en bron-SHA vergeleken. De commitgebonden Actions-runs en hun publicatielog zijn het bewijs van deze resultaten.

Geen fysieke batterij-, SG-, warmtepomp- of laadproef uitgevoerd. Een gepubliceerde versie bewijst geen gemaakte lokale bronkoppeling, bevestigde meetdekking of reeds geïnstalleerde update.
