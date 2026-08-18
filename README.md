# Calibration of UAV thermal imagery and its influence on evapotranspiration estimation in a montane peatland: a case study of Úpské rašeliniště

This repository contains the code developed for the Master's thesis of the same name (Daniela Dančejová, Charles University, Faculty of Science, Department of Applied Geoinformatics and Cartography, Prague 2026; supervisor doc. RNDr. Lucie Kupková, Ph.D.).

The work calibrates thermal imagery from an uncooled UAV sensor (DJI H20T) against ground references, and examines how the difference between uncalibrated and calibrated thermal input propagates into a surface energy balance (OSEB) estimate of evapotranspiration (ET) over the Úpské rašeliniště peatland. The full pipeline is implemented in Python and built entirely on open-source tools.

## Reproducing the analysis

### Code and environment

The project uses [uv](https://docs.astral.sh/uv/) to manage the Python environment. Clone the repository as following:

```bash
git clone https://github.com/dancejod/masters-thesis.git
cd masters-thesis
uv sync
```

### Data

The input data are archived on Zenodo and are **not** included in this repository. If you encounter an error while running the notebooks, note that a freshly cloned repository has no `data/` or `results/` folder.

**Zenodo archive:** https://doi.org/10.5281/zenodo.21906256 (released under CC-BY-4.0).

Download the archive and unpack it into the project root.

A few steps rely on third-party tools that are not redistributed in this repository.

- **DJI Thermal SDK v1.15**: converts the raw DJI H20T radiometric JPEGs to temperature values. Download from [DJI](https://www.dji.com/downloads/softwares/dji-thermal-sdk). Distributed under DJI's proprietary SDK license (free to download; see the license bundled with the SDK).
- **MicaSense's `imageprocessing`**: radiometric processing of the MicaSense Altum-PT multispectral imagery, at [github.com/micasense/imageprocessing](https://github.com/micasense/imageprocessing). Released under MIT license. The library is reported discontinued, but is still functional.
- **ExifTool**: copies the image metadata onto the calibrated frames; bundled in `tools/`. By Phil Harvey, released under the same terms as Perl (Artistic License / GPL).
- **OpenDroneMap / WebODM**: orthomosaicking of the thermal and multispectral frames. Processing codes to be added. ([opendronemap.org](https://opendronemap.org)). Released under AGPL-3.0 license.

The orthomosaics in this thesis were produced with OpenDroneMap v3.5.6 through the WebODM 2.9.0 interface. As of 6 April 2026, WebODM has been decoupled from OpenDroneMap and the two are now maintained as separate projects.

## Repository structure

- `01_find_tcp.ipynb` – `06_evapotranspiration.ipynb`: the six notebooks that show the pipeline (see below).
- `modules/`: the Python modules that hold the pipeline implementation.
- `data/`: input data (from Zenodo; see above).
- `results/`: generated outputs (created on running the notebooks).
- `manuscript/`: the thesis itself.
- `tools/`: bundled utilities.

## Notebooks

The six notebooks show the processing pipeline and are meant to be run in order.

1. **`01_find_tcp`**: detects the temperature calibration plates (TCPs) in the thermal frames by template matching, extracts their radiometric temperatures and matches them to the PT100 ground reference measurements to build the per-flight calibration dataframes.
2. **`02_explore_data`**: explores the calibration dataframe and the weather station data, and compares the on-site station to the nearby Luční bouda station.
3. **`03_regression`**: fits the empirical line calibration (ELC), an ordinary-least-squares regression of reference on image temperature, per flight, and validates it by leave-one-out cross-validation.
4. **`04_calibrate_thermal`**: applies the fitted models to every thermal frame, writes calibrated GeoTIFFs with the metadata preserved for mosaicking.
5. **`05_correct_emissivity`**: derives the surface properties (NDVI, water mask, per-class emissivity and albedo, land cover, canopy height), applies the emissivity correction to obtain land surface temperature, and stacks the layers into the model input.
6. **`06_evapotranspiration`**: runs the one-source energy balance (OSEB) model on the stack, once with the calibrated LST orthomosaic and once with the uncalibrated brightness temperature orthomosaic, and compares the resulting ET against a Bowen ratio reference from the weather station.

## License

The data archive on Zenodo is released under the [Creative Commons Attribution 4.0 International (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/) license. The third-party tools used by the pipeline remain under their own respective licenses.

## Credits

This work was supervised by doc. RNDr. Lucie Kupková, Ph.D.

Field data collection was carried out with the [Team of Image and Laboratory Spectroscopy (TILSPEC)](https://www.tilspec.cz/); the participants were Dr Lucie Červená, Dr Jakub Lysák, Dr Záboj Hrázský, and the flights were piloted by Ing. Jan Fechtner. Dr Julius Česák constructed the thermal calibration plates and the on-site weather station. A dear colleague Eliška Pospěchová also kindly offered to provide company during one campaign in summer 2025.

Advice on the physics of thermal remote sensing was provided by doc. Ing. Josef Kolář, CSc.; on conducting thermal UAV surveys by Dr Jennifer Susan Adams (University of Zurich); and on the validation of thermal data by Quanxing Wan (Wageningen University) and Simon Grieger (University of Göttingen).

The template used for this thesis was created by Dr Martin Fleischmann, available [here](https://github.com/uscuni/quarto-thesis-template), licensed under Creative Commons CC-BY-4.0.

This thesis was supported by the European Commission Horizon Europe programme, project No. 101081307, "Towards Sustainable Land-Use in the Context of Climate Change and Biodiversity in Europe (Europe-LAND)".
