# Aydin 2020 tandem outdoor source layer

## Citation

Aydin, E., Allen, T. G., De Bastiani, M. et al. Interplay between temperature and bandgap energies on the outdoor performance of perovskite/silicon tandem solar cells. Nature Energy 5, 851-859, 2020. DOI `10.1038/s41560-020-00687-4`.

Publisher page: https://www.nature.com/articles/s41560-020-00687-4

Source-data workbook: https://static-content.springer.com/esm/art%3A10.1038%2Fs41560-020-00687-4/MediaObjects/41560_2020_687_MOESM3_ESM.xlsx

Supporting information: https://static-content.springer.com/esm/art%3A10.1038%2Fs41560-020-00687-4/MediaObjects/41560_2020_687_MOESM1_ESM.pdf

Retrieved on 2026-07-20.

## Archived files

| File | SHA-256 | Role |
| --- | --- | --- |
| `raw/Source_Data_Fig_1.xlsx` | `80e8d9a633887a37ec81af2249f46c7a31a295ef2ce1bb067f2ae5591b119674` | Publisher source data for outdoor tandem response and annual predicted temperature |
| `raw/Supplementary_Information.pdf` | `6f301b222d5893504b3fe8f317f59b03f4aae0cac0750344e002ede4fc02cb60` | Experimental details and published spectral evidence |

The article page states that the generated and analysed datasets are available in the paper, supporting information and source-data files. A separate redistribution licence is not stated for these two files. They are retained here as a local acquisition cache for analysis. Publisher terms must be checked before depositing the raw files in a public release archive.

## Data interpretation

The workbook sheet `Figure 2a` contains tandem outdoor measurements with elapsed days, ambient temperature, tandem-cell temperature, irradiance in suns, short-circuit current, open-circuit voltage, fill factor, power density and efficiency. The populated performance columns cover nine day clusters.

The sheet contains blank and zero-filled night records as well as isolated irradiance and efficiency inconsistencies. The validation retains complete records with irradiance from 0.2 to 1.05 suns, device temperature from 10 to 80 C, ambient temperature from 10 to 55 C, efficiency from 5 to 35 percent, open-circuit voltage from 1 to 2 V and positive power density. The temperature-coefficient regression further requires irradiance of at least 0.4 suns.

The workbook sheet `Figure 2d` contains the authors' predicted 2016 cell-temperature series. It is not an independent measured target and is not used to validate this model.

The supporting information reports measured spectral changes at the field site and the article establishes temperature- and spectrum-driven current mismatch. No synchronized raw spectral time series is supplied. The source therefore supports the need for an explicit two-subcell current-matching architecture, but it does not identify or calibrate the numerical spectral mismatch factor used in this project.
