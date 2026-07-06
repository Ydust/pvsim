# Release Manifest

Last updated: 2026-07-01

Manifest status: complete.

This manifest records the journal-facing files that should travel together in a reproducibility package. It gives a file-level checksum boundary for the manuscript, SI evidence, source tables, core scripts, outputs and tests.

| Group | File | Bytes | SHA256 | Role |
| --- | --- | ---: | --- | --- |
| package metadata | `README.md` | 9112 | `47e2d9d0d025bf69` | Repository overview |
| package metadata | `CITATION.cff` | 912 | `bc58c79e78440ca2` | Citation metadata |
| package metadata | `.zenodo.json` | 1117 | `c3ee4afde78f932e` | Archive metadata draft |
| environment | `requirements-lock.txt` | 590 | `cf07c2e01cd8c44e` | Verified Python package lock |
| environment | `pyproject.toml` | 1591 | `a76f99a038396184` | Test and package configuration |
| manuscript | `docs/PAPER_C_draft.md` | 38056 | `056541e30bcc7a52` | English manuscript draft |
| manuscript | `docs/PAPER_MAIN_COMPLETE.md` | 22291 | `e95dc4546bcb1465` | Complete separated main manuscript |
| manuscript | `docs/PAPER_MAIN_COMPLETE_zh.md` | 18065 | `601264e71c11992a` | Complete separated Chinese main manuscript |
| manuscript | `docs/PAPER_C_draft_zh.md` | 31094 | `fd19f911f2f4b6b4` | Chinese manuscript draft |
| manuscript | `docs/SUPPORTING_INFORMATION_DRAFT.md` | 34134 | `137be876b8d50c57` | Supporting information draft |
| manuscript | `docs/SUPPORTING_INFORMATION_COMPLETE.md` | 18507 | `c3f8ee281b3394ea` | Complete separated supporting information |
| manuscript | `docs/SUPPORTING_INFORMATION_COMPLETE_zh.md` | 15586 | `4d26846e7e536e61` | Complete separated Chinese supporting information |
| provenance | `docs/DATA_PROVENANCE.md` | 8408 | `d3e1cb30036a630c` | Input and assumption tiering |
| provenance | `docs/DATA_SOURCES_AND_REFERENCES_zh.md` | 10055 | `b9be32e814fd9ec2` | Chinese data-source and reference-system overview |
| provenance | `docs/MODEL_ARCHITECTURE_AND_CALCULATION_LOGIC_zh.md` | 12456 | `c7d2cc6ac6cb61ed` | Chinese model architecture and calculation-logic overview |
| provenance | `docs/SOURCE_APPENDIX.md` | 6801 | `1639059595681417` | Provincial source-table appendix |
| provenance | `docs/SI_SOURCE_AUDIT_STATUS.md` | 1546 | `9b039c53939d91b5` | Provincial release-gate audit |
| provenance | `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md` | 1542 | `42fe8ec18d22d7ca` | Provincial row-level source evidence worklist |
| provenance | `docs/EXTERNAL_VALIDATION_AUDIT.md` | 5132 | `5b7bd69c8b2cff97` | External validation local audit |
| provenance | `docs/GOVERNMENT_PV_GENERATION_INVENTORY_AUDIT.md` | 4153 | `17c8dd91a0638574` | Government provincial PV generation inventory acquisition audit |
| provenance | `docs/NBS_MANUAL_EXPORT_PROTOCOL.md` | 2414 | `128441e8737d1706` | Manual protocol for official provincial PV generation export |
| provenance | `docs/SI_GOVERNMENT_PV_GENERATION_INVENTORY_VALIDATION.md` | 955 | `fe63af63b4f5583d` | Candidate government provincial PV generation inventory validation |
| provenance | `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md` | 3281 | `66a49f1eddddb048` | National aggregate external validation check |
| provenance | `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md` | 2061 | `13ee6988cff53696` | Location-resolved PV utilization external validation |
| provenance | `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md` | 2069 | `5d0c3be0874f4a66` | NBS spatial absolute generation context |
| provenance | `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md` | 2872 | `b0d2a1d41e4feecb` | CTGR spatial PV generation sample validation |
| provenance | `docs/REFERENCE_AUDIT.md` | 2558 | `4a73e5a2d60caa83` | Crossref DOI audit |
| review audit | `docs/JOULE_PLUS_GAP_AUDIT.md` | 6115 | `c5aa072a40573a0b` | Remaining submission risks |
| review audit | `docs/SCIENTIFIC_HARDENING_CHECKLIST.md` | 5925 | `d7e889388c8ec8fd` | Scientific hardening checklist |
| SI evidence | `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md` | 5229 | `60f18b5b7c80f9fe` | Validation and robustness tables |
| SI evidence | `docs/SI_GRID_UNCERTAINTY.md` | 2133 | `001f4987dddf82b3` | ERA5 grid uncertainty appendix |
| SI evidence | `docs/SI_CLOUD_SPECTRAL_SENSITIVITY.md` | 1410 | `e73d43b45713a178` | Cloud spectral boundary appendix |
| SI evidence | `docs/SI_SILICON_BASELINE_SENSITIVITY.md` | 1941 | `cdd576f451f44c2b` | Modern silicon baseline sensitivity |
| SI evidence | `docs/SI_PEROVSKITE_PARAMETER_SENSITIVITY.md` | 2191 | `56acf01f3c99d892` | Perovskite parameter sensitivity |
| SI evidence | `docs/SI_MECHANISM_SPECIFICITY.md` | 1623 | `d2a6f99af55b88e7` | Mechanism specificity checks |
| SI evidence | `docs/SI_TRANSFERABILITY_BOUNDARY.md` | 1830 | `f2edff23ed24f0c4` | Mechanism phase-plane transferability boundary |
| source table | `data/source_tables/provincial_pv_capacity_2024.csv` | 11894 | `0bb0639ead3dd8e2` | Provincial PV capacity |
| source table | `data/source_tables/provincial_fleet_hours_2024.csv` | 11736 | `a89be788e9582bbd` | Provincial fleet utilisation hours |
| source table | `data/source_tables/nea_pv_utilization_rate_2024.csv` | 10598 | `f68d7e869ffd8ea7` | NEA regional PV generation utilization rates |
| source table | `data/source_tables/nbs_provincial_total_power_generation_2024.csv` | 8588 | `99b671fb68a19137` | NBS provincial total electricity generation |
| source table | `data/source_tables/ctgr_pv_generation_by_region_2024.csv` | 10238 | `149acdc72cb6e46d` | CTGR operating-region PV generation |
| source evidence | `data/source_tables/nea_2024_pv_construction.jpeg` | 250942 | `12ce026ce5ac9e34` | NEA 2024 PV construction official table image |
| source evidence | `data/source_tables/nea_2024_renewable_monitoring_result.doc` | 186880 | `b2c460a50a2bcd37` | NEA renewable monitoring official attachment |
| source evidence | `data/source_tables/nbs_2025_yearbook_C09_19.jpg` | 250455 | `7b1d1c5d526905e4` | NBS 2025 yearbook Table 9-19 official image |
| source evidence | `data/source_tables/sse_600905_2024_annual_report.pdf` | 2061339 | `26a8e5d9285ccd85` | CTGR 2024 annual report official exchange filing |
| main figure | `outputs/figures/NEWFig1_inversion.png` | 625890 | `54826c16d493e6ff` | Fig 1 image |
| main figure | `outputs/figures/NEWFig2_mechanisms.png` | 517267 | `855d8220c8213138` | Fig 2 image |
| main figure | `outputs/figures/NEWFig3_segmentation.png` | 355476 | `48fc1905dd55710c` | Fig 3 image |
| main figure | `outputs/figures/NEWFig4_economics_timing.png` | 423273 | `8c51e1d5304569f6` | Fig 4 image |
| main figure | `outputs/figures/NEWFig5_deployment.png` | 461081 | `b9627959f52c5a91` | Fig 5 image |
| SI data | `outputs/si_source_audit_status.csv` | 377 | `258f11af03654b69` | Source-audit summary data |
| SI data | `outputs/provincial_source_evidence_matrix.csv` | 38104 | `ba4dbb4920d2ea73` | Provincial row-level source evidence worklist |
| SI data | `outputs/external_validation_local_audit.csv` | 3465 | `41d6fc9e3e92e46a` | External validation local audit data |
| SI data | `outputs/government_pv_generation_inventory_audit.csv` | 3410 | `2a20160e927ef61e` | Government provincial PV generation inventory acquisition audit data |
| SI data | `outputs/government_pv_generation_inventory_validation.csv` | 586 | `a480851d88045b1f` | Candidate government provincial PV generation inventory validation data |
| SI data | `outputs/si_national_external_validation.csv` | 1909 | `cef23751b77f24b4` | National aggregate external validation data |
| SI data | `outputs/si_pv_utilization_external_validation.csv` | 9207 | `82ee859f28421594` | Location-resolved PV utilization external validation data |
| SI data | `outputs/si_pv_utilization_external_validation_summary.csv` | 242 | `d58a2651f016466c` | Location-resolved PV utilization external validation summary |
| SI data | `outputs/si_nbs_spatial_generation_validation.csv` | 9210 | `d9403e7b1cd68e74` | NBS spatial generation validation data |
| SI data | `outputs/si_nbs_spatial_generation_validation_summary.csv` | 452 | `7da4f4b894de1623` | NBS spatial generation validation summary |
| SI data | `outputs/si_ctgr_spatial_pv_generation_validation.csv` | 11394 | `0710ff15f82a0af9` | CTGR spatial PV generation validation data |
| SI data | `outputs/si_ctgr_spatial_pv_generation_validation_summary.csv` | 1010 | `728b76428dacda91` | CTGR spatial PV generation validation summary |
| SI data | `outputs/si_silicon_baseline_sensitivity_summary.csv` | 684 | `5eb436ad2629f2b3` | Silicon baseline summary data |
| SI data | `outputs/si_perovskite_parameter_sensitivity_summary.csv` | 1353 | `1be68b3a224a759e` | Perovskite parameter summary data |
| SI data | `outputs/si_mechanism_specificity.csv` | 710 | `12ac58d9ed26a115` | Mechanism specificity data |
| SI data | `outputs/si_transferability_phase_summary.csv` | 587 | `18862e00ab4f67ca` | Transferability phase-plane summary |
| SI figure | `outputs/figures/SI_transferability_phase_plane.png` | 131986 | `b482c6b330477d11` | Transferability phase-plane figure |
| SI data | `outputs/si_grid_uncertainty_quantiles.csv` | 173 | `ca7d50f2e0d4fe33` | Grid uncertainty quantiles |
| SI data | `outputs/si_cloud_spectral_sensitivity_summary.csv` | 668 | `affcf2f15261ee2b` | Cloud spectral summary data |
| core code | `pvsim/materials.py` | 12778 | `63858998c3ba0d92` | Device parameter definitions |
| core code | `pvsim/source_data.py` | 3446 | `b71b745d30e48a58` | Versioned source-table loaders |
| core code | `pvsim/economic_priors.py` | 6802 | `55010b0deb1b04a1` | Monte Carlo economic priors |
| analysis script | `scripts/source_audit_gate.py` | 7319 | `1f2202f11fb11e2f` | Source-audit release gate |
| analysis script | `scripts/provincial_source_evidence_matrix.py` | 7459 | `3625ea436042303f` | Provincial source evidence worklist |
| analysis script | `scripts/external_validation_audit.py` | 12368 | `42625939640cc474` | External validation local audit |
| analysis script | `scripts/government_pv_generation_inventory_audit.py` | 10290 | `53099449ac3cb689` | Government provincial PV generation inventory acquisition audit |
| analysis script | `scripts/validate_government_pv_generation_inventory.py` | 11078 | `9c761fd0e38d81a7` | Candidate government provincial PV generation inventory validation |
| analysis script | `scripts/national_external_validation.py` | 13305 | `39d358009f427360` | National aggregate external validation |
| analysis script | `scripts/pv_utilization_external_validation.py` | 7209 | `fb9fa515766d92b4` | Location-resolved PV utilization external validation |
| analysis script | `scripts/nbs_spatial_generation_validation.py` | 6426 | `aeb2bd87c6d625fd` | NBS spatial generation validation |
| analysis script | `scripts/ctgr_spatial_pv_generation_validation.py` | 9843 | `766006c53233395d` | CTGR spatial PV generation validation |
| analysis script | `scripts/silicon_baseline_sensitivity.py` | 7218 | `31521a258d374242` | Silicon baseline sensitivity |
| analysis script | `scripts/perovskite_parameter_sensitivity.py` | 7014 | `2dd52e05308a63a7` | Perovskite parameter sensitivity |
| analysis script | `scripts/mechanism_specificity.py` | 5785 | `cc5a302bc826d529` | Mechanism specificity checks |
| analysis script | `scripts/global_transferability_boundary.py` | 8659 | `a7606a9f3f621580` | Transferability phase-plane boundary |
| analysis script | `scripts/grid_uncertainty_appendix.py` | 4392 | `02fbc31449d408a8` | Grid uncertainty appendix |
| analysis script | `scripts/cloud_spectral_sensitivity.py` | 5867 | `5bb3f58b8c74cebb` | Cloud spectral boundary test |
| tests | `tests/test_data_integrity.py` | 1987 | `d99fcc0ba2425bab` | Source-table and capacity closure tests |
| tests | `tests/test_external_validation_audit.py` | 2677 | `15fb08e8216d5087` | External validation local audit tests |
| tests | `tests/test_government_pv_generation_inventory_audit.py` | 932 | `f10e9da83873f000` | Government provincial PV generation inventory acquisition audit tests |
| tests | `tests/test_validate_government_pv_generation_inventory.py` | 2292 | `2b3569bda9b88614` | Candidate government provincial PV generation inventory validation tests |
| tests | `tests/test_national_external_validation.py` | 1313 | `c73274149d9a48c5` | National aggregate external validation tests |
| tests | `tests/test_pv_utilization_external_validation.py` | 1234 | `35ea2083cd31a956` | Location-resolved PV utilization external validation tests |
| tests | `tests/test_nbs_spatial_generation_validation.py` | 905 | `4b1905756c46f358` | NBS spatial generation validation tests |
| tests | `tests/test_ctgr_spatial_pv_generation_validation.py` | 1272 | `b094eb735bce636e` | CTGR spatial PV generation validation tests |
| tests | `tests/test_source_audit_gate.py` | 953 | `787905952385906c` | Source-audit gate tests |
| tests | `tests/test_provincial_source_evidence_matrix.py` | 1041 | `983565df21fa77fe` | Provincial source evidence worklist tests |
| tests | `tests/test_silicon_baseline_sensitivity.py` | 458 | `e055b5befdda0cc3` | Silicon baseline sensitivity tests |
| tests | `tests/test_perovskite_parameter_sensitivity.py` | 564 | `1f37b14e3b22a718` | Perovskite parameter sensitivity tests |
| tests | `tests/test_mechanism_specificity.py` | 553 | `de9e035a84cfac88` | Mechanism specificity tests |
| tests | `tests/test_global_transferability_boundary.py` | 838 | `4c82349ef7132157` | Transferability boundary tests |

## Release Gate

A final archive should include every file listed above or explain why a file is generated on demand. The full checksums are stored in `outputs/release_manifest.csv`.

The manifest is not a substitute for row-level source provenance or external validation layers. Those are checked by the dedicated audit scripts.

## Command

`.venv\Scripts\python.exe -m scripts.release_manifest`
