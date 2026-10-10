"""Read-only fingerprint verification. Packed on-disk code is not runtime code."""
from pathlib import Path
import argparse,hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1]
DLL_SHA256='2e2c3b7c2500646dadd5f2b4c6e0504dbb7e7896139f64cddc0d1813c718f51e'
EXE_SHA256='f5fee03dcfdb2e553a4752c283590950ac13316b376d8196aa556ff0400d5f06'
LOADER_SHA256='950a1b29c70a5bf3f94f5b6a154a3935d5c354be20cb7191d803c4c7ed9191e2'

def verify(game,loader):
    dll=(game/'data/game/game.dll').read_bytes()
    exe=(game/'bin/helldivers2.exe').read_bytes()
    assert hashlib.sha256(dll).hexdigest()==DLL_SHA256,'Unsupported game.dll fingerprint'
    assert hashlib.sha256(exe).hexdigest()==EXE_SHA256,'Unsupported EXE fingerprint'
    pe=struct.unpack_from('<I',dll,60)[0]
    assert struct.unpack_from('<I',dll,pe+8)[0]==0x6ab3b43f
    assert struct.unpack_from('<I',dll,pe+80)[0]==0x4744000
    b=(loader/'data/9ba626afa44a3aa3.patch_0').read_bytes()
    assert hashlib.sha256(b).hexdigest()==LOADER_SHA256,'Local loader differs from inspected v18'
    nt,nf=struct.unpack_from('<II',b,4);assert (nt,nf)==(1,1)
    r=struct.unpack_from('<7Q6I',b,72+nt*32)
    assert r[:2]==(0x7251fdd9bb62480a,0xa14e8dfa2cd117e2)
    body=b[r[2]+8:r[2]+r[7]]
    # LuaJIT bytecode table constants: string tag 5+length, integer tag 3.
    # Confirms the encoded provider contract without executing its bytecode.
    assert b'\x08api\x03\x01' in body and b'\x0cversion\x03\x11' in body
    assert b'HD2%-Addon:' in body and b'CowboyBingusModLoader' in body
    result={'game_build':25480438,'game_dll_sha256':DLL_SHA256,'game_exe_sha256':EXE_SHA256,
        'loader_archive_sha256':LOADER_SHA256,'loader_api':1,'loader_internal_version':17,
        'loader_bytecode_executed':False,'runtime_anchors_verified_live':False,
        'scope':'Current installed file hashes and PE identity; provider encoded constants. Runtime signatures checked by addon at startup; DLL is packed on disk.'}
    (ROOT/'validation').mkdir(exist_ok=True)
    (ROOT/'validation/environment.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('PASS installed game fingerprints, PE identity and v18 encoded API contract')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--game-dir',type=Path,required=True)
    parser.add_argument('--loader-dir',type=Path,required=True)
    args=parser.parse_args();verify(args.game_dir,args.loader_dir)
