# SolarPilot publiceren

Gebruik de bestaande repository. Publiceer wijzigingen eerst op een werkbranch en open een pull request naar main. Verplaats geen oude tags en overschrijf geen release-assets.

## Controle vóór samenvoegen

Werk manifest, const, frontendversies, actuele uitleg, veldhulp, CHANGELOG en OVERDRACHT samen bij. Iedere release heeft een eigen installatie-/rollbackdocument en testverslag, ook ingebed in de integratie. Gebruik uitsluitend generieke of fictieve gegevens in broncode, fixtures en documentatie.

Voer passende regressies, de volledige suite, actuele-uitleg-/handoffcontrole, repositoryprivacy/structuur, SG-opdrachtgrens, actuele online upstreamreview en JavaScript-syntaxcontrole uit. Bouw het offline voorbeeld uit de actuele bron. De verplichte GitHub Validate-workflow toetst vijf afzonderlijke onderdelen:

1. Repository, documentatie, upstream, grenzen en volledige testsuite.
2. HACS.
3. Hassfest.
4. De echte Chromium-interactietests met fictieve data, waaronder voorrang, externe SG-overname en de actuele SG-stop-/netgrensuitleg.
5. Echte Home Assistant-startup met huidige en historische immutable fixtures.

Voeg alleen de gecontroleerde head samen wanneer alle vijf slagen. Een oudere groene commit is geen bewijs voor een nieuwe wijziging. Publiceer geen ZIP als vervanging voor een mislukte verplichte gate.

## Publicatie op main

Main herhaalt de vijf gates. Alleen daarna maakt dezelfde Validate-workflow de versie-tag, een HACS-repository-ZIP, een lokale integratie-ZIP en de twee release-documenten. De vier gedownloade assets worden met tools/check_release_packages.py opnieuw tegen de exacte tag en broncommit vergeleken.

De oude afzonderlijke Manual Release-workflow is verwijderd: die route maakte alleen een release en hield de volledige vijf-gate- en assetprocedure niet afgedwongen. Er is één publicatieroute. Een bestaande tag of release wordt nooit verplaatst of overschreven om een mislukte controle groen te maken.

## Verificatie achteraf

Controleer de definitieve main-commit, geslaagde jobs, gepubliceerde tagcommit en vier overeenkomstige assets. Vermeld pas daarna dat de update via HACS beschikbaar is. Installeren op een gebruikersinstallatie en een fysieke SG-/Wallbox-proef zijn aparte handelingen; softwarepublicatie bewijst die niet.
