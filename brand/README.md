# RuleCheck app icon — export

Mark: ProSymbols whistle, recoloured. Solar palette (amber #E9A13C on ink #1C1611),
Lunar for the dark appearance (gold #E9CE7B on indigo #1E1B3C).
The mark occupies 85% of the tile; the source SVG's two Noun Project credit
`<text>` nodes have been stripped.

## Attribution — required

Whistle by ProSymbols from Noun Project (CC BY 3.0)
https://thenounproject.com/browse/icons/term/whistle/

Ship this line in **AboutView** (under the GRDB licence note) and in the
**website footer**, with the link live. A paid Noun Project licence removes the
requirement if you would rather drop the credit.

## Files

| Path | Use |
| --- | --- |
| `AppIcon.appiconset/` | Drop into the asset catalog wholesale — Contents.json included |
| `icon-1024.png` | Default appearance. Square, opaque, no alpha — App Store safe |
| `icon-1024-dark.png` | iOS 18 dark appearance |
| `icon-1024-tinted.png` | iOS 18 tinted appearance. Greyscale mark on transparency, as the system expects |
| `rulecheck-whistle.svg` | Mark only, `currentColor` — for in-app SF-Symbol-adjacent use and the website |
| `web/apple-touch-icon-180.png` | `<link rel="apple-touch-icon">` |
| `web/favicon-32.png`, `web/favicon-192.png` | Browser favicons |
| `web/icon-512-rounded.png` | Pre-rounded, for marketing surfaces that don't mask |

## Wiring it up

The Xcode project is generated: add the asset catalog to `app/project.yml` and run
`just app-gen`. Never hand-edit `app/RuleCheck.xcodeproj`. Expect local signing to
be wiped by the regen.

Do not round the corners of `icon-1024.png` and do not add alpha to it — App Store
Connect rejects both. iOS applies the mask itself.
