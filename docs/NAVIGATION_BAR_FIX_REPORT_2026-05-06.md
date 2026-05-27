# Navigation Bar Fix Report - 2026-05-06

## What Was Broken

The desktop navbar attempted to fit the brand, `LOCALIZATION` tag, nine full-width nav links, and two CTA buttons in a single row. At common desktop widths, the center nav could invade the right CTA area, causing `Results` and `View architecture` to touch or overlap. The brand group could also crowd `Workflow`.

## Root Cause

The previous layout used one desktop row for too many full labels. Adjusting gaps alone was not robust because long labels such as `Language Integrity` and the fixed-width CTA buttons left too little safe space.

## Layout Strategy Implemented

Implemented priority navigation:

- Brand remains left aligned with a no-shrink minimum width.
- Primary desktop links remain visible in the center.
- Secondary links moved into a polished `More` dropdown.
- CTA buttons remain in a no-shrink right group.
- Mobile/tablet keeps the animated full overlay menu.

The navbar still uses the existing sticky/glass styling, scrolled rounded container, hover underline animation, and `transition-all duration-500` behavior.

## More Dropdown

Added a `More` dropdown using the existing dropdown-menu component and the current design language:

- rounded border
- `bg-background/90`
- backdrop blur
- subtle shadow
- consistent typography and hover/focus behavior

Dropdown links:

- Languages
- Architecture
- Results

Primary visible desktop links:

- Workflow
- Differentiators
- Backends
- Economics
- OTT Export
- Language Integrity

## Desktop And Mobile Behavior

Desktop at `xl` and above shows the priority nav and CTA group. Below `xl`, the hamburger overlay appears before the desktop row can collide.

The mobile overlay menu still includes:

- Workflow
- Differentiators
- Backends
- Economics
- OTT Export
- Language Integrity
- Languages
- Architecture
- Results

The mobile `Start a localization job` button remains.

## Routes Preserved

All requested routes/anchors remain present:

- `/`
- `/differentiators`
- `/backends`
- `/economics`
- `/multilingual-export`
- `/language-integrity`
- `/architecture`
- `/results`
- `/upload`
- `/#workflow`
- `/#languages`

## Validation

- `corepack pnpm run lint`: first sandbox attempt hit Corepack cache `EPERM`; approved rerun passed.
- `corepack pnpm run build`: passed. Next skipped type validation per project config and emitted the existing `baseline-browser-mapping` age warning.
- Visual QA was handled by layout reasoning rather than browser screenshots: at 1280, 1366, 1440, 1536, 1728, and 1920 px the desktop row contains six primary links plus `More`, while the CTA group is a separate no-shrink column. Below `xl`, the hamburger overlay appears before collision risk.

## Remaining Limitations

No known overlap remains by layout reasoning for 1280, 1366, 1440, 1536, 1728, and 1920 pixel widths. The desktop row no longer attempts to display all nine links beside the two CTA buttons.
