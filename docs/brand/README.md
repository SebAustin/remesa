# Remesa — Brand assets

| Asset | File | Use |
|---|---|---|
| App icon (512) | `logo-icon.png` / `.svg` | Avatar, DoraHacks project logo, favicon |
| App icon (1024) | `logo-icon-1024.png` | High-res upload |
| Horizontal lockup | `logo-lockup.png` / `.svg` | README header, slides, banners |

PNGs have transparent backgrounds. SVGs are the source of truth — re-export with:

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --force-device-scale-factor=2 \
  --screenshot=logo-icon-1024.png --window-size=512,512 \
  --default-background-color=00000000 "$PWD/logo-icon.svg"
```

## Palette
| Color | Hex | Use |
|---|---|---|
| Base Blue | `#0A5BFF` | Primary / gradient start, `$` mark |
| Teal | `#00C2A8` | Gradient end |
| Ink Navy | `#0A1F44` | Wordmark |
| Slate | `#5B6472` | Tagline / secondary text |

**Concept:** a paper plane (send + a nod to Telegram) lifts off a `$` coin along a
dotted on-chain trail — the agent dispatching money home *and* paying its own way.
