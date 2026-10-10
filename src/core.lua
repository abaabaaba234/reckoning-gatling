-- HD2-Addon: mods/reckoning_gatling/core
-- Native incendiary gatling delta; preserves current damage, cooldown and ship upgrades.
local previous=rawget(_G,'ReckoningGatling')
if previous then return previous end
local S={version='0.1.0',phase='waiting',elapsed=0,owned={},writes=0,cleanup_attempts=0}
rawset(_G,'ReckoningGatling',S)
local ffi=require('ffi')
local kernel={}
for _,d in ipairs{
    {'GetCurrentProcess','void *','(void)'},
    {'GetModuleHandleA','void *','(const char *)'},
    {'ReadProcessMemory','int','(void *, const void *, void *, size_t, size_t *)'},
    {'WriteProcessMemory','int','(void *, void *, const void *, size_t, size_t *)'},
    {'VirtualQuery','size_t','(const void *, void *, size_t)'},
    {'VirtualProtect','int','(void *, size_t, uint32_t, uint32_t *)'},
    {'MoveFileExA','int','(const char *, const char *, uint32_t)'},
} do
    local alias='reckoninggatling_'..d[1]
    ffi.cdef(d[2]..' '..alias..d[3]..' __asm__("'..d[1]..'");')
    kernel[d[1]]=ffi.load('kernel32')[alias]
end
local folder=(os.getenv('LOCALAPPDATA') or '')..'\\CowboyBingus\\Helldivers2\\Logs\\'
local config_path=folder..'ReckoningGatling.cfg'
local first=true
local function log(message)
    S.status=message;pcall(print,'[ReckoningGatling] '..message)
    local f=io.open(folder..'ReckoningGatling.log',first and 'w' or 'a')
    if f then first=false;f:write(os.date('%H:%M:%S ')..message..'\n');f:close() end
end
local config={enabled=1};S.config=config
local last_config,menu,menu_blocked
local function save(value)
    local text='enabled='..value..'\n';local tmp=config_path..'.tmp'
    local f,reason=io.open(tmp,'wb');if not f then return false,reason end
    local written,why=f:write(text);local flushed=f:flush();local closed=f:close()
    if not written or not flushed or not closed then os.remove(tmp);return false,why or 'config I/O failed' end
    if kernel.MoveFileExA(tmp,config_path,9)==0 then os.remove(tmp);return false,'config replace failed' end
    last_config=text;return true
end
local function read_config()
    local f=io.open(config_path,'rb')
    if not f then if last_config==nil then save(config.enabled)end;return end
    local text=f:read('*a');f:close();if not text or text==last_config then return end
    local next_value
    for line in text:gmatch('[^\r\n]+')do
        local key,value=line:gsub('^\239\187\191',''):gsub('#.*$',''):match('^%s*([%w_]+)%s*=%s*(.-)%s*$')
        if key=='enabled' then
            if value~='0' and value~='1' then last_config=text;log('Invalid enabled value; retaining config');return end
            next_value=tonumber(value)
        end
    end
    last_config=text;if next_value~=nil then config.enabled=next_value end
end
local function change(value)
    if S.phase=='stopped' then return false,S.stop_reason end
    if type(value)~='boolean' then return false,'expected boolean' end
    value=value and 1 or 0;if config.enabled==value then return true end
    local ok,why=save(value);if not ok then return false,why end
    config.enabled=value;S.elapsed=1;return true
end
local function checked(ok,why)if ok~=true then error(tostring(why or 'menu API failed'),0)end end
local function menu_step()
    if menu_blocked then return end
    local ok,why=pcall(function()
        if not menu then
            local api=rawget(_G,'ModOptionsMenu');if not api then return end
            if api.api~=1 or (tonumber(api.version) or 0)<2 then error('Requires menu API 1 / version 2 or newer',0)end
            for _,method in ipairs{'register_option','on_change','get','set'}do
                if type(api[method])~='function' then error('Missing menu method '..method,0)end
            end
            local spec={type='toggle',mod='清算节燃烧轨道加特林',label='启用',default=config.enabled==1,
                description='使用原生清算节燃烧弹序，落点留地火。保留当前伤害、冷却和舰船升级。只影响之后创建的火力网；关闭会恢复本模组拥有的配置。'}
            if api.version>=3 then spec.mod_id='reckoning_gatling' end
            checked(api.register_option('reckoning_gatling_enabled',spec))
            checked(api.on_change('reckoning_gatling_enabled',change))
            menu=api;S.menu_registered=true;log('MODS menu registered')
        end
        local value=config.enabled==1
        if menu.get('reckoning_gatling_enabled')~=value then checked(menu.set('reckoning_gatling_enabled',value))end
    end)
    if not ok then menu_blocked=tostring(why);log('Menu unavailable: '..menu_blocked)end
end
local process=kernel.GetCurrentProcess()
local buffer=ffi.new('uint8_t[512]');local count=ffi.new('size_t[1]')
local function read(p,n)
    if not p or p<0x10000 or n<1 or n>512 or p+n>0x7fffffff0000 then return nil end
    count[0]=0
    if kernel.ReadProcessMemory(process,ffi.cast('const void *',p),buffer,n,count)==0 or tonumber(count[0])~=n then return nil end
    return ffi.string(buffer,n)
end
local function u32(s,o)
    local a,b,c,d=s:byte(o+1,o+4);return a and d and a+b*256+c*65536+d*16777216 or nil
end
local function u64(s,o)return u32(s,o)+u32(s,o+4)*4294967296 end
local function ptr(p)local b=read(p,8);return b and u64(b,0)end
local function unhex(s)return(s:gsub('..',function(x)return string.char(tonumber(x,16))end))end
local function uint(n)return ffi.string(ffi.new('uint32_t[1]',n),4)end
local function float(n)return ffi.string(ffi.new('float[1]',n),4)end
local mbi=ffi.new('uint8_t[48]');local old_protection=ffi.new('uint32_t[1]')
local function write(p,bytes)
    if kernel.VirtualQuery(ffi.cast('const void *',p),mbi,48)~=48 then return false end
    local region=ffi.string(mbi,48);local protection=u32(region,36)
    if u32(region,32)~=0x1000 or u32(region,40)~=0x20000 or (protection~=4 and protection~=2)
        or p+#bytes>u64(region,0)+u64(region,24) then return false end
    if protection==2 and kernel.VirtualProtect(ffi.cast('void *',p),#bytes,4,old_protection)==0 then return false end
    count[0]=0
    local ok=kernel.WriteProcessMemory(process,ffi.cast('void *',p),bytes,#bytes,count)~=0 and tonumber(count[0])==#bytes
    if protection==2 and kernel.VirtualProtect(ffi.cast('void *',p),#bytes,2,old_protection)==0 then
        S.protection_pending={address=p,size=#bytes,start=u64(region,0),extent=u64(region,24)};ok=false
    end
    if ok and read(p,#bytes)==bytes then S.writes=S.writes+1;return true end
    return false
end
-- The v18 supported build, pinned by PE identity and accessor instructions.
local BUILD={steam=25480438,timestamp=0x6ab3b43f,image_size=0x4744000}
local ADDRESS={root=0x346bf98,bombardment=0xf12a80,stratagems=0x37cb600,names=0x21d4aa0,projectiles=0x37c7670}
local ANCHORS={
    {0x503dcf,'4c8b90802af100'},
    {0x503e29,'8b4808488d044948c1e0064805c00200004903c2'},
    {0x7b8449,'f30f104024'},
}
local KEY=unhex('21c47a03917b252f') -- OrbitalGatlingBarrage entity
local SEQUENCE=unhex('48000000fe000000fe000000fe00000000000000000000000000000000000000')
local BASE_SEQUENCE=unhex('4d0000002a0000002a0000002a00000000000000000000000000000000000000')
local function check_build()
    local base=tonumber(ffi.cast('uintptr_t',kernel.GetModuleHandleA('game.dll')))
    if not base or base==0 then return nil end
    local dos=read(base,64);if not dos or dos:sub(1,2)~='MZ' then error('Invalid module header',0)end
    local pe=read(base+u32(dos,60),96)
    if not pe or pe:sub(1,4)~='PE\0\0' or u32(pe,8)~=BUILD.timestamp or u32(pe,80)~=BUILD.image_size then error('Unsupported game build',0)end
    for _,a in ipairs(ANCHORS)do
        local bytes=unhex(a[2]);if read(base+a[1],#bytes)~=bytes then error('Bombardment code identity differs',0)end
    end
    return base
end
local function identity()
    return S.base and ptr(S.base+ADDRESS.root)==S.root and ptr(S.root+ADDRESS.bombardment)==S.table_address
        and read(S.index_address,16)==S.index_bytes and ptr(S.base+ADDRESS.stratagems+4*8)==S.stratagem
        and read(S.stratagem,4)==uint(4) and read(S.table_address-28,28)==S.table_header
end
local function owned_prefix(current,before,wanted)
    if not current then return false end
    for n=0,#wanted do if current==wanted:sub(1,n)..before:sub(n+1) then return true end end
    return false
end
local function restore()
    local pending=0
    for i=#S.owned,1,-1 do
        local e=S.owned[i]
        if identity() then
            local current=read(e.address,#e.original)
            if current==e.original then table.remove(S.owned,i)
            elseif current==e.last then
                local ok=write(e.address,e.original);local after=read(e.address,#e.original)
                if owned_prefix(after,current,e.original) then e.last=after end
                if ok and after==e.original then table.remove(S.owned,i) else pending=pending+1 end
            else pending=pending+1 end
        else pending=pending+1 end
    end
    local e=S.protection_pending
    if e then
        if identity() and kernel.VirtualQuery(ffi.cast('const void *',e.address),mbi,48)==48 then
            local r=ffi.string(mbi,48)
            if u64(r,0)==e.start and u64(r,24)==e.extent and u32(r,40)==0x20000
                and (u32(r,36)==2 or (u32(r,36)==4 and kernel.VirtualProtect(ffi.cast('void *',e.address),e.size,2,old_protection)~=0)) then
                S.protection_pending=nil
            end
        end
        if S.protection_pending then pending=pending+1 end
    end
    S.cleanup_pending=pending;return pending==0
end
local function stop(reason)
    S.phase='stopped';S.stop_reason=reason;S.cleanup_attempts=0
    restore();log('STOPPED: '..reason..'; restore pending='..S.cleanup_pending)
end
local function initialize()
    S.base=S.base or check_build();if not S.base then return false end
    local strat=ptr(S.base+ADDRESS.stratagems+4*8)
    local raw=strat and read(strat,400);if not raw then return false end
    local name=read(ptr(S.base+ADDRESS.names+4*8),64)
    if u32(raw,0)~=4 or not name or name:match('^([^%z]+)')~='OrbitalGatlingBarrage'
        or u64(raw,0xa0)~=1 or read(u64(raw,0x98),8)~=KEY then error('Gatling stratagem identity differs',0)end
    local root=ptr(S.base+ADDRESS.root);local p=root and ptr(root+ADDRESS.bombardment)
    local header=p and read(p-28,28);if not header then return false end
    if header:sub(5,8)~='LDLD' or u32(header,12)~=0xcdbc43d8 or u32(header,16)~=5120 then error('Bombardment layout differs',0)end
    local entry,entry_bytes
    for i=0,43 do
        local bytes=read(p+i*16,16);if not bytes then return false end
        if bytes:sub(1,8)==KEY then entry=p+i*16;entry_bytes=bytes;break end
    end
    if not entry then error('Gatling bombardment not found',0)end
    local index=u32(entry_bytes,8);if index>=23 then error('Bombardment row index out of bounds',0)end
    local row=p+704+index*192;local bytes=read(row,192);if not bytes then return false end
    if u32(bytes,4)~=60 or u32(bytes,24)~=4 or bytes:sub(9,12)~=float(0.045)
        or bytes:sub(29,32)~=float(0) or bytes:sub(37,40)~=float(7) or bytes:sub(65,96)~=BASE_SEQUENCE then
        error('Gatling baseline differs; another mod or event may be active',0)
    end
    -- Shared direct-hit damage record 218. Native explosive round 72 produces
    -- Medium ground fire via ExplosionType 108; remaining rounds are type 254.
    for _,t in ipairs{42,77,72,254}do
        local a=ptr(S.base+ADDRESS.projectiles+t*8);local pr=a and read(a,304)
        if not pr then return false end
        local expected=t==72 and 108 or (t==77 and 266 or 0)
        if u32(pr,0)~=t or u32(pr,60)~=218 or u32(pr,144)~=expected
            or pr:sub(33,36)~=float(1050) or pr:sub(129,136)~=string.rep('\0',8) then
            error('Gatling projectile identity differs',0)
        end
    end
    S.root=root;S.table_address=p;S.table_header=header;S.index_address=entry;S.index_bytes=entry_bytes;S.stratagem=strat
    S.plan={{address=row+64,original=bytes:sub(65,96),wanted=SEQUENCE}}
    return true
end
local function apply()
    if config.enabled==0 then
        if not restore() then error('Disable restoration incomplete',0)end
        S.phase='disabled';return
    end
    if not identity() then error('Table identity changed',0)end
    for _,e in ipairs(S.plan)do
        if read(e.address,#e.original)~=e.original then error('Baseline changed before apply',0)end
    end
    for _,e in ipairs(S.plan)do
        if e.wanted~=e.original then
            if not identity() then error('Table identity changed during apply',0)end
            local owned={address=e.address,original=e.original,last=e.wanted}
            S.owned[#S.owned+1]=owned
            local ok=write(e.address,e.wanted)
            local after=read(e.address,#e.wanted)
            if owned_prefix(after,e.original,e.wanted) then owned.last=after end
            if not ok then error('Data write failed',0)end
        end
    end
    S.phase='active';log('Active: native incendiary sequence 72/254/254/254; 60 rounds/salvo, 4 base salvos, spread=7; current damage and upgrades')
end
local function tick(dt)
    S.elapsed=S.elapsed+((type(dt)=='number' and dt>0 and dt<5) and dt or 1/60)
    if S.elapsed<1 then return end;S.elapsed=0
    if S.phase=='stopped' then
        if S.cleanup_pending>0 and S.cleanup_attempts<3 then S.cleanup_attempts=S.cleanup_attempts+1;restore() end
        return
    end
    read_config();menu_step()
    if not S.plan then
        if config.enabled==0 then S.phase='disabled';return end
        if not initialize() then return end
    end
    if not identity() then error('Table identity changed',0)end
    if config.enabled==0 then
        if S.phase~='disabled' then apply();log('Disabled: restored owned settings; existing barrages continue') end
    elseif S.phase~='active' then apply()
    else
        for _,e in ipairs(S.plan)do
            if read(e.address,#e.wanted)~=e.wanted then error('Another writer changed a configured field',0)end
        end
    end
end
S.disable=function()return change(false)end
local loader=rawget(_G,'CowboyBingusModLoader')
if not loader or loader.api~=1 or (tonumber(loader.version) or 0)<17 then
    stop('Requires Bingus Shared Loader v18 / API 1');return S
end
read_config();menu_step()
local old_update=rawget(_G,'update')
if type(old_update)~='function' then stop('Global update callback unavailable');return S end
function update(dt,...)
    local ok,why=pcall(tick,dt);if not ok then stop(tostring(why))end
    return old_update(dt,...)
end
log('Loaded v'..S.version..': Bingus Shared Loader v18 / API 1; Steam build 25480438; native ground-fire dependencies included')
return S
