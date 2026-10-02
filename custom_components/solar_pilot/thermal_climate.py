"""Slow, explainable thermal planning for Panasonic AUTO/coast.

SolarPilot deliberately never chooses HEAT versus COOL. Panasonic AUTO keeps that
ownership. SolarPilot can only decide whether AUTO should remain available or a
long OFF/coast block is safe, primarily in shoulder-season weather.

The climate model includes three bounded learning layers:
- solar-gain learning using actual PV as a local irradiation proxy;
- local correction of weather-forecast temperature bias at 6/12/24/48 h horizons;
- coast-result scoring that can cautiously tune the *minimum useful coast window*.

The Panasonic thermostat target is always the comfort reference and is never
rewritten by this module. No open-window logic is part of this climate model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
import math


SMART_CLIMATE_DEFAULTS = {
    # Sources / master switches
    "enabled": False,
    "control_enabled": False,
    "weather_entity": "",
    "outside_temp_entity": "",
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
        description="Leert hoe huis en vloer reageren en maakt een AUTO/coast-advies.",
        recommendation="Aan laten zodra de juiste zones en temperatuurbronnen gekoppeld zijn.",
        on_effect="SolarPilot leert en adviseert; dit stuurt nog niets zonder aparte bedieningstoestemming.",
        off_effect="Geen thermisch leren of klimaatadvies."),
    "control_enabled": dict(group="Basis", label="AUTO/coast werkelijk toepassen", type="boolean",
        description="Geeft SolarPilot toestemming om alleen AUTO of OFF/coast te sturen. Nooit HEAT of COOL.",
        recommendation="Eerst meerdere dagen in adviesmodus laten leren en pas daarna activeren.",
        on_effect="SolarPilot kan langdurige coastblokken starten en AUTO tijdig weer vrijgeven.",
        off_effect="Alles blijft adviserend; Panasonic wordt niet door SolarPilot geschakeld."),
    "weather_entity": dict(group="Koppelingen", label="Weerbron", type="weather_entity",
        description="Levert de uurverwachting waarmee het gebouw over de ingestelde horizon vooruit wordt doorgerekend.",
        recommendation="Gebruik een betrouwbare lokale weather-entiteit met hourly forecasts.",
        change_effect="Een andere weersdienst kan een andere systematische fout hebben: het weerbias-model leert opnieuw. Als je géén aparte buitensensor gebruikt, leert ook het thermische model opnieuw."),
    "outside_temp_entity": dict(group="Koppelingen", label="Actuele buitentemperatuur", type="temperature_entity",
        description="Werkelijke buitentemperatuur voor leren en controle. Leeg = temperatuur van de weerentiteit.",
        recommendation="Een fysieke buitensensor bij de woning is meestal beter dan alleen een internetwaarde.",
        change_effect="Omdat een andere sensor anders geplaatst/gekalibreerd kan zijn, worden het thermische model en de lokale weerscorrectie veilig opnieuw opgebouwd."),
    "zone_entities": dict(group="Koppelingen", label="Panasonic klimaatzones", type="climate_entities",
        description="Zones waarvan doeltemperatuur, binnentemperatuur, AUTO/OFF en hvac_action worden gebruikt.",
        recommendation="Selecteer alleen zones die dezelfde Panasonic-installatie vormen en AUTO én OFF ondersteunen.",
        change_effect="Toevoegen/verwijderen verandert de comfortgrenzen en welke zone de conservatieve beslissing bepaalt."),

    "decision_interval_h": dict(group="Comfort & planning", label="Normale planningsbeslissing", type="number", min=6, max=24, step=1, unit="uur",
        description="Hoe vaak een gewone lange-termijnbeslissing opnieuw wordt gemaakt.",
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
        description="Bij overschrijding wordt AUTO meteen weer vrijgegeven, ook buiten het normale beslisritme.",
        recommendation="±1,0 °C houdt een duidelijke veiligheidsmarge rond de zachte comfortband.",
        lower_effect="AUTO grijpt sneller opnieuw in; meer comfortbescherming maar minder besparingsruimte.",
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
        description="Laat de energiebesparende OFF-logica ook buiten het tussenseizoen toe.",
        recommendation="Uit laten. In duidelijke zomer/winter kan Panasonic AUTO meestal beter moduleren.",
        on_effect="Meer coastkansen, maar hoger risico op comfortverlies en inefficiënte inhaalvraag.",
        off_effect="In duidelijke zomer/winter blijft AUTO normaal actief; coastoptimalisatie focust op tussenseizoen."),
    "thermal_start_margin_h": dict(group="Comfort & planning", label="Herstartmarge boven vloerreactie", type="number", min=0, max=12, step=0.5, unit="uur",
        description="Extra tijd bovenop de geleerde reactievertraging om AUTO vóór een voorspelde comfortgrens vrij te geven.",
        recommendation="2 uur geeft een bruikbare veiligheidsmarge voor vloerverwarming/-koeling.",
        lower_effect="Later AUTO vrijgeven; zuiniger mogelijk, maar groter risico dat de woning achterloopt.",
        higher_effect="Eerder AUTO vrijgeven; veiliger comfort, maar minder coasttijd."),
    "solar_precondition_extra_lead_h": dict(group="Comfort & planning", label="Extra voorsprong bij veel PV", type="number", min=0, max=12, step=0.5, unit="uur",
        description="Als PV-voorconditionering aanstaat kan een toch al noodzakelijke AUTO-herstart hiermee vervroegd worden.",
        recommendation="4 uur is ruim; alleen gebruiken als praktijkdata toont dat eerder draaien op PV zinvol is.",
        lower_effect="Minder vervroegen; minder kans op onnodig verbruik.",
        higher_effect="Meer kans om eigen PV te gebruiken, maar ook grotere kans dat je energie gebruikt die later niet nodig bleek."),
    "manual_hold_h": dict(group="Comfort & planning", label="Rust na handmatige modewijziging", type="number", min=1, max=72, step=1, unit="uur",
        description="Hoe lang SolarPilot na een handmatige Panasonic-modewijziging niet probeert terug te sturen.",
        recommendation="12 uur respecteert een bewuste handmatige keuze zonder het systeem dagenlang uit te schakelen.",
        lower_effect="SolarPilot neemt sneller opnieuw over.",
        higher_effect="Handmatige keuzes blijven langer onaangeroerd, maar automatisering hervat later."),

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
        description="Onder dit vertrouwen start SolarPilot geen nieuwe automatische coastperiode.",
        recommendation="0,55 laat leren eerst bewijs opbouwen zonder extreem lang te wachten.",
        lower_effect="Sneller automatische coast, maar meer kans op foutieve voorspellingen.",
        higher_effect="Conservatiever; minder coast tot het model veel bewijs heeft."),

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
        description="Begrenst gewone SolarPilot-modeopdrachten per dag; harde comfortrecovery mag altijd AUTO vrijgeven.",
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
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _med(values, default=None):
    vals = [float(v) for v in values if finite(v) is not None]
    return median(vals) if vals else default


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

    def snapshot(self):
        return {
            "passive_k": self.passive_k[-240:],
            "heat_gain": self.heat_gain[-240:],
            "cool_gain": self.cool_gain[-240:],
            "solar_gain_per_kw": self.solar_gain_per_kw[-240:],
            "days": sorted(self.days)[-120:],
            "samples": self.samples,
            "last": self.last,
            "response_delays_h": self.response_delays_h[-60:],
        }

    def restore(self, data):
        if not isinstance(data, dict):
            return
        limits = {"passive_k": 240, "heat_gain": 240, "cool_gain": 240,
                  "solar_gain_per_kw": 240, "response_delays_h": 60}
        for name, limit in limits.items():
            vals = []
            for x in data.get(name, []):
                v = finite(x)
                if v is not None:
                    vals.append(v)
            setattr(self, name, vals[-limit:])
        self.days = set(str(x) for x in data.get("days", []))
        self.samples = int(data.get("samples", 0) or 0)
        self.last = data.get("last") if isinstance(data.get("last"), dict) else None

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
                "status": self.confidence_status(confidence, count),
            }

        passive = component(self.passive_k, max(6, min_samples // 2))
        solar = component(self.solar_gain_per_kw, max(6, min_samples // 2))
        heating = component(self.heat_gain, 6)
        cooling = component(self.cool_gain, 6)
        delay = component(self.response_delays_h, 4, use_days=False)
        return {
            "passive_temperature_change": passive,
            "solar_gain": solar,
            "heating_response": heating,
            "cooling_response": cooling,
            "response_delay": delay,
        }

    def confidence(self, settings):
        """Conservative control confidence, not a generic data-completeness score."""
        parts = self.confidence_components(settings)
        passive = parts["passive_temperature_change"]["confidence"]
        heating = parts["heating_response"]["confidence"]
        cooling = parts["cooling_response"]["confidence"]
        delay = parts["response_delay"]["confidence"]
        # A generic AUTO/coast confidence may not hide a missing active response.
        # Until both heating and cooling have controlled evidence, optimisation
        # remains conservative. Hard comfort overrides are evaluated separately.
        return min(passive, heating, cooling, delay)

    def solar_confidence(self, settings):
        min_samples = max(6, min(48, int(settings.get("learning_min_samples", 24)) // 2 or 6))
        return min(1.0, len(self.solar_gain_per_kw) / min_samples)

    def observe(self, *, wall_ts, day, indoor_c, outdoor_c, hvac_action,
                pv_w=None, settings=None):
        """Learn from Panasonic's actual hvac_action and optional PV proxy."""
        c = {**SMART_CLIMATE_DEFAULTS, **(settings or {})}
        indoor = finite(indoor_c)
        outdoor = finite(outdoor_c)
        pv = max(0.0, finite(pv_w) or 0.0)
        if indoor is None or outdoor is None:
            return False
        cur = {
            "t": float(wall_ts), "indoor": indoor, "outdoor": outdoor,
            "action": str(hvac_action or "idle"), "pv_w": pv,
        }
        prev = self.last
        self.last = cur
        if not prev:
            return False
        dt_h = (cur["t"] - float(prev.get("t", cur["t"]))) / 3600.0
        if not 0.15 <= dt_h <= 1.5:
            return False
        slope = (indoor - float(prev["indoor"])) / dt_h
        if abs(slope) > 3.0:
            return False
        self.days.add(str(day))
        self.samples += 1
        prev_action = str(prev.get("action", "idle")).casefold()
        cur_action = str(cur.get("action", "idle")).casefold()
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
                self.action_started = None

        delta = float(prev["outdoor"]) - float(prev["indoor"])
        action = prev_action
        prev_pv = max(0.0, finite(prev.get("pv_w")) or 0.0)
        min_pv = float(c.get("solar_gain_min_pv_w", 800.0))
        k, _, _, _ = self.coefficients()
        passive = k * delta
        solar_coeff = self.solar_coefficient()
        solar_effect = min(float(c.get("solar_gain_max_c_h", 0.35)), solar_coeff * prev_pv / 1000.0)

        if action in ("idle", "off", "none"):
            # Learn envelope leakage mainly from low-solar periods; otherwise sunlight
            # would be misattributed to a weak/negative thermal loss coefficient.
            if abs(delta) >= 1.0 and (not c.get("solar_gain_enabled") or prev_pv < min_pv):
                learned_k = slope / delta
                if 0 <= learned_k <= 0.25:
                    self.passive_k.append(learned_k)
            if (c.get("solar_gain_enabled") and c.get("solar_gain_learning_enabled")
                    and prev_pv >= min_pv):
                residual = slope - passive
                if residual > 0:
                    gain_per_kw = residual / max(0.25, prev_pv / 1000.0)
                    if 0 <= gain_per_kw <= 0.5:
                        self.solar_gain_per_kw.append(gain_per_kw)
        else:
            # Active HVAC learning subtracts both passive drift and already learned
            # solar gain so sunny hours do not inflate heat-pump response.
            if "heat" in action:
                gain = slope - passive - solar_effect
                if 0 <= gain <= 3.0:
                    self.heat_gain.append(gain)
            elif "cool" in action:
                gain = -(slope - passive - solar_effect)
                if 0 <= gain <= 3.0:
                    self.cool_gain.append(gain)

        for name in ("passive_k", "heat_gain", "cool_gain", "solar_gain_per_kw"):
            setattr(self, name, getattr(self, name)[-240:])
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
        for h in self.BUCKETS:
            key = str(h)
            self.errors[key] = [float(x) for x in data.get("errors", {}).get(key, [])[-120:] if finite(x) is not None]
            self.days[key] = set(str(x) for x in data.get("days", {}).get(key, [])[-90:])
        self.pending = {}
        for row in data.get("pending", [])[-240:]:
            if not isinstance(row, dict):
                continue
            valid_ts = finite(row.get("valid_ts")); predicted = finite(row.get("predicted_c")); bucket = int(row.get("bucket", 0) or 0)
            if valid_ts is None or predicted is None or bucket not in self.BUCKETS:
                continue
            self.pending[f"{int(valid_ts//1800)}:{bucket}"] = {"valid_ts": valid_ts, "predicted_c": predicted, "bucket": bucket}
        self.total_samples = max(0, int(data.get("total_samples", 0) or 0))

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

    def restore(self, data):
        if not isinstance(data, dict):
            return
        # Active/pending episodes are not resumed across HA restarts: the runtime
        # reconciles device state separately and should not score a discontinuous run.
        self.active = None
        self.pending = None
        self.history = [x for x in data.get("history", [])[-40:] if isinstance(x, dict)]
        self.adjust_h = finite(data.get("adjust_h")) or 0.0
        self.scored = max(0, int(data.get("scored", 0) or 0))
        self.total_coast_h = max(0.0, finite(data.get("total_coast_h")) or 0.0)

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

    fixed = [z for z in zones if str(z.get("mode", "")).casefold() in ("heat", "cool")]
    if fixed:
        modes = ", ".join(sorted({str(z.get("mode", "")).upper() for z in fixed}))
        return ClimateDecision("hold", f"Panasonic staat handmatig op {modes}; SolarPilot wijzigt nooit zelf HEAT/COOL",
                               season_context=season, season_strength=season_strength)

    below = [z for z in zones if z["current"] < z["target"] - hard]
    above = [z for z in zones if z["current"] > z["target"] + hard]
    if below and above:
        return ClimateDecision("auto", "Zones zitten aan beide kanten van de harde comfortband; Panasonic AUTO vrijgeven en zelf laten beslissen",
                               True, season_context=season, season_strength=season_strength)
    if below:
        return ClimateDecision("auto", f"Harde comfortondergrens onderschreden in {below[0]['name']}; Panasonic AUTO onmiddellijk vrijgeven",
                               True, season_context=season, season_strength=season_strength, comfort_direction="heating")
    if above:
        return ClimateDecision("auto", f"Harde comfortbovengrens overschreden in {above[0]['name']}; Panasonic AUTO onmiddellijk vrijgeven",
                               True, season_context=season, season_strength=season_strength, comfort_direction="cooling")

    confs = [profiles[z["entity_id"]].confidence(c) for z in zones if z["entity_id"] in profiles]
    confidence = min(confs) if confs else 0.0
    off_mins, off_maxs, low_crossings, high_crossings, low_leads, high_leads = [], [], [], [], [], []
    solar_used = False
    solar_rows = list(solar_hourly_w or [])
    for z in zones:
        profile = profiles.get(z["entity_id"], ThermalProfile())
        use_solar = bool(c.get("solar_gain_enabled")) and profile.solar_confidence(c) >= 0.35 and bool(solar_rows)
        pred = profile.predict(z["current"], z["target"], outside_hourly, "off",
                               solar_hourly_w=solar_rows if use_solar else None, settings=c)
        solar_used = solar_used or use_solar
        if not pred:
            continue
        off_mins.append(min(pred)); off_maxs.append(max(pred))
        low = z["target"] - soft; high = z["target"] + soft
        low_cross = next((idx + 1 for idx, val in enumerate(pred) if val < low), None)
        high_cross = next((idx + 1 for idx, val in enumerate(pred) if val > high), None)
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
    effective_window = max(1.0, float(c.get("min_coast_window_h", 8.0)) + float(coast_window_adjust_h or 0.0))

    if season in ("winter", "summer") and not bool(c.get("allow_winter_summer_coast", False)):
        label = "winter" if season == "winter" else "zomer"
        avg_txt = f" (24 u buiten gemiddeld {avg24:.1f} °C)" if avg24 is not None else ""
        return ClimateDecision("auto", f"Duidelijke {label}vraag{avg_txt}; besparings-coasting bewust niet streng toepassen en Panasonic AUTO laten regelen",
                               False, confidence, pred_min, pred_max, season_context=season,
                               season_strength=season_strength, effective_coast_window_h=effective_window,
                               solar_gain_used=solar_used)

    min_conf = float(c.get("model_confidence_min", 0.55))
    if confidence < min_conf:
        return ClimateDecision("hold", f"Thermisch model leert nog ({confidence*100:.0f}% < {min_conf*100:.0f}%); geen automatische coastperiode starten",
                               False, confidence, pred_min, pred_max, season_context=season,
                               season_strength=season_strength, effective_coast_window_h=effective_window,
                               solar_gain_used=solar_used)

    if low_cross is not None and high_cross is not None:
        return ClimateDecision("auto", "Gemengde tussenseizoensverwachting kan zowel warmte als koeling vragen; Panasonic AUTO actief laten",
                               False, confidence, pred_min, pred_max, min(low_cross, high_cross),
                               max(low_lead or 0.0, high_lead or 0.0), season, season_strength,
                               effective_coast_window_h=effective_window, solar_gain_used=solar_used)

    if low_cross is not None:
        crossing, lead, direction, direction_label = low_cross, float(low_lead or 0.0), "heating", "ondergrens"
    elif high_cross is not None:
        crossing, lead, direction, direction_label = high_cross, float(high_lead or 0.0), "cooling", "bovengrens"
    else:
        crossing, lead, direction, direction_label = None, None, "", ""

    if crossing is None:
        suffix = " Zonnewinst is meegewogen." if solar_used else ""
        return ClimateDecision("off", "Tussenseizoen: bouwschil blijft binnen de voorspelde comfortband; lange coastperiode is verantwoord." + suffix,
                               False, confidence, pred_min, pred_max, None, None, season, season_strength,
                               effective_coast_window_h=effective_window, solar_gain_used=solar_used)

    # Near the edges of shoulder season require a longer useful OFF window. The
    # learned coast feedback only adjusts this minimum window within hard bounds.
    effective_window *= (1.0 + 0.75 * season_strength)
    spare = crossing - float(lead or 0.0)
    if spare < effective_window:
        return ClimateDecision("auto", f"Voorspelde {direction_label} over circa {crossing:.0f} uur; te weinig nuttige coasttijd vóór Panasonic AUTO weer nodig is",
                               False, confidence, pred_min, pred_max, crossing, lead, season, season_strength, direction,
                               round(effective_window, 2), solar_used)

    return ClimateDecision("off", f"Tussenseizoen: circa {spare:.0f} uur bruikbare coasttijd vóór Panasonic AUTO opnieuw nodig wordt",
                           False, confidence, pred_min, pred_max, crossing, lead, season, season_strength, direction,
                           round(effective_window, 2), solar_used)


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

    def restore(self, data, zone_entities=()):
        if not isinstance(data, dict):
            return
        for entity_id, raw in data.get("profiles", {}).items():
            if not zone_entities or entity_id in zone_entities:
                self.profile(entity_id).restore(raw)
        self.weather_bias.restore(data.get("weather_bias", {}))
        self.coast_feedback.restore(data.get("coast_feedback", {}))
        # Monotonic-style holds/command ages are intentionally not resumed after restart.
        self.manual_hold_until = 0.0
        self.command_day = str(data.get("command_day", ""))
        self.commands_today = int(data.get("commands_today", 0) or 0)
        self.expected_mode = dict(data.get("expected_mode", {}))
        self.last_command_mode = str(data.get("last_command_mode", ""))
        self.fault = str(data.get("fault", ""))
