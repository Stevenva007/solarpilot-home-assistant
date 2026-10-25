# SolarPilot 1.0.0-beta.108 installeren

Werk bij via HACS naar **1.0.0-beta.108**, herstart Home Assistant volledig en herlaad de app of browser. Backend en geladen kaart moeten allebei beta.108 tonen. Toestellen, koppelingen, voorrang, bestaande timerinstellingen, lokaal bevestigde SG-capaciteiten, modellen en historie blijven behouden.

## SG mag zonnestroom van de Wallbox overnemen

Staat **SG vóór Auto laden**, dan mag de warmtepomp actueel betrouwbaar gemeten vermogen van een bevestigde autonome zonnelaadsessie gebruiken. De Wallbox krijgt tijd om zelfstandig terug te regelen. SolarPilot verstuurt geen laadcommando.

Alleen de softwarematige grens voor de totale netafname mag hiervoor tijdelijk worden overschreden. De extra ruimte is hoogstens het minimum van het coherente gemeten zonnelaadvermogen, de geraamde SG-opname en **max_takeover_w**. De eerste toegelaten bijdrage blijft het plafond voor dezelfde episode; een later hoger laadrapport vergroot haar niet. De beta.107-controle op de actuele P1/PV-balans blijft behouden.

Fictief voorbeeld: bij een softwaregrens van 4.000 W en een geldige begrensde bijdrage van 2.000 W kan tijdens de reactieperiode maximaal 6.000 W totale netafname passen. Dit is geen gemeten vrij vermogen of fysieke aansluitcapaciteit. Fase-, kwartier-, batterij-, bron-, contact- en andere SG-voorwaarden kunnen alsnog eerder vrijgeven.

## Hoelang mag de Wallbox reageren?

De bestaande **handover_s** bepaalt de periode: standaard **240 seconden**, voor de SG-route maximaal 600 seconden. Bij een lopende bevestigde SG-aanvraag, of een exact actueel waargenomen extern AAN-contact binnen zijn oorspronkelijke vijftien minuten, begint de episode bij het eerste bruikbare P1-rapport boven de softwaregrens. Een piek later in een al lopende SG-sessie kan dus ook worden overbrugd.

De oorspronkelijke absolute eindtijd blijft bewaard. Nieuwe polls, kaartverversingen, leasevernieuwing en herstart geven geen nieuwe vier minuten. Een nieuwe episode wordt pas mogelijk nadat de ruwe P1-netafname op of onder de gewone SG-importdrempel ligt, standaard 600 W, gedurende **handover_confirm_s**, standaard vijftien seconden, met minstens twee verschillende nieuwe rapporten. Rond de softwaregrens schommelen herstart de klok niet.

Zonder bewaard geldig episodebewijs moet na een herstart eerst nieuw herstelbewijs komen. Een wijziging van bronnen, beleid of effectieve voorrang en ontbrekende, oude, handmatige of tegenstrijdige laadgegevens geven geen uitzondering. De lokale korte SG-terugval en het oorspronkelijke sessiemaximum blijven afzonderlijk gelden. Het vierminutenvenster is beleid van de actieve Home Assistant-regeling. Voor een eigen SolarPilot-aanvraag heeft de bestaande lokale lease haar eigen afloop, standaard 300 seconden. Bij HA-uitval is fysieke UIT precies na 240 seconden daardoor niet gegarandeerd.

## De gewone wolkenbuffer blijft parallel lopen

De bestaande wolkenbuffer blijft standaard **600 W gedurende vijf minuten**. Zij gebruikt de werkelijke ruwe P1-netafname, inclusief de nog ladende auto. Het overgenomen EV-vermogen wordt daarvoor niet afgetrokken. De reactieperiode en wolkentimer lopen tegelijk; er komt geen extra vijfminutenperiode bij. De minimumduur verlengt de oorspronkelijke Wallbox-reactie-eindtijd niet.

Zonder geldige overdracht, na de oorspronkelijke eindtijd of bij een te grote overschrijding geldt de normale softwarematige netgrens weer. Een fase-, kwartier-, batterij- of bronprobleem krijgt geen uitstel. Een nieuwe SG-start moet daarnaast voldoende werkelijk kwalificerend zonnevermogen en alle overige startvoorwaarden hebben.

## Controle na de update

Controleer de effectieve volgorde onder **Voorrang**. De Wallbox staat standaard achteraan; een bewust opgeslagen andere volgorde blijft staan. In **Warmtepomp → Details** zie je een geldige overdracht en de resterende reactietijd. Een aflopende schermklok verleent geen toestemming; backend en oorspronkelijke bronrapporten blijven beslissend.

Laat de normale regeling nieuwe metingen verzamelen. De analyse-export behoudt oorspronkelijke net-/PV-/Wallboxrapporten en kan een volgende reactie helpen beoordelen. Snelle waarnemingen bewaren ook de overdracht; begin, eindtijd en toestandsovergangen met broncontext blijven in de begrensde gebeurtenissenhistorie tot maximaal zeven dagen bewaard. Herstel wist dit eerdere diagnosebewijs binnen de retentie niet. Dit geeft geen nieuwe toestemming of automatische herstart. Binnen de oorspronkelijke externe vijftien minuten kan de beperkte Wallbox-reactietijd een exact passend actueel AAN-contact behouden. Dit geeft geen eigendom, ON-opdracht, leasevernieuwing of nieuw SG-minimum. De oorspronkelijke vijftienminutendeadline blijft staan en bij de daaropvolgende overnamebeoordeling geldt de bestaande ruwe SG-importdrempel, standaard 600 W. Fysieke handmatige UIT-bescherming en tijdelijke SG-bediening houden hun eigen voorwaarden. Deze update activeert of herbevestigt geen SG-uitgang en wijzigt geen Panasonic-capaciteit.

## Terugzetten

Maak vooraf een volledige privéback-up, inclusief SolarPilot-opslag, userfiles en historie. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk veilig vrij en controleer de lokale terugval. Installeer beta.107 met behoud van entry en gegevens, herstart Home Assistant volledig en herlaad de kaart. Beta.107 mist de begrensde Wallbox-reactie-uitzondering: SG kan daar opnieuw direct openen bij een totale netpiek terwijl de auto nog laadt. Gebruik geen twee runtimes tegelijk en verwijder de integratie niet als migratiemethode.

[Actuele werking](ACTUELE_WERKING.md) · [Softwarebewijs en beperkingen](TESTRESULTATEN_BETA108.md)
