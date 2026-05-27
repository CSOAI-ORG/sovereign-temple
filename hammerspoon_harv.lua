-- Hammerspoon → HARV bridge
-- Install: copy to ~/.hammerspoon/harv.lua, then in init.lua: require("harv")
-- Posts Mac context (idle time, active app, window title) to Sovereign every 30s

local HARV_URL = "http://localhost:3100/harv/update"
local lastApp = ""
local lastWindow = ""
local lastIdle = 0

local function postContext()
    local idle = math.floor(hs.host.idleTime())
    local app = ""
    local win = ""

    local frontApp = hs.application.frontmostApplication()
    if frontApp then
        app = frontApp:name() or ""
    end

    local focusedWin = hs.window.focusedWindow()
    if focusedWin then
        win = focusedWin:title() or ""
    end

    -- Only post if changed
    if idle == lastIdle and app == lastApp and win == lastWindow then return end
    lastIdle = idle; lastApp = app; lastWindow = win

    local body = hs.json.encode({
        pc_idle = idle,
        pc_app = app,
        pc_window = win
    })

    hs.http.asyncPost(HARV_URL, body, {["Content-Type"] = "application/json"},
        function(status, response, headers)
            -- silent success
        end)
end

-- Post every 30 seconds
local harvTimer = hs.timer.doEvery(30, postContext)

-- Also post on app switch
hs.application.watcher.new(function(appName, eventType, app)
    if eventType == hs.application.watcher.activated then
        hs.timer.doAfter(0.5, postContext)
    end
end):start()

-- Post wake from sleep
hs.caffeinate.watcher.new(function(event)
    if event == hs.caffeinate.watcher.systemDidWake then
        hs.timer.doAfter(2, postContext)
    end
end):start()

-- Post app activation events to StreamAggregator
local appWatcher = hs.application.watcher.new(function(appName, eventType, app)
    if eventType == hs.application.watcher.activated then
        local win = hs.window.focusedWindow()
        local winTitle = win and win:title() or ""
        local body = hs.json.encode({
            type = "app_activated",
            app_name = appName,
            detail = winTitle
        })
        hs.http.asyncPost("http://localhost:3100/context/app_event", body,
            {["Content-Type"] = "application/json"}, function() end)
    end
end)
appWatcher:start()

print("HARV Hammerspoon bridge loaded — posting to " .. HARV_URL)
