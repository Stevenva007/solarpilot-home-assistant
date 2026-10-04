"""Options-flow helpers: inspect at any time, confirm saves, manage one device."""
from __future__ import annotations
from copy import deepcopy
import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.exceptions import HomeAssistantError
from .live_options import replacement_profile, PENDING, pending_rows


class LiveOptionsMixin:
    def _base_options(self):
        if not hasattr(self, "_options_base"):
            self._options_base = deepcopy(dict(self.config_entry.options))
        return self._options_base

    async def _live_save(self, options):
        self._live_desired = deepcopy(options)
        self._live_error = ""
        return await self.async_step_apply_changes()

    async def async_step_apply_changes(self, user_input=None):
        rt = self._runtime()
        schema = {}
        error = ""
        effects = ["Instellingen worden opgeslagen; de integratie is momenteel niet geladen."]
        ids = []
        if rt is not None:
            try:
                _, effects = rt.live_options.prepare(self._base_options(), self._live_desired)
                ids = rt.live_options.needs_request_choice(self._base_options(), self._live_desired)
            except HomeAssistantError as err:
                error = str(err)
        if ids:
            schema[vol.Required("request_scope", default="future")] = selector.SelectSelector({"options":[
                {"value":"future","label":"Alleen volgende beurten; huidige aanvraag blijft ongewijzigd"},
                {"value":"current","label":"Ook huidige klaargezette beurt; geplande dag behouden"}]})
        schema[vol.Required("confirm", default=False)] = selector.BooleanSelector()
        if user_input is not None and not error:
            if not user_input.get("confirm"):
                error = "Bevestig de beschreven wijziging om op te slaan."
            else:
                if rt is None:
                    return self.async_create_entry(title="", data=self._live_desired)
                try:
                    async with rt._lock:
                        data = await rt.live_options.submit(self._base_options(), self._live_desired,
                                                           user_input.get("request_scope","future"))
                    return self.async_create_entry(title="", data=data)
                except HomeAssistantError as err:
                    error = str(err)
        return self.async_show_form(step_id="apply_changes", data_schema=vol.Schema(schema),
            description_placeholders={"summary":"\n".join(effects),"issue":error},
            errors={"base":"live_change"} if error else {})

    async def async_step_pending_changes(self, user_input=None):
        rt=self._runtime(); opts=dict(self.config_entry.options)
        pending=pending_rows(opts.get(PENDING,{}))
        choices=[{"value":k,"label":str(v.get("old",{}).get("name",v.get("group",k)) if isinstance(v.get("old"),dict) else v.get("group",k))+" — "+str(v.get("reason",""))} for k,v in pending.items()]
        if user_input is not None and rt is not None:
            async with rt._lock:
                data=await rt.live_options.cancel_pending(user_input.get("cancel",[]))
            return self.async_create_entry(title="",data=data)
        return self.async_show_form(step_id="pending_changes",data_schema=vol.Schema({
            vol.Optional("cancel"):selector.SelectSelector({"options":choices,"multiple":True})}) if choices else vol.Schema({}),
            description_placeholders={"status":"\n".join(x["label"] for x in choices) or "Geen wachtende wijzigingen. De huidige regeling loopt gewoon verder."})

    async def async_step_replace(self, user_input=None):
        devices=self._base_options().get("devices",[])
        if not devices:return self.async_abort(reason="no_devices")
        if user_input is not None:
            self._replace_old=user_input["device_id"]
            return await self.async_step_confirm_replace()
        return self.async_show_form(step_id="replace",data_schema=self._choice_schema())

    async def async_step_confirm_replace(self, user_input=None):
        if user_input is not None and user_input.get("confirm"):
            old=next(d for d in self._base_options().get("devices",[]) if d["id"]==self._replace_old)
            self._editing=None
            self._device=replacement_profile(old)
            return await self.async_step_device()
        return self.async_show_form(step_id="confirm_replace",data_schema=vol.Schema({
            vol.Required("confirm",default=False):selector.BooleanSelector()}))

    async def async_step_manage_device(self, user_input=None):
        devices=self._base_options().get("devices",[])
        if not devices:return self.async_abort(reason="no_devices")
        if user_input is not None:
            self._editing=user_input["device_id"]
            self._device=deepcopy(next(d for d in devices if d["id"]==self._editing))
            rt=self._runtime()
            if rt and not rt.priority_board.active:self._device["priority"]=rt.priorities.get(self._editing,self._device.get("priority",50))
            section=user_input.get("section","settings")
            if section=="connections":return await self.async_step_connection()
            if section=="planning":return await self.async_step_device_schedule()
            return await self.async_step_device()
        return self.async_show_form(step_id="manage_device",data_schema=vol.Schema({
            vol.Required("device_id"):selector.SelectSelector({"options":[{"value":d["id"],"label":d["name"]} for d in devices]}),
            vol.Required("section",default="settings"):selector.SelectSelector({"options":[
                {"value":"settings","label":"Instellingen"},{"value":"connections","label":"Koppelingen"},{"value":"planning","label":"Planning en tijdvensters"}]})}))
