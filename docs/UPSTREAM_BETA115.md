# Upstreambroncontrole voor beta.115

## Aquarea en SDK — 2 november 2026

De acht officiële GitHub-API-records zijn opnieuw online gecontroleerd: publieke repository-identiteit, defaultbranch, actuele HEAD, laatste gepubliceerde stabiele release en opgeloste releasetag voor beide bronnen. Beide repositories zijn publiek en gebruiken main. Beide releases hebben draft=false, prerelease=false en target_commitish=main; beide tagverwijzingen wijzen rechtstreeks naar de onderstaande commit.

| Bron | Defaultbranch en HEAD | Stabiele release en opgeloste commit |
|---|---|---|
| [Aquarea](https://github.com/wpatrik14/home-assistant-aquarea) | main · `76f7e84c98897a7ef354ea8f1e5a6f34d0a71b4b` | [v1.9.1](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.9.1) · dezelfde commit; gepubliceerd 1 november 2026, 18:52:58 UTC |
| [SDK](https://github.com/wpatrik14/aioaquarea) | main · `55da9428ddf43ed26f2386d79c43d50cf4d9da0c` | [v1.5.0](https://github.com/wpatrik14/aioaquarea/releases/tag/v1.5.0) · dezelfde commit; gepubliceerd 23 oktober 2026, 15:00:23 UTC |

Beide HEADs en stabiele tagcommits zijn identiek aan de inhoudelijk beoordeelde checkpoints uit beta.113 en beta.114. Er is geen nieuwe upstreamdiff te verwerken. De bestaande getypeerde status-, LIVE/CACHED-, taak- en energieperiodecontracten blijven vereist; mislukte polls leveren geen nieuwe actualiteit. Het machineleesbare checkpoint behoudt reviewed_base_commit=head_commit, review_result=no_additional_changes en compatibility_claim=false.

## Marstek en formulierwijzigingen

Het bestaande native contract blijft [taurgis/has-marstek-local-api v1.12.0](https://github.com/taurgis/has-marstek-local-api/releases/tag/v1.12.0), opgelost naar `97e70c6959c5784c17b291a32c3ed5fe54d7215c`. De vastgepinde AC-/DC-/CT-veldsemantiek, tekenrichting, bronkwaliteit en oorspronkelijke ontvangen veldtijden blijven zoals inhoudelijk beoordeeld in [UPSTREAM_BETA113.md](UPSTREAM_BETA113.md) en [UPSTREAM_BETA114.md](UPSTREAM_BETA114.md).

Beta.115 herstelt de route naar het bestaande profiel en de mobiele formulierweergave. Een zoekterm, heropend formulier of opslagbevestiging bewijst geen nieuwe meting. Een AC-bevestiging wordt nooit automatisch aangezet; bestaande bron-/tekenvalidatie blijft gelden. Geen extra RPC, polling, providerupgrade, cachemutatie of fabrikantbediening. Marstek blijft uitsluitend uitleesbaar.

Deze controle bevestigt de actualiteit van het publieke broncheckpoint, geen lokale installatiecompatibiliteit of fysieke meetkalibratie. Zie [het bronregister](UPSTREAM_BRONNEN.md). De releasegate controleert de actuele Aquarea-/SDK-stand opnieuw vóór publicatie.
