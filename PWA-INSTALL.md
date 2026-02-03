
# Espace-Image Home Screen Installation (iPad/PC)

## Modern Version

1. Open the main URL in Safari (iPad/iPhone) or Chrome/Edge (PC).
2. Click the share button (Safari) or the menu (Chrome).
3. Select "Add to Home Screen".
4. The Espace-Image icon will appear on your desktop, opening the app in full screen.

## Legacy Version

1. Open the `/legacy` URL in your browser.
2. Repeat the steps above to add it to your home screen.

## Admin

1. Open the `/admin` URL in your browser.
2. Use "Add to Home Screen" as with the other pages.
3. The admin app will open in standalone mode with the Espace-Image Admin icon.

## PWA Features

- Custom icon
- Full screen mode
- Works offline (static cache)
- Minimal service worker

## Notes

- Tested on iPad (Safari) and PC (Chrome/Edge).
- For the best experience, use the modern version on recent devices.

## Note — SVG → PNG Conversion (to do later)

The vector icons `app/static/espaceimage-192.svg` and `app/static/espaceimage-512.svg` are present.
If you want optimized raster PNGs (for maximum compatibility), run locally:

```bash
uv add --dev cairosvg
uv run cairosvg app/static/espaceimage-192.svg -o app/static/espaceimage-192.png -W 192 -H 192
uv run cairosvg app/static/espaceimage-512.svg -o app/static/espaceimage-512.png -W 512 -H 512
ls -la app/static/espaceimage-*
```

Note: The remote editing environment may block tool installation (FS error). Run these commands on your local machine if needed.
