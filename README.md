# Wizard Click

![Wizard Click UI](Wizard_UI.png)

Live: https://wizard.click  
GitHub Pages (fallback): https://meeshmakes.github.io/wizard-click/

Wizard Click is a fun, single-file “button website”: click the big wizard button to spawn magical effects and play a custom sound.

This is meant to be a free starting template for making your own themed button sites (swap the emoji/image, sound, colors, and particles).

Inspired by https://lizard.click/

## What’s included

- Big centered 3D button
- Local counters: My Clicks, CPS, Best CPS
- Visual effects: wizard spawns + sparkles/bursts
- Overlapping click audio (each click triggers its own sound)

## Run it

Recommended (local server):

```bash
python -m http.server
```

Then visit:

- http://localhost:8000/

Quick option: you can also open `index.html` directly, but some browsers restrict audio loading for `file://` pages.

## Customize

- Replace the sound: overwrite `wizard.wav` (keep the name)
- Replace the vibe: edit colors and effects inside `wizard.html`
- Make it your own “button site”: duplicate `wizard.html` and rename text/assets

## Credits

Made by - Meesh Makes: https://github.com/MeeshMakes
