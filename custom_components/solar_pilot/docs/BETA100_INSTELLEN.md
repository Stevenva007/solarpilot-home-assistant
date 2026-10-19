# SolarPilot beta.100 — lichtere uitlezing van de SG-bediening

Versie: **1.0.0-beta.100** · 19 oktober 2026 · Bouwbasis: gepubliceerde beta.99.

## Wat verandert

De tijdelijke **SG-boost bediening** heeft voor haar beschikbaarheid, gekozen stand en resterende duur alleen de bestaande configuratie en handmatige keuze nodig. Beta.100 gebruikt daarvoor een lichte uitlezing. De uitlezingen voor beschikbaarheid, gekozen stand en attributen vragen het volledige SG-/Panasonic-overzicht daardoor niet meer op.

Automatisch en Aan/Uit voor 30/60 minuten behouden hun bestaande betekenis. De resterende duur volgt de huidige klok en de oorspronkelijke absolute eindtijd. Openen, verversen of herstarten maakt geen nieuwe volledige handmatige duur. De bestaande afloop- en uitvoeringsroute blijven verantwoordelijk voor hun eigen actuele controles; de getoonde keuze is geen bevestiging dat het fysieke SG-contact AAN of UIT staat.

Dit is een gerichte correctie van de SG-bediening. Het aantal vermeden berekeningen is geen gemeten tijdwinst op een live installatie. Andere statussensorvertragingen, netwerkstoringen of fouten van externe integraties zijn hiermee niet als opgelost bewezen.

## Behouden functies en gegevens

De klikbare geschiedenis van gewone en gearchiveerde toestellen, Wallbox-laadperioden en afzonderlijke SG-lagen uit beta.99 blijft beschikbaar. De huidige boilertemperatuur en het ingestelde doel openen nog steeds de toegestane bijbehorende Home Assistant-bronhistorie. Lange warmtepompsessies houden hun compacte taaksamenvatting, uitklapbare oorspronkelijke perioden, seconden en herkenbare meetgaten. De bronvolgordecorrectie voor nieuwe Aquarea-berichten blijft behouden.

Huidige en historische bronrechten, bestaande instellingen, modellen, meetgegevens, historie, eigen opslag en userfiles blijven behouden. De update voegt geen opslagmigratie of nieuwe bronkoppeling toe. Aquarea-/SDK-bronactualiteit, SG-profiel, net-/fase-/kwartiergrenzen, koelvoorwaarden, lokale aflooptimer, minimum-/maximumtijden en oorspronkelijke handmatige deadline houden dezelfde grenzen.

Panasonic blijft zelfstandig regelen. SolarPilot behoudt uitsluitend de bestaande toegestane SG-uitgang voor extra warmtepompvraag. De andere apparaatfuncties, beschermde afwascyclus, Wallbox-bevoegdheden, batterijbescherming en gebruikersvolgorde blijven behouden. Er is geen nieuwe dependency of aparte dienst nodig.

## Bijwerken

1. Bewaar een volledige privé Home Assistant-back-up, inclusief instellingen en eigen opslag.
2. Werk via HACS bij naar **beta.100** nadat de releasecontroles zijn geslaagd en de release is gepubliceerd. Behoud dezelfde entry, instellingen, modellen, opslag, historie en userfiles.
3. Herstart Home Assistant volledig en herlaad de app/browser. Controleer backend- en kaartversie afzonderlijk op **1.0.0-beta.100**.
4. Bekijk de SG-bediening. Indien er al een tijdelijke keuze liep, vergelijk haar oorspronkelijke eindtijd met de getoonde resterende duur. Verversen van de weergave mag die eindtijd niet verlengen. Alleen het bekijken van deze informatie geeft geen nieuwe apparaatopdracht.
5. Controleer de behouden toestelgeschiedenis en de directe boilerbronhistorie. Home Assistant bepaalt welke bronhistorie werkelijk is opgeslagen en toegankelijk is.

Geen nieuwe bron, percentage, SG-profiel of lokale bevestiging is nodig. Een nieuwe fysieke proef of het handmatig wijzigen van een SG-keuze is geen vereiste voor deze leescontrole. Deze documentatie en softwarevalidatie bewijzen geen reeds uitgevoerde update op een Home Assistant-installatie.

## Rollback

Herstel indien nodig de gepubliceerde **beta.99-code** met behoud van entry, opslag, modellen, historie en userfiles. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk vooraf veilig vrij; onderbreek geen beschermde cyclus. Herstart Home Assistant volledig en herlaad de app/browser.

Beta.99 behoudt de klikbare historie, directe boilerbronhistorie, compacte warmtepompperioden en Aquarea-bronvolgordecorrectie. De uitlezingen van de SG-bediening vragen dan opnieuw het volledige SG-/Panasonic-overzicht op. Er is geen opslagmigratie, historieherstel of reset van de oorspronkelijke deadline nodig. Verwijder of maak de entry niet opnieuw aan en draai geen twee runtimes tegelijk.

[Actuele werking](ACTUELE_WERKING.md) · [Testverslag](TESTRESULTATEN_BETA100.md) · [Overdracht](../OVERDRACHT.md)
