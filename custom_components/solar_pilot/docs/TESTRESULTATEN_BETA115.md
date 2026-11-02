# SolarPilot beta.115 — softwarevalidatie

## Gedrag dat wordt gecontroleerd

De gewone Marstek-menuactie configureert bij nul bestaande monitoren de eerste monitor, laadt bij één bestaande monitor dezelfde identiteit met de opgeslagen velden en laat bij meerdere Marstek-monitoren eerst het betreffende profiel kiezen. Een afzonderlijke expliciete Extra Marstek-monitor toevoegen-route maakt een nieuw profiel. Generieke batterijen worden niet stil als Marstek herkend. Backendveldvalidatie, AC-bevestiging, bekende native bron-/tekencontrole en conflictafwijzing blijven vereist.

Verder in een formulier slaat nog niets op. Alleen de laatste overzichtsstap met bewuste bevestiging en Wijzigingen opslaan kan de wijziging vastleggen. Annuleren en ontbrekende bevestiging veranderen de bestaande configuratie niet. Veldfouten behouden de lokale invoer, inclusief lege optionele velden en false-vinkjes. Een geslaagde eindstap toont opslag; een netwerkfout bewijst dat niet. Regressies controleren opnieuw openen, dezelfde profielidentiteit en het voorkomen van een onbedoeld duplicaat.

De eigen entiteitskiezer filtert namen en entity_id's binnen een begrensde lijst met eigen achtergrond en scroll. Zoektekst en gekozen entity_id blijven afzonderlijk; alleen een geschikte exacte entiteit gaat naar de backend. Toetsenbordnavigatie, keuze, wissen, fouten, focus en mobiele schermhoogte worden met fictieve bronnen gecontroleerd. De echte Chromium-proef gebruikt gesimuleerde mobiele scherm- en toetsenbordhoogtes, geen fysieke Android- of WebViewinstallatie.

Routecontroles toetsen het werkelijke backendmenu voor batterij-/Wallboxconfiguratie. Account- en integratiewissel maken de geopende conceptsessie ongeldig; late antwoorden en invoer uit de oude context mogen niet overgaan. Een globale batterijbronmelding biedt Batterijbron controleren en geen foutreset. Echte toestelstoringen behouden hun bestaande herstelroute. Het openen, zoeken en bewaren verleent geen actuatorrecht. Marstek blijft uitsluitend uitleesbaar; er is geen automatische AC-bevestiging, bronbinding, polling of fabrikantbediening.

## Grenzen en bronnen

De bestaande oorspronkelijke bronrapporttijden, native veldbewijzen, afzonderlijke SoC, basislast-fleetvoorwaarden, SG-buffers, eigendom, Wallboxreactie, deadlines, fase-/kwartiergrenzen, afwascyclus en opslag-/commandogrenzen blijven vereist. Ontbrekende gegevens worden geen nul. Fixtures bevatten alleen generieke of fictieve data.

Op 2 november 2026 zijn de acht officiële Aquarea-/SDK-bronrecords opnieuw online gecontroleerd: publieke identiteit, defaultbranch, HEAD, laatste gepubliceerde stabiele release en opgeloste tag. Aquarea v1.9.1 en SDK v1.5.0 zijn identiek aan het inhoudelijk beoordeelde checkpoint. Er is geen nieuwe upstreamdiff. Het afzonderlijke native Marstek-contract blijft vastgepind op v1.12.0. Zie [UPSTREAM_BETA115.md](UPSTREAM_BETA115.md).

## Commitgebonden validatie en publicatie

Canonieke uitleg en optiehulp worden uit dezelfde actuele bron gegenereerd. Overdracht, privacy/structuur, SG-opdrachtgrens, upstreamreview, JavaScript-syntax, passende regressies en de volledige suite worden gezamenlijk gecontroleerd. De vaste echte-Home-Assistant-gate controleert de huidige en historische immutable startupfixtures; de aanvullende optiestest controleert de werkelijke optionsflow en het teruglezen van bewaarde batterijopties.

Alle vijf Validate-gates moeten op de exacte PR-HEAD groen zijn vóór samenvoegen: repository/full-suite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Main herhaalt dezelfde gates vóór de automatische versie-tag en vier release-assets. Daarna worden de vier gedownloade assets opnieuw tegen de exacte tag en bron-SHA vergeleken. De Actions-run en publicatielog voor die commit bewijzen de volledige-suiteuitslag, HA-startup en pakketten; een oudere groene commit is geen vervanging.

Geen fysieke batterij-, SG-, warmtepomp- of laadproef uitgevoerd. Publicatie bewijst geen lokale installatie, reeds gerepareerde huishoudconfiguratie, fysieke kalibratie of meetdekking.
