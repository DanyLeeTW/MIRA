# MIMICEnums 🧑‍💻

### Structure
This folder contains enums used to type-hint options in MIRA tools and related evaluation code.
The actively exported enums are defined in `__init__.py`.
Some are created manually via lookup (see comments/links in the respective `.py` files), and some were created programmatically.

`LabEventsEnums.py` and `_60MicroBiologyEnum.py` are legacy/generated artifacts and are not part of the active public exports in `__init__.py`.

### Regeneration (optional)
Not required for standard runs. The generated enums are already versioned in this folder.

If you intentionally want to refresh enum/code-map artifacts:

1. Edit `src/MimicEnums/make_enums_and_code_maps.py` and uncomment the relevant generation blocks.
2. From `HospitalAgent/` run:

```bash
uv run --project src python src/MimicEnums/make_enums_and_code_maps.py
```
