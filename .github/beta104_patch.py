from pathlib import Path
root=Path.cwd()
p=root/'custom_components/solar_pilot/runtime.py'
s=p.read_text()
s=s.replace('''        if not self.problem and wb.state == "unavailable":
            self.problem = wb.reason
''','''        if not self.problem and wb.state == "unavailable":
            # Read-only charger telemetry is not a consumer command fault.
            # It must never offer a site-wide verified-OFF reset.
            self.problem_kind = ("wallbox_configuration" if conflicting_devices(
                self.hass, self.wallbox_settings, list(self.configs.values()))
                else "wallbox_wait")
            self.problem = wb.reason
''')
start=s.index('    async def reset(self):')
end=s.index('    def entity_id(',start)
s=s[:start]+'''    async def reset(self):
        """Review actual faults, without consuming unrelated automatic waits.

        Missing telemetry is not evidence of ON or OFF and needs no manual
        shutdown. Its journal, lease and one-shot tickets stay with their own
        read-only reconciliation route. Uncertain sent commands remain guarded.
        """
        async with self._lock:
            if self.pending or self.battery_fleet.state.pending:
                raise HomeAssistantError("Wacht eerst op de lopende opdracht")
            ids = (set(self.faults) | set(self._restart_faults)
                   | set(self.reclaim_blocks) | set(self.dishwasher_priority.ev_blocks))
            # Only a possibly dispatched command belongs in the OFF review.
            # Ordinary source_wait records must neither veto nor be erased by it.
            ids.update(i for i, item in self.device_retry.records.items()
                       if item.get("state") != "source_wait")
            # Source-only restart leases reconcile automatically. A verified-OFF
            # lease may still be reviewed, but an unknown one cannot block peers.
            ids.update(i for i in self.recovery if i in self.configs
                       and self._restart_active(self.configs[i]) is False)
            reviewed_pause = self.pause_cause in ("internal_fault", "command_fault")
            if not ids and not self.battery_fleet.state.faults and not reviewed_pause:
                # Idempotent stale-page/direct call: no fake OFF claim, no cleared
                # wait or request, no persistence and no dispatch from this call.
                return
            not_off = []
            for i in ids:
                cfg = self.configs.get(i)
                item = self.device_retry.records.get(i, {})
                if (cfg is None or self._restart_active(cfg) is not False
                        or (item and item.get("state") != "source_wait"
                            and (item.get("state") != "command_wait"
                                 or not self.device_retry._post_command_report(
                                     cfg, item.get("issued_wall"))))):
                    not_off.append(cfg["name"] if cfg else i)
            if not_off:
                raise HomeAssistantError("Controleer en schakel eerst veilig uit: " + ", ".join(sorted(not_off)))
            for i in ids:
                if i in self.states:
                    self.states[i].owned = False
                    self.states[i].target_w = 0
                    self.minimum_rest.note_off(i, time.monotonic(), time.time())
                    self.states[i].fault = ""
                    self.states[i].manual_forced = False
                    self.states[i].manual_stop_requested = False
                    if self.configs[i].get("kind") == "dishwasher":
                        self.dishwasher.review(i)
                        self.states[i].cycle_armed = False
                self.faults.pop(i, None)
                self.device_retry.records.pop(i, None)
                self.recovery.pop(i, None)
                self._restart_faults.pop(i, None)
                self.reclaim_blocks.pop(i, None)
                self.dishwasher_priority.ev_blocks.pop(i, None)
            self.dishwasher_priority.watches = {i: v for i, v in self.dishwasher_priority.watches.items()
                if i not in ids or v.get("status") != "attention"}
            self.battery_fleet.state.faults.clear()
            if reviewed_pause:
                self.pause_cause = "user"
            await self.store.async_save(self._snapshot())
            self.note("Foutpauze gecontroleerd. Kies Automatisch regelen om nu te hervatten; bestaande toestelbeveiligingen blijven gelden."
                      if reviewed_pause else
                      "Foutcontrole afgerond voor bevestigde UIT-toestellen. Tijdelijk onbereikbare toestellen blijven onder automatische hercontrole.")
        await self.tick()

'''+s[end:]
p.write_text(s)
p=root/'custom_components/solar_pilot/frontend/solar-pilot-card.js'
s=p.read_text()
s=s.replace("    const sourceConfiguration=!automaticRestart&&a.problem_kind==='source_configuration';", "    const sourceConfiguration=!automaticRestart&&a.problem_kind==='source_configuration';\n    const wallboxWait=!automaticRestart&&a.problem_kind==='wallbox_wait';\n    const wallboxConfiguration=!automaticRestart&&a.problem_kind==='wallbox_configuration';")
s=s.replace("sourceConfiguration?'Toestelgegevens controleren':'Aandacht nodig';", "sourceConfiguration?'Toestelgegevens controleren':wallboxWait?'Wallbox tijdelijk niet bereikbaar':wallboxConfiguration?'Wallboxkoppeling controleren':'Aandacht nodig';")
s=s.replace("sourceConfiguration?'Controleer de gekoppelde bronnen en instellingen van dit toestel.':'';", "sourceConfiguration?'Controleer de gekoppelde bronnen en instellingen van dit toestel.':wallboxWait?'Dit blokkeert andere toestellen niet. Zij mogen actueel gemeten netoverschot gebruiken zodra hun eigen voorwaarden zijn gehaald. SolarPilot controleert de Wallbox automatisch opnieuw; onbekend laadvermogen wordt niet als vrij vermogen gerekend.':wallboxConfiguration?'Controleer de Wallboxkoppelingen. Controle afronden herstelt deze koppeling niet.':'';")
s=s.replace("const canReset=!automaticRestart&&!sourceWait&&!sourceConfiguration&&a.reset_entity;", "const canReset=!automaticRestart&&!sourceWait&&!sourceConfiguration&&!wallboxWait&&!wallboxConfiguration&&a.reset_entity;")
s=s.replace("}`,!automaticRestart&&!sourceWait):''}${isolatedNotice}", "}`,!automaticRestart&&!sourceWait&&!wallboxWait):''}${isolatedNotice}")
p.write_text(s)
p=root/'tests/test_source_wait52.py';s=p.read_text()
s=s.replace('''    with pytest.raises(HomeAssistantError, match="Controleer en schakel eerst veilig uit"):
        await runtime.reset()
''','''    await runtime.reset()
''')
p.write_text(s)
