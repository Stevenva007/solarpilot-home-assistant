"""Demand-led room control and explainable Panasonic AUTO/OFF planning.

SolarPilot deliberately never chooses HEAT versus COOL. Panasonic AUTO keeps that
ownership. SolarPilot can only decide whether AUTO should remain available or a
OFF block is useful. Automatic room control uses measured demand first and
direction-specific predictive evidence as it becomes available. The opt-out
legacy coast policy remains available for existing installations.

The climate model includes three bounded learning layers:
- solar-gain learning using actual PV as a local irradiation proxy;
- local correction of weather-forecast temperature bias at 6/12/24/48 h horizons;
- coast-result scoring that can cautiously tune the *minimum useful coast window*.

The Panasonic thermostat target is always the comfort reference and is never
rewritten by this module. No open-window logic is part of this climate model.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from itertools import islice
from statistics import median
import math
import time


SMART_CLIMATE_DEFAULTS = {
    # Sources / master switches
    "enabled": False,
    "control_enabled": False,
    "automatic_zone_control": True,
    "weather_entity": "",
    "outside_temp_entity": "",
    "operation_mode_entity": "",
    "zone_entities": [],

    # Slow planning / comfort
    "decision_interval_h": 12.0,
    "forecast_refresh_s": 3600.0,
    "forecast_horizon_h": 48.0,
    "soft_band_c": 0.5,
    "hard_band_c": 1.0,
    "shoulder_band_c": 3.0,
    "season_extreme_delta_c": 5.0,
    "min_coast_window_h": 8.0,
    "min_state_hold_h": 8.0,
    "allow_winter_summer_coast": False,
    "thermal_start_margin_h": 2.0,
    "solar_precondition_extra_lead_h": 4.0,
    "manual_hold_h": 12.0,
    "automatic_min_run_h": 1.0,
    "automatic_min_off_h": 1.0,
    "automatic_demand_confirm_s": 600.0,

    # Thermal learning
    "sample_interval_s": 900.0,
    "learning_min_samples": 24,
    "learning_min_days": 5,
    "model_confidence_min": 0.55,

    # PV-aware timing (existing preconditioning)
    "solar_preconditioning_enabled": False,
    "precondition_min_pv_w": 3000.0,

    # Solar gains in the building model
    "solar_gain_enabled": True,
    "solar_gain_learning_enabled": True,
    "solar_gain_min_pv_w": 800.0,
    "solar_gain_max_c_h": 0.35,

    # Local weather forecast correction
    "weather_bias_enabled": True,
    "weather_bias_min_samples": 12,
    "weather_bias_min_days": 4,
    "weather_bias_min_confidence": 0.45,
    "weather_bias_max_c": 3.0,

    # Coast evaluation / bounded adaptation
    "coast_feedback_enabled": True,
    "coast_feedback_min_episodes": 4,
    "coast_feedback_step_h": 0.5,
    "coast_feedback_min_adjust_h": -2.0,
    "coast_feedback_max_adjust_h": 3.0,
    "coast_feedback_eval_h": 3.0,
    "coast_feedback_center_margin_c": 0.2,

    # Safety / pacing
    "max_commands_per_day": 2,
    "stale_s": 1800.0,
    "guard_recheck_s": 900.0,
}


# The dashboard renders this catalog directly. Keep one spec for every setting so
# no hidden tuning knob exists without an explanation and consequence.
CLIMATE_SETTING_SPECS = {
    "enabled": dict(group="Basis", label="Thermisch model en advies", type="boolean",
        description="Leert het gemeten temperatuurverloop en maakt per ruimte een AUTO/UIT-advies. Bouwschiltemperatuur wordt niet afzonderlijk gemeten of bewezen.",
        recommendation="Aan laten zodra de juiste zones en temperatuurbronnen gekoppeld zijn.",
        on_effect="SolarPilot leert en adviseert; dit stuurt nog niets zonder aparte bedieningstoestemming.",
        off_effect="Geen thermisch leren of klimaatadvies."),
    "control_enabled": dict(group="Basis", label="AUTO/coast werkelijk toepassen", type="boolean",
        description="Geeft SolarPilot toestemming om alleen AUTO of OFF/coast te sturen. Nooit HEAT of COOL.",
        recommendation="Aan voor de gewenste automatische bediening. Gemeten comfortregeling werkt tijdens leren; lange vooruitplanning wacht op richtinggebonden praktijkbewijs.",
        on_effect="SolarPilot kan ruimtes zelf UIT zetten en Panasonic AUTO bij relevante behoefte tijdig beschikbaar maken.",
        off_effect="Alles blijft adviserend; Panasonic wordt niet door SolarPilot geschakeld."),
    "automatic_zone_control": dict(group="Basis", label="Ruimtes automatisch AUTO of UIT", type="boolean",
        description="SolarPilot schakelt elke gekoppelde ruimte zelf tussen Panasonic AUTO en UIT op basis van comfort en bruikbare voorspellingen. Panasonic kiest verwarmen of koelen; het thermostaatdoel verandert niet.",
        recommendation="Aan voor automatische ruimtebediening. Gebruik de dashboardschakelaar om een ruimte vast AUTO of UIT te houden; een externe ingreep geeft tijdelijk rust.",
        on_effect="Ook een reeds uitgeschakelde ruimte kan bij noodzakelijke warmtevraag of koelvraag automatisch AUTO krijgen; zonder behoefte wordt UIT voorgesteld.",
        off_effect="De eerdere pauzeregeling blijft gelden: alleen een eigen SolarPilot-pauze wordt automatisch hervat; handmatige UIT blijft uit."),
    "automatic_demand_confirm_s": dict(group="Bescherming", label="Gewone warmtevraag of koelvraag bevestigen", type="number", min=0, max=1800, step=60, unit="s",
        description="Een UIT-ruimte moet gedurende deze tijd een relevante behoefte buiten de gewone comfortband blijven melden voordat AUTO wordt gevraagd. Een echte overschrijding van de harde grens en een onderbouwde dringende voorspelling wachten niet op deze bevestiging.",
        recommendation="600 s voorkomt dat één korte of afgeronde temperatuurmeting een lange AUTO-periode begint.",
        lower_effect="Sneller AUTO, maar meer kans op onnodig inschakelen door een korte meetdip.",
        higher_effect="Meer zekerheid dat de gewone vraag aanhoudt; de normale comfortcorrectie begint later."),
    "weather_entity": dict(group="Koppelingen", label="Weerbron", type="weather_entity",
        description="Levert de uurverwachting waarmee het gebouw over de ingestelde horizon vooruit wordt doorgerekend.",
        recommendation="Gebruik een betrouwbare lokale weather-entiteit met hourly forecasts.",
        change_effect="Een andere weersdienst kan een andere systematische fout hebben: het weerbias-model leert opnieuw. Als je géén aparte buitensensor gebruikt, leert ook het thermische model opnieuw."),
    "outside_temp_entity": dict(group="Koppelingen", label="Actuele buitentemperatuur", type="temperature_entity",
        description="Werkelijke buitentemperatuur voor leren en controle. Leeg = temperatuur van de weerentiteit.",
        recommendation="Een fysieke buitensensor bij de woning is meestal beter dan alleen een internetwaarde.",
        change_effect="Omdat een andere sensor anders geplaatst/gekalibreerd kan zijn, worden het thermische model en de lokale weerscorrectie veilig opnieuw opgebouwd."),
    "operation_mode_entity": dict(group="Koppelingen", label="Werkelijk Panasonic-programma", type="program_entity",
        description="Alleen-lezen bron voor het echte verwarmings- of koelprogramma. Leeg gebruikt de gecontroleerde native Aquarea-koppeling als die beschikbaar is. De AUTO/UIT-stand van een ruimte en PUMP/WATER zijn geen bewijs van het programma.",
        recommendation="Laat leeg bij de ondersteunde Aquarea-koppeling. Anders koppel een actuele bron met heat/heating/auto_heat, cool/cooling/auto_cool of heat_cool; een onbekend programma blokkeert een nieuwe automatische AUTO-start.",
        change_effect="Het programma wordt opnieuw gecontroleerd; een warmtevraag mag AUTO niet inschakelen wanneer de warmtepomp alleen op koelen staat, en andersom."),
    "zone_entities": dict(group="Koppelingen", label="Panasonic klimaatzones", type="climate_entities",
        description="Zones waarvan doeltemperatuur, binnentemperatuur, AUTO/OFF en hvac_action worden gebruikt.",
        recommendation="Selecteer alleen zones die dezelfde Panasonic-installatie vormen en AUTO én OFF ondersteunen.",
        change_effect="Toevoegen/verwijderen verandert de comfortgrenzen en welke zone de conservatieve beslissing bepaalt."),

    "decision_interval_h": dict(group="Comfort & planning", label="Normale planningsbeslissing", type="number", min=6, max=24, step=1, unit="uur",
        description="Interval voor de oudere pauzeplanner. Automatische ruimtebediening controleert gemeten behoefte bij gewijzigde invoer en het comfortcontrole-interval.",
        recommendation="12 uur past goed bij trage vloer- en bouwmassa.",
        lower_effect="Reageert vaker, maar kan meer schakelmomenten en minder rust geven.",
        higher_effect="Rustiger en stabieler, maar kan later reageren op veranderende vooruitzichten."),
    "forecast_refresh_s": dict(group="Comfort & planning", label="Weersvoorspelling vernieuwen", type="number", min=900, max=21600, step=300, unit="s",
        description="Hoe vaak de hourly weersverwachting opnieuw wordt opgehaald.",
        recommendation="3600 s is meestal voldoende; de vloer reageert veel trager dan het weerbericht verandert.",
        lower_effect="Nieuwere forecast, maar meer API-verkeer zonder garantie op betere regeling.",
        higher_effect="Minder API-verkeer, maar wijzigingen in de verwachting komen later binnen."),
    "forecast_horizon_h": dict(group="Comfort & planning", label="Voorspellingshorizon", type="number", min=12, max=72, step=1, unit="uur",
        description="Hoe ver vooruit de binnentemperatuur wordt gesimuleerd.",
        recommendation="48 uur geeft voldoende context zonder te zwaar te leunen op onzekere lange forecast.",
        lower_effect="Minder onzekerheid, maar minder anticipatie op trage vloerrespons.",
        higher_effect="Meer vooruitblik, maar weersfouten worden belangrijker."),
    "soft_band_c": dict(group="Comfort & planning", label="Gewenste comfortband", type="number", min=0.2, max=3.0, step=0.1, unit="±°C",
        description="Normale band rond het Panasonic-doel waarbinnen coasten comfortabel wordt geacht.",
        recommendation="±0,5 °C is een evenwichtige start voor een woning met vloerverwarming/-koeling.",
        lower_effect="Constantere temperatuur, maar minder mogelijkheid om energie te besparen door coasten.",
        higher_effect="Meer coastkansen en mogelijk minder verbruik, maar grotere voelbare temperatuurschommeling."),
    "hard_band_c": dict(group="Comfort & planning", label="Harde comfortgrens", type="number", min=0.3, max=5.0, step=0.1, unit="±°C",
        description="Bij overschrijding met relevante warmte- of koelvraag vraagt automatische ruimtebediening dringend AUTO. Een van nature herstellende ruimte krijgt geen tegenstrijdige vraag; handmatige ingrepen en vaste HEAT/COOL blijven beschermd. De oudere pauzeplanner hervat alleen een eigen UIT-pauze.",
        recommendation="±1,0 °C houdt een duidelijke veiligheidsmarge rond de zachte comfortband.",
        lower_effect="Eigen coast wordt sneller beëindigd; meer comfortbescherming maar minder besparingsruimte.",
        higher_effect="Meer tolerantie voor afwijking; potentieel minder verbruik maar groter comfort-risico."),
    "shoulder_band_c": dict(group="Comfort & planning", label="Tussenseizoen-band", type="number", min=0.5, max=6.0, step=0.5, unit="°C",
        description="Bepaalt wanneer de buitentemperatuur nog als tussenseizoen rond het binnendoel wordt gezien.",
        recommendation="3 °C maakt de besparingslogica vooral actief wanneer verwarmen/koelen niet vanzelfsprekend is.",
        lower_effect="Sneller zomer/winter-context; minder vaak agressief coasten.",
        higher_effect="Meer dagen worden tussenseizoen; de coastlogica krijgt vaker invloed."),
    "season_extreme_delta_c": dict(group="Comfort & planning", label="Duidelijke zomer/winter vanaf", type="number", min=1.5, max=12.0, step=0.5, unit="°C",
        description="Schaal voor hoe sterk een duidelijke zomer- of wintersituatie is.",
        recommendation="5 °C geeft een geleidelijke overgang zonder kalendermaanden te gebruiken.",
        lower_effect="Seizoenscontext wordt sneller sterk en AUTO krijgt eerder rust van SolarPilot.",
        higher_effect="SolarPilot blijft langer in tussenseizoenslogica."),
    "min_coast_window_h": dict(group="Comfort & planning", label="Minimum nuttige coastperiode", type="number", min=2, max=24, step=0.5, unit="uur",
        description="Minimale voorspelde nuttige OFF-periode voordat SolarPilot een nieuwe coast start.",
        recommendation="8 uur voorkomt korte OFF/AUTO-cycli bij een trage vloer.",
        lower_effect="Meer en kortere coastperioden; mogelijk meer besparing maar ook meer schakelen/inhaalvraag.",
        higher_effect="Alleen lange, duidelijke coastkansen worden benut; rustiger maar conservatiever."),
    "min_state_hold_h": dict(group="Comfort & planning", label="Minimum AUTO/OFF-vasthoudtijd", type="number", min=2, max=24, step=0.5, unit="uur",
        description="Minimumtijd voordat een gewone tegengestelde AUTO/OFF-opdracht mag volgen.",
        recommendation="8 uur past bij thermische traagheid en voorkomt pendelen.",
        lower_effect="Sneller bijsturen, maar meer risico op onrustig schakelen.",
        higher_effect="Meer rust, maar trager corrigeren als de situatie echt verandert."),
    "allow_winter_summer_coast": dict(group="Comfort & planning", label="Ook in duidelijke zomer/winter coasten", type="boolean",
        description="Beïnvloedt alleen de oudere pauzeplanner wanneer automatische ruimtebediening UIT staat. De nieuwe ruimtebediening bepaalt AUTO/UIT uit relevante comfortbehoefte, ook in winter of zomer.",
        recommendation="Voor de oudere regeling uit laten. Voor automatische ruimtebediening is geen extra seizoentoestemming nodig.",
        on_effect="De oudere pauzeplanner mag ook buiten het tussenseizoen langere UIT-blokken voorstellen.",
        off_effect="De oudere pauzeplanner houdt AUTO beschikbaar in duidelijke winter/zomer; de nieuwe behoeftegestuurde regeling blijft actief."),
    "thermal_start_margin_h": dict(group="Comfort & planning", label="Herstartmarge boven vloerreactie", type="number", min=0, max=12, step=0.5, unit="uur",
        description="Veiligheidsmarge vóór het laatst haalbare AUTO-startmoment uit de geleerde richtingrespons. De oudere planner telt deze tijd bij de gedeelde reactievertraging op.",
        recommendation="2 uur geeft een bruikbare veiligheidsmarge voor vloerverwarming/-koeling.",
        lower_effect="Later AUTO vrijgeven; zuiniger mogelijk, maar groter risico dat de woning achterloopt.",
        higher_effect="Eerder AUTO vrijgeven; veiliger comfort, maar minder coasttijd."),
    "solar_precondition_extra_lead_h": dict(group="Comfort & planning", label="Extra voorsprong bij veel PV", type="number", min=0, max=12, step=0.5, unit="uur",
        description="Als PV-voorconditionering aanstaat kan een toch al noodzakelijke AUTO-herstart hiermee vervroegd worden.",
        recommendation="4 uur is ruim; alleen gebruiken als praktijkdata toont dat eerder draaien op PV zinvol is.",
        lower_effect="Minder vervroegen; minder kans op onnodig verbruik.",
        higher_effect="Meer kans om eigen PV te gebruiken, maar ook grotere kans dat je energie gebruikt die later niet nodig bleek."),
    "manual_hold_h": dict(group="Comfort & planning", label="Rust na handmatige modewijziging", type="number", min=1, max=72, step=1, unit="uur",
        description="Tijdelijke rust per zone na een onverwachte externe AUTO/UIT-wijziging. Daarna hervat automatische ruimtebediening; een vaste dashboardskeuze AUTO/UIT blijft gelden tot je die terug op Automatisch zet. Vaste Panasonic HEAT/COOL blijft beschermd.",
        recommendation="12 uur laat een externe ingreep rustig uitwerken. Gebruik de dashboardschakelaar voor een blijvende keuze.",
        lower_effect="Automatische ruimtebediening hervat sneller na een externe ingreep.",
        higher_effect="Automatische ruimtebediening wacht langer na een externe ingreep; de vaste dashboardskeuze blijft ongewijzigd."),
    "automatic_min_run_h": dict(group="Bescherming", label="Minimum automatische AUTO-periode", type="number", min=0.25, max=12, step=0.25, unit="uur",
        description="Een door SolarPilot gestart AUTO-venster duurt minstens zo lang voordat de gewone regeling de ruimte UIT zet. Dit is een modevenster, geen gemeten compressorlooptijd.",
        recommendation="1 uur voorkomt korte AUTO/UIT-cycli; verhoog na praktijkmetingen voor een trage vloer.",
        lower_effect="Sneller UIT bij verdwenen behoefte, maar meer schakelen.",
        higher_effect="Meer rust voor het systeem, maar mogelijk langer AUTO beschikbaar."),
    "automatic_min_off_h": dict(group="Bescherming", label="Minimum automatische UIT-periode", type="number", min=0.25, max=12, step=0.25, unit="uur",
        description="Na een automatische UIT-opdracht wacht de gewone regeling minstens zo lang vóór AUTO. Een harde comfortgrens kan eerder AUTO vereisen.",
        recommendation="1 uur geeft hysterese zonder een dag lang op een noodzakelijke herstart te wachten.",
        lower_effect="Sneller reageren op nieuwe behoefte, maar meer schakelen.",
        higher_effect="Langere pauzes, maar later hervatten bij gewone comfortvraag."),

    "sample_interval_s": dict(group="Leren & kwaliteit", label="Thermisch leersample", type="number", min=300, max=3600, step=300, unit="s",
        description="Minimumtijd tussen thermische leerpunten.",
        recommendation="900 s filtert ruis maar houdt voldoende detail over voor een trage woning.",
        lower_effect="Meer samples en meer ruis/onderlinge afhankelijkheid.",
        higher_effect="Schonere maar tragere leercurve en minder detail rond reacties."),
    "learning_min_samples": dict(group="Leren & kwaliteit", label="Minimum leersamples", type="number", min=6, max=240, step=1, unit="samples",
        description="Aantal bruikbare thermische samples dat meeweegt in modelzekerheid.",
        recommendation="24 voorkomt dat één dag meteen veel invloed krijgt.",
        lower_effect="Model wordt sneller vertrouwenswaardig maar kan te vroeg conclusies trekken.",
        higher_effect="Langzamer maar robuuster leren."),
    "learning_min_days": dict(group="Leren & kwaliteit", label="Minimum verschillende leerdagen", type="number", min=2, max=30, step=1, unit="dagen",
        description="Verschillende dagen wegen apart mee zodat één uitzonderlijke dag niet domineert.",
        recommendation="5 dagen is een goede minimale spreiding.",
        lower_effect="Sneller leren met meer risico op overfitting aan één weerssituatie.",
        higher_effect="Meer seizoens-/weersvariatie nodig voordat het model veel vertrouwen krijgt."),
    "model_confidence_min": dict(group="Leren & kwaliteit", label="Minimum modelzekerheid voor coast", type="number", min=0.25, max=0.95, step=0.05, unit="0–1",
        description="Minimum meetdekking voor benodigde leeronderdelen; dit is geen percentage voorspellingsnauwkeurigheid. Voor de nieuwe vooruitplanning moeten ook richtinggebonden dagen, consistente waarden en controle van volgende metingen beschikbaar zijn.",
        recommendation="0,55 behouden. Gemeten comfortbediening hoeft hier niet op te wachten; ontbrekende koelervaring wordt nooit vervangen door een verwarmingsvertraging.",
        lower_effect="Sneller automatische coast, maar meer kans op foutieve voorspellingen.",
        higher_effect="Conservatiever; minder coast tot de werkelijk benodigde modelonderdelen voldoende bewijs hebben."),

    "solar_preconditioning_enabled": dict(group="Zonnewinst & PV", label="PV mag noodzakelijke AUTO-herstart vervroegen", type="boolean",
        description="Vervroegt alleen een reeds voorspelde noodzakelijke AUTO-herstart; verandert geen thermostaatdoel.",
        recommendation="Uit laten tot de thermische data toont dat vervroegen werkelijk helpt.",
        on_effect="Meer eigen PV kan in de bouwmassa terechtkomen, maar het totale verbruik kan ook stijgen.",
        off_effect="AUTO-herstart volgt uitsluitend de comfortvoorspelling."),
    "precondition_min_pv_w": dict(group="Zonnewinst & PV", label="Minimum PV voor vervroegde AUTO", type="number", min=0, max=20000, step=100, unit="W",
        description="PV-productie waaronder PV-voorconditionering niet actief wordt.",
        recommendation="3000 W voorkomt vervroegen voor kleine zonne-restjes.",
        lower_effect="Vaker vervroegen, ook bij beperkte zon.",
        higher_effect="Alleen bij duidelijke zonneproductie vervroegen."),
    "solar_gain_enabled": dict(group="Zonnewinst & PV", label="Zonnewinst meenemen in gebouwmodel", type="boolean",
        description="Voegt voorspelde zonnewarmte toe aan de binnentemperatuurprognose zodra er voldoende leerdata is.",
        recommendation="Aan laten; dit maakt lente/herfst realistischer dan alleen buitentemperatuur gebruiken.",
        on_effect="Een zonnige dag kan minder verwarmingsbehoefte of eerder koelrisico voorspellen.",
        off_effect="Het thermische model negeert zonnewinst in de woning."),
    "solar_gain_learning_enabled": dict(group="Zonnewinst & PV", label="Zonnewinst lokaal bijleren", type="boolean",
        description="Leert per zone hoeveel extra opwarming samenhangt met werkelijk PV-vermogen als lokale instralingsproxy.",
        recommendation="Aan laten zolang de PV-meter betrouwbaar is.",
        on_effect="Het model past de zonnewinst aan jouw woning aan.",
        off_effect="Bestaande geleerde waarde blijft beschikbaar maar krijgt geen nieuwe samples."),
    "solar_gain_min_pv_w": dict(group="Zonnewinst & PV", label="Minimum PV voor zonnewinstsample", type="number", min=100, max=10000, step=100, unit="W",
        description="Onder deze productie wordt opwarming niet aan zoninstraling toegeschreven.",
        recommendation="800 W vermijdt dat kleine meetruis als zonnewinst wordt geleerd.",
        lower_effect="Meer samples maar meer kans op ruis/onjuiste toeschrijving.",
        higher_effect="Schonere sterke-zon-samples maar trager leren bij bewolkt weer."),
    "solar_gain_max_c_h": dict(group="Zonnewinst & PV", label="Maximum toegerekende zonnewinst", type="number", min=0.05, max=1.5, step=0.05, unit="°C/uur",
        description="Harde bovengrens op de voorspelde opwarming door zoninstraling per uur.",
        recommendation="0,35 °C/uur voorkomt dat een fout geleerd verband de comfortvoorspelling domineert.",
        lower_effect="Conservatiever: zon krijgt minder invloed op de voorspelde woningtemperatuur.",
        higher_effect="Meer invloed voor zonnewinst; pas verhogen na voldoende praktijkbewijs."),

    "weather_bias_enabled": dict(group="Weerscorrectie", label="Lokale weersverwachting corrigeren", type="boolean",
        description="Leert de systematische fout van de gekozen weersdienst voor 6/12/24/48 uur vooruit.",
        recommendation="Aan laten; de correctie blijft begrensd en wordt pas gebruikt bij voldoende vertrouwen.",
        on_effect="Structureel te warme/koude forecast kan lokaal worden gecorrigeerd.",
        off_effect="Ruwe weerforecast wordt ongewijzigd gebruikt."),
    "weather_bias_min_samples": dict(group="Weerscorrectie", label="Minimum weersfout-samples", type="number", min=4, max=100, step=1, unit="samples",
        description="Aantal gemeten forecastfouten dat nodig is voor volledige samplezekerheid.",
        recommendation="12 is voldoende om incidentele forecastmissers te dempen.",
        lower_effect="Correctie wordt sneller actief maar kan te veel op enkele situaties steunen.",
        higher_effect="Langzamere, stabielere correctie."),
    "weather_bias_min_days": dict(group="Weerscorrectie", label="Minimum verschillende weersdagen", type="number", min=2, max=30, step=1, unit="dagen",
        description="Aantal verschillende dagen dat meeweegt in de betrouwbaarheid van de lokale forecastcorrectie.",
        recommendation="4 dagen voorkomt dat één front of hittegolf het model bepaalt.",
        lower_effect="Sneller correcteren, maar minder robuust.",
        higher_effect="Meer variatie nodig; correctie komt later op gang."),
    "weather_bias_min_confidence": dict(group="Weerscorrectie", label="Minimum vertrouwen voor weerscorrectie", type="number", min=0.2, max=0.95, step=0.05, unit="0–1",
        description="Onder deze zekerheid wordt de gemeten bias alleen getoond en nog niet toegepast.",
        recommendation="0,45 is voorzichtig genoeg om extreme vroege correcties te vermijden.",
        lower_effect="Forecast wordt sneller lokaal aangepast.",
        higher_effect="Alleen zeer goed bevestigde bias wordt toegepast."),
    "weather_bias_max_c": dict(group="Weerscorrectie", label="Maximale weerscorrectie", type="number", min=0.5, max=6.0, step=0.25, unit="°C",
        description="Absolute begrenzing van de lokale correctie op de externe buitentemperatuurforecast.",
        recommendation="3 °C is ruim genoeg voor lokale bias zonder dat het model een slechte forecast volledig herschrijft.",
        lower_effect="Veiliger/conservatiever, maar structurele grotere fouten blijven deels staan.",
        higher_effect="Meer correctiekracht; verhoog alleen als historie overtuigend een grote vaste afwijking toont."),

    "coast_feedback_enabled": dict(group="Coast-evaluatie", label="Coastresultaten evalueren en begrensd bijsturen", type="boolean",
        description="Scoort elke SolarPilot-coast als correct, te lang of te voorzichtig en past alleen het minimale coastvenster voorzichtig aan.",
        recommendation="Aan laten in advies/leerfase; de aanpassing is begrensd en verandert geen comfortgrenzen.",
        on_effect="Toekomstige coastbeslissingen leren van echte resultaten.",
        off_effect="Resultaten worden niet gebruikt voor automatische fijnafstelling."),
    "coast_feedback_min_episodes": dict(group="Coast-evaluatie", label="Minimum geëvalueerde coastperioden", type="number", min=2, max=30, step=1, unit="episodes",
        description="Aantal afgeronde coastperioden voordat de automatische vensterfijnafstelling mag meetellen.",
        recommendation="4 voorkomt bijsturen op één toevallige coast.",
        lower_effect="Sneller aanpassen, maar grotere kans op overreactie.",
        higher_effect="Meer bewijs nodig; stabieler maar trager leren."),
    "coast_feedback_step_h": dict(group="Coast-evaluatie", label="Aanpassingsstap coastvenster", type="number", min=0.1, max=2.0, step=0.1, unit="uur",
        description="Hoeveel het effectieve minimum-coastvenster per duidelijke uitkomst mag opschuiven.",
        recommendation="0,5 uur is bewust traag voor een inert vloersysteem.",
        lower_effect="Zeer geleidelijk leren.",
        higher_effect="Sneller leren, maar grotere kans op heen-en-weer aanpassen."),
    "coast_feedback_min_adjust_h": dict(group="Coast-evaluatie", label="Maximale versoepeling coastvenster", type="number", min=-8, max=0, step=0.5, unit="uur",
        description="Ondergrens van de automatische aanpassing t.o.v. jouw ingestelde minimum-coastvenster.",
        recommendation="−2 uur laat optimaliseren zonder de 8-uursbasis volledig uit te hollen.",
        lower_effect="Meer automatische versoepeling mogelijk en dus meer coastkansen.",
        higher_effect="Minder versoepeling; dichter bij jouw handmatige basisinstelling."),
    "coast_feedback_max_adjust_h": dict(group="Coast-evaluatie", label="Maximale verstrenging coastvenster", type="number", min=0, max=8, step=0.5, unit="uur",
        description="Bovengrens van de automatische aanpassing t.o.v. het ingestelde minimum-coastvenster.",
        recommendation="+3 uur kan het model duidelijk voorzichtiger maken na comfortmissers zonder coast volledig uit te schakelen.",
        lower_effect="Minder mogelijkheid om na slechte coastresultaten conservatiever te worden.",
        higher_effect="Meer automatische verstrenging mogelijk; coast zal minder vaak starten."),
    "coast_feedback_eval_h": dict(group="Coast-evaluatie", label="Evaluatietijd na AUTO-herstart", type="number", min=1, max=12, step=0.5, unit="uur",
        description="Na het beëindigen van coast wacht SolarPilot deze periode om te zien of Panasonic werkelijk moet verwarmen/koelen.",
        recommendation="3 uur past bij een trage vloer: lang genoeg om echte vraag te zien zonder een halve dag te wachten.",
        lower_effect="Sneller als ‘te voorzichtig’ bestempelen; risico op te vroege conclusie.",
        higher_effect="Betere kans om late vloerreactie te zien, maar trager leren."),
    "coast_feedback_center_margin_c": dict(group="Coast-evaluatie", label="Marge voor ‘nog comfortabel gecentreerd’", type="number", min=0.05, max=0.8, step=0.05, unit="°C",
        description="Een coast die wordt beëindigd terwijl alle zones nog ruim binnen deze marge van het doel blijven kan na evaluatie ‘te voorzichtig’ blijken.",
        recommendation="0,2 °C is streng genoeg om echte comfortabele reserve te eisen.",
        lower_effect="Minder snel ‘te voorzichtig’ classificeren.",
        higher_effect="Meer coast-eindes kunnen als te voorzichtig worden gezien."),

    "max_commands_per_day": dict(group="Bescherming", label="Maximum gewone AUTO/OFF-opdrachten per dag", type="number", min=1, max=6, step=1, unit="opdrachten",
        description="Begrenst gewone SolarPilot-modeopdrachten per dag. Noodzakelijke comfort-AUTO mag deze grens passeren met behoud van bron-, handmatige-ingreep- en opdrachtbevestigingscontroles; de oude planner hervat alleen eigen UIT-pauzes.",
        recommendation="2 past bij de gewenste halve-dag/dagregeling.",
        lower_effect="Nog rustiger, maar minder mogelijkheden om een gewone beslissing later op de dag te corrigeren.",
        higher_effect="Meer flexibiliteit, maar ook meer kans op onnodig schakelen."),
    "stale_s": dict(group="Bescherming", label="Klimaatmeting te oud na", type="number", min=300, max=7200, step=60, unit="s",
        description="Oudere klimaat-/buitentemperatuurdata wordt niet vertrouwd voor automatische regeling.",
        recommendation="1800 s past bij cloudintegraties zonder meteen bij een korte hapering te blokkeren.",
        lower_effect="Strenger op datakwaliteit; sneller blokkeren bij cloudvertraging.",
        higher_effect="Meer tolerantie voor trage updates, maar grotere kans op beslissen met oude data."),
    "guard_recheck_s": dict(group="Bescherming", label="Controle tijdens coast", type="number", min=300, max=3600, step=300, unit="s",
        description="Tijdens OFF/coast controleert SolarPilot zo vaak of AUTO eerder terug nodig is.",
        recommendation="900 s is ruim sneller dan de gebouwreactie zonder onnodig vaak te rekenen.",
        lower_effect="Snellere comfortbewaking, iets meer reken-/serviceactiviteit.",
        higher_effect="Minder controles; een onverwachte weersomslag kan later worden opgemerkt."),
}


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _med(values, default=None):
    vals = [float(v) for v in values if finite(v) is not None]
    return median(vals) if vals else default


def _stored_counter(value, default=0):
    """Accept finite whole counters without allocating or trusting huge values."""
    number = None if isinstance(value, bool) else finite(value)
    if number is None or number < 0 or number != math.floor(number):
        return default
    return int(min(number, 2_147_483_647))


def _stored_numbers(value, limit, lo=None, hi=None):
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    for raw in value[-limit:]:
        number = None if isinstance(raw, bool) else finite(raw)
        if number is not None and (lo is None or number >= lo) and (hi is None or number <= hi):
            out.append(number)
    return out


def _stored_days(value, limit):
    if not isinstance(value, (list, tuple, set)):
        return set()
    days = set()
    rows = list(islice(value, limit)) if isinstance(value, set) else value[-limit:]
    for raw in rows:
        if not isinstance(raw, str):
            continue
        try:
            parsed = date.fromisoformat(raw)
        except ValueError:
            continue
        days.add(parsed.isoformat())
    return days


def _stored_json_value_valid(value, depth=0, budget=None):
    """Keep saved history serializable without traversing unbounded trees."""
    budget = [1000] if budget is None else budget
    budget[0] -= 1
    if depth > 6 or budget[0] < 0:
        return False
    if value is None or isinstance(value, (str, bool)):
        return True
    if isinstance(value, (int, float)):
        return finite(value) is not None
    if isinstance(value, dict):
        return len(value) <= 100 and all(
            isinstance(key, str) and _stored_json_value_valid(item, depth + 1, budget)
            for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return len(value) <= 100 and all(
            _stored_json_value_valid(item, depth + 1, budget) for item in value)
    return False


@dataclass
class ThermalProfile:
    passive_k: list[float] = field(default_factory=list)
    heat_gain: list[float] = field(default_factory=list)
    cool_gain: list[float] = field(default_factory=list)
    solar_gain_per_kw: list[float] = field(default_factory=list)
    days: set[str] = field(default_factory=set)
    samples: int = 0
    last: dict | None = None
    action_started: dict | None = None
    response_delays_h: list[float] = field(default_factory=list)
    heating_delays_h: list[float] = field(default_factory=list)
    cooling_delays_h: list[float] = field(default_factory=list)
    component_days: dict[str, set[str]] = field(default_factory=dict)
    validation_errors: dict[str, list[float]] = field(default_factory=dict)
    validation_horizons: dict[str, list[float]] = field(default_factory=dict)

    def snapshot(self):
        out = {
            "passive_k": self.passive_k[-240:],
            "heat_gain": self.heat_gain[-240:],
            "cool_gain": self.cool_gain[-240:],
            "solar_gain_per_kw": self.solar_gain_per_kw[-240:],
            "days": sorted(self.days)[-120:],
            "samples": self.samples,
            "last": self.last,
            "response_delays_h": self.response_delays_h[-60:],
        }
        # Older journals round-trip unchanged. Their shared delay observations
        # are retained, but never relabelled as verified cooling/heating data.
        for name in ("heating_delays_h", "cooling_delays_h"):
            if getattr(self, name):
                out[name] = getattr(self, name)[-60:]
        if self.component_days:
            out["component_days"] = {key: sorted(days)[-120:] for key, days in self.component_days.items() if days}
        for name in ("validation_errors", "validation_horizons"):
            values = getattr(self, name)
            if values:
                out[name] = {key: rows[-240:] for key, rows in values.items() if rows}
        return out

    def restore(self, data):
        if not isinstance(data, dict):
            return
        # These ranges match observe()'s acceptance bounds. An invalid saved
        # value is dropped, rather than clamped into a fictitious observation.
        limits = {"passive_k": (240, .25), "heat_gain": (240, 3.),
                  "cool_gain": (240, 3.), "solar_gain_per_kw": (240, .5),
                  "response_delays_h": (60, 12.)}
        for name, (limit, upper) in limits.items():
            setattr(self, name, _stored_numbers(data.get(name), limit, 0., upper))
        for name in ("heating_delays_h", "cooling_delays_h"):
            setattr(self, name, _stored_numbers(data.get(name), 60, 0., 48.))
        known = ("passive_temperature_change", "solar_gain", "heating_response", "cooling_response",
                 "heating_delay", "cooling_delay")
        days = data.get("component_days")
        self.component_days = {key: _stored_days(days.get(key), 120) for key in known
                               if isinstance(days, dict) and _stored_days(days.get(key), 120)}
        for name, upper in (("validation_errors", 3.), ("validation_horizons", 1.5)):
            values = data.get(name)
            setattr(self, name, {key: _stored_numbers(values.get(key), 240, 0., upper)
                                for key in ("passive", "heating", "cooling")
                                if isinstance(values, dict) and _stored_numbers(values.get(key), 240, 0., upper)})
        self.days = _stored_days(data.get("days"), 120)
        self.samples = _stored_counter(data.get("samples"))
        self.last = None
        self.action_started = None
        last = data.get("last")
        if isinstance(last, dict):
            stamp, indoor, outdoor = (None if isinstance(last.get(key), bool) else finite(last.get(key))
                                      for key in ("t", "indoor", "outdoor"))
            action = last.get("action")
            pv = finite(last.get("pv_w"))
            if (stamp is not None and stamp >= 0 and indoor is not None and outdoor is not None
                    and isinstance(action, str) and action):
                self.last = {"t": stamp, "indoor": indoor, "outdoor": outdoor,
                             "action": action,
                             "pv_w": max(0., pv) if pv is not None else None}
                slope = finite(last.get("slope_c_h"))
                if slope is not None and abs(slope) <= 3.:
                    self.last["slope_c_h"] = slope
                # Legacy slopes describe active and mixed intervals as well.
                # Only explicitly observed passive provenance may guide AUTO.
                passive_slope = finite(last.get("passive_slope_c_h"))
                if (action.casefold() in ("idle", "off", "none")
                        and passive_slope is not None and abs(passive_slope) <= 3.):
                    self.last["passive_slope_c_h"] = passive_slope

    def coefficients(self):
        """Compatibility tuple: passive k, heat gain, cool gain, response delay."""
        k = _med(self.passive_k, 0.035) if len(self.passive_k) >= 6 else 0.035
        heat = _med(self.heat_gain, 0.12) if len(self.heat_gain) >= 6 else 0.12
        cool = _med(self.cool_gain, 0.12) if len(self.cool_gain) >= 6 else 0.12
        delay = _med(self.response_delays_h, 2.0)
        return (
            _clamp(k, 0.002, 0.20),
            _clamp(heat, 0.02, 2.0),
            _clamp(cool, 0.02, 2.0),
            _clamp(delay, 0.0, 12.0),
        )

    def solar_coefficient(self):
        if len(self.solar_gain_per_kw) < 6:
            return 0.0
        return _clamp(_med(self.solar_gain_per_kw, 0.0), 0.0, 0.5)

    @staticmethod
    def confidence_status(confidence, samples=0):
        if not samples:
            return "Nog niet geleerd"
        if confidence < 0.35:
            return "Eerste metingen"
        if confidence < 0.70:
            return "Voorlopig"
        return "Betrouwbaar"

    def confidence_components(self, settings):
        """Separate evidence; sample count alone can never imply a complete model."""
        min_samples = max(1, int(settings.get("learning_min_samples", 24)))
        min_days = max(1, int(settings.get("learning_min_days", 5)))
        day_conf = min(1.0, len(self.days) / min_days)

        def component(values, need, use_days=True):
            count = len(values)
            sample_conf = min(1.0, count / max(1, need))
            confidence = sample_conf * (0.5 + 0.5 * day_conf) if use_days else sample_conf
            confidence = min(0.98, confidence)
            return {
                "confidence": round(confidence, 3),
                "samples": count,
                "required_samples": need,
                "status": self.confidence_status(confidence, count),
            }

        passive = component(self.passive_k, max(6, min_samples // 2))
        solar = component(self.solar_gain_per_kw, max(6, min_samples // 2))
        heating = component(self.heat_gain, 6)
        cooling = component(self.cool_gain, 6)
        delay = component(self.response_delays_h, 4, use_days=False)
        # Older journals did not retain the action that produced each delay.
        # Preserve those observations, without presenting them as a separately
        # verified heating or cooling delay.
        delay["evidence_scope"] = "shared_heating_or_cooling"
        return {
            "passive_temperature_change": passive,
            "solar_gain": solar,
            "heating_response": heating,
            "cooling_response": cooling,
            "response_delay": delay,
        }

    def confidence(self, settings):
        """Compatibility score for callers requiring both active directions."""
        parts = self.confidence_components(settings)
        passive = parts["passive_temperature_change"]["confidence"]
        heating = parts["heating_response"]["confidence"]
        cooling = parts["cooling_response"]["confidence"]
        delay = parts["response_delay"]["confidence"]
        # Keep the complete-model score conservative. Scoped coast decisions
        # use readiness() so an irrelevant season does not hide useful learning.
        return min(passive, heating, cooling, delay)

    def readiness(self, settings, *, directions=(), use_solar=False):
        """Describe the evidence needed for this particular OFF forecast.

        A passive forecast does not require an unrelated cooling season. When
        that forecast crosses a comfort boundary, starting a coast additionally
        requires the relevant observed active response and a measured delay.
        Coefficient fallbacks remain available for advice, but cannot qualify
        their missing observations as control evidence.
        """
        parts = self.confidence_components(settings)
        directions = [x for x in ("heating", "cooling") if x in directions]
        required = ["passive_temperature_change"]
        if use_solar:
            required.append("solar_gain")
        required.extend(f"{direction}_response" for direction in directions)
        if directions:
            required.append("response_delay")
        min_conf = float(settings.get("model_confidence_min", 0.55))
        missing = [key for key in required
                   if parts[key]["confidence"] < min_conf
                   or parts[key]["samples"] < parts[key]["required_samples"]]
        labels = {
            "passive_temperature_change": "passief temperatuurverloop",
            "solar_gain": "zonnewinst",
            "heating_response": "verwarmingsreactie",
            "cooling_response": "koelreactie",
            "response_delay": "gemeten reactievertraging",
        }
        return {
            "confidence": min(parts[key]["confidence"] for key in required),
            "control_ready": not missing,
            "required_components": required,
            "missing_components": missing,
            "block_reason": ("Nog onvoldoende praktijkbewijs voor "
                             + ", ".join(labels[key] for key in missing)) if missing else "",
            "directions": directions,
            "solar_required": bool(use_solar),
        }

    def solar_confidence(self, settings):
        min_samples = max(6, min(48, int(settings.get("learning_min_samples", 24)) // 2 or 6))
        return min(1.0, len(self.solar_gain_per_kw) / min_samples)

    def directional_evidence(self, settings):
        """Observed coverage and consistency, rather than forecast accuracy.

        Each new component has its own dated provenance. Undated older samples
        remain useful for advice but cannot prove a newly authorised long pause
        or anticipatory start in the opposite HVAC direction.
        """
        min_samples = max(6, int(settings.get("learning_min_samples", 24)) // 2)
        min_days = max(2, int(settings.get("learning_min_days", 5)))
        parts = {}
        rows = {
            "passive_temperature_change": (self.passive_k, min_samples),
            "solar_gain": (self.solar_gain_per_kw, min_samples),
            "heating_response": (self.heat_gain, 6),
            "cooling_response": (self.cool_gain, 6),
            "heating_delay": (self.heating_delays_h, 4),
            "cooling_delay": (self.cooling_delays_h, 4),
        }
        for key, (values, need) in rows.items():
            days = len(self.component_days.get(key, set()))
            coverage = min(.98, min(1., len(values) / need) * min(1., days / min_days))
            middle = _med(values, 0.)
            relative_error = (_med([abs(x - middle) for x in values], 0.)
                              / max(.01, abs(middle))) if values else None
            consistent = bool(values) and relative_error <= .75
            parts[key] = {"confidence": round(coverage, 3), "samples": len(values),
                          "required_samples": need, "days": days, "required_days": min_days,
                          "status": self.confidence_status(coverage, len(values)),
                          "consistent": consistent,
                          "median_relative_deviation": round(relative_error, 3) if relative_error is not None else None,
                          "ready": len(values) >= need and days >= min_days and consistent
                          and coverage >= float(settings.get("model_confidence_min", .55)),
                          "meaning": "meetdekking; geen percentage voorspellingsnauwkeurigheid"}
        return parts

    def validation_summary(self):
        """One-step predictions made before admitting each new observation."""
        out = {}
        for direction in ("passive", "heating", "cooling"):
            errors = self.validation_errors.get(direction, [])
            horizons = self.validation_horizons.get(direction, [])
            out[direction] = {
                "samples": len(errors),
                "mean_absolute_error_c": round(sum(errors) / len(errors), 3) if errors else None,
                "max_horizon_h": round(max(horizons), 2) if horizons else None,
                "ready": len(errors) >= 12 and sum(errors) / len(errors) <= .25,
                "note": "Controle op volgende meting; geen bewijs van bouwschiltemperatuur of 48-uursnauwkeurigheid.",
            }
        return out

    def predictive_readiness(self, settings, *, directions=(), use_solar=False):
        parts = self.directional_evidence(settings)
        required = ["passive_temperature_change"]
        if use_solar:
            required.append("solar_gain")
        for direction in ("heating", "cooling"):
            if direction in directions:
                required.extend((f"{direction}_response", f"{direction}_delay"))
        missing = [key for key in required if not parts[key]["ready"]]
        validation = self.validation_summary()
        validations = ["passive", *[d for d in ("heating", "cooling") if d in directions]]
        missing.extend(f"{d}_validation" for d in validations if not validation[d]["ready"])
        return {"confidence": min(parts[key]["confidence"] for key in required),
                "control_ready": not missing, "required_components": required,
                "missing_components": missing, "directions": list(directions),
                "solar_required": bool(use_solar), "validation": validation,
                "block_reason": ("Nog onvoldoende richtinggebonden metingen of gecontroleerde voorspellingen: "
                                 + ", ".join(missing)) if missing else ""}

    def observe(self, *, wall_ts, day, indoor_c, outdoor_c, hvac_action,
                pv_w=None, settings=None):
        """Learn from actual HVAC action with every selected source known."""
        c = {**SMART_CLIMATE_DEFAULTS, **(settings or {})}
        indoor = finite(indoor_c)
        outdoor = finite(outdoor_c)
        pv = finite(pv_w)
        pv = max(0.0, pv) if pv is not None else None
        if indoor is None or outdoor is None:
            self.last = self.action_started = None
            return False
        cur = {
            "t": float(wall_ts), "indoor": indoor, "outdoor": outdoor,
            "action": str(hvac_action or "idle"), "pv_w": pv,
        }
        prev = self.last
        self.last = cur
        # An unknown PV report is not evidence of darkness. Retain that missing
        # endpoint so the next known report cannot bridge this unobserved period.
        # Learned coefficients/history survive; only an incomplete response
        # interval is discarded when the selected solar model needs PV.
        if c.get("solar_gain_enabled") and (pv is None or (prev and finite(prev.get("pv_w")) is None)):
            self.action_started = None
            return False
        if not prev:
            return False
        dt_h = (cur["t"] - float(prev.get("t", cur["t"]))) / 3600.0
        if not 0.15 <= dt_h <= 1.5:
            self.action_started = None
            return False
        slope = (indoor - float(prev["indoor"])) / dt_h
        if abs(slope) > 3.0:
            self.action_started = None
            return False
        self.last["slope_c_h"] = slope
        self.days.add(str(day))
        self.samples += 1
        prev_action = str(prev.get("action", "idle")).casefold()
        cur_action = str(cur.get("action", "idle")).casefold()
        if prev_action in ("idle", "off", "none") and cur_action in ("idle", "off", "none"):
            self.last["passive_slope_c_h"] = slope
        if cur_action != prev_action and ("heat" in cur_action or "cool" in cur_action):
            self.action_started = {"t": cur["t"], "temp": indoor, "action": cur_action}
        if self.action_started and cur_action == self.action_started.get("action"):
            move = indoor - float(self.action_started.get("temp", indoor))
            expected = move >= 0.15 if "heat" in cur_action else move <= -0.15
            if expected:
                delay = (cur["t"] - float(self.action_started["t"])) / 3600.0
                if 0.0 <= delay <= 12.0:
                    self.response_delays_h.append(delay)
                    self.response_delays_h = self.response_delays_h[-60:]
                # Keep direction and day provenance separate from the legacy
                # shared journal. Long measured responses remain up to 48 h;
                # this is room response, never a measured shell temperature.
                if 0.0 <= delay <= 48.0:
                    direction = "heating" if "heat" in cur_action else "cooling"
                    attr = f"{direction}_delays_h"
                    setattr(self, attr, (getattr(self, attr) + [delay])[-60:])
                    self.component_days.setdefault(f"{direction}_delay", set()).add(str(day))
                self.action_started = None
        elif self.action_started:
            self.action_started = None

        # No full-interval HVAC attribution exists when the two endpoints show
        # different actions. Preserve the transition for delay measurement,
        # but do not turn its mixed slope into passive/active learning evidence.
        if cur_action != prev_action:
            return True

        delta = float(prev["outdoor"]) - float(prev["indoor"])
        action = prev_action
        prev_pv = max(0.0, finite(prev.get("pv_w")) or 0.0)
        min_pv = float(c.get("solar_gain_min_pv_w", 800.0))
        k, _, _, _ = self.coefficients()
        passive = k * delta
        solar_coeff = self.solar_coefficient() if c.get("solar_gain_enabled") else 0.0
        solar_effect = min(float(c.get("solar_gain_max_c_h", 0.35)), solar_coeff * prev_pv / 1000.0)
        direction = "heating" if "heat" in action else "cooling" if "cool" in action else "passive"
        active_rows = self.heat_gain if direction == "heating" else self.cool_gain
        if len(self.passive_k) >= 6 and (direction == "passive" or len(active_rows) >= 6):
            # Unknown sunny gain cannot validate a supposedly complete model.
            solar_known = (not c.get("solar_gain_enabled") or prev_pv < min_pv
                           or len(self.solar_gain_per_kw) >= 6)
            if solar_known:
                _, heat_gain, cool_gain, _ = self.coefficients()
                predicted_slope = passive + solar_effect
                if direction == "heating":
                    predicted_slope += heat_gain
                elif direction == "cooling":
                    predicted_slope -= cool_gain
                error = abs(indoor - (float(prev["indoor"]) + predicted_slope * dt_h))
                if error <= 3.:
                    self.validation_errors.setdefault(direction, []).append(error)
                    self.validation_horizons.setdefault(direction, []).append(dt_h)
                    self.validation_errors[direction] = self.validation_errors[direction][-240:]
                    self.validation_horizons[direction] = self.validation_horizons[direction][-240:]

        if action in ("idle", "off", "none"):
            # Learn envelope leakage mainly from low-solar periods; otherwise sunlight
            # would be misattributed to a weak/negative thermal loss coefficient.
            if abs(delta) >= 1.0 and (not c.get("solar_gain_enabled") or prev_pv < min_pv):
                learned_k = slope / delta
                if 0 <= learned_k <= 0.25:
                    self.passive_k.append(learned_k)
                    self.component_days.setdefault("passive_temperature_change", set()).add(str(day))
            if (c.get("solar_gain_enabled") and c.get("solar_gain_learning_enabled")
                    and prev_pv >= min_pv):
                residual = slope - passive
                if residual > 0:
                    gain_per_kw = residual / max(0.25, prev_pv / 1000.0)
                    if 0 <= gain_per_kw <= 0.5:
                        self.solar_gain_per_kw.append(gain_per_kw)
                        self.component_days.setdefault("solar_gain", set()).add(str(day))
        else:
            # Active HVAC learning subtracts both passive drift and already learned
            # solar gain so sunny hours do not inflate heat-pump response.
            if "heat" in action:
                gain = slope - passive - solar_effect
                if 0 <= gain <= 3.0:
                    self.heat_gain.append(gain)
                    self.component_days.setdefault("heating_response", set()).add(str(day))
            elif "cool" in action:
                gain = -(slope - passive - solar_effect)
                if 0 <= gain <= 3.0:
                    self.cool_gain.append(gain)
                    self.component_days.setdefault("cooling_response", set()).add(str(day))

        for name in ("passive_k", "heat_gain", "cool_gain", "solar_gain_per_kw"):
            setattr(self, name, getattr(self, name)[-240:])
        self.component_days = {key: set(sorted(days)[-120:]) for key, days in self.component_days.items()}
        return True

    def predict(self, initial_c, target_c, outside_hourly, mode="off",
                solar_hourly_w=None, settings=None):
        """Small first-order model; OFF/coast is the main planning path."""
        c = {**SMART_CLIMATE_DEFAULTS, **(settings or {})}
        initial = finite(initial_c)
        target = finite(target_c)
        if initial is None or target is None or not outside_hourly:
            return []
        k, heat_gain, cool_gain, delay_h = self.coefficients()
        solar_coeff = self.solar_coefficient() if c.get("solar_gain_enabled") else 0.0
        solar_rows = list(solar_hourly_w or [])
        temp = initial
        result = []
        active_age = 0.0
        for idx, outside in enumerate(outside_hourly):
            tout = finite(outside)
            if tout is None:
                continue
            passive = k * (tout - temp)
            pv = max(0.0, finite(solar_rows[idx]) or 0.0) if idx < len(solar_rows) else 0.0
            solar = min(float(c.get("solar_gain_max_c_h", 0.35)), solar_coeff * pv / 1000.0)
            active = 0.0
            active_age += 1.0
            gain_scale = min(1.0, active_age / max(1.0, delay_h)) if mode in ("heat", "cool") else 0.0
            if mode == "heat" and temp < target - 0.1:
                active = heat_gain * gain_scale
            elif mode == "cool" and temp > target + 0.1:
                active = -cool_gain * gain_scale
            temp += passive + solar + active
            if mode == "heat":
                temp = min(temp, target + 0.15)
            if mode == "cool":
                temp = max(temp, target - 0.15)
            result.append(round(temp, 3))
        return result


class ForecastBiasProfile:
    """Bounded local correction of weather forecast temperature error."""

    BUCKETS = (6, 12, 24, 48)

    def __init__(self):
        self.errors = {str(h): [] for h in self.BUCKETS}
        self.days = {str(h): set() for h in self.BUCKETS}
        self.pending = {}
        self.total_samples = 0

    def snapshot(self):
        return {
            "errors": {k: v[-120:] for k, v in self.errors.items()},
            "days": {k: sorted(v)[-90:] for k, v in self.days.items()},
            "pending": list(self.pending.values())[-240:],
            "total_samples": self.total_samples,
        }

    def restore(self, data):
        if not isinstance(data, dict):
            return
        errors = data.get("errors") if isinstance(data.get("errors"), dict) else {}
        days = data.get("days") if isinstance(data.get("days"), dict) else {}
        for h in self.BUCKETS:
            key = str(h)
            self.errors[key] = _stored_numbers(errors.get(key), 120, -10., 10.)
            self.days[key] = _stored_days(days.get(key), 90)
        self.pending = {}
        pending = data.get("pending")
        for row in pending[-240:] if isinstance(pending, (list, tuple)) else []:
            if not isinstance(row, dict):
                continue
            valid_ts = None if isinstance(row.get("valid_ts"), bool) else finite(row.get("valid_ts"))
            predicted = None if isinstance(row.get("predicted_c"), bool) else finite(row.get("predicted_c"))
            bucket = _stored_counter(row.get("bucket"))
            if valid_ts is None or valid_ts <= 0 or predicted is None or bucket not in self.BUCKETS:
                continue
            self.pending[f"{int(valid_ts//1800)}:{bucket}"] = {"valid_ts": valid_ts, "predicted_c": predicted, "bucket": bucket}
        self.total_samples = _stored_counter(data.get("total_samples"))

    def reset(self):
        self.__init__()

    @staticmethod
    def _bucket(lead_h):
        return min(ForecastBiasProfile.BUCKETS, key=lambda x: abs(float(lead_h) - x))

    def queue(self, forecast_rows, now_ts):
        for row in forecast_rows or []:
            valid_ts = finite(row.get("valid_ts")); temp = finite(row.get("temperature"))
            if valid_ts is None or temp is None:
                continue
            lead_h = (valid_ts - float(now_ts)) / 3600.0
            if not 3.0 <= lead_h <= 54.0:
                continue
            bucket = self._bucket(lead_h)
            # Only collect points reasonably close to the intended horizon bucket.
            tolerance = 2.0 if bucket <= 12 else 4.0 if bucket == 24 else 6.0
            if abs(lead_h - bucket) > tolerance:
                continue
            key = f"{int(valid_ts//1800)}:{bucket}"
            self.pending[key] = {"valid_ts": valid_ts, "predicted_c": temp, "bucket": bucket}
        if len(self.pending) > 300:
            ordered = sorted(self.pending.items(), key=lambda item: item[1]["valid_ts"])
            self.pending = dict(ordered[-300:])

    def observe(self, now_ts, actual_c, day):
        actual = finite(actual_c)
        if actual is None:
            return 0
        accepted = 0
        keep = {}
        for key, row in self.pending.items():
            valid_ts = float(row["valid_ts"])
            age = float(now_ts) - valid_ts
            if -900 <= age <= 5400:
                if age >= -300:
                    bucket = str(int(row["bucket"]))
                    error = actual - float(row["predicted_c"])
                    if -10 <= error <= 10:
                        self.errors[bucket].append(error)
                        self.errors[bucket] = self.errors[bucket][-120:]
                        self.days[bucket].add(str(day))
                        self.total_samples += 1
                        accepted += 1
                    continue
                keep[key] = row
            elif age < -900:
                keep[key] = row
        self.pending = keep
        return accepted

    def stats_for(self, horizon_h, settings):
        c = {**SMART_CLIMATE_DEFAULTS, **(settings or {})}
        bucket = self._bucket(horizon_h)
        key = str(bucket)
        vals = self.errors.get(key, [])
        days = self.days.get(key, set())
        raw = _med(vals, 0.0) or 0.0
        max_abs = max(0.0, float(c.get("weather_bias_max_c", 3.0)))
        raw = _clamp(raw, -max_abs, max_abs)
        min_samples = max(1, int(c.get("weather_bias_min_samples", 12)))
        min_days = max(1, int(c.get("weather_bias_min_days", 4)))
        sample_conf = min(1.0, len(vals) / min_samples)
        day_conf = min(1.0, len(days) / min_days)
        spread = 0.0
        if len(vals) >= 4:
            ordered = sorted(vals)
            p20 = ordered[max(0, int(len(ordered) * .2) - 1)]
            p80 = ordered[min(len(ordered) - 1, int(len(ordered) * .8))]
            spread = abs(p80 - p20)
        consistency = max(0.25, 1.0 - spread / 5.0)
        confidence = min(1.0, (sample_conf + day_conf) / 2.0 * consistency)
        applied = raw if c.get("weather_bias_enabled") and confidence >= float(c.get("weather_bias_min_confidence", .45)) else 0.0
        return {"horizon_h": bucket, "bias_c": round(raw, 3), "applied_c": round(applied, 3),
                "confidence": round(confidence, 3), "samples": len(vals), "days": len(days)}

    def correction_for(self, lead_h, settings):
        stats = self.stats_for(lead_h, settings)
        return float(stats["applied_c"]), float(stats["confidence"])

    def overview(self, settings):
        return {
            "enabled": bool(settings.get("weather_bias_enabled", True)),
            "total_samples": self.total_samples,
            "pending": len(self.pending),
            "horizons": [self.stats_for(h, settings) for h in self.BUCKETS],
            "note": "Positief = de gekozen weersdienst voorspelde lokaal gemiddeld te koud; negatief = gemiddeld te warm.",
        }


class CoastFeedback:
    """Score SolarPilot-owned coast episodes and cautiously adapt only coast duration."""

    def __init__(self):
        self.active = None
        self.pending = None
        self.history = []
        self.adjust_h = 0.0
        self.scored = 0
        self.total_coast_h = 0.0

    def snapshot(self):
        return {
            "active": self.active, "pending": self.pending,
            "history": self.history[-40:], "adjust_h": self.adjust_h,
            "scored": self.scored, "total_coast_h": self.total_coast_h,
        }

    def restore(self, data, settings=None):
        if not isinstance(data, dict):
            return
        # Active/pending episodes are not resumed across HA restarts: the runtime
        # reconciles device state separately and should not score a discontinuous run.
        self.active = None
        self.pending = None
        history = data.get("history")
        self.history = [dict(x) for x in history[-40:]
                        if isinstance(x, dict) and isinstance(x.get("outcome"), str)
                        and _stored_json_value_valid(x)] if isinstance(history, (list, tuple)) else []
        c = {**SMART_CLIMATE_DEFAULTS, **(settings or {})}
        lo = _clamp(finite(c.get("coast_feedback_min_adjust_h")) or 0., -8., 0.)
        hi = _clamp(finite(c.get("coast_feedback_max_adjust_h")) or 0., 0., 8.)
        self.adjust_h = _clamp(finite(data.get("adjust_h")) or 0., lo, hi)
        self.scored = _stored_counter(data.get("scored"))
        self.total_coast_h = min(2_147_483_647., max(0.0, finite(data.get("total_coast_h")) or 0.0))

    def reset_learning(self):
        """Forget learned coast outcomes without abandoning a live control episode."""
        self.history = []
        self.adjust_h = 0.0
        self.scored = 0
        self.total_coast_h = 0.0

    def effective_window(self, settings):
        base = float(settings.get("min_coast_window_h", 8.0))
        if not settings.get("coast_feedback_enabled", True):
            return base
        lo = float(settings.get("coast_feedback_min_adjust_h", -2.0))
        hi = float(settings.get("coast_feedback_max_adjust_h", 3.0))
        return max(1.0, base + _clamp(self.adjust_h, lo, hi))

    def _score(self, outcome, row, settings):
        row = dict(row or {})
        row["outcome"] = outcome
        self.history.append(row)
        self.history = self.history[-40:]
        if outcome not in ("correct", "te_lang", "te_voorzichtig"):
            return
        self.scored += 1
        if not settings.get("coast_feedback_enabled", True):
            return
        if self.scored < int(settings.get("coast_feedback_min_episodes", 4)):
            return
        step = float(settings.get("coast_feedback_step_h", .5))
        lo = float(settings.get("coast_feedback_min_adjust_h", -2.0))
        hi = float(settings.get("coast_feedback_max_adjust_h", 3.0))
        if outcome == "te_lang":
            self.adjust_h = _clamp(self.adjust_h + step, lo, hi)
        elif outcome == "te_voorzichtig":
            self.adjust_h = _clamp(self.adjust_h - step, lo, hi)

    def start(self, now_ts, zones, decision, settings):
        if self.pending:
            # If a new coast starts before AUTO ever had to work, the previous AUTO
            # release was probably conservative rather than necessary.
            row = self.pending
            self.pending = None
            self._score("te_voorzichtig", row, settings)
        targets = {z["entity_id"]: float(z["target"]) for z in zones}
        currents = {z["entity_id"]: float(z["current"]) for z in zones}
        self.active = {
            "started_ts": float(now_ts), "targets": targets,
            "min_temp": dict(currents), "max_temp": dict(currents),
            "hard_breach": False, "soft_breach": False,
            "predicted_crossing_h": decision.crossing_h,
            "reason": decision.reason,
        }

    def update(self, zones, settings):
        if not self.active:
            return
        soft = float(settings.get("soft_band_c", .5)); hard = float(settings.get("hard_band_c", 1.0))
        for z in zones:
            eid = z["entity_id"]; cur = float(z["current"]); target = float(z["target"])
            self.active["min_temp"][eid] = min(cur, float(self.active["min_temp"].get(eid, cur)))
            self.active["max_temp"][eid] = max(cur, float(self.active["max_temp"].get(eid, cur)))
            if cur < target - hard or cur > target + hard:
                self.active["hard_breach"] = True
            if cur < target - soft or cur > target + soft:
                self.active["soft_breach"] = True

    def abort_manual(self, now_ts, zones, settings):
        if not self.active:
            return
        self.update(zones, settings)
        row = self._close_row(now_ts, zones, "handmatig beëindigd")
        self._score("handmatig", row, settings)

    def _close_row(self, now_ts, zones, reason):
        row = dict(self.active or {})
        self.active = None
        duration_h = max(0.0, (float(now_ts) - float(row.get("started_ts", now_ts))) / 3600.0)
        self.total_coast_h += duration_h
        row["duration_h"] = round(duration_h, 3)
        row["ended_reason"] = reason
        row["ended_temps"] = {z["entity_id"]: float(z["current"]) for z in zones}
        return row

    def release_to_auto(self, now_ts, zones, reason, settings):
        if not self.active:
            return
        self.update(zones, settings)
        row = self._close_row(now_ts, zones, reason)
        if row.get("hard_breach") or row.get("soft_breach"):
            self._score("te_lang", row, settings)
            return
        center = float(settings.get("coast_feedback_center_margin_c", .2))
        centered = all(abs(float(z["current"]) - float(z["target"])) <= center for z in zones)
        row["centered_at_release"] = centered
        row["evaluate_after_ts"] = float(now_ts) + float(settings.get("coast_feedback_eval_h", 3.0)) * 3600.0
        row["action_seen"] = False
        self.pending = row

    def observe_after_release(self, now_ts, zones, settings):
        if not self.pending:
            return
        if any(str(z.get("action", "idle")).casefold() in ("heating", "cooling") for z in zones):
            row = self.pending; self.pending = None
            row["action_seen"] = True
            self._score("correct", row, settings)
            return
        hard = float(settings.get("hard_band_c", 1.0))
        if any(abs(float(z["current"]) - float(z["target"])) > hard for z in zones):
            row = self.pending; self.pending = None
            self._score("te_lang", row, settings)
            return
        if float(now_ts) >= float(self.pending.get("evaluate_after_ts", now_ts + 1)):
            row = self.pending; self.pending = None
            outcome = "te_voorzichtig" if row.get("centered_at_release") else "correct"
            self._score(outcome, row, settings)

    def overview(self, settings):
        counts = {"correct": 0, "te_lang": 0, "te_voorzichtig": 0, "handmatig": 0}
        for row in self.history:
            outcome = row.get("outcome")
            if outcome in counts:
                counts[outcome] += 1
        return {
            "enabled": bool(settings.get("coast_feedback_enabled", True)),
            "active": bool(self.active), "pending_evaluation": bool(self.pending),
            "scored": self.scored, "counts": counts,
            "adjustment_h": round(self.adjust_h, 2),
            "effective_min_coast_window_h": round(self.effective_window(settings), 2),
            "total_coast_h": round(self.total_coast_h, 2),
            "recent": list(self.history[-8:]),
            "note": "De automatische aanpassing verandert alleen het minimale coastvenster, nooit comfortgrenzen of Panasonic HEAT/COOL.",
        }


@dataclass(frozen=True)
class ClimateDecision:
    desired_mode: str
    reason: str
    hard_override: bool = False
    prediction_confidence: float = 0.0
    predicted_min_c: float | None = None
    predicted_max_c: float | None = None
    crossing_h: float | None = None
    required_lead_h: float | None = None
    season_context: str = "unknown"
    season_strength: float = 0.0
    comfort_direction: str = ""
    effective_coast_window_h: float | None = None
    solar_gain_used: bool = False
    forecast_confidence: float = 0.0
    control_ready: bool = False
    required_components: list[str] = field(default_factory=list)
    missing_components: list[str] = field(default_factory=list)
    readiness_by_zone: dict[str, dict] = field(default_factory=dict)
    block_reason: str = ""
    evaluated_forecast_h: int = 0
    stage: str = "legacy"
    comfort_required: bool = False
    urgent_auto: bool = False
    restart_after_h: float | None = None
    forecast_feasible: bool | None = None


def _season_context(c, outside_hourly, target_avg):
    vals = [finite(x) for x in (outside_hourly or [])[:24]]
    vals = [x for x in vals if x is not None]
    if not vals:
        return "unknown", 0.0, None
    avg = sum(vals) / len(vals)
    shoulder = max(0.5, float(c.get("shoulder_band_c", 3.0)))
    extreme = max(shoulder + 0.5, float(c.get("season_extreme_delta_c", 5.0)))
    cold_fraction = sum(x < target_avg - shoulder for x in vals) / len(vals)
    hot_fraction = sum(x > target_avg + shoulder for x in vals) / len(vals)
    delta = avg - target_avg
    if delta <= -shoulder and cold_fraction >= 0.70:
        ctx = "winter"
    elif delta >= shoulder and hot_fraction >= 0.70:
        ctx = "summer"
    else:
        ctx = "shoulder"
    strength = _clamp(abs(delta) / extreme, 0.0, 1.0)
    return ctx, strength, avg


def passive_trend(profile, zone, settings):
    """Use a measured passive interval only at its still-fresh live endpoint."""
    last = profile.last or {}
    stamp, indoor, slope = (finite(last.get(key)) for key in ("t", "indoor", "passive_slope_c_h"))
    passive = ("idle", "off", "none")
    if (stamp is None or not 0 <= time.time() - stamp <= float(settings.get("stale_s", 1800))
            or indoor != finite(zone.get("current"))
            or str(last.get("action", "")).casefold() not in passive
            or str(zone.get("action", "")).casefold() not in passive):
        return None
    return slope


def decide_zone(*, settings, zone, outside_hourly, profile, solar_hourly_w=None,
                solar_precondition=False, outside_c=None):
    """Demand-led AUTO/OFF for one room, with a bounded predictive stage.

    Panasonic retains its target and HEAT/COOL selection. The forecast compares
    an OFF path with possible native-target AUTO windows; it never treats AUTO
    availability as a guarantee that Panasonic will actively pre-cool a shell.
    A missing model still permits measured, direction-aware thermostat control.
    """
    c = {**SMART_CLIMATE_DEFAULTS, **(settings or {})}
    current, target = finite(zone.get("current")), finite(zone.get("target"))
    if not c.get("enabled") or current is None or target is None:
        return ClimateDecision("hold", "Geen bruikbare ruimtemeting voor automatische bediening", stage="reactive")
    mode = str(zone.get("mode", "")).casefold()
    if mode not in ("off", "auto"):
        return ClimateDecision("hold", "Handmatige Panasonic HEAT/COOL-stand blijft behouden", stage="reactive")
    raw_weather = [finite(x) for x in list(outside_hourly or [])[:int(c.get("forecast_horizon_h", 48))]]
    raw_solar = [finite(x) for x in list(solar_hourly_w or [])[:len(raw_weather)]]
    actual_outside = finite(outside_c)
    if actual_outside is None:
        actual_outside = finite((profile.last or {}).get("outdoor"))
    soft = max(.1, float(c.get("soft_band_c", .5)))
    hard = max(soft, float(c.get("hard_band_c", 1.)))
    season, strength, _ = _season_context(c, raw_weather, target)
    # Thermal projections use only a contiguous common source horizon. A
    # shorter PV tail or an internal missing hour cannot become invented zero
    # solar gain, or an apparent 48-hour thermal forecast.
    weather_hours = next((idx for idx, value in enumerate(raw_weather) if value is None), len(raw_weather))
    solar_hours = next((idx for idx, value in enumerate(raw_solar) if value is None or value < 0), len(raw_solar))
    common_hours = min(weather_hours, solar_hours) if c.get("solar_gain_enabled") else weather_hours
    weather, solar = raw_weather[:common_hours], raw_solar[:common_hours]
    positive_solar = bool(c.get("solar_gain_enabled")) and any(x is not None and x > 0 for x in solar)
    known_passive = len(profile.passive_k) >= 6
    # Reactive trends must be observed while HVAC is not changing temperature;
    # an active heater's rising temperature is not proof of natural overheating.
    trend = passive_trend(profile, zone, c)
    drift = None
    if known_passive and actual_outside is not None:
        k = _clamp(_med(profile.passive_k, .035), 0., .20)
        drift = k * (actual_outside - current)
    # Forecast warmth and solar gain belong to the validated predictive path.
    # They cannot pretend to be a current heating/cooling measurement while
    # response evidence is still missing.
    warm_outlook = actual_outside is not None and actual_outside > target + .25
    cool_outlook = actual_outside is not None and actual_outside < target - .25
    cooling_context = warm_outlook or (trend is not None and trend > .03) or (drift is not None and drift > .03)
    heating_context = cool_outlook or (trend is not None and trend < -.03) or (drift is not None and drift < -.03)
    # The measured trend can establish that an excursion is recovering without
    # HVAC; distant outdoor season labels never independently command AUTO.
    if trend is not None and trend < -.03:
        cooling_context = False
    if trend is not None and trend > .03:
        heating_context = False

    def measured_result(desired, reason, *, direction="", urgent=False):
        d = ClimateDecision(desired, reason, hard_override=urgent, stage="reactive",
                            comfort_required=desired == "auto", urgent_auto=urgent,
                            season_context=season, season_strength=strength,
                            comfort_direction=direction, evaluated_forecast_h=len(weather))
        return d

    if current < target - hard and heating_context:
        return measured_result("auto", "Gemeten harde ondergrens en relevante warmtevraag: Panasonic AUTO nodig", direction="heating", urgent=True)
    if current > target + hard and cooling_context:
        return measured_result("auto", "Gemeten harde bovengrens en relevante koelvraag: Panasonic AUTO nodig", direction="cooling", urgent=True)
    if current < target - soft and heating_context:
        return measured_result("auto", "Gemeten temperatuur onder de comfortband; Panasonic AUTO voor warmte beschikbaar maken", direction="heating")
    if current > target + soft and cooling_context:
        return measured_result("auto", "Gemeten temperatuur boven de comfortband; Panasonic AUTO voor koeling beschikbaar maken", direction="cooling")
    if mode == "auto" and current < target - .1 and heating_context:
        return measured_result("auto", "Bestaande warmtevraag loopt tot nabij het Panasonic-doel; AUTO behouden", direction="heating")
    if mode == "auto" and current > target + .1 and cooling_context:
        return measured_result("auto", "Bestaande koelvraag loopt tot nabij het Panasonic-doel; AUTO behouden", direction="cooling")

    # Complete *available* horizons can be shorter than the configured 48 h,
    # but their real coverage is explicit and must still cover a useful pause.
    min_hours = max(6, math.ceil(float(c.get("min_coast_window_h", 8.))))
    forecast_ready = len(weather) >= min_hours
    weather_ready = weather_hours >= min_hours
    solar_ready = not c.get("solar_gain_enabled") or solar_hours >= min_hours
    solar_coeff = profile.solar_coefficient() if c.get("solar_gain_enabled") else 0.
    k = _clamp(_med(profile.passive_k, .035), 0., .20)

    def path(start=None, direction=""):
        temperature, active_age = current, 0.
        temperatures = []
        gain_rows = profile.heat_gain if direction == "heating" else profile.cool_gain
        delays = profile.heating_delays_h if direction == "heating" else profile.cooling_delays_h
        gain = _clamp(_med(gain_rows, 0.), 0., 2.)
        delay = _clamp(_med(delays, 0.), 0., 48.)
        for idx, outside in enumerate(weather):
            if outside is None:
                return []
            solar_w = max(0., solar[idx]) if idx < len(solar) and solar[idx] is not None else 0.
            change = k * (outside - temperature) + min(float(c.get("solar_gain_max_c_h", .35)), solar_coeff * solar_w / 1000.)
            # Actual native-target demand starts the response clock. Merely
            # enabling AUTO while comfortable cannot magically cool the mass.
            demand = (direction == "heating" and temperature < target - .1 or
                      direction == "cooling" and temperature > target + .1)
            if start is not None and idx >= start and demand:
                active_age += 1.
                fraction = min(1., active_age / max(1., delay))
                active = gain * fraction * (1 if direction == "heating" else -1)
                # Limit only the HVAC contribution at the native target; don't
                # clamp weather warming away as the legacy advice model did.
                projected = temperature + change
                if direction == "heating":
                    active = min(active, max(0., target - projected))
                else:
                    active = max(active, min(0., target - projected))
                change += active
            else:
                active_age = 0.
            temperature += change
            temperatures.append(temperature)
        return temperatures

    def crossings(temperatures):
        low_cross = high_cross = None
        entered = target - soft <= current <= target + soft
        previous = current
        for idx, temperature in enumerate(temperatures):
            if target - soft <= temperature <= target + soft:
                entered = True
            # A current excursion may naturally recover. Flag it only if it
            # worsens, then use the normal band after recovery has occurred.
            low = temperature < target - soft and (entered or temperature < min(current, previous) - 1e-6)
            high = temperature > target + soft and (entered or temperature > max(current, previous) + 1e-6)
            if low and low_cross is None:
                low_cross = idx + 1
            if high and high_cross is None:
                high_cross = idx + 1
            previous = temperature
        return low_cross, high_cross

    off_path = path() if forecast_ready else []
    low_cross, high_cross = crossings(off_path)
    directions = (["heating"] if low_cross is not None else []) + (["cooling"] if high_cross is not None else [])
    evidence = profile.predictive_readiness(c, directions=directions, use_solar=positive_solar)
    missing = list(evidence["missing_components"])
    if not weather_ready:
        missing.append("hourly_forecast")
    if not solar_ready:
        missing.append("solar_forecast")
    ready = not missing
    d = measured_result("off", "Geen relevante gemeten warmte- of koelvraag; ruimte automatisch UIT")
    d = replace(d, prediction_confidence=evidence["confidence"],
                forecast_confidence=evidence["confidence"],
                required_components=evidence["required_components"], missing_components=missing,
                control_ready=True,  # Measured control remains useful while learning.
                readiness_by_zone={zone.get("entity_id", ""): {**evidence, "forecast_hours": len(weather)}},
                block_reason=("Vooruit plannen wacht op: " + ", ".join(missing)) if missing else "")
    if off_path:
        d = replace(d, predicted_min_c=round(min(off_path), 3), predicted_max_c=round(max(off_path), 3))
    if not ready:
        return replace(d, reason=d.reason + "; korte comfortbewaking tijdens leren, geen onbewezen lange voorconditionering")
    d = replace(d, stage="predictive", solar_gain_used=positive_solar)
    if not directions:
        return replace(d, reason=f"Geleerd passief verloop blijft binnen de comfortband gedurende de beschikbare {len(weather)} uur; ruimte UIT", forecast_feasible=True)
    if len(directions) != 1:
        return replace(d, desired_mode="auto", comfort_required=True, forecast_feasible=False,
                       comfort_direction="mixed",
                       reason="Voorspelling vraagt zowel warmte als koeling; Panasonic AUTO beschikbaar houden en zelf laten kiezen",
                       block_reason="Geen eenduidige voorspelde AUTO/UIT-periode")
    direction = directions[0]
    crossing = float(low_cross if direction == "heating" else high_cross)
    # Search the latest feasible native-target AUTO window, including real
    # response capacity and measured direction-specific delay. The search does
    # not assume room/shell cooling merely from a distant hot weather forecast.
    feasible = []
    for start in range(len(weather)):
        low, high = crossings(path(start, direction))
        if low is None and high is None:
            feasible.append(float(start))
    d = replace(d, crossing_h=crossing, comfort_direction=direction)
    if not feasible:
        return replace(d, desired_mode="auto", comfort_required=True, urgent_auto=True,
                       forecast_feasible=False, restart_after_h=0., required_lead_h=crossing,
                       reason="De geleerde respons kan de voorspelde comfortgrens niet aantoonbaar opvangen; Panasonic AUTO nu beschikbaar maken",
                       block_reason="Voorspelde comfortbescherming niet haalbaar met de geleerde respons; AUTO garandeert geen actieve voorconditionering")
    start = max(feasible)
    margin = max(0., float(c.get("thermal_start_margin_h", 2.)))
    if solar_precondition:
        margin += max(0., float(c.get("solar_precondition_extra_lead_h", 4.)))
    start = max(0., start - margin)
    d = replace(d, restart_after_h=start, required_lead_h=max(0., crossing - start), forecast_feasible=True)
    # The runtime will re-evaluate on current input changes and regular guards;
    # one guard of remaining time means release AUTO now, without a timer loop.
    if start <= max(.25, float(c.get("guard_recheck_s", 900.)) / 3600.):
        d = replace(d, desired_mode="auto", comfort_required=True, urgent_auto=True,
                    reason=f"Geleerde {direction}-respons vereist Panasonic AUTO nu vóór de verwachte comfortgrens over circa {crossing:.0f} uur")
    else:
        d = replace(d, reason=f"Geen actuele vraag; geleerde respons laat circa {start:.1f} uur UIT toe vóór Panasonic AUTO nodig is")
    return d


def decide_mode(*, settings, zones, outside_hourly, profiles, current_season_mode="", hours_since_season_change=9999,
                pending_candidate="", pending_count=0, solar_precondition=False, solar_hourly_w=None,
                coast_window_adjust_h=0.0):
    """Decide only between Panasonic AUTO, room-zone OFF/coast, or HOLD."""
    del current_season_mode, hours_since_season_change, pending_candidate, pending_count
    c = {**SMART_CLIMATE_DEFAULTS, **(settings or {})}
    if not c["enabled"] or not zones:
        return ClimateDecision("hold", "Slim klimaatbeheer uitgeschakeld")

    soft = max(0.1, float(c["soft_band_c"]))
    hard = max(soft, float(c["hard_band_c"]))
    target_avg = sum(float(z["target"]) for z in zones) / len(zones)
    season, season_strength, avg24 = _season_context(c, outside_hourly, target_avg)

    off_mins, off_maxs, low_crossings, high_crossings, low_leads, high_leads = [], [], [], [], [], []
    solar_used = False
    solar_rows = list(solar_hourly_w or [])
    effective_window = max(1.0, float(c.get("min_coast_window_h", 8.0)) + float(coast_window_adjust_h or 0.0))
    forecast_hours = [finite(x) for x in (outside_hourly or [])]
    required_forecast_hours = math.ceil(effective_window * (1.0 + 0.75 * season_strength))
    forecast_ready = (len(forecast_hours) >= required_forecast_hours
                      and all(x is not None for x in forecast_hours))
    solar_hours = [finite(x) for x in solar_rows[:len(forecast_hours)]]
    # predict() scans the supplied outside horizon for eventual comfort bounds.
    # PV must cover that same horizon, not silently become zero after a shorter
    # minimum coast window. A caller supplying a shorter complete horizon may
    # still qualify when it covers the minimum useful coast period.
    solar_forecast_ready = (not c.get("solar_gain_enabled") or
                            (len(solar_rows) >= max(required_forecast_hours, len(forecast_hours))
                             and all(x is not None for x in solar_hours)))
    positive_solar = bool(c.get("solar_gain_enabled")) and any(x is not None and x > 0 for x in solar_hours)
    readiness_by_zone = {}
    for z in zones:
        profile = profiles.get(z["entity_id"], ThermalProfile())
        # Advice may show a provisional forecast, but a sunny OFF period may not
        # be authorised by silently omitting an unlearned source of warming.
        use_solar = positive_solar and len(profile.solar_gain_per_kw) >= 6
        pred = profile.predict(z["current"], z["target"], outside_hourly, "off",
                               solar_hourly_w=solar_rows if use_solar else None, settings=c)
        solar_used = solar_used or use_solar
        low = z["target"] - soft; high = z["target"] + soft
        low_cross = next((idx + 1 for idx, val in enumerate(pred) if val < low), None)
        high_cross = next((idx + 1 for idx, val in enumerate(pred) if val > high), None)
        directions = (["heating"] if low_cross is not None else []) + (["cooling"] if high_cross is not None else [])
        forecast_evidence = profile.readiness(c, use_solar=positive_solar)
        evidence = profile.readiness(c, directions=directions, use_solar=positive_solar)
        evidence["forecast_confidence"] = forecast_evidence["confidence"]
        evidence["forecast_hours"] = len(forecast_hours)
        forecast_blockers = []
        if not forecast_ready:
            evidence["required_components"].append("hourly_forecast")
            evidence["missing_components"].append("hourly_forecast")
            forecast_blockers.append("Bruikbare uurvoorspelling voor een volledige coastperiode ontbreekt")
        if not solar_forecast_ready:
            evidence["required_components"].append("solar_forecast")
            evidence["missing_components"].append("solar_forecast")
            forecast_blockers.append("Bruikbare PV-uurverwachting voor een volledige coastperiode ontbreekt")
        if forecast_blockers:
            evidence["control_ready"] = False
            evidence["block_reason"] = "; ".join([x for x in [evidence["block_reason"], *forecast_blockers] if x])
        readiness_by_zone[z["entity_id"]] = evidence
        if not pred:
            continue
        off_mins.append(min(pred)); off_maxs.append(max(pred))
        _k, _heat, _cool, delay = profile.coefficients()
        lead = delay + float(c.get("thermal_start_margin_h", 2.0))
        if solar_precondition:
            lead += float(c.get("solar_precondition_extra_lead_h", 4.0))
        if low_cross is not None:
            low_crossings.append(float(low_cross)); low_leads.append(lead)
        if high_cross is not None:
            high_crossings.append(float(high_cross)); high_leads.append(lead)

    pred_min = min(off_mins) if off_mins else None
    pred_max = max(off_maxs) if off_maxs else None
    low_cross = min(low_crossings) if low_crossings else None
    high_cross = min(high_crossings) if high_crossings else None
    low_lead = max(low_leads) if low_leads else None
    high_lead = max(high_leads) if high_leads else None
    confidence = min(x["confidence"] for x in readiness_by_zone.values())
    forecast_confidence = min(x["forecast_confidence"] for x in readiness_by_zone.values())
    required = list(dict.fromkeys(key for row in readiness_by_zone.values() for key in row["required_components"]))
    missing = list(dict.fromkeys(key for row in readiness_by_zone.values() for key in row["missing_components"]))
    model_ready = all(x["control_ready"] for x in readiness_by_zone.values())
    blockers = list(dict.fromkeys(x["block_reason"] for x in readiness_by_zone.values() if x["block_reason"]))
    block_reason = "; ".join(blockers)

    def result(mode, reason, *, hard_override=False, crossing=None, lead=None,
               direction="", window=None, control_ready=None, blocked=""):
        return ClimateDecision(
            mode, reason, hard_override, confidence, pred_min, pred_max,
            crossing, lead, season, season_strength, direction,
            effective_window if window is None else window, solar_used,
            forecast_confidence, model_ready if control_ready is None else control_ready,
            required, missing, readiness_by_zone, blocked or block_reason,
            evaluated_forecast_h=len(forecast_hours),
        )

    fixed = [z for z in zones if str(z.get("mode", "")).casefold() in ("heat", "cool")]
    if fixed:
        modes = ", ".join(sorted({str(z.get("mode", "")).upper() for z in fixed}))
        reason = f"Panasonic staat handmatig op {modes}; SolarPilot wijzigt nooit zelf HEAT/COOL"
        return result("hold", reason, control_ready=False, blocked=reason)

    below = [z for z in zones if z["current"] < z["target"] - hard]
    above = [z for z in zones if z["current"] > z["target"] + hard]
    if below and above:
        return result("auto", "Zones zitten aan beide kanten van de harde comfortband; Panasonic AUTO vrijgeven en zelf laten beslissen",
                      hard_override=True, direction="mixed")
    if below:
        return result("auto", f"Harde comfortondergrens onderschreden in {below[0]['name']}; Panasonic AUTO onmiddellijk vrijgeven",
                      hard_override=True, direction="heating")
    if above:
        return result("auto", f"Harde comfortbovengrens overschreden in {above[0]['name']}; Panasonic AUTO onmiddellijk vrijgeven",
                      hard_override=True, direction="cooling")

    if season in ("winter", "summer") and not bool(c.get("allow_winter_summer_coast", False)):
        label = "winter" if season == "winter" else "zomer"
        avg_txt = f" (24 u buiten gemiddeld {avg24:.1f} °C)" if avg24 is not None else ""
        reason = (f"Buitenverwachting past bij {label}context{avg_txt}; automatische coast is voor deze context uitgeschakeld. "
                  "Dit bewijst geen actuele warmte- of koelvraag; handmatige OFF-zones blijven uit.")
        return result("auto", reason, control_ready=False,
                      blocked="Automatische coast is voor deze buitencontext uitgeschakeld")

    if not model_ready:
        # An already owned coast must not remain OFF while the evidence needed
        # for a safe return disappears. The runtime still excludes manual OFF
        # zones from this AUTO release; starting a new coast remains forbidden.
        mode = "auto" if any(str(z.get("mode", "")).casefold() == "off" for z in zones) else "hold"
        return result(mode, block_reason + "; geen nieuwe automatische coastperiode", control_ready=False)

    if low_cross is not None and high_cross is not None:
        return result("auto", "Gemengde tussenseizoensverwachting kan beide comfortgrenzen bereiken; Panasonic AUTO beschikbaar houden",
                      crossing=min(low_cross, high_cross), lead=max(low_lead or 0.0, high_lead or 0.0),
                      direction="mixed",
                      control_ready=False, blocked="Gemengde verwachting laat geen eenduidige coastperiode toe")

    if low_cross is not None:
        crossing, lead, direction, direction_label = low_cross, float(low_lead or 0.0), "heating", "ondergrens"
    elif high_cross is not None:
        crossing, lead, direction, direction_label = high_cross, float(high_lead or 0.0), "cooling", "bovengrens"
    else:
        crossing, lead, direction, direction_label = None, None, "", ""

    if crossing is None:
        suffix = " Zonnewinst is meegewogen." if solar_used else ""
        return result("off", f"Tussenseizoen: bouwschil blijft binnen de voorspelde comfortband voor de komende {len(forecast_hours)} uur; lange coastperiode is verantwoord." + suffix)

    # Near the edges of shoulder season require a longer useful OFF window. The
    # learned coast feedback only adjusts this minimum window within hard bounds.
    effective_window *= (1.0 + 0.75 * season_strength)
    spare = crossing - float(lead or 0.0)
    if spare < effective_window:
        return result("auto", f"Voorspelde {direction_label} over circa {crossing:.0f} uur; te weinig nuttige coasttijd vóór Panasonic AUTO weer nodig is",
                      crossing=crossing, lead=lead, direction=direction, window=round(effective_window, 2),
                      control_ready=False, blocked="Te weinig bruikbare coasttijd vóór de verwachte comfortgrens")

    return result("off", f"Tussenseizoen: circa {spare:.0f} uur bruikbare coasttijd vóór Panasonic AUTO opnieuw nodig wordt",
                  crossing=crossing, lead=lead, direction=direction, window=round(effective_window, 2))


class SmartClimateState:
    def __init__(self):
        self.profiles = {}
        self.weather_bias = ForecastBiasProfile()
        self.coast_feedback = CoastFeedback()
        self.last_sample_wall = 0.0
        self.last_decision_wall = 0.0
        self.last_guard_wall = 0.0
        self.last_forecast_wall = 0.0
        self.forecast = []
        self.last_decision = ClimateDecision("hold", "Nog geen klimaatbeslissing")
        self.manual_hold_until = 0.0
        self.command_day = ""
        self.commands_today = 0
        self.expected_mode = {}
        self.last_command_wall = 0.0
        self.last_command_mode = ""
        self.fault = ""

    def profile(self, entity_id):
        return self.profiles.setdefault(entity_id, ThermalProfile())

    def reset_learning(self):
        """Clear learned climate models while preserving operational safety state."""
        self.profiles = {}
        self.weather_bias.reset()
        self.coast_feedback.reset_learning()

    def snapshot(self):
        return {
            "profiles": {k: v.snapshot() for k, v in self.profiles.items()},
            "weather_bias": self.weather_bias.snapshot(),
            "coast_feedback": self.coast_feedback.snapshot(),
            "manual_hold_until": self.manual_hold_until,
            "command_day": self.command_day,
            "commands_today": self.commands_today,
            "expected_mode": self.expected_mode,
            "last_command_mode": self.last_command_mode,
            "fault": self.fault,
        }

    def restore(self, data, zone_entities=(), settings=None):
        if not isinstance(data, dict):
            return
        profiles = data.get("profiles")
        profile_ids = (zone_entities or list(islice(profiles, 100))) if isinstance(profiles, dict) else []
        for entity_id in profile_ids:
            raw = profiles.get(entity_id) if isinstance(entity_id, str) else None
            if isinstance(entity_id, str) and isinstance(raw, dict) and (not zone_entities or entity_id in zone_entities):
                self.profile(entity_id).restore(raw)
        self.weather_bias.restore(data.get("weather_bias", {}))
        self.coast_feedback.restore(data.get("coast_feedback", {}), settings)
        # This hold is a wall-clock timestamp, so a restart is not permission
        # to cancel a user's remaining rest period. Reject non-finite/expired
        # values and bound a future journal to the currently configured period.
        saved_hold = finite(data.get("manual_hold_until"))
        hold_h = finite((settings or SMART_CLIMATE_DEFAULTS).get("manual_hold_h"))
        hold_h = SMART_CLIMATE_DEFAULTS["manual_hold_h"] if hold_h is None else _clamp(hold_h, 0.0, 72.0)
        now = time.time()
        self.manual_hold_until = min(saved_hold, now + hold_h * 3600) if saved_hold is not None and saved_hold > now else 0.0
        self.command_day = str(data.get("command_day", ""))
        daily_limit = _stored_counter((settings or SMART_CLIMATE_DEFAULTS).get("max_commands_per_day"), 2)
        self.commands_today = _stored_counter(data.get("commands_today", 0), daily_limit)
        expected = data.get("expected_mode")
        expected_ids = (zone_entities or list(islice(expected, 100))) if isinstance(expected, dict) else []
        self.expected_mode = {eid: expected[eid] for eid in expected_ids
                              if isinstance(eid, str) and expected.get(eid) in ("off", "auto")}
        self.last_command_mode = str(data.get("last_command_mode", ""))
        self.fault = str(data.get("fault", ""))
