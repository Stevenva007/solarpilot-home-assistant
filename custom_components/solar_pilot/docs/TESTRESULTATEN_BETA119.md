# SolarPilot beta.119 — softwarevalidatie

## Gedrag en bewijsgrenzen

De regressies gebruiken fictieve grote forecasts en planning. Ze toetsen dat de gezamenlijke live-attributen van 23 deelsensoren plus de complete EMS-statussensor minder dan 30% van de vroegere herhaling bevatten. Dit is een vergelijking van geserialiseerde attributen, geen netwerkbandbreedte- of fysieke paneelmeting.

De complete EMS-statussensor en Status → `ems` houden hetzelfde complete gecachte object. De tests controleren onveranderde native waarden, bronobjecten, onbekende waarden, rapporttijden en geldigheidsgrenzen. Niet-gerelateerde batterij-/plannerwijzigingen veranderen de lokale-PV-attributen niet; een nieuwe passende fasepublicatie wordt wel doorgegeven. Er worden geen services aangeroepen.

## Lokale controles

Op 14 november 2026 slaagden **31 gerichte sensorregressies**. Hieronder vallen de bestaande Recorder-, publicatie-, geld- en isolatietests en negen nieuwe payloadregressies. Daarna slaagde de volledige lokale suite met **9619 tests in 586,57 seconden** onder Python 3.12. De controles voor repositorystructuur/privacy, actuele uitleg en veldhulp, overdracht, SG-opdrachtgrens en JavaScript-syntax slaagden. De online upstreamcontrole bevestigde dat beide actuele Aquarea/SDK-HEADs en de gepubliceerde stabiele tags nog overeenkomen met de inhoudelijk beoordeelde bronpinnen. Deze controle installeert geen provider en verleent geen compatibiliteits- of bedieningsrecht.

## Verplichte publicatiecontrole

Alle vijf Validate-gates moeten op de exacte PR-HEAD slagen: repository en volledige testsuite, HACS, Hassfest, Chromium-interacties en echte Home Assistant-startup. De bestaande browserproeven behouden de complete EMS-bron van het dashboard. Main herhaalt alle gates, maakt vervolgens de tag en vier assets en vergelijkt de teruggedownloade pakketten met die exacte broncommit.

Een mislukte gate wordt niet met een los installatiepakket omzeild. Dit softwarebewijs bevat geen fysieke SG-/warmtepompproef en bewijst op zichzelf geen herstelde wandpaneelverbinding.
