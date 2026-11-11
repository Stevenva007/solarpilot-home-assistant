# SolarPilot beta.118 — softwarevalidatie

## Gedrag dat wordt getoetst

De regressies simuleren voor- en achterlopende schermklokken en herhaalde oorspronkelijke bronpublicaties. Een ingelezen keuze Automatisch en bevestigd open contact moeten stabiel blijven. Nieuwe tijdsafstemming mag oude bronrapporten niet verjongen, toekomstige rapporten niet goedkeuren en lokale contact- of handmatige eindtijden niet verlengen.

De uitsluitend uitleesbare WS-route vereist authenticatie en een geladen SolarPilot-entry. Zij accepteert geen tijd, save- of controlargument van de aanvrager. De kaart weigert trage en ongeldige antwoorden; contextwissel, tijdsprong, slaap, verlopen afstemming en onbeschikbare/restored bronstatussen blijven afzonderlijk gecontroleerd.

## Lokale controles

Op 11 november 2026 slaagde de gerichte run met 140 tests voor de nieuwe tijdsafstemming en de bestaande SG-bediening, platformen en sensorregistratie. Daarna slaagde de volledige lokale suite met **9610 tests** in **235,15 seconden**. JavaScript-syntaxis, actuele uitleg/veldhulp, handoff, SG-opdrachtgrens en de online upstreamcontrole slaagden. De upstream-HEADs en gepubliceerde stabiele releases zijn nog gelijk aan het inhoudelijk beoordeelde beta.117-checkpoint; er zijn geen aanvullende onbewerkte bronwijzigingen. Ook de afzonderlijke repositoryprivacy-/structuurcontrole slaagde na het verwijderen van gegenereerde Python-cachebestanden.

Lokale Chromium-start is in deze werkruimte niet toegestaan door de proces-/socketomgeving. Daarom is een lokale browserrun geen geslaagd bewijs. De verplichte GitHub Chromium-gate voert de echte knoppenproef met 453 fictieve actuele publicaties, mobiel/breed scherm en bronveroudering uit. De bestaande vijf gates blijven verplicht.

## Commitgebonden validatie en publicatie

Publicatie vereist vijf groene Validate-gates op de exacte PR-HEAD: repository en volledige testsuite, HACS, Hassfest, Chromium-interacties en echte Home Assistant-startup. De echte-HA-proef controleert ook de geregistreerde tijdsroute, schema, ingelogde gewone lezer, weigering van anonieme aanvragen en behoud van configuratie/SG-opslag.

Na samenvoegen herhaalt main alle gates en maakt daarna pas tag en vier assets. De teruggedownloade HACS-ZIP, lokale integratie-ZIP en twee releasedocumenten worden tegen de exacte tag en bron-SHA vergeleken. Een mislukte gate wordt niet met een losse ZIP omzeild. Geen fysieke SG-/warmtepompproef of aangepaste lokale veiligheidstoestemming.
