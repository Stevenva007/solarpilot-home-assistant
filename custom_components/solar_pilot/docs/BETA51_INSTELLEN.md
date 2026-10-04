# SolarPilot 1.0.0-beta.51 — instellen en controleren

Beta.51 laat het zijbalkpaneel en de automatisch beschikbare dashboardkaart via hetzelfde JavaScript-modulebestand laden. Dit voorkomt de eerdere combinatie van klassieke scriptlading en modulelading. Herhaald laden van release-URL's geeft geen dubbele eigen kaartcatalogusitems; kaarten van andere integraties blijven behouden. Alle boiler- en veiligheidsregels uit beta.50 blijven gelden.

## Bronbasis en gegevensbehoud

De codebasis is de werkelijk gepubliceerde beta.50 op commit `5348ecaedd75326debc3b60764ab711882adf446`, tree `e67da41e0928a25b73893216edf34be6ff0ce5bc`. Haar onveranderlijke release en gecontroleerde pakketten zijn de rollbackbasis. Updates zijn cumulatief: geldige instellingen, toestelbindingen, prioriteiten, modellen, historiek en APP-aanvragen blijven behouden. Deze frontendreparatie vraagt geen algemene leerreset of extra fysieke toestemming.

## Upgrade en frontendcontrole

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.50-release.
2. Laat beschermde afwas- of andere cycli afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.51` via HACS zodra de release beschikbaar is, of vervang uitsluitend `custom_components/solar_pilot` met het juiste lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad daarna de webpagina; op Android stop je de Home Assistant-app volledig en open je haar opnieuw, op iOS kun je de weergave naar beneden trekken om te verversen.
5. Controleer backendversie en geladen kaart afzonderlijk, open SolarPilot in de zijbalk en controleer **Uitleg** op beta.51 en hash `7f0c9817f8b1c53a`. Een download of manifestnummer bewijst geen geladen kaartcode.

SolarPilot registreert de gebundelde frontend zelf. Voeg geen tweede www-bestand, extra Lovelace-resource of nieuw dashboard-YAML toe voor deze update. Een al open pagina kan eerder geregistreerde kaartcode vasthouden; een backendherstart alleen vervangt die pagina niet.

De officiële [Home Assistant-paneldocumentatie](https://www.home-assistant.io/integrations/panel_custom/) onderscheidt `module_url` voor modulelading en `js_url` voor klassieke scriptlading. De [Companion FAQ](https://companion.home-assistant.io/docs/troubleshooting/faqs/#something-in-home-assistant-doesnt-work-the-same-way-it-does-on-my-desktop) beschrijft het verversen/heropenen van de app en vergelijking met een browser. Dit vraagt geen wissen van Home Assistant-configuratie, leerdata of appregistratie.

## Als de laadmelding blijft verschijnen

De aangeleverde **Unable to load custom panel**-melding met de beta.50-kaart-URL bewijst op zichzelf niet of het kaartbestand, de browser of WebView de specifieke oorzaak is. Beta.51 herstelt twee aangetoonde problemen bij herladen: botsende globale declaraties bij opnieuw klassiek laden en dubbele eigen kaartcatalogusitems. Dat bewijst niet dat deze problemen de aangeleverde melding veroorzaakten of dat een eventuele live HTTP-fout daarmee is opgelost.

Vergelijk de app met dezelfde Home Assistant-installatie in een browser. Noteer bij een blijvende fout de werkelijk gevraagde kaart-URL en de bijbehorende HTTP-status, inhoudstype en browser-/appfout. Een bestandsantwoord dat geen bruikbare JavaScript levert vraagt een andere diagnose dan een fout tijdens module-evaluatie. Deel geen aanmeldtokens of private serveradressen. Dit zijn uitleescontroles; verander geen boilerstand, wachttijd of toestelbediening om de interface te testen.

## Behouden boiler- en toestelregels

De reparatie uit beta.50 blijft behouden: zonnestabiliteit en de minimumtijd sinds de laatste werkelijk verstuurde boilerdoelopdracht lopen afzonderlijk. Een voortdurend geldige afgeronde stabiliteitscontrole begint niet opnieuw alleen vanwege opdrachtrust. De standaard 1800 seconden sinds de laatste opdracht, bronversheid, koeling, hygiëne, eigendom, doelbevestiging en zichtbare uitvoeringswachtreden blijven gelden. Een onuitgevoerd hoog voorstel krijgt geen eigendoms- of hysteresevrijgave.

Handmatige OFF-zones blijven uit tot expliciete gebruikers-AUTO. Beschermde afwascycli worden niet onderbroken; onzekere opdrachten krijgen geen blinde retry. De Wallbox blijft read-only. Geldige leerdata en alle bestaande actuator-, elektrische, comfort- en prioriteitsgrenzen blijven behouden. Geen Force DHW, Powerful, extra APP-aanvraag of algemene datareset.

## Teststatus en rollback

De softwaregate staat in `TESTRESULTATEN_BETA51.md`. Node-tests met DOM-doubles controleren echte module-evaluatie, kaartregistratie en paneelconstructie; zij bewijzen geen browser-HTTP-levering, WebView-cache of geladen live appkaart. Er is in deze werksessie geen live Home Assistant-toegang of fysieke toestelactie.

Voor rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.50-release of gecontroleerde volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart, actuele bronnen, eigendom en beveiligingen controleren**. Beta.50 behoudt de boilerreparatie en eerdere veiligheidsregels, maar bevat nog de klassieke/module-loadercombinatie en mogelijke dubbele eigen catalogusitems die beta.51 herstelt. Oude releasedocumenten blijven historie; het actuele `OVERDRACHT.md` beschrijft de huidige bron.
