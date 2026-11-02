# SolarPilot beta.113 — softwarevalidatie

## Wijzigingen die worden gecontroleerd

De Marstek Venus E 3.0-monitor leest uitsluitend bestaande Home Assistant-entiteiten. Vereist zijn een getekende AC-batterijvermogensbron, bewuste tekenrichting en bevestigde meetdekking; SoC en fase zijn optioneel. Geen automatische bronbinding, nieuwe UDP-/Modbuspolling, setpoint, modus- of reservebediening. Het profiel blijft read-only bij verkeerde of achtergebleven controlevelden en algemene bedieningstoestemming.

Vermogensregressies moeten beide richtingen, W/kW, gemeten nul, ontbrekende/verouderde/restored/toekomstige bronnen, verkeerde meetdekking, overlappende sitebronnen en onafhankelijke SoC-weergave toetsen. Ontlading wordt eenmaal van beschikbare zon afgetrokken; laden zit al in P1. Een monitor krijgt geen SoC-reserveprioriteit. Bronkwaliteit en harde grenzen blijven leidend.

De native broncontrole moet de daadwerkelijke Marstek-entiteit/coordinator, oorspronkelijke ES-methodesuccessen, bronkwaliteit en werkelijk ontvangen AC-/SoC-velden toetsen. Herpublicatie van een oud HA-bericht of een gedeeltelijk antwoord zonder het betreffende veld mag geen frisheid creëren. Een nieuw passend antwoord met onveranderde 0 W moet bruikbaar blijven. Bewaard veldbewijs moet zijn oorspronkelijke ontvangsttijd behouden na het opruimen van de kortere providercache en binnen de ingestelde bronleeftijd verlopen. Falende bronstatus wordt meteen onbekend; gewijzigde binding of coordinator wist het eerdere bewijs. Verkeerd bronadres, ontbrekend native veldbewijs, veranderd broncontract, toekomstige tijden en oude cache krijgen geen nieuwe toestemming. SoC en power worden afzonderlijk getoetst. Er mogen geen extra RPC- of netwerkaanvragen plaatsvinden.

De gerichte overdrachtwaarschuwing moet haar betrokken toestel en controle tonen zonder een oude herstelwacht, onzekere opdracht of overige fout automatisch te wissen. Bestaande keuze-, opdracht- en herstelvoorwaarden blijven behouden. Fixtures bevatten uitsluitend fictieve gegevens.

De SG-regeling behoudt de vijftienminutenbuffers en alle beta.112-regressies, waaronder lopend moduleren, niet-gelijktijdige bronrapporten, oorspronkelijke deadlines, handmatige eindtijden, minimale duur, lokale lease en actuele elektrische grenzen.

## Broncontrole

Op 2 november 2026 is de volledige officiële Aquarea-bronvergelijking van v1.9.0 naar v1.9.1 beoordeeld. De login-backoff verleent geen nieuwe geslaagde bronrapportage; SolarPilot bewaakt dat reeds. SDK v1.5.0 blijft ongewijzigd. Drie bestaande bron-/poll-/energieperiodetestsuites slaagden met **131 tests**. Deze gerichte uitslag is geen definitieve volledige beta.113-testuitslag.

De officiële Marstek EU-brochure bevestigt model Venus E 3.0 en 5,12 kWh nominale capaciteit. Er wordt geen fabrikant-API of lokale HA-entiteitsbetekenis uit die capaciteit afgeleid. De gebruiker moet de bestaande daadwerkelijke AC-meetbron expliciet kiezen en bevestigen. Zie UPSTREAM_BETA113.md.

## Definitieve validatie

De gerichte nieuwe Marstek-regressies zijn groen: **116 tests**.

| Onderdeel | Geslaagde gevallen |
|---|---:|
| Native provider en veldactualiteit | 28 |
| Harde read-only-opdrachtgrens | 21 |
| SG en batterijcorrectie | 12 |
| Runtime en batterijflow | 31 |
| Configuratie en UI-contract | 21 |
| Fasebewaking | 3 |

De echte Chromium-controle slaagde op vier schermbreedtes. Ook de historie-, timer- en gemengde kaartencontroles slaagden. De canonieke uitleggenerator en controle zijn groen: **1.0.0-beta.113**, hash **6b26f5854ba02df7**, 371 hulpvelden. Het overdrachtsdossier en de diff-opmaakcontrole zijn groen.

De definitieve publicatievalidatie gebeurt op de exacte PR-HEAD en opnieuw op de uiteindelijke main-commit. De bijbehorende GitHub Actions-runs leveren het commitgebonden bewijs van de volledige suite en HA-startup. Dit document rapporteert de hierboven uitgevoerde gerichte controles en claimt geen volledige-suiteuitslag voor een andere of nog niet gevalideerde commit. Eerdere groene beta.112-uitslagen zijn geen bewijs voor deze nieuwe versie. De actuele uitleg en optiehulp worden uit dezelfde canonieke bron gegenereerd.

Alle vijf Validate-gates moeten voor die exacte bron groen zijn: repository/full-suite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Publicatie vereist de volledige suite en alle overige gates; main herhaalt ze vóór automatische publicatie. Daarna worden de vier gedownloade release-assets tegen de exacte tag en bron-SHA vergeleken.

Geen fysieke Marstek-, SG-, warmtepomp- of laadproef uitgevoerd. Er wordt niet beweerd dat de nieuwe batterij al lokaal is gekoppeld. Privé-installatiegegevens, exports en apparaatidentiteiten horen niet in de openbare repository of fixtures.
