"""Forecast orchestration, diagnostics and persistent model, without actuators."""
from __future__ import annotations
from datetime import datetime, timedelta
from hashlib import sha256
import json
from .pv_forecast_source import PV_FORECAST_DEFAULTS, ForecastSolarSource, finite
from .pv_calibration import PVCalibration, solar_position


class PVForecast:
    def __init__(self, runtime):
        self.runtime=runtime
        opts=runtime.entry.options
        self.settings={**PV_FORECAST_DEFAULTS,**opts.get("pv_forecast",{})}
        # An explicit old opt-out stays an opt-out. No new physical permissions.
        if "enabled" not in opts.get("pv_forecast",{}) and opts.get("forecast",{}).get("enabled") is False:
            self.settings["enabled"]=False
        # Reuse explicit existing entity selections, never guessed default entity IDs.
        mapping={"remaining_today_entity":"remaining_entity","tomorrow_entity":"tomorrow_entity",
                 "current_hour_entity":"current_hour_entity","next_hour_entity":"next_hour_entity"}
        for old,new in mapping.items():
            if not self.settings.get(new) and opts.get("forecast",{}).get(old):
                self.settings[new]=opts["forecast"][old]
        if not self.settings.get("now_entity") and opts.get("local_pv",{}).get("forecast_power_entity"):
            self.settings["now_entity"]=opts["local_pv"]["forecast_power_entity"]
        if "calibration_enabled" not in opts.get("pv_forecast",{}) and opts.get("local_pv",{}).get("enabled") is False:
            self.settings["calibration_enabled"]=False
        self.source=ForecastSolarSource(runtime.hass,self.settings)
        self.model=PVCalibration(self.settings);self.cached={"enabled":self.settings["enabled"],"available":False,"status":"Nog geen forecast"}
        self.last_update=None;self.error="";self._last_saved_revision=-1
        self.hourly_cache={}

    def position(self, dt):
        c=getattr(self.runtime.hass,"config",None)
        return solar_position(dt,getattr(c,"latitude",None),getattr(c,"longitude",None))

    def _correct(self, ts, raw, tz):
        dt=datetime.fromtimestamp(ts,tz);az,el=self.position(dt)
        factor,confidence,days,source=self.model.factor(dt,az,el)
        return min(float(self.settings["inverter_limit_w"]),max(0.,raw*factor))

    def update(self, now):
        ts=now.timestamp()
        if self.last_update is not None and 0<=ts-self.last_update<60:
            return
        self.last_update=ts;self.hourly_cache={}
        try:
            self.source.refresh(ts)
            az,el=self.runtime._sun_position()
            if az is None or el is None:az,el=self.position(now)
            raw=self.source.raw_at(ts,ts)
            actual,meter_stamp=self.runtime._power(self.runtime.settings.get("pv_entity"))
            actual_obj=self.runtime.hass.states.get(self.runtime.settings.get("pv_entity"))
            attrs=actual_obj.attributes if actual_obj else {}
            if attrs.get("restored") or attrs.get("estimated") is True or attrs.get("is_estimated") is True:
                actual=None
            bind=sha256(json.dumps([self.source.entry_id,self.source.refs,self.runtime.settings.get("pv_entity"),
                self.settings["inverter_limit_w"],self.settings["azimuth_deg"],self.settings["tilt_deg"],self.source.metadata],sort_keys=True).encode()).hexdigest()
            if self.settings["enabled"]:
                self.model.observe(now=now,actual_w=actual,raw_w=raw,meter_stamp=meter_stamp,azimuth=az,elevation=el,binding=bind)
            currentfactor,confidence,days,why=self.model.factor(now,az,el)
            horizon=[]
            for h in range(4):
                t=ts+h*3600;dt=datetime.fromtimestamp(t,now.tzinfo);val=self.source.raw_at(t,ts)
                pa,pe=(az,el) if not h else self.position(dt)
                factor,conf,ndays,origin=self.model.factor(dt,pa,pe)
                horizon.append({"hours":h,"time":dt.isoformat(),"raw_w":None if val is None else round(val,1),
                    "corrected_w":None if val is None else round(min(self.settings["inverter_limit_w"],val*factor),1),
                    "factor":round(factor,3),"confidence":round(conf,3),"days":ndays,"source":origin})
            midnight=(now+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
            after=(midnight+timedelta(days=1))
            hour_start=now.replace(minute=0,second=0,microsecond=0).timestamp()
            # Calendar days can contain 23 or 25 hours. Hour counters and power
            # horizons each describe one real elapsed hour, including DST folds.
            windows={"remaining_today":(now.timestamp(),midnight.timestamp()),
                     "tomorrow":(midnight.timestamp(),after.timestamp()),
                     "current_hour":(hour_start,hour_start+3600),
                     "next_hour":(hour_start+3600,hour_start+7200)}
            totals={};energy_modes={}
            for k,(a,b) in windows.items():
                raw_energy=self.source.series.energy(a,b) if self.source.valid else None
                corrected=self.source.series.energy(a,b,lambda t,w:self._correct(t,w,now.tzinfo)) if raw_energy is not None else None
                if raw_energy is None:
                    role={"remaining_today":"remaining_entity","tomorrow":"tomorrow_entity","current_hour":"current_hour_entity","next_hour":"next_hour_entity"}[k]
                    raw_energy=self.source.scalars.get(role)
                    # Do not apply today's factor to tomorrow or invent a time distribution.
                    corrected=raw_energy;energy_modes[k]="Ruwe energieteller; geen volledige curve om lokaal te corrigeren" if raw_energy is not None else "Geen volledige dekking"
                else:energy_modes[k]="Geïntegreerde vermogenscurve (tijdstempels, kWh)"
                totals[f"raw_{k}_kwh"]=None if raw_energy is None else round(raw_energy,4)
                totals[f"corrected_{k}_kwh"]=None if corrected is None else round(corrected,4)
            summary=self.model.summary()
            self.cached={"enabled":self.settings["enabled"],"available":self.source.valid,"status":self.source.status,
                "warning":self.source.warning,"error":"","show_raw":self.settings["show_raw"],
                "horizon":horizon,**totals,"energy_methods":energy_modes,
                "raw_today_kwh":self.source.scalars.get("today_entity"),
                "native_raw_now_w":self.source.scalars.get("now_entity"),
                "curve_method":"Lineaire interpolatie tussen ruwe Forecast.Solar-vermogenspunten; kan afwijken van de native trapsgewijze nu-sensor",
                "factor":round(currentfactor,3),"confidence":round(confidence,3),"comparable_days":days,
                "model_source":why,"mae_w":summary.get("mae_w"),"bias_w":summary.get("bias_w"),
                "dayparts":summary.get("periods",{}),"last_learning_reason":summary.get("last_reason"),
                "minimum_days_required":summary.get("minimum_days_required"),
                "model":summary,"source_age_s":round(ts-self.source.source_stamp) if self.source.source_stamp else None,
                "source_entry_id":self.source.entry_id,"series_points":len(self.source.series.points),
                "inverter_limit_w":self.settings["inverter_limit_w"],"panel_peak_wp":self.settings["panel_peak_wp"],
                "actual_w":actual,"updated":now.isoformat(),"note":"Voorspelling, geen beschikbaar vermogen. Realtime meters blijven leidend."}
            if self.source.metadata.get("inverter_size") not in (None,0,self.settings["inverter_limit_w"]):
                self.cached["warning"]="Omvormerlimiet van Forecast.Solar wijkt af van SolarPilot; controleer broninstellingen"
            if any((self.source.metadata.get(k) or 0)>0 for k in ("damping_morning","damping_evening")):
                self.cached["warning"]+=("; " if self.cached["warning"] else "")+"Forecast.Solar heeft damping; voorkom dubbele schaduwcorrectie"
            if self.model.revision!=self._last_saved_revision and getattr(self.runtime,"data_loaded",False):
                self._last_saved_revision=self.model.revision
                self.runtime.store.async_delay_save(self.runtime._snapshot,30)
            self.error=""
        except Exception as err:
            # Forecast is optional. Never interrupt the real-time control tick.
            self.error=type(err).__name__;self.source.valid=False;self.hourly_cache={}
            self.cached={"enabled":self.settings["enabled"],"available":False,"status":"Forecastanalyse tijdelijk niet beschikbaar; actuele regeling blijft werken","error":self.error}

    def hourly(self, now, hours):
        """Average W over exact future hours; None for uncovered hours."""
        key=(now.isoformat(),hours)
        if key in self.hourly_cache:return self.hourly_cache[key]
        result=[]
        for h in range(hours):
            a=now.timestamp()+h*3600;b=a+3600
            kwh=self.source.series.energy(a,b,lambda t,w:self._correct(t,w,now.tzinfo)) if self.source.valid else None
            result.append(None if kwh is None else kwh*1000)
        self.hourly_cache[key]=result
        return result

    def snapshot(self):
        return self.model.snapshot()

    def restore(self, data):
        try:self.model.restore(data)
        except (ValueError,TypeError,AttributeError,OverflowError):
            self.error="Opgeslagen PV-model onleesbaar; overige leerdata blijven behouden"

    def diagnostics(self):
        return {"summary":self.cached,"history":list(self.model.history),"settings":{k:v for k,v in self.settings.items() if not k.endswith("entity")},
                "sources":self.source.refs,"source_metadata":self.source.metadata,"candidate_sources":self.source.candidates,
                "limitations":["Geen nieuwe cloudoproepen", "Een lokale afwijking bewijst niet op zichzelf structurele schaduw",
                "Zonder tijdreeks blijven +2/+3 en ontbrekende correcties onbekend", "Voorbije 15-minutenmetingen zonder gelijktijdige ruwe forecast worden niet als bewezen kalibratie geïmporteerd"]}

    def reset(self):
        self.model=PVCalibration(self.settings);self.last_update=None;self.hourly_cache={}
        # Explicit PV-only reset also clears the legacy live correction to avoid
        # bringing an old live factor back through the fallback path.
        self.runtime.local_pv.reset_live()
        self.cached={"enabled":self.settings["enabled"],"available":False,"status":"PV-profiel gewist; wachten op nieuwe metingen", "model":self.model.summary()}

# Stable entity suffixes, not physical entity IDs. Forecast energy is NOT a counter.
PV_SENSOR_DEFINITIONS = {
    **{f"pvf_{kind}_{h}h": (f"PV {label} {'nu' if h==0 else '+'+str(h)+' uur'}", "W", kind+"_w", h)
       for kind,label in (("raw","Forecast.Solar ruw"),("corrected","lokaal gecorrigeerd")) for h in range(4)},
    "pvf_remaining_raw": ("PV resterend vandaag ruw", "kWh", "raw_remaining_today_kwh", None),
    "pvf_remaining_corrected": ("PV resterend vandaag gecorrigeerd", "kWh", "corrected_remaining_today_kwh", None),
    "pvf_tomorrow_corrected": ("PV morgen gecorrigeerd", "kWh", "corrected_tomorrow_kwh", None),
    "pvf_factor": ("PV correctiefactor", None, "factor", None),
    "pvf_confidence": ("PV kalibratiezekerheid", "%", "confidence", None),
    "pvf_error": ("PV gemiddelde afwijking bij zon", "W", "mae_w", None),
}
