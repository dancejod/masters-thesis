# modules

The Python modules that contain functions for the processing pipeline.

- `tcp.py`: template matching and detection of the temperature calibration plates (TCPs).
- `utils.py`: general helpers: data loading and aggregation, reprojection to a common grid, and some others.
- `air.py`: air / psychrometric properties, Bowen ratio and the Bowen-ratio energy balance (BREB).
- `emissivity.py`: per-class emissivity assignment, water masking and the production of LST orthomosaics.
- `surface.py`: surface fields, roughness lengths, aerodynamic resistance and Monin–Obukhov stability corrections needed for modelling of the energy fluxes.
- `fluxes.py`: the terms of the surface energy balance and the OSEB model.
- `ws.py`: weather station data loading (the on-site station and the nearby CHMI Luční bouda station).

TODO: add docs