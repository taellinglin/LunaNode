# LunaNode v1.0.0 Release Notes

**Release date:** 2026-01-21

## Highlights
- Stabilized mining workflow with improved logging and status updates.
- Lunalib-only submission path with plain JSON fallback for compatibility.
- Faster startup via deferred heavy loading and cached stats.
- Added performance balance control to reduce CPU load while mining.
- Improved UI responsiveness and sidebar/live stats updates.

## Improvements
- More reliable block submissions and duplicate suppression.
- Cached statistics on startup with periodic live updates.
- Reduced network bandwidth usage during mining.
- Improved mining history persistence and reward tracking.
- Build workflow artifacts for Windows, macOS, and Linux.

## Known Limitations
- Release uploads skip archives larger than 2 GB.
- macOS packaging uses a single app bundle archive (not notarized).

## Upgrade Notes
- No manual migration required. Existing data files are reused.
- If mining performance is high, adjust **Performance Balance** in Settings.

## Checksums
- See GitHub Releases for published SHA256 checksums.
