local root=assert(arg[1])
local passed=0
local function test(name,fn)
    local ok,err=pcall(fn);assert(ok,name..": "..tostring(err));passed=passed+1
end
local function setup()
    local a={id=0,name="DP-1",description="A"};local b={id=1,name="HDMI-A-2",description="B"}
    local wa={id=1,name="1",monitor=a,active=true};local wb={id=21,name="21",monitor=b,active=true}
    a.active_workspace=wa;b.active_workspace=wb
    local e={monitor=b,workspaces={wa,wb},calls={},events={}}
    e.window={workspace=wb,pinned=false}
    local api={dsp={window={},workspace={}},on=function(name,fn)e.events[name]=fn end,
        get_active_monitor=function()return e.monitor end,get_active_window=function()return e.window end,
        get_active_workspace=function()return e.monitor.active_workspace end,
        get_monitors=function()return {a,b} end,get_workspaces=function()return e.workspaces end,
        get_config=function()return false end,config=function()end,workspace_rule=function()end}
    api.get_workspace=function(id)
        id=tonumber(id)
        for _,w in ipairs(e.workspaces)do if w.id==id then return w end end
    end
    local function get(id)
        local w=api.get_workspace(id)
        if not w then w={id=tonumber(id),name=tostring(id),monitor=e.monitor};e.workspaces[#e.workspaces+1]=w end
        return w
    end
    api.dsp.focus=function(args)return {callback=function()
        if args.monitor then e.monitor=args.monitor
        else e.monitor.active_workspace=get(args.workspace) end
        e.calls[#e.calls+1]={kind="focus",args=args};return {ok=true}
    end}end
    api.dsp.window.move=function(args)return {callback=function()
        local w=get(args.workspace);e.window.workspace=w
        if args.follow then e.monitor.active_workspace=w end
        e.calls[#e.calls+1]={kind="move",args=args};return {ok=true}
    end}end
    api.dispatch=function(d)
        if type(d)=="function"then local r=d();return r or {ok=true} end
        assert(type(d)=="table");return d.callback()
    end
    local hs=assert(loadfile(root.."/vendor/hyprsplit/init.lua","t",setmetatable({hl=api},{__index=_G})))()
    hs.config({num_workspaces=20,persistent_workspaces=false});hs.monitor_priority({"DP-1","HDMI-A-2"})
    local rows=dofile(root.."/modules/workspace-bindings.lua").new(api,hs)
    return e,hs,rows,a,b
end
test("top clamps on second monitor",function()local e,h=setup();assert(h.get_workspace_string("-1")=="21")end)
test("bottom clamps on second monitor",function()local e,h=setup();e.monitor.active_workspace.id=40;assert(h.get_workspace_string("+1")=="40")end)
test("relative below creates next local slot",function()local e,h=setup();assert(h.get_workspace_string("+1")=="22")end)
test("first monitor has independent range",function()local e,h,r,a=setup();e.monitor=a;assert(h.get_workspace_string("-1")=="1" and h.get_workspace_string("+1")=="2")end)
test("focus top no-op",function()local e,h,r=setup();r.step(-1,false);assert(#e.calls==0)end)
test("move top no-op",function()local e,h,r=setup();r.step(-1,true);assert(#e.calls==0)end)
test("focus bottom no-op",function()local e,h,r=setup();e.monitor.active_workspace.id=40;r.step(1,false);assert(#e.calls==0)end)
test("focus next slot stays on own monitor",function()
 local e,h,r,a,b=setup();r.step(1,false);assert(b.active_workspace.id==22 and a.active_workspace.id==1)
end)
test("move follows focused window",function()
 local e,h,r,a,b=setup();r.step(1,true);assert(e.window.workspace.id==22 and b.active_workspace.id==22 and a.active_workspace.id==1)
end)
test("repeated move recalculates relative target",function()
 local e,h,r=setup();r.step(1,true);r.step(1,true);r.step(-1,true);assert(e.window.workspace.id==22)
end)
test("empty screen cannot move a window",function()local e,h,r=setup();e.window=nil;r.step(1,true);assert(#e.calls==0)end)
test("scratchpad blocks workspace movement",function()local e,h,r=setup();e.monitor.active_special_workspace={};r.step(1,true);r.step(1,false);assert(#e.calls==0)end)
test("pinned window stays put",function()local e,h,r=setup();e.window.pinned=true;r.step(1,true);assert(#e.calls==0)end)
test("spaces are not persistent",function()local e,h=setup();assert(h.get_config("persistent_workspaces")==false)end)
test("upstream reload callback handles normalized monitors",function()
 local e,h,r,a,b=setup();e.events["config.reloaded"]();assert(a.active_workspace.id==1 and b.active_workspace.id==21)
end)
print(passed.." hyprsplit integration tests passed")
