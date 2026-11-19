# Extensions for trying by hand

`heading-check/` is a small extension (design document F25) for the hand check T-EXT-16: it lists the headings of the open chapter and has one secret setting, to see that the secret goes into the computer's keychain. It is not shipped in the app. Pack it as a `.scmod` file and install it in Settings ▸ Extensions:

```
python -c "from pathlib import Path; from scriptorum.core.modules import pack_scmod; pack_scmod(Path('tests/extensions/heading-check'), Path('heading-check.scmod'))"
```
