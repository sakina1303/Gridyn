# External measured load and PV benchmark

The primary paired benchmark uses [CODECO/ETSIT Building C, Zenodo 19006030](https://zenodo.org/records/19006030) (CC BY 4.0). Its publisher describes one-minute monitoring of Building C at Universidad Politécnica de Madrid, with `L_Tot` building load and `PV_Tot` PV generation in W, and Unix UTC timestamps. This is a Spanish campus building, not a FlexGrid site pilot or an Indian facility.

## Reproduce

Download `edificio_C_pro_power_2019.csv` from the [Zenodo record](https://zenodo.org/records/19006030) or its [publisher GitLab mirror](https://gitlab.eclipse.org/eclipse-research-labs/codeco-project/datasets/energy-demand-management/-/raw/main/datasets_2019/edificio_C_pro_power_2019.csv). Save it as `.local/public_etsit/edificio_C_pro_power_2019.csv`; `.local/` is Git-ignored. The runner verifies publisher MD5 `ad32daf43040ff243c05d60d0014cc4e` before processing:

```bash
PYTHONPATH=backend/src .venv/bin/python scripts/run_public_etsit_benchmark.py --summary-out configs/public_benchmarks/etsit_paired_summary.json
```

The fixed first 41 days span 2018-12-31 23:00 UTC to 2019-02-10 23:00 UTC. For each channel, 15-minute average kW is formed only when all 15 one-minute W readings exist and are finite and nonnegative. The file repeats every minute; exact same-channel duplicates are collapsed, and conflicting readings invalidate that minute. No value is imputed or silently clipped. The one-minute readings are power samples, so their arithmetic mean is a 15-minute proxy, not an independently metered interval-energy total.

Days 34–40 are held out. Previous-day and previous-week persistence use only earlier slots. Load is scored over the full day. PV is scored only over slots 40–59 (10:00–15:00 local winter time) because the published nighttime PV signal includes negative offsets. Missing test or lagged training slots cause abstention. The full fold table and Markdown report are generated under `.local/public_etsit/`; the checked-in [summary](../configs/public_benchmarks/etsit_paired_summary.json) contains source hash, coverage, duplicate/conflict counts, evaluated/abstained days and errors.

This test checks forecast accuracy and data-readiness/abstention behavior on measured paired load/PV signals. It does **not** establish grid import/export, PV availability or curtailment, battery SOC, EV/pump service, operator constraints, delivered flexibility, savings or field reliability. Those outcomes remain **Unknown**.

## Source access note

[Engel et al.'s Dryad smart-building record](https://datadryad.org/dataset/doi:10.5061/dryad.73n5tb363) was the initial choice because its reduced archive contains 15-minute measured grid and PV channels. Public metadata loaded, but file download returned HTTP 401/403 from this environment on 27 October 2026. No Dryad metric was computed. ETSIT is a different, accessible measured-data source.
