"""Build a plaintext v18 addon with native resource dependency references."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
IDENTITY=json.loads((ROOT/'tools/identity.json').read_text())
VERSION=IDENTITY['version']
RESOURCE=IDENTITY['resource']

def murmur64(data):
    mask=(1<<64)-1;m=0xc6a4a7935bd1e995;h=len(data)*m&mask
    for i in range(0,len(data)//8*8,8):
        k=int.from_bytes(data[i:i+8],'little')*m&mask;k^=k>>47;k=k*m&mask;h=(h^k)*m&mask
    tail=data[len(data)//8*8:]
    if tail:h=(h^int.from_bytes(tail,'little'))*m&mask
    h^=h>>47;h=h*m&mask;return h^(h>>47)

def fire_package():
    f=json.loads((ROOT/'tests/fixtures/packages_build25480438.json').read_text())
    items=sorted({tuple(x) for x in f['base']['entries']+f['fire_support']['entries']})
    header=bytearray.fromhex(f['base']['header_hex']);struct.pack_into('<I',header,8,len(items))
    return bytes(header)+b''.join(struct.pack('<QQ',int(t,16),int(n,16)) for t,n in items)

def patch(source):
    resources=[(murmur64(RESOURCE.encode()),0xa14e8dfa2cd117e2,struct.pack('<II',len(source),2)+source),
               (0x7d72a031b0b3c618,0xad9c6d9ed1e5e77a,fire_package())]
    kinds=sorted({r[1] for r in resources});offset=(72+len(kinds)*32+len(resources)*80+15)&~15
    entries=[];payload=bytearray()
    for name,kind,body in resources:
        entries.append(struct.pack('<7Q6I',name,kind,offset+len(payload),0,0,0,0,len(body),0,0,16,16,0))
        payload.extend(body);payload.extend(bytes((-len(payload))%16))
    size=max(4096,offset+len(payload))
    header=struct.pack('<4I',0xf0000011,len(kinds),len(resources),0)+bytes(16)+struct.pack('<Q',size)+bytes(32)
    types=b''.join(struct.pack('<IIQQII',0,0,k,sum(r[1]==k for r in resources),16,16) for k in kinds)
    tables=header+types+b''.join(entries)
    return tables+bytes(offset-len(tables))+payload+bytes(size-offset-len(payload))

def manifest():
    return {'Version':1,'Guid':IDENTITY['guid'],
        'Name':'清算节燃烧轨道加特林 / Reckoning Gatling v'+VERSION,
        'Description':'原生清算节燃烧弹序，落点留地火；保留当前弹体直击伤害、冷却与舰船升级。MODS 菜单提供中文/英文选择，介绍始终中英同显。需要 Bingus Shared Loader v18 / API1 和 ModOptionsMenu API1 / version2 或更新。支持 Steam build 25480438。菜单更新仅离线验证；用户于 2026-10-10 对 v0.1.0 实机测试反馈无问题。联机兼容性未确认。 / Native Reckoning incendiary sequence with ground fire; keeps current direct-hit damage, cooldown and ship upgrades. Chinese/English menu choices always show bilingual descriptions. Requires Bingus Shared Loader v18 / API1 and ModOptionsMenu API1 / version2 or newer. Steam build 25480438. Menu update tested offline; v0.1.0 passed user-reported gameplay on 2026-10-10. Multiplayer unconfirmed.',
        'Options':[{'Name':'清算节燃烧轨道加特林 / Reckoning Gatling','Description':'Esc → MODS 中应用启用开关和语言选择。默认开启、默认中文，介绍始终中英同显。 / Apply Enable and Language in Esc → MODS. Enabled by default; Chinese labels by default; descriptions always bilingual.','Include':['Core']}]}

def build():
    subprocess.run([sys.executable,str(ROOT/'tests/test_runtime.py')],cwd=ROOT,check=True)
    source=(ROOT/'src/core.lua').read_bytes().replace(b'\r\n',b'\n')
    report=json.loads((ROOT/'validation/offline.json').read_text())
    assert report['source_sha256']==hashlib.sha256(source).hexdigest()
    env_path=ROOT/'validation/environment.json'
    if env_path.exists():report['environment_verification']=json.loads(env_path.read_text())
    name='Core/9ba626afa44a3aa3.patch_0'
    files={name:patch(source),name+'.stream':b'',name+'.gpu_resources':b'',
        'manifest.json':json.dumps(manifest(),ensure_ascii=True,indent=2).encode('ascii'),
        'VALIDATION.json':json.dumps(report,indent=2).encode('utf8'),
        'USER_TEST_FEEDBACK.json':(ROOT/'tests/fixtures/user_test_feedback.json').read_bytes()}
    output=ROOT/'dist'/f'ReckoningGatling_v{VERSION}.zip';output.parent.mkdir(exist_ok=True)
    tmp=output.with_suffix('.zip.tmp')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for key,value in sorted(files.items()):
            info=zipfile.ZipInfo(key,(2026,10,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,value)
    with zipfile.ZipFile(tmp) as z:
        assert z.testzip() is None
        assert all(z.read(k)==v for k,v in files.items())
    tmp.replace(output);(ROOT/'manifest.json').write_bytes(files['manifest.json'])
    print(output);print('SHA256',hashlib.sha256(output.read_bytes()).hexdigest());return output

if __name__=='__main__':build()
