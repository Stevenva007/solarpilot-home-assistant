# SolarPilot beta.28 — rustig tapwater, cumulatieve update

Deze versie bevat beta.27 en alle eerdere verbeteringen. Hij voegt een onafhankelijk
normaal boilerdoel, een bewaakte comfortgrens en rustige zonnebuffers toe.
**Geen tijdelijke verhoging naar 52 °C om een te koude tank te laten herstarten.**
Geen Force DHW, Powerful, hoofdvoedings-, compressor- of DHW-modeopdrachten.

## 1. Wat deze regeling wel en niet kan

Het gewenste profiel is **50 °C normaal, 46 °C bewaakt**. Panasonic bepaalt zelf
wanneer en hoe hij tankverwarming en ruimteverwarming/koeling verdeelt.

Bij 50 °C doel en de fysieke differentie −5 °C ligt de nominale herstart rond
**45 °C**. Daarom kan 46 °C niet als gegarandeerd minimum worden aangeboden.
Bij onderschrijding of voorspeld tekort verschijnt een waarschuwing; SolarPilot
laat alleen het normale doel beschikbaar. Hij compenseert de differentie niet
met een extra opwarmdoel. Een grote waterafname of storing kan ook andere doelen
onhaalbaar maken. Dit pakket geeft geen fysieke acceptatietest of garantie.

Ook een ochtenddoel is een bewaakte voorraadwens, geen gedwongen opwarmopdracht.
Netstroom voor gewone herverwarming blijft mogelijk, ook 's nachts. Dit is geen
netstroomvergrendeling, geen elektrische beveiliging en geen legionellabestrijdingsgarantie.

## 2. Bijwerken en oude waarden behouden

Maak een Home Assistant-back-up. Zet SolarPilot op **Pauze** en wacht tot eigen
lasten volgens hun minimumtijden zijn vrijgegeven; Pauze is geen noodstop.
Publiceer dit complete pakket over je bestaande Git-repository en bewaar `.git`.
Kopieer geen extra versie-map als submap. Upload nooit een privébundel,
Home Assistant-configuratie of `.storage`-inhoud.

Voer de tests en controles uit. Push eerst de commit naar `main`; publiceer pas
na geslaagde validatie van precies die commit een nieuwe tag `v1.0.0-beta.28`.
Bestaande release-tags niet verplaatsen. Werk daarna via HACS bij en herstart
Home Assistant. Er is geen losse dashboardresource of herimport nodig.

**Bestaande instellingen worden niet stilzwijgend naar 50/46 herschreven.**
Bij oude configuraties wordt het vroegere berekende basisdoel éénmalig bewaard
als expliciet normaal doel. Bijvoorbeeld oud 43/−5/1 blijft normaal 49 °C.
Vanaf die migratie verandert een andere comfortgrens/differentie het normale
doel niet meer. Kies hieronder bewust het nieuwe profiel. Nieuwe lege
configuraties gebruiken 50/46 en schakelen geen fysieke functie automatisch in.

## 3. Kies het nieuwe profiel

Open in SolarPilot **Configureren met uitleg ? → Comfort & warmtepomp → Sanitair
warm water**. Dit is dezelfde gecontroleerde optieswizard. Laat de bestaande
bron- en beveiligingskoppelingen staan. Koppel echte klimaatbronnen met actuele
`hvac_action` voor het rekening houden met actieve ruimteverwarming.

### Temperatuurregels

| Optie | Gewenst profiel |
|---|---:|
| Normale boilerdoeltemperatuur | **50 °C** |
| Bewaakte comfortondergrens | **46 °C** |
| Fysieke tankdifferentie | **−5 °C**, alleen informatie, niet door SolarPilot gewijzigd |
| Doel bij voldoende PV-productie | **50 °C** |
| Extra hoog-overschotdoel | **60 °C**, alleen na geschikte fysieke vrijgave |
| Maximum bij actieve/onzekere koeling | **50 °C** |
| PV-productiedrempel | **1000 W** |
| Echte restinjectie voor extra 60 °C | **strikt meer dan 3500 W** |
| Nachtvenster | **23:00–06:00** |

De gewone zonnedrempel geeft met dit profiel geen hogere temperatuur dan normaal:
50 °C blijft 50 °C. Alleen een echte toegestane voorraadbuffer geeft een verhoging.
De oude extra basisbuffer is niet meer instelbaar. Hij wordt niet gebruikt om
het normale doel te verhogen. Leren verandert deze vaste keuzes nooit.

### Nacht, ochtend en avondvoorraad

| Optie | Gewenst profiel |
|---|---:|
| Nachtbeleid | **Wachten op stabiele zon voor extra buffer; normaal doel blijft staan** |
| Ochtendvoorraad bewaken | **AAN** |
| Voorraad beoordelen om | **09:00** |
| Gewenste gemeten ochtendtemperatuur | **46 °C** |
| Reserve in voorspelling/avondvoorraad | **1 °C** |
| Maximale voorlooptijd ochtendcontrole | **180 min** |
| Extra opwarmtijdmarge voor beoordeling | **30 min** |
| Controle na deadline | **30 min** |
| Avondvoorraad op laatste bruikbare zon | **AAN** |
| Hoogste avondsetpoint | **55 °C** |
| Vooruitkijkvenster laatste nuttige zon | **3 uur** |
| Venster zonder bruikbare forecast | **vanaf 14:00**, nog altijd werkelijke zon vereist |
| Reserve voor waterafname | **2 °C**, expliciete aanname |
| Vermogensmarge voor avondvoorraad | **150 W** |
| Voorlopige afkoelschatting | **0,25 °C/uur** |
| Voorlopige opwarmschatting | **6 °C/uur** |

Er wordt geen ochtendsetpoint van 52/55 °C meer berekend. Een voorraadtekort
herstelt hoogstens het gewone 50 °C-doel. Panasonic bepaalt of dat tot verwarmen
leidt. De nominale herstartgrens en eventuele onzekerheid staan in Comfort.
De ochtendgrens is altijd minstens de algemene bewaakte comfortgrens.

Voorbeeld van een **zonnebuffer**, niet van een minimumherstelboost: doel 46 °C,
verwacht nachtverlies 3 °C, waterafnamereserve 2 °C en extra marge 1 °C leveren een
avonddoel van 52 °C op. Dat mag alleen binnen de toegestane zonnevoorwaarden.
Het wordt niet verder verhoogd om de differentie te passeren. Na bereiken van de
berekende reserve wordt die dag geen tweede avondbuffer gestart. Gewone
fabrikantverwarming en een afzonderlijk toegestane extra 60 °C-fase blijven apart.

Het leermodel begint niet met gegarandeerde kennis van het vat. De gekozen
terugvalramingen en de herkomst van geleerde waarden staan erbij. Onverwachte
waterafname kan niet betrouwbaar uit alleen een temperatuursensor worden voorspeld.

### Terugmelding en stabiliteit

| Optie | Gewenst profiel |
|---|---:|
| Voldoende zon/overschot gedurende | **300 s** |
| Wachten bij wegvallende zon/overschot | **300 s** |
| Minimum tijd tussen extra doelverhogingen | **1800 s** |
| Extra zonne-opwarming uitstellen zolang ruimteklimaat actief is | **AAN** |
| PV-terugvalmarge | **100 W** |
| Injectie-terugvalmarge | **300 W** |
| Uitloop na koeling/onzekere koelstatus | **1800 s** |
| Maximum leeftijd temperatuur-/klimaatrapport | **300 s** |
| Maximum wachten op doelterugmelding | **180 s** |
| Netafnamegrens verlaten extra hoge fase | **100 W** |
| Extra verhoging uitstellen bij voorspelde koelvraag | **AAN** |
| Vooruitkijken naar koelvraag | **2 uur** |

Nieuwe extra doelen wachten bij actuele ruimteverwarming/koeling of onbekende
actie. Een gekozen HEAT-modus met idle geldt niet als actieve verwarming.
Een reeds gevraagd hoger doel wordt niet uitsluitend wegens een nieuwe verwarmactie
afgebroken. Nacht, echte netafname, koelgrenzen en hygiëne blijven wel leidend.

De 1800 s pauze geldt voor extra **verhogingen**, gerekend vanaf de laatste
verstuurde doelopdracht. Normale doelherstelling en beschermende verlagingen
worden niet daardoor geblokkeerd. Deze tijden zijn geen compressor-aan/uit-timers.

## 4. Hygiëne en exclusieve bediening

De onafhankelijke Panasonic-sterilisatie blijft aan. Het ingestelde
sterilisatievenster, handmatige krachtige modus en Force DHW worden niet
overschreven. SolarPilot start of stopt die functies niet. Een softwarevenster
of een gemeten warme tank bewijst niet dat alle leidingen gedesinfecteerd zijn.

De gecombineerde veiligheidsbevestiging blijft verplicht: fabrikantgeschiktheid,
onafhankelijke hygiëne en verbrandingsbeveiliging werkelijk controleren voordat
fysieke regeling wordt vrijgegeven. Ook een cap van 50 °C vervangt die controle niet.

De keuze 46/50 is een comfort-/energieprofiel, geen bewezen hygiëneprogramma.
Voor temperatuurgebaseerde Legionella-beheersing noemt HSE onder andere minstens
60 °C opslag; WHO benadrukt beheer van de gehele installatie. Bespreek met de
installateur hoe het gekozen profiel veilig in deze installatie wordt beheerd.
Bronnen: https://www.hse.gov.uk/legionnaires/hot-and-cold.htm en
https://www.who.int/news-room/fact-sheets/detail/legionellosis (geraadpleegd 28-09-2026).

Borg dat oude helperautomatiseringen het tankdoel niet meer wijzigen. Een
uitgeschakelde zonnecontroller voorkomt niet per definitie een handmatige helperactie.
Behoud fabrikantbeveiligingen en andere echte veiligheidsfuncties.

## 5. Na opslaan

Pas na de volledige wizard wordt de configuratie toegepast. Controleer **Comfort**:
Normaal 50 °C, comfortgrens 46 °C, nominale herstart rond 45 °C, echte tanktemperatuur,
voorraadvoorspelling en de werkelijk teruggemelde Panasonic-doeltemperatuur.
Een waarschuwing over 46 versus 45 is inhoudelijke informatie, geen installatiefout.

Hervat alleen na de passende fysieke vrijgave de Zonnestroommodus. Observeer een
avond en ochtend; vergelijk gemeten verloop, bronactualiteit en netafname. Forceer
geen start om een prognose waar te maken. Er worden geen echte apparaten door
softwaretests bediend en niets op GitHub of Home Assistant namens jou gepubliceerd.
