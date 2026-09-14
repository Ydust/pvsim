# Jaramillo and Montoya 2018 outdoor validation dataset

## Citation

Velilla, E., Ramirez, D., Uribe, J.-I., Montoya, J. F., and Jaramillo, F. 2019. Outdoor performance of perovskite solar technology: Silicon comparison and competitive advantages at different irradiances. Solar Energy Materials and Solar Cells 191, 15-20. DOI: 10.1016/j.solmat.2018.10.018.

Dataset: Jaramillo, F. and Montoya, J. 2018. Data for: Outdoor performance of perovskite solar technology: silicon comparison and competitive advantages at different irradiances. Mendeley Data, version 1. DOI: 10.17632/9jx8mdh8xd.1.

License: Creative Commons Attribution 4.0 International.

Dataset URL: https://data.mendeley.com/datasets/9jx8mdh8xd/1

Retrieved: 2026-07-20.

## Evidence role

The dataset contains minute-resolved outdoor I-V summaries for 17 square centimetre and 50 square centimetre perovskite minimodules, a co-located Sharp NU-RC290 silicon panel, and two-channel irradiance and temperature observations from Medellin, Colombia. It provides an independent device-level field check of thermal response and irradiance dependence.

It is not a multi-site validation layer. It uses early perovskite minimodules, a 2018 commercial silicon comparator, one tropical site, and about 500 hours of exposure. It cannot establish nationwide annual energy-yield superiority over modern TOPCon, PERC, or HJT modules.

## Raw-file integrity

Files under `raw` are preserved byte for byte. The analysis script checks every SHA-256 value before reading the data.

| File | SHA-256 |
| --- | --- |
| Datos_Atmos_01_2018.csv | c0c7e84aaa8c877acb26bdfd9a07f3ecdab409845c491c86b6422037700ebbb1 |
| Datos_Atmos_02_2018.csv | 6d459dd742cb2deb34572a1ad88520c07a0e142d5a43e396cd3272b44ecfa887 |
| Datos_Atmos_03_2018.csv | f4b777a7759ddd28d59ab886ed5a4bdd4c1dbd5f1c2f68ffbfdc4ee02c70771e |
| Datos_Atmos_04_2018.csv | a49b9d81c96e4f3c183333272d81334c25be9d31ab29aa86ed0b6527d6d4d1ab |
| PSM17_I-V_data.xls | fb4a0da6dd2d0d07de67cfccaa73193b23f29a9b6d9e8c2c4bf792a6b97a9945 |
| PSM50_IV.csv | 54a04096dde12f107d88987c1b0316564f27a5001a933d511af18379b4473040 |
| Sharp_I-V_data.xls | 0f89206965754494c40d7a51dcc349c02e447a78dc70e8ba79835e5df649ba45 |
| Supporting information_28_09_2018.docx | 9b6de985e5d1c585904319452db128e8e15cea8d2ec31fdf61715f107de16ac7 |

## Unit and quality-control rules

The perovskite files label power and current as W and A, but the supporting-information maps establish mW and mA. The script converts perovskite maximum power from mW to W. The Sharp power remains in W.

The PSM50 CSV encloses each complete row in quotation marks. The parser disables normal CSV quotation handling and strips the outer marks before numeric conversion.

The archived Sharp short-circuit-current field is inconsistent with its maximum-power-point current and the supporting-information current map. The validation therefore uses maximum power and open-circuit voltage only. It does not use the archived short-circuit-current field for quality control or inference.

Pairs are retained when the perovskite, silicon, and atmospheric timestamps match within 90 seconds, mean irradiance is 150 to 1200 W per square metre, the two irradiance channels agree within 75 W per square metre or 15 percent, and power and voltage fall inside the published Figure S7 envelopes.
