# SolarPilot beta.99 — aanklikbare geschiedenis en betrouwbare bronverwerking

Versie: **1.0.0-beta.99** · 18 oktober 2026 · Bouwbasis: gepubliceerde beta.98.

## Wat verandert

Lange warmtepompsessies tonen een compacte samenvatting per taak en bewijsniveau. Alle oorspronkelijk geregistreerde perioden blijven chronologisch uitklapbaar. Korte perioden tonen seconden en duur. Een los meetpunt krijgt het label dat er geen duur is vastgesteld; een echte positieve periode onder één seconde blijft een periode. Elektrische ondersteuning staat afzonderlijk naast de taak. Bij overlappende bronperioden is de opgetelde duur als zodanig herkenbaar; dit is geen aaneengesloten fysieke looptijd.

De samenvatting is uitsluitend presentatie. Zij vult onbekende tijd niet in, maakt geen compressorcycli, wijzigt geen historische taak en verdeelt geen kWh over taken. De tijdlijnen, aanraakbare markering, oorspronkelijke meetpunten en dagtotalen blijven dezelfde geregistreerde gegevens gebruiken. Een meetgat blijft herkenbaar. Een lijstregel met Taak onbekend betekent ontbrekend taakbewijs tijdens eventueel waargenomen elektrische activiteit.

Daarnaast herstelt deze versie een reproduceerbare volgordefout bij Aquarea-bronberichten. Een uitlezing tijdens de verwerking van een nieuw bericht mag dat bericht niet al als verwerkt registreren. De echte bevestiging van hetzelfde nieuwe geldige bericht kan daarna direct bruikbaar worden. Zonder die bevestiging ontstaat geen nieuw bewijs. Cachedata, wijzigingen aan dezelfde afgekeurde status, ongeschikte bronnen en mislukte polls blijven beschermd. Een schermopname bewijst niet welke oorzaak bij een specifieke historische onderbreking speelde; eerdere onbekende perioden worden niet achteraf gewijzigd.

Aquarea 1.8.0 en de werkelijke SDK 1.4.0 zijn opnieuw met de actuele GitHub-defaultbranches, stabiele releases en tagcommits vergeleken. Er zijn sinds beta.98 geen nieuwe bronwijzigingen. De afzonderlijke LIVE/CACHED-semantiek en de stabiele broncontrole over Python-versies blijven behouden.

## Andere toestellen en sturingen

Gewone en gearchiveerde toestellen krijgen klikbare tijdlijnen, sessies en gebeurtenissen met hun bewaarde tijden, duur, bevestiging en redenen. Een compacte selectie houdt de tijdsbalk op mobiel bereikbaar; volledige oorspronkelijke tijden en redenen blijven uitklapbaar. Een lege plek is geen bewezen UIT. Historisch vermogen, programma of doel wordt niet uit de actuele toestand ingevuld. Wallbox-laadperioden worden afzonderlijk aanklikbaar met oorspronkelijke status- en grensmetingen; SG houdt zijn afzonderlijke aanvraag-, contact- en ontvangstlagen.

Voor aanvullende metingen en sturingen is **Bronhistorie** beschikbaar. Kies de gekoppelde bron om de geschiedenisweergave van Home Assistant te openen, bijvoorbeeld SoC, batterijvermogen of een regeldoel. Alleen toegestane huidige bronkoppelingen met leesrechten zijn bereikbaar. De normale Home Assistant Recorder, bewaartermijn en eigen toegang bepalen welke brongegevens bestaan. Dit is de geschiedenis van die entiteit, geen achteraf bewezen toestelbinding. Er wordt geen analysearchief ontsloten, recorder ingeschakeld, meting verzonnen of opdracht uitgevoerd.

Tik op de huidige boilertemperatuur of het ingestelde doel om direct de bijbehorende Home Assistant-historyweergave te openen. De knop volgt de bron van de getoonde waarde. Bij twee attributen van dezelfde Aquarea-boilerentiteit openen beide knoppen die entiteit. Het berekende SG-doel heeft geen afzonderlijke bronentiteit.

## Bijwerken

1. Bewaar een volledige privé Home Assistant-back-up.
2. Werk via HACS bij naar beta.99 na geslaagde releasecontroles en publicatie. Behoud dezelfde entry, instellingen, modellen, opslag, historie en userfiles.
3. Herstart Home Assistant volledig en herlaad de app/browser. Controleer backend- en kaartversie apart.
4. Open Warmtepomp → Geschiedenis. Bekijk een lange sessie, klap de oorspronkelijke taakperioden open en controleer seconden en korte duur. De markering op de balken blijft beschikbaar.
5. Open bij een ander toestel **Geschiedenis**. Tik op de balk, sessie of gebeurtenis voor de bewaarde details. Open bij een batterij of Wallbox **Bronhistorie in HA** om een gekoppelde bron te kiezen; Home Assistant toont haar beschikbare geschiedenis.

Geen nieuwe bron, percentage, SG-profiel of bevestiging is nodig. Panasonic blijft zelfstandig regelen; SolarPilot bedient voor de warmtepomp uitsluitend de bestaande toegestane SG-uitgang. Deze update installeert Aquarea niet en voert geen lokale HA-update uit.

## Rollback

Herstel indien nodig de gepubliceerde beta.98-code met behoud van entry, opslag en userfiles. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk vooraf veilig vrij en onderbreek geen beschermde cyclus. Herstart Home Assistant volledig en herlaad de app. Beta.98 behoudt de aanraakbare warmtepompgeschiedenis en Aquarea 1.8.0/SDK 1.4.0, maar mist de nieuwe overige klikdetails, compacte periodeweergave en bronvolgordecorrectie. Er is geen opslagmigratie of historieherstel nodig.

[Actuele werking](ACTUELE_WERKING.md) · [Testverslag](TESTRESULTATEN_BETA99.md) · [Overdracht](../OVERDRACHT.md)
