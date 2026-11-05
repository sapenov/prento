#!/usr/bin/env python3
"""Package source, QA instructions/logs and selected raw evidence; no binaries."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES=('README.md','LICENSE','AGENTS.md','DESIGN.md','Makefile','CMakeLists.txt','Dockerfile',
            'compose.yaml','.gitignore','.dockerignore','.gitattributes')
SOURCE_DIRS=('src','include','tests','scripts','docs','deploy','.github','qa')

def write_bundle(root,files,output):
    root=Path(root).resolve()
    output=Path(output).resolve()
    payload={}
    for name in sorted(set(files)):
        relative=Path(name)
        path=root/relative
        if relative.as_posix() in ('BUNDLE.json','MANIFEST.sha256'):
            raise ValueError('reserved bundle metadata name: '+name)
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError('missing or unsafe bundle payload: '+name)
        if path.resolve()==output:
            raise ValueError('cannot include output archive in itself')
        payload[relative.as_posix()]=path.read_bytes()
    if not payload:
        raise ValueError('empty QA bundle')
    payload['BUNDLE.json']=(json.dumps({
        'format_version':2,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_payload_files':len(payload),'payload_files':len(payload)+1,
        'archive_files':len(payload)+2,'purpose':'QA source and evidence bundle',
        'integrity':'SHA-256 detects changed files; it is not a publisher signature',
        'excluded':['.git','compiled binaries','caches','unselected local scratch runs']
    },indent=2)+'\n').encode()
    manifest=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in sorted(payload.items()))
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(payload.items()):
            archive.writestr('prento/'+name,data)
        archive.writestr('prento/MANIFEST.sha256',manifest)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n')
    return digest

def collect(root,results):
    root=Path(root).resolve()
    files=list(ROOT_FILES)
    for name in (*SOURCE_DIRS,*results):
        directory=root/name
        if not directory.is_dir() or not directory.resolve().is_relative_to(root) or directory.is_symlink():
            raise ValueError('missing/unsafe source or evidence directory: '+name)
        for path in directory.rglob('*'):
            if '__pycache__' in path.parts or path.suffix=='.pyc':
                continue
            if path.is_symlink():
                raise ValueError('symlink in bundle input: '+str(path))
            if path.is_file():
                files.append(path.relative_to(root).as_posix())
    return files

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',action='append',required=True,help='Evidence directory relative to project; repeat to include a baseline')
    parser.add_argument('--output',default='dist/prento-qa.zip')
    args=parser.parse_args()
    digest=write_bundle(ROOT,collect(ROOT,args.results),Path(args.output))
    print(f'{args.output}: SHA-256 {digest}')

if __name__=='__main__':
    main()
