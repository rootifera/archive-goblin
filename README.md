# Archive Goblin

Archive Goblin is a local desktop workstation for preparing Archive.org uploads.

It starts with file review and renaming, then carries that work forward into project metadata, upload preview, and Archive.org upload.

## Current Features

- Rule-based filename matching against file stems
- Protected disk-image extension handling
- Folder scan, review table, image preview, and safe rename apply
- Built-in cover-image copy support
- Persistent local rules and metadata settings
- Per-project metadata saved in the selected folder
- Archive.org page URL generation and availability check
- Archive.org credential storage and connection test
- Upload preview with identifier, tags, description, size, warnings, and blockers
- Real Archive.org upload flow with progress dialog

## Project Structure

```text
archive_goblin/
  main.py
  models/
  services/
  storage/
  ui/
```

## Requirements

- Python 3.12+
- PySide6
- internetarchive

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

From the repo root:

```bash
python -m archive_goblin
```

## Main Workflow

1. Open a folder.
2. Review detected file names and apply renames.
3. Open `Project -> Metadata...` and fill the project details.
4. Open `Project -> Upload Preview...` to review the Archive.org upload summary.
5. Start the upload when the preview has no blocking issues.

## Settings

`Settings -> Rules...`
- matching rules
- protected file extensions

`Settings -> Metadata...`
- Title Pattern
- Page URL Pattern
- Default Tags

`Settings -> Archive.org...`
- S3 API Access Key
- S3 Secret Key
- Test Connection

## Shortcuts

- `Ctrl+O` open folder
- `Ctrl+R` rescan
- `Ctrl+Enter` apply renames
- `Ctrl+P` project metadata
- `Ctrl+Alt+R` rules settings
- `Ctrl+Alt+M` metadata settings
- `Ctrl+Alt+A` Archive.org settings
- `Ctrl+Shift+Q` quit

Files page:
- `J` next file
- `K` previous file
- `C` toggle cover image
- `D` toggle do not rename

## Notes

- Archive Goblin ignores `.archive-goblin-project.json` during rename review and upload.
- SMB / CIFS shares can behave unpredictably for rename visibility on Linux. Local folders are more reliable.
- Upload currently targets new items and blocks identifiers that already exist.
- Automatic retry for partial upload failures is not implemented yet, because partial Archive.org uploads need careful recovery.
- The current application icon was picked randomly from `icon-icons.com`.
