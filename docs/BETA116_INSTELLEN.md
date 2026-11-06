# SolarPilot beta.116 — installatie en rollback

## Wat deze versie oplost

Na een SG-stop door onbetrouwbare noodzakelijke energiemetingen mag een nog actieve tijdelijke handmatige AAN-keuze niet iedere korte bronterugkeer in een nieuwe AAN-puls omzetten. Eerst loopt de bestaande ingestelde bronstoprust, standaard 900 seconden. Daarna zijn bevestigde actuele UIT, meerdere nieuwe oorspronkelijke bronrapporten en de ingestelde startstabiliteit, standaard 120 seconden, nodig. Wisselende of ongeldige bronkwaliteit wist de opgebouwde stabiliteit. Een eerste handmatige AAN-keuze zonder eerdere bronstop houdt het bestaande gedrag.

De bronherstelwacht blijft bij herstart en een nieuwe bedieningskeuze behouden. Stabiliteit van vóór de herstart is geen nieuw bewijs. Automatisch herstel of herstart verlengt de oorspronkelijke handmatige eindtijd niet. Bewust opnieuw een tijdsduur kiezen is een nieuwe gebruikersvraag; dat wist de bronherstelwacht en het oorspronkelijke harde sessiebegin niet. Aanvraagrust, twintigminutenminimum, vijftienminuten-tekortbuffers en onafhankelijke harde grenzen zijn afzonderlijke voorwaarden; een noodzakelijke ongeldige bron kan een lopende aanvraag blijven beëindigen.

De Marstek-route behandelt een herkenbare nog lopende providerpoll afzonderlijk van een mislukte poll. Alleen eerder volledig bevestigd veldbewijs voor dezelfde gekoppelde bron en waarde kan binnen de oorspronkelijke maximale leeftijd van 120 seconden bruikbaar blijven; er ontstaat geen nieuwe ontvangsttijd, nulwaarde of bediening. Verlopen bewijs, expliciete fout, ongeldige kwaliteit en gewijzigde binding blijven afwijzingen. Begrensde bronhistorie helpt de oorspronkelijke afwijsreden terug te vinden. Programmakeuze/veiligheidscontext en gemelde native bedrijfsactie worden in SG-gebeurtenissen apart benoemd.

## Bijwerken

1. Maak vooraf een volledige privé Home Assistant-back-up inclusief SolarPilot-configuratie en -opslag.
2. Werk na gepubliceerde release via HACS bij naar **1.0.0-beta.116**.
3. Herstart Home Assistant volledig. Herlaad de browser of sluit en heropen de HA-app om de meegeleverde kaart/optiehulp te laden.
4. Behoud bestaande configuratie, sensorkoppelingen, bewuste bronbevestigingen, tijdelijke eindtijden en privégeschiedenis. Verwijder de integratie niet en maak geen duplicaat batterijprofiel.
5. Controleer zonder geforceerde fysieke proef de actuele bronreden en SG-status. Na een eerdere bronstop kan de bronherstelwacht terecht langer zichtbaar blijven dan één geldige meting. Na werkelijk nieuw stabiel bewijs worden de actuele voorwaarden opnieuw getoetst.

Geen nieuwe Home Assistant-hulpentiteiten, YAML, extra polling of fabrikantappinstelling nodig. De update bevestigt geen AC-bron, koppelt geen sensor en verandert geen Panasonic-doel, native programma of Wallbox-/batterijbediening. Panasonic blijft verantwoordelijk voor comfort en warm water. Een actuele bron kan ook om een echte providerfout onbruikbaar blijven; deze update beweert geen reparatie van wifi, firmware of fysieke meting.

## Rollback

Rollback naar beta.115 behoudt de bestaande configuratie maar mist de nieuwe SG-bronherstelblokkering en het begrensde onderscheid tussen een lopende en mislukte Marstek-poll. Daardoor kan de oude tijdelijke handmatige route opnieuw kort schakelen bij wisselende bronkwaliteit. Gebruik bij rollback geen tijdelijke SG-AAN-keuze als workaround voor bronuitval. Een bestaande lokale SG-toestemming houdt haar eigen korte timer en veilige eindtijd; geen oude opdracht opnieuw uitvoeren.

Gebruik voor oudere versies de bijbehorende installatie-/rollbackdocumentatie; verwijder geen privéopslag om een bronwacht te wissen. De bronwijziging is geen migratie van oorspronkelijke meettijden. Zie [TESTRESULTATEN_BETA116.md](TESTRESULTATEN_BETA116.md) voor de softwarecontrole en bewijsgrenzen.
