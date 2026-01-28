# AD-HDTV Assets Policy

## Where to Place Large/Binary Files

- Place all large assets (videos, binaries, zips, etc.) in the `assets/` directory.
- Do NOT commit large files directly to the repository unless essential and under 100MB.
- For very large or copyrighted assets, provide a download script or instructions in this file.

## How to Obtain Assets

- Logos and graphics: `assets/logos/`
- Guide graphics: `assets/guide/` (create if needed)
- Test videos: Not included in repo. Download from [sample-videos.com](https://sample-videos.com/) or similar.

## .gitignore

- The `.gitignore` file is configured to prevent accidental commits of large/binary files and build outputs.

---

If you need to add a new asset type, update this document and the `.gitignore` accordingly.
