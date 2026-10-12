# SolarPilot 1.0.0-beta.80 — Aquarea-bedrijfsstand en SG-koeldiagnose

Deze update herstelt een concrete compatibiliteitsfout bij de ondersteunde oudere Aquarea-integratie: een werkelijk nieuwe cloudrapportage kon onherkend blijven terwijl de integratie wel de actuele bedrijfsstand bezat. De moderne providerroute blijft ondersteund. De SG-diagnose benoemt nu welke bestaande bron of lokale bevestiging ontbreekt.

De update verandert geen Panasonic-programma, SG-percentage, koeltemperatuur, bronbinding, prioriteit, actuatorrecht of condensbevestiging. Alle beta.79-auditcorrecties blijven behouden. Geen add-on, externe solver, extra package, tweede regelaar of nieuwe hardware nodig voor deze softwarecorrectie.

## Upgrade met behoud van gegevens

1. Maak een volledige privé Home Assistant-back-up, inclusief instellingen, eigen opslag, modellen, PV-factoren, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.79-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.80` na geslaagde releasecontroles. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart Home Assistant volledig en herlaad app/browser volledig. Controleer backend- én kaartversie onder **Instellingen & controle**.
5. Open bij de warmtepomp **Waarom wel of nog niet?** en bekijk de SG-koeldiagnose. Laat de Aquarea-integratie een nieuwe geslaagde cloudpoll leveren. Een opgeslagen startup-snapshot geeft geen actuele vrijgave.

Verwijder of hermaak de integratie niet. Geldige bestaande SG-/profiel-/split-/koelbevestigingen, APP-deadlines en verbruikte beladingen blijven behouden. Een gewone update verleent geen nieuwe AEG-START.

## Blijvende oplossing voor de koelvoorwaarde

| Diagnose | Wat helpt |
|---|---|
| Geen gekoppelde ruimtebron | Controleer de bestaande Panasonic-bronkeuze in SG-instellingen. Alleen werkelijk bij hetzelfde toestel horende native klimaatbronnen zijn bruikbaar. Automatisch ontdekte displaybronnen worden niet stil als controlbron opgeslagen. |
| Bron ontbreekt of is verouderd | Herstel de betreffende Aquarea-bron of cloudverbinding en wacht op een echte nieuwe geslaagde rapportage. De diagnose toont de betrokken bron en tijd; een oude meting langer geldig verklaren is geen herstel. |
| AUTO-programma onbekend | De gekozen AUTO-stand vertelt niet of Panasonic verwarmen of koelen kiest. De ondersteunde native programme-uitlezing gebruikt een nieuwe geverifieerde providerpoll; een optimistische lokale modewijziging bewijst dat niet. |
| Tegenstrijdige context | Controleer de aangewezen bestaande ruimtebronnen, hun actuele programme en acties. Tankopwarming alleen kan een strijdige koelbron niet opheffen. |
| Verse context sluit koeling uit | De algemene SG-aanvraag mag binnen de overige bestaande voorwaarden starten en vernieuwen. Hiervoor is geen condensbevestiging vereist. |
| Koeling mogelijk en condensbeveiliging niet bevestigd | Stel lokaal vast welke geschikte beveiliging werkelijk aanwezig is en werkt. Bevestig de bestaande optie uitsluitend op basis van die controle. De software bevestigt dit niet namens de installatie. |

SolarPilot gebruikt geen verwarmingstoestemming uit tanktemperatuur, watts, kalender, sterilisatie of een automatisch gevonden displaybron. Een geplande of actieve sterilisatie is geen afzonderlijke SG-blokkering. Panasonic blijft eigenaar van de uitvoering daarvan.

Voor beoordeling van een concrete installatie zijn een actueel privé SolarPilot-analysebestand, de gebruikte koelafgifte (vloer/wand/plafond of ventiloconvectoren) en de aanwezige automatische dauwpunt-/condensbeveiliging relevant. Indien de beveiliging onbekend is, kan de verse bewezen verwarmingsroute wel werken; mogelijke koeling blijft afzonderlijk beoordeeld. Extra SG-koeling van −2 °C wordt niet automatisch teruggezet of stil vrijgegeven.

## Behouden regeling

Panasonic blijft read-only behalve het expliciet toegewezen SG-contact. Wallbox blijft read-only; AEG behoudt maximaal één native START per geldige nieuwe belading. De afwasdeadline staat netstroom toe zonder zonnevoorwaarde, binnen bestaande elektrische grenzen en native apparaatvoorwaarden.

SG behoudt bestaande gebruikerswaarden, standaard 600 W aanhoudende netafname / vijf continue minuten / twintig minuten minimum, de begrensde sessie en korte lokale leases 300 s met vernieuwing 60 s. Harde bron-, net-, fase-, kwartier-, batterij-, lease-, handmatige- en voorrangsvoorwaarden blijven leidend. Een nieuwe poll maakt geen oud ON-journal opnieuw uitvoerbaar.

## Rollback naar beta.79

Geef een eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.80 en herstel gecontroleerde beta.79-code. Behoud dezelfde entry, instellingen, actuele opslag en userfiles. De brede beta.79-auditcorrecties blijven beschikbaar; de nieuwe legacy-providerherkenning en gerichte koeldiagnose vervallen.

Exact herstel vraagt de passende volledige privéback-up. Bewaar gewenste nieuwe historie eerst. Herstel geen oude onverbruikte APP-aanvraag nadat dezelfde belading al gestart of afgerond is. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken.

Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Uitgevoerde brongebonden controles en pakketbewijs: [TESTRESULTATEN_BETA80.md](TESTRESULTATEN_BETA80.md). Softwareproeven bewijzen geen aanwezige fysieke condensbeveiliging of live Panasonic-/Shelly-reactie.
