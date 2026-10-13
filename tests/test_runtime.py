"""Execute the actual addon in LuaJIT with bounded Windows data-memory doubles."""
from pathlib import Path
import hashlib,json,os,re,struct,sys,tempfile
from lupa import luajit21
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'src/core.lua').read_bytes().replace(b'\r\n',b'\n')
FIXTURE=json.loads((ROOT/'tests/fixtures/native_2025.json').read_text())
BASE=0x180000000
Q=lambda n:struct.pack('<Q',n)
U=lambda n:struct.pack('<I',n)
F=lambda n:struct.pack('<f',n)

class Memory:
    def __init__(self):
        self.pages={};self.writes=[];self.protection={};self.fail=None;self.partial=None;self.deny=False
        self.restore_fail=0;self.reads=0
    def put(self,p,b):
        for i,v in enumerate(b):self.pages.setdefault((p+i)>>12,bytearray(4096))[(p+i)&4095]=v
    def read(self,p,n):
        self.reads+=1
        try:return bytes(self.pages[(p+i)>>12][(p+i)&4095] for i in range(n))
        except KeyError:return None
    def write(self,p,b):
        self.writes.append((p,b))
        if self.fail==p:self.fail=None;return False
        if self.partial==p:self.partial=None;self.put(p,b[:max(1,len(b)//2)]);return False
        self.put(p,b);return True
    def protect(self,p,v):
        if v==2 and self.restore_fail:self.restore_fail-=1;return 0
        self.protection[p>>12]=v;return 1
    def prot(self,p):return self.protection.get(p>>12,4)
    def query(self,p):
        start=p&~4095
        return struct.pack('<QQIIQIIII',start,start,4,0,4096,0x1000,32 if self.deny else self.prot(p),0x20000,0)

class Scenario:
    def __init__(self,cfg=None,bad_build=False,menu=False,loader_version=17,has_update=True):
        self.temp=tempfile.TemporaryDirectory();self.local=Path(self.temp.name)
        self.logs=self.local/'CowboyBingus/Helldivers2/Logs';self.logs.mkdir(parents=True)
        self.cfg_path=self.logs/'ReckoningGatling.cfg'
        if cfg is not None:self.cfg_path.write_text(cfg,encoding='utf8')
        self.mem=Memory();self.lua=luajit21.LuaRuntime(encoding=None);self.replace_failure=False
        dos=bytearray(4096);dos[:2]=b'MZ';struct.pack_into('<I',dos,60,0x100);dos[0x100:0x104]=b'PE\0\0'
        struct.pack_into('<I',dos,0x108,0 if bad_build else 0x6ab3b43f);struct.pack_into('<I',dos,0x150,0x4744000)
        self.mem.put(BASE,dos)
        for a,h in re.findall(rb"\{(0x[0-9a-f]+),'([0-9a-f]+)'\}",SOURCE):self.mem.put(BASE+int(a,16),bytes.fromhex(h.decode()))
        self.root=0x60000000;self.table=0x61000000;self.strat=0x20000000;self.row=self.table+704+11*192
        self.mem.put(BASE+0x346bf98,Q(self.root));self.mem.put(self.root+0xf12a80,Q(self.table))
        self.mem.put(self.table-28,struct.pack('<I4sIIIII',0xcdbc43d8,b'LDLD',1,0xcdbc43d8,5120,1,0))
        self.baseline=bytes.fromhex(FIXTURE['baseline_row_hex'])
        self.mem.put(self.table,bytes(5120));self.mem.put(self.table+13*16,bytes.fromhex('21c47a03917b252f')+U(11)+U(0))
        self.mem.put(self.row,self.baseline)
        raw=bytearray(400);struct.pack_into('<I',raw,0,4);struct.pack_into('<QQ',raw,0x98,0x40000000,1)
        self.mem.put(self.strat,raw);self.mem.put(0x40000000,bytes.fromhex('21c47a03917b252f'))
        self.mem.put(BASE+0x37cb600+4*8,Q(self.strat));self.mem.put(BASE+0x21d4aa0+4*8,Q(0x41000000))
        self.mem.put(0x41000000,b'OrbitalGatlingBarrage'+bytes(64))
        for pr in FIXTURE['projectiles']:
            t=pr['id'];p=0x58000000+t*4096;raw=bytes.fromhex(pr['record_hex'])
            self.mem.put(p,raw);self.mem.put(BASE+0x37c7670+t*8,Q(p))
        g=self.lua.globals();g[b'pyread']=lambda p,n:self.mem.read(int(p),int(n));g[b'pywrite']=lambda p,b:self.mem.write(int(p),bytes(b))
        g[b'pyquery']=lambda p:self.mem.query(int(p));g[b'pyprot']=lambda p:self.mem.prot(int(p))
        g[b'pyprotect']=lambda p,n,v:self.mem.protect(int(p),int(v));g[b'pyreplace']=self.replace
        g[b'localpath']=str(self.local).encode()
        self.lua.execute(b'''
          local real=require('ffi');local ffi={};for k,v in pairs(real)do ffi[k]=v end
          local k={GetCurrentProcess=function()return real.cast('void *',1)end,
            GetModuleHandleA=function()return real.cast('void *',0x180000000)end}
          k.ReadProcessMemory=function(_,p,b,n,c)local s=pyread(tonumber(real.cast('uintptr_t',p)),n)
            if not s then c[0]=0;return 0 end;real.copy(b,s,n);c[0]=n;return 1 end
          k.WriteProcessMemory=function(_,p,b,n,c)local ok=pywrite(tonumber(real.cast('uintptr_t',p)),real.string(b,n));c[0]=ok and n or 0;return ok and 1 or 0 end
          k.VirtualQuery=function(p,b,n)local s=pyquery(tonumber(real.cast('uintptr_t',p)));real.copy(b,s,n);return n end
          k.VirtualProtect=function(p,n,v,old)local a=tonumber(real.cast('uintptr_t',p));old[0]=pyprot(a);return pyprotect(a,n,v)end
          k.MoveFileExA=function(a,b,flags)assert(flags==9);return pyreplace(a,b)end
          local aliases={};for name,fn in pairs(k)do aliases['reckoninggatling_'..name]=fn end
          ffi.load=function()return aliases end
          local old=require;require=function(n)if n=='ffi' then return ffi end;return old(n)end
          local getenv=os.getenv;os.getenv=function(k)if k=='LOCALAPPDATA' then return localpath end;return getenv(k)end
          CowboyBingusModLoader={api=1,version=17};print=function()end;calls=0;update=function(dt,x)calls=calls+1;return dt,x,42 end
        ''')
        if loader_version is None:self.lua.execute(b'CowboyBingusModLoader=nil')
        else:self.lua.globals()[b'CowboyBingusModLoader'][b'version']=loader_version
        if not has_update:self.lua.execute(b'update=nil')
        if menu:self.load_menu()
        self.state=self.lua.eval(b'function(s)return assert(loadstring(s,"@mods/reckoning_gatling/core"))()end')(SOURCE)
    def replace(self,a,b):
        if self.replace_failure:return 0
        try:os.replace(os.fsdecode(a),os.fsdecode(b));return 1
        except OSError:return 0
    def tick(self):return self.lua.eval(b'function()return update(1.1,"preserved")end')()
    def cfg(self,s):self.cfg_path.write_text(s,encoding='utf8');self.tick()
    def bytes(self):return self.mem.read(self.row,192)
    def close(self):self.lua=None;self.temp.cleanup()
    def load_menu(self):
        self.lua.execute(b'''
          menu_state={values={reckoning_gatling_enabled=false},options={},order={},callbacks={},pending={},sets=0}
          local s=menu_state;local api={api=1,version=3}
          function api.register_option(id,spec)
            assert(not s.options[id]);s.options[id]=spec;s.order[#s.order+1]=id
            if s.values[id]==nil then s.values[id]=spec.default end;return true end
          function api.get(id)return s.values[id]end
          function api.set(id,value)s.values[id]=value;s.pending[id]=nil;s.sets=s.sets+1;return true end
          function api.on_change(id,fn)assert(not s.callbacks[id]);s.callbacks[id]=fn;return true end
          function menu_apply(id,value)s.values[id]=value;return s.callbacks[id](value)end
          ModOptionsMenu=api
        ''')

def run_case(name,fn):
    s=Scenario()
    try:fn(s);print('PASS',name)
    finally:s.close()

def native_sequence(s):
    assert s.tick()==(1.1,b'preserved',42) and s.state[b'phase']==b'active'
    expected=bytearray(s.baseline)
    for ch in FIXTURE['delta']['changes']:
        data=bytes.fromhex(ch['data']);expected[ch['offset']:ch['offset']+len(data)]=data
    assert s.bytes()==bytes(expected)
    assert s.mem.writes==[(s.row+64,bytes(expected[64:96]))]
    for _ in range(4):s.tick()
    assert len(s.mem.writes)==1
    assert struct.unpack_from('<I',s.bytes(),24)[0]==4
    assert all(x['damage_info_id']==218 for x in FIXTURE['projectiles'])
    explosion=next(x for x in FIXTURE['explosions'] if x['id']==108)
    assert struct.unpack_from('<I',bytes.fromhex(explosion['record_hex']),96)[0]==2

def toggle(s):
    s.tick();s.cfg('enabled=0\n');assert s.bytes()==s.baseline and s.state[b'phase']==b'disabled'
    s.cfg('enabled=1\n');assert s.state[b'phase']==b'active'
    assert s.state[b'disable']() is True;s.tick();assert s.bytes()==s.baseline

def foreign_writer(s):
    s.tick();s.mem.put(s.row+64,U(99));current=s.bytes();s.tick()
    assert s.state[b'phase']==b'stopped' and s.bytes()==current

def stale_pointer(s):
    s.tick();n=len(s.mem.writes);s.mem.put(s.root+0xf12a80,Q(0x62000000));s.tick()
    assert s.state[b'phase']==b'stopped' and len(s.mem.writes)==n

def partial_failure(s):
    s.mem.partial=s.row+64;s.tick();assert s.state[b'phase']==b'stopped' and s.bytes()==s.baseline

def denied(s):
    s.mem.deny=True;s.tick();assert s.state[b'phase']==b'stopped' and s.bytes()==s.baseline and not s.mem.writes

def readonly(s):
    s.mem.protection[s.row>>12]=2;s.tick();assert s.state[b'phase']==b'active' and s.mem.prot(s.row)==2
    s.state[b'disable']();s.tick();assert s.bytes()==s.baseline and s.mem.prot(s.row)==2

def protection_failure(s):
    s.mem.protection[s.row>>12]=2;s.mem.restore_fail=1;s.tick()
    assert s.state[b'phase']==b'stopped' and s.bytes()==s.baseline and s.mem.prot(s.row)==2

def malformed(s):
    s.mem.put(s.row+4,U(8));s.tick();assert s.state[b'phase']==b'stopped' and not s.mem.writes

def header(s):
    s.mem.put(s.table-12,U(6000));s.tick();assert s.state[b'phase']==b'stopped' and not s.mem.writes

def missing_payload(s):
    s.mem.put(s.root+0xf12a80,Q(0));s.tick();assert s.state[b'phase']==b'waiting' and not s.mem.writes
    s.mem.put(s.root+0xf12a80,Q(s.table));s.tick();assert s.state[b'phase']==b'active'

def projectile_guard(s):
    s.mem.put(0x58000000+72*4096+144,U(0));s.tick()
    assert s.state[b'phase']==b'stopped' and not s.mem.writes

def identity_guard(s):
    s.mem.put(s.strat+0x98,Q(0x40001000));s.tick()
    assert s.state[b'phase']==b'stopped' and not s.mem.writes

def signature_guard(s):
    s.mem.put(BASE+0x503dcf,b'badcode');s.tick()
    assert s.state[b'phase']==b'stopped' and not s.mem.writes

def restore_partial(s):
    s.tick();s.mem.partial=s.row+64;s.cfg('enabled=0\n')
    assert s.state[b'phase']==b'stopped' and s.bytes()==s.baseline

def invalid_config(s):
    s.tick();s.cfg('enabled=no\n');assert s.state[b'phase']==b'active'
    s.cfg('# incomplete file\n');assert s.state[b'phase']==b'active'
    s.cfg('enabled=0\nlanguage=invalid\n');assert s.state[b'phase']==b'active' and s.state[b'config'][b'language']==b'zh'

def duplicate_init(s):
    old=s.lua.globals()[b'update']
    again=s.lua.eval(b'function(s)return assert(loadstring(s))()end')(SOURCE)
    assert s.lua.eval(b'function(a,b)return rawequal(a,b)end')(again,s.state)
    assert s.lua.eval(b'function(a)return rawequal(a,update)end')(old)

def menu_case():
    s=Scenario(menu=True)
    try:
        s.tick();m=s.lua.globals()[b'menu_state']
        assert len(m[b'order'])==2 and m[b'order'][1]==b'reckoning_gatling_language' and m[b'order'][2]==b'reckoning_gatling_enabled'
        assert m[b'values'][b'reckoning_gatling_enabled'] is True and m[b'values'][b'reckoning_gatling_language']==1
        descriptions={key:m[b'options'][b'reckoning_gatling_'+key][b'description'] for key in (b'language',b'enabled')}
        for description in descriptions.values():
            assert len(description.decode('utf8'))<=400
        assert '中英同显' in descriptions[b'language'].decode('utf8') and b'Chinese and English' in descriptions[b'language']
        assert '原生清算节' in descriptions[b'enabled'].decode('utf8') and b'native Reckoning' in descriptions[b'enabled']
        s.lua.execute(b'menu_state.pending.reckoning_gatling_enabled=false')
        count=m[b'sets'];s.tick();assert m[b'sets']==count and m[b'pending'][b'reckoning_gatling_enabled'] is False
        writes=len(s.mem.writes)
        for choice,label in ((2,b'Enable'),(1,'启用'.encode('utf8')),(2,b'Enable')):
            assert s.lua.globals()[b'menu_apply'](b'reckoning_gatling_language',choice) is True;s.tick()
            assert len(s.mem.writes)==writes and m[b'options'][b'reckoning_gatling_enabled'][b'label']()==label
            assert all(m[b'options'][b'reckoning_gatling_'+key][b'description']==description for key,description in descriptions.items())
        assert s.lua.globals()[b'menu_apply'](b'reckoning_gatling_enabled',False) is True
        s.tick();assert s.bytes()==s.baseline;saved=s.cfg_path.read_text();assert saved=='language=en\nenabled=0\n'
        s.replace_failure=True;result=s.lua.globals()[b'menu_apply'](b'reckoning_gatling_enabled',True)
        assert result[0] is False;s.tick();assert s.state[b'phase']==b'disabled'
        result=s.lua.globals()[b'menu_apply'](b'reckoning_gatling_language',1)
        assert result[0] is False and s.state[b'config'][b'language']==b'en' and s.cfg_path.read_text()==saved
        assert s.lua.globals()[b'menu_apply'](b'reckoning_gatling_language',3)[0] is False
    finally:s.close()
    s=Scenario(cfg=saved,menu=True)
    try:s.tick();assert s.state[b'phase']==b'disabled' and not s.mem.writes and s.state[b'config'][b'language']==b'en'
    finally:s.close()
    s=Scenario(cfg='enabled=0\n',menu=True)
    try:s.tick();assert s.state[b'phase']==b'disabled' and s.state[b'config'][b'language']==b'zh' and not s.mem.writes
    finally:s.close()
    print('PASS menu bilingual descriptions, language/legacy config, Apply, pending edits, persistence and save failure')

def external_menu():
    path=os.environ.get('HD2_MOD_OPTIONS_MENU_SOURCE')
    if not path:return None
    source=Path(path).read_bytes()
    def module(name):
        marker=b'mom_files.'+name+b' = function(...)';start=source.index(marker)
        return source[start:source.index(b'\nmom_files.',start+len(marker))]
    s=Scenario()
    try:
        s.lua.execute(br'''
          local T={upper=string.upper,check=function()return true end,
            length=function(s)local _,n=s:gsub('[^\128-\191]','');return n end}
          mom={state={mods={},options={},option_count=0,values={},callbacks={},revision=0,
            saved={reckoning_gatling_enabled='false'},pending={},pending_count=0,
            refused={},refused_count=0,queued={}},translation={T=T,tr=function(k)return k end},
            note=function()end,TEXT_TEMPLATE=123,MAX_MODS=112,MAX_ROWS=32,descriptor=function()return {},{}end}
          mom_files={}
        '''+module(b'options')+b'\n'+module(b'api')+b'''
          mom_files.options(mom);mom_files.api(mom);ModOptionsMenu=mom.api
        ''')
        s.tick();mom=s.lua.globals()[b'mom'];api=mom[b'api'];state=mom[b'state']
        assert s.state[b'menu_registered'] is True and api[b'version']==3
        assert len(state[b'mods'])==1 and len(state[b'mods'][1][b'order'])==2
        descriptions={key:state[b'options'][b'reckoning_gatling_'+key][b'description'] for key in (b'language',b'enabled')}
        writes=len(s.mem.writes)
        for choice,label in ((2,b'Enable'),(1,'启用'.encode('utf8'))):
            mom[b'set_pending'](b'reckoning_gatling_language',choice)
            assert mom[b'apply_pending']()==1;s.tick();mom[b'translation'][b'refresh']()
            assert len(s.mem.writes)==writes and len(state[b'mods'])==1 and len(state[b'mods'][1][b'order'])==2
            assert state[b'options'][b'reckoning_gatling_enabled'][b'label']==label
            assert all(state[b'options'][b'reckoning_gatling_'+key][b'description']==description for key,description in descriptions.items())
        mom[b'set_pending'](b'reckoning_gatling_enabled',False);s.tick()
        assert state[b'pending'][b'reckoning_gatling_enabled'] is False
        assert mom[b'apply_pending']()==1;s.tick();assert s.bytes()==s.baseline
        mom[b'set_pending'](b'reckoning_gatling_enabled',True)
        assert mom[b'apply_pending']()==1;s.tick();assert s.state[b'phase']==b'active'
        assert len(state[b'callbacks'][b'reckoning_gatling_enabled'])==1
        print('PASS actual external menu API 1 / version 3 bilingual text, language refresh, registration and Apply')
        return {'version':3,'source_sha256':hashlib.sha256(source).hexdigest(),
            'scope':'actual API/options modules; native UI descriptor and text service mocked; no in-game rendering'}
    finally:s.close()

def package_checks():
    sys.path.insert(0,str(ROOT/'tools'));from build import patch,murmur64,RESOURCE,fire_package
    archive=patch(SOURCE);magic,nt,nf,_=struct.unpack_from('<4I',archive)
    assert (magic,nt,nf)==(0xf0000011,2,2)
    entries={}
    for i in range(nf):
        r=struct.unpack_from('<7Q6I',archive,72+nt*32+i*80)
        assert r[2]%16==0 and r[2]+r[7]<=len(archive)
        entries[r[0]]=(r[1],archive[r[2]:r[2]+r[7]])
    kind,lua=entries[murmur64(RESOURCE.encode())]
    assert kind==0xa14e8dfa2cd117e2 and struct.unpack_from('<II',lua)==(len(SOURCE),2)
    assert lua[8:]==SOURCE and SOURCE.startswith(b'-- HD2-Addon: '+RESOURCE.encode()+b'\n')
    kind,pkg=entries[0x7d72a031b0b3c618];assert kind==0xad9c6d9ed1e5e77a and pkg==fire_package()
    fixture=json.loads((ROOT/'tests/fixtures/packages_build25480438.json').read_text())
    items=set(struct.iter_unpack('<QQ',pkg[16:]))
    for key in ('base','fire_support'):
        f=fixture[key];raw=bytes.fromhex(f['header_hex'])+b''.join(struct.pack('<QQ',int(t,16),int(n,16)) for t,n in f['entries'])
        assert hashlib.sha256(raw).hexdigest()==f['sha256']
        assert {(int(t,16),int(n,16)) for t,n in f['entries']}<=items
    assert struct.unpack_from('<I',pkg,8)[0]==len(items)
    assert pkg[:8]==bytes.fromhex(fixture['base']['header_hex'])[:8]
    assert pkg[12:16]==bytes.fromhex(fixture['base']['header_hex'])[12:16]
    print('PASS archive discovery declaration, exact Lua and native dependency union')
    return {'dependency_count':len(items),'added_count':len(items)-len(fixture['base']['entries']),
        'sha256':hashlib.sha256(pkg).hexdigest()}

def main():
    cases=[native_sequence,toggle,foreign_writer,stale_pointer,partial_failure,denied,readonly,
        protection_failure,malformed,header,missing_payload,projectile_guard,identity_guard,
        signature_guard,restore_partial,invalid_config,duplicate_init]
    for fn in cases:run_case(fn.__name__,fn)
    s=Scenario(bad_build=True)
    try:s.tick();assert s.state[b'phase']==b'stopped' and not s.mem.writes
    finally:s.close()
    print('PASS unsupported build')
    for version in (None,16):
        s=Scenario(loader_version=version)
        try:assert s.state[b'phase']==b'stopped' and not s.mem.writes
        finally:s.close()
    print('PASS missing and old loader rejection')
    s=Scenario(has_update=False)
    try:assert s.state[b'phase']==b'stopped' and not s.mem.writes
    finally:s.close()
    print('PASS missing callback rejection')
    menu_case();provider=external_menu();package=package_checks()
    identity=json.loads((ROOT/'tools/identity.json').read_text())
    report={'status':'OFFLINE_PASSED','version':identity['version'],'game_build':25480438,
        'source_sha256':hashlib.sha256(SOURCE).hexdigest(),'test_groups':len(cases)+5+(1 if provider else 0),
        'ingame_tested':False,'multiplayer_tested':False,'external_menu_verification':provider,
        'package':package,'fixture_origin':FIXTURE['origin'],
        'policy':{'projectile_slots':[72,254,254,254,0,0,0,0],'rounds_per_salvo':60,'base_salvos':4,
            'round_interval_seconds':0.045,'spread_field':7,'current_damage':True,'current_upgrades':True}}
    (ROOT/'validation').mkdir(exist_ok=True)
    (ROOT/'validation/offline.json').write_text(json.dumps(report,indent=2),encoding='utf8')

if __name__=='__main__':main()
