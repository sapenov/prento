#!/usr/bin/env python3
"""Verify provided QA payloads against MANIFEST.sha256 after extraction."""
import argparse
import hashlib
from pathlib import Path
import sys

def verify(root, *, strict=False):
    root=Path(root).resolve()
    manifest=root/'MANIFEST.sha256'
    seen=set()
    for line in manifest.read_text().splitlines():
        digest,name=line.split('  ',1)
        relative=Path(name)
        if (len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest)
                or relative.is_absolute() or '..' in relative.parts or name in seen):
            raise ValueError('invalid or duplicate manifest entry')
        path=root/relative
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('missing/unsafe payload: '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('checksum mismatch: '+name)
        seen.add(name)
    if not seen:
        raise ValueError('empty QA manifest')
    if strict:
        actual={path.relative_to(root).as_posix() for path in root.rglob('*')
                if path.is_file() or path.is_symlink()}
        extra=actual-seen-{'MANIFEST.sha256'}
        if extra:
            raise ValueError('unlisted files: '+', '.join(sorted(extra)))
    return len(seen)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',nargs='?',default='.')
    parser.add_argument('--strict',action='store_true',help='Also reject unlisted files; use before building a fresh extraction')
    args=parser.parse_args()
    try:
        count=verify(args.root,strict=args.strict)
        print(f'Verified {count} payload checksums. This detects changes, not publisher identity.')
    except (OSError,ValueError) as error:
        raise SystemExit(str(error))
