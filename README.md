# WLED Presets and Configuration

[WLED](https://kno.wled.ge) presets I want to keep in source control

As a personal convention, if a preset is prefixed with `///`, it has segment-specific settings I want to keep.

* [Office shelves](./office-shelves.json)
* [Roof line](./roof-line.json)

## Preset style

Default to calm, visually appealing effects: slow movement, soft twinkles, and gradual changes. Avoid strobes, rapid flashes, and harsh flicker unless explicitly requested.

Default brightness to 40% (`bri: 102` on WLED's 0-255 scale). This is a starting point, not a limit.

## Usage

Copy a line from the json into a new preset in your WLED dashboard.

In the new Preset window, uncheck "Use current state" and paste in the value. Skip the "0"/"1"/"2" prefix in the JSON file - that's the ID.

After presets are updated outside an open WLED page, refresh it before selecting them again; the page may otherwise apply cached older settings.

![New Preset](./.docs/new-preset.png)

## Layered presets (WLED 16+)

Some roof presets (e.g. `Christmas • … v2`, `111`–`117`) use WLED 16 segment layering: full-length segments stacked on top of each other, with a per-segment blend mode (`bm`) and opacity (`bri`). Later segments render on top. These require WLED 16 or newer.

## Home Assistant

I use Home Assistant automations to enable holiday-specific presets/playlists based on the day. Details are in the [Home Assistant Configuration](./home-assistant.md) doc.

## Validation

GitHub Actions runs on pushes and pull requests (or manually via **Validate presets**).
It lints every root-level `*.json` preset backup for invalid JSON, duplicate keys,
and non-JSON numbers, then checks it against
[`schemas/wled-presets.schema.json`](./schemas/wled-presets.schema.json).
Compact formatting is preserved; whitespace and key order are not enforced.

Run the same checks locally with Python 3.12:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python scripts/validate_presets.py
```

Pass file paths to the validator to check specific backups.

The schema is maintained here, **not an official WLED schema**. It covers the
stored state/segment fields and playlists used in this repository, including
WLED 16 layering, the empty `"0": {}` placeholder, partial states, and
`"stop": 0` segment deletion entries. The initial baseline is based on the
[WLED JSON API reference](https://kno.wled.ge/interfaces/json-api/) and the
[WLED 16.0.1 state](https://github.com/wled/WLED/blob/v16.0.1/wled00/json.cpp) and
[playlist](https://github.com/wled/WLED/blob/v16.0.1/wled00/playlist.cpp) implementations.
Unknown fields are rejected to catch typos; extend the schema when adopting other
WLED fields or command forms (such as relative effect strings).
It does not check device-specific LED/segment limits, effect availability,
playlist references, or visual behavior, and brightness is not capped at 40%.

### Enforced lint and schema rules

| Rule | What it catches |
| --- | --- |
| Strict JSON syntax | Malformed JSON, trailing commas, and comments. |
| Unique object keys at every level | Duplicate preset IDs or fields that would silently overwrite earlier values. |
| JSON numbers only | `NaN`, `Infinity`, and `-Infinity`. |
| Known fields and correct types | Misspelled fields, unsupported command forms, and booleans used as integer values. |
| Valid ranges and shapes | Preset IDs 1-250, brightness/color channels 0-255, RGB/RGBW colors, and playlist structure and limits. |

These are correctness checks, not formatting rules: compact JSON and existing
key order are allowed. Brightness above 40% is valid; the default is not a cap.
Playlist reference existence, device-specific segment limits, and animation
behavior are not currently linted.

Keep the `validate` job from **Validate presets** required in branch protection
or rulesets. It runs offline against the committed schema; upstream docs changes
cannot affect its result.

### Manual schema refresh

Use the repository skill
[`wled-schema`](./.agents/skills/wled-schema/SKILL.md) when a firmware update or a
new legitimate preset field requires a schema change. It explains how to review
the official WLED firmware and documentation, update the schema and focused
tests, and validate existing presets.

There are no upstream drift checks, scheduled maintenance jobs, or automatic
maintenance issues. Schema updates are made manually when needed; no extra
Actions secrets are required.

## Todo?

- [ ] Add a script to automatically pull the json files from my WLED instances into this repo
- [ ] Add a script to automatically format the json files, stripping unnecessary info (LED counts, etc.)
