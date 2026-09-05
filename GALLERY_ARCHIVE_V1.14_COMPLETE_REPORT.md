# Kosmik Circles V1.14 — Gallery Archive

## What changed
The public Gallery is no longer a five-image gallery. It is now an event/night archive made of folders.

Each folder contains:
- title
- date
- location
- venue
- description
- cover image
- photos and videos
- individual download links

## Admin
The Admin now has a Night archive folders section where the operator can:
- create folders
- edit metadata
- upload/change a cover image
- upload multiple photos/videos
- delete individual media
- delete an entire folder and its media

## Supported archive media
Images:
- PNG
- JPEG
- WebP
- GIF

Video:
- MP4
- WebM
- MOV
- AVI

Maximum archive media file size: 1 GB.

## Public behavior
Gallery landing page → night folder → media list → view/download.
Folder navigation uses a URL hash (`#album=<id>`) so an archive can be reopened/shared.

## Backward compatibility
The former `gallery` database table is retained for rollback/data preservation, but the public Gallery no longer renders those legacy five slots.

## Test performed
A clean isolated runtime was used to verify:
- album creation
- image media upload
- video media upload
- public album listing
- album detail
- media streaming
- media download with attachment header
- media deletion
- album deletion
- Gallery HTML availability

Result: PASS.
