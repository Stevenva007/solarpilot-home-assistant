# SolarPilot beta.98 — details bij aanraken van de geschiedenis

Versie: **1.0.0-beta.98** · 18 oktober 2026 · Bouwbasis: gepubliceerde beta.97.

## Schuiven door historische meetpunten

Open **Warmtepomp → Geschiedenis**. Schuif horizontaal met je vinger over de taakbalk, SG-contactbalk of een andere tijdsbalk. De balken delen één markering en een detailvak met de geselecteerde tijd, taak, SG-informatie en beschikbare gemeten waarden. Op een computer zijn muis en toetsenbord beschikbaar. Vorig/volgend meetpunt maakt de werkelijk bewaarde punten ook apart bereikbaar.

Wanneer een meetpunt voldoende dichtbij ligt, springt de markering naar de daadwerkelijke vastleggingstijd. Dat tijdstip geldt ook voor de taak- en SG-informatie. Boilertemperatuur, normaal doel, berekend SG-doel, totaalvermogen en afzonderlijke voedingen houden daarnaast hun oorspronkelijke rapporttijden. Het bovenste vak **Boiler nu** blijft de actuele toestand tonen; dat wordt niet gebruikt om oude uren aan te vullen.

Niet ieder uur bevat een volledige meting. Bij een meetgat, ontbrekend oud totaal of onbruikbare bron staat de betreffende waarde onbekend. Er worden geen tussenliggende watts of temperaturen berekend. De vergelijkingspunten worden bij relevante contextwijzigingen en uiterlijk volgens het bestaande vijfminutenritme vastgelegd, met de bestaande begrensde retentie. Dit is geen continue vermogensgrafiek.

Nieuwe vergelijkingspunten bewaren aanvullend het gevalideerde volledige warmtepompvermogen. Oudere punten krijgen geen achteraf opgeteld totaal uit hun deelvoedingen. Het weergegeven W-vermogen is een meting op dat punt. Het dagelijkse gemeten kWh-verbruik en zijn meetdekking blijven apart; verbruik per taak, compressor of SG-sessie wordt niet verzonnen.

De markering gebruikt de werkelijke lokale daggrenzen. Daardoor blijven dagen van 23 of 25 uur correct en houden dubbele uren tijdens de wintertijdwissel hun tijdzoneverschil.

## Aquarea 1.8.0 en SDK 1.4.0

Sinds de vorige SolarPilot-update zijn Aquarea 1.8.0 en de daadwerkelijk gebruikte SDK 1.4.0 verschenen. De SDK verandert de parser, de betekenis van `specialStatus` en de werkelijke status-/actieafleiding. Deze bronvorm wordt afzonderlijk gecontroleerd naast de oudere bronbetekenis. Oude geregistreerde contracten worden niet met de nieuwe betekenis hernoemd.

De nieuwe SDK kan ook cachedata leveren na een geslaagde poll. Alleen de getypeerde actuele LIVE-status mag nieuw actueel bewijs geven; een nieuwe ontvangstdatum van cachedata volstaat niet. De bestaande bronkoppeling, rapporttijden, pomp-/route-/zonevoorwaarden, native koelcontrole en SG-vrijgave blijven nodig. SolarPilot gebruikt geen nieuwe Panasonic-schrijfopdracht of nieuwe providerinstelling.

De nieuwe Aquarea-diagnostiek en zonetemperatuur maken geen nieuwe automatische bronkoppeling. De bestaande cloudenergieroute blijft dezelfde gepubliceerde interval-/maandwaarden met eigen oorspronkelijke periode en tijd controleren. De provider wordt niet door SolarPilot geïnstalleerd.

## Installeren en controleren

1. Bewaar een actuele volledige privé Home Assistant-back-up.
2. Installeer beta.98 via HACS na geslaagde controles en publicatie. Behoud dezelfde entry, instellingen, opgeslagen modellen, geschiedenis en userfiles.
3. Herstart Home Assistant volledig en herlaad browser/app volledig. Controleer backend- en geladen kaartversie afzonderlijk.
4. Open de geschiedenis, schuif over de balken en controleer de aangegeven meetpunttijd. Bekijk ook een meetgat en een oudere dag. Het lezen van de geschiedenis schakelt geen apparaat en wijzigt geen instelling.

De bestaande SG-herhaalwachtcorrectie van beta.97 blijft behouden. Voor deze update hoeft geen profiel, percentage of SG-bevoegdheid opnieuw te worden bevestigd.

## Rollback

Herstel zo nodig de gepubliceerde beta.97-code met behoud van entry, opslag en userfiles; herstart Home Assistant volledig. Geef een eigen SG-aanvraag vooraf veilig vrij waar betrouwbaar mogelijk en onderbreek geen beschermde apparaatcyclus. Oudere code mist de interactieve markering en kent de nieuwe SDK-bronvorm niet. Ga bij Aquarea 1.8.0 daarom niet uit van dezelfde bronherkenning na rollback.

[Actuele werking](ACTUELE_WERKING.md) · [Testverslag](TESTRESULTATEN_BETA98.md) · [Upstreamcontrole](https://github.com/Stevenva007/solarpilot-home-assistant/blob/main/docs/AQUAREA_UPSTREAM_REVIEW_BETA98.md) · [Overdracht](../OVERDRACHT.md)
