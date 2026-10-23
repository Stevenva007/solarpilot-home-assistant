# Upstream review for beta.105 — 23 October 2026

This is a source-impact review, not a claim of live compatibility or a completed test run.

## Exact public sources

- Integration: `wpatrik14/home-assistant-aquarea`, main and stable tag `v1.9.0`: `d3867f4143f7e2c15b84ed67c6e7ace2561f5f96`, published 2026-10-23T15:12:05Z. Compared from reviewed `6717d82ccfb14708abb4a66f494b97418ad80863` (1.8.1), five commits.
- SDK: `wpatrik14/aioaquarea`, stable tag `v1.5.0` and comparison head `55da9428ddf43ed26f2386d79c43d50cf4d9da0c`, published 2026-10-23T15:00:23Z. Compared from reviewed `893065a81c014cb9aa1d3350446d61c01bccf3b9` (1.4.0), five commits.
- Official release, tag-reference and comparison responses were fetched during this review. The existing online gate must independently revalidate the current heads and releases before publication.

Comparison sources:
https://github.com/wpatrik14/home-assistant-aquarea/compare/6717d82ccfb14708abb4a66f494b97418ad80863...d3867f4143f7e2c15b84ed67c6e7ace2561f5f96
https://github.com/wpatrik14/aioaquarea/compare/893065a81c014cb9aa1d3350446d61c01bccf3b9...55da9428ddf43ed26f2386d79c43d50cf4d9da0c

## Relevant changes examined

Integration setup, config flow and coordinator now distinguish `APP_VERSION_REJECTED` from wrong credentials. Setup raises ConfigEntryNotReady and creates a repair; coordinator polling raises UpdateFailed and keeps retrying rather than initiating reauthentication. A successful login/poll clears the repair. New issue helpers, translated messages and the dependency floor `aioaquarea-ng>=1.5.0` implement that behavior. Branding changes do not alter SolarPilot's data contract.

SDK authentication now probes candidate app versions from Google Play, App Store, last-known-good and built-in versions. Rejected versions are distinct from unexpected/unreachable responses; it caches only an accepted candidate and retries a rejected login once. Exhausted or repeatedly rejected candidates raise AppVersionRejectedError, an AuthenticationError subtype with a specific error code. Safe error-code logging does not log response bodies. The source changes include the credential-free canary and its tests, not changed heat-pump state/zone/tank semantics.

## SolarPilot impact and decision

SolarPilot does not implement provider login, import these authentication internals, change tokens or execute the new gate probe. Existing read-only bindings in native_program.py and cloud_energy_period.py require a successfully updated coordinator and existing timestamp/contract evidence. A failed poll stays failed; a repair message is not a fresh physical observation, a stopped heat pump, or new SG authority. The examined SDK changes do not change DeviceImpl, device/zone/tank data or operation-status parsers used by the existing contract evidence.

No additional production-code change is required for these authentication/repair changes. Do not suppress the provider repair, treat cached values as fresh, map authentication failure to OFF, or bypass the existing online review gate. The previous monthly energy-period review remains applicable. Actual loaded-source contract checks and all regression/startup/browser gates still apply; reviewed version numbers alone grant no compatibility or actuator authority.

The dishwasher meter is an independent local read-only observer and does not depend on these login changes. No provider update, login, live meter configuration or physical command was performed by this review.
