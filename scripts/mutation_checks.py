#!/usr/bin/env python3
"""Build three temporary intentional defects; prove scheduling tests reject them.

The repository source is never changed. This is a test-sensitivity check, not a
benchmark and not a production build configuration.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def replace_once(text,old,new):
    if text.count(old)!=1:
        raise RuntimeError("mutation location changed; inspect the source before updating this check")
    return text.replace(old,new,1)

def main():
    with tempfile.TemporaryDirectory(prefix="prento-mutation-") as tmp:
        temp=Path(tmp)
        shutil.copytree(ROOT/'include',temp/'include')
        shutil.copytree(ROOT/'src',temp/'src')
        original=(temp/'src/collector.cpp').read_text()
        grant='if(h.credit){h.type=Grant;send_header(fd,h,timeout);h.type=Announce;}'
        gate='if(!gate.acquire(item,timeout))'
        defects=[
            ('disabled-admission-priority',replace_once(original,'admission(priority,quota)','admission(false,quota)'),
             'later_critical','Lists differ'),
            ('disabled-service-priority',replace_once(original,'service(priority,quota)','service(false,quota)'),
             'ready_critical','Lists differ'),
            ('premature-grant',replace_once(replace_once(original,grant,''),gate,grant+'\n                    '+gate),
             'credit_is_withheld','not raised'),
        ]
        for name,source,selector,expected in defects:
            (temp/'src/collector.cpp').write_text(source)
            binary=temp/name
            command=['g++','-std=c++20','-O1','-pthread','-I'+str(temp/'include'),
                     *[str(temp/'src'/name) for name in ('main.cpp','collector.cpp','producer.cpp','sink.cpp')],'-o',str(binary)]
            subprocess.run(command,check=True)
            result=subprocess.run(['python3','-m','unittest','discover','-s','tests','-p','test_*.py','-k',selector,'-v'],
                                  cwd=ROOT,env=dict(os.environ,PRENTO_BINARY=str(binary)),capture_output=True,text=True,timeout=30)
            print(f'=== {name}: test exit {result.returncode} ===',flush=True)
            print(result.stdout+result.stderr,flush=True)
            if result.returncode==0 or expected not in result.stdout+result.stderr:
                raise RuntimeError('test did not reject the intended defect for the expected reason: '+name)
        print('All three intentional defects were rejected; original source was unchanged.')

if __name__=='__main__':
    main()
