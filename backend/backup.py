#!/usr/bin/env python3
"""Consistent private SQLite + immutable image backups; restore into an empty folder."""
import argparse
import json
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

def create_backup(database: Path, uploads: Path, destination: Path) -> Path:
    if not database.is_file(): raise ValueError('Database not found')
    destination.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    target=destination/f'kosmik-{stamp}.zip'
    temporary=target.with_suffix('.partial')
    try:
        with tempfile.TemporaryDirectory() as scratch:
            snapshot=Path(scratch)/'kosmik.db'
            with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(snapshot)) as dest:
                source.backup(dest)
                if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Backup integrity check failed')
            with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot,'data/kosmik.db')
                for image in uploads.glob('*'):
                    if image.is_file() and not image.is_symlink(): archive.write(image,'uploads/'+image.name)
                archive.writestr('manifest.json',json.dumps({'version':1,'createdAt':datetime.now(timezone.utc).isoformat()}))
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target

def restore_backup(archive: Path, destination: Path):
    if destination.exists() and any(destination.iterdir()): raise ValueError('Restore destination must be empty; never overwrite a live database')
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            p=Path(member.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in member.filename or ':' in member.filename: raise ValueError('Unsafe backup path')
            if member.filename not in ('manifest.json','data/kosmik.db') and not (len(p.parts)==2 and p.parts[0]=='uploads'): raise ValueError('Unexpected backup entry')
        if 'data/kosmik.db' not in source.namelist(): raise ValueError('Database missing from backup')
        destination.mkdir(parents=True,exist_ok=True)
        source.extractall(destination)
    with closing(sqlite3.connect(destination/'data/kosmik.db')) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Restored database is invalid')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore',type=Path)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    if args.restore:
        if not args.destination: parser.error('--destination is required for restore')
        restore_backup(args.restore,args.destination)
        print('Restored. Stop the application before pointing its data/upload directories to this folder.')
    else:
        from server import DB,UPLOADS,DATA
        print(create_backup(DB,UPLOADS,args.destination or DATA/'backups'))

