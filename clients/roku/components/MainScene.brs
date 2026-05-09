sub init()
    m.titleLabel = m.top.findNode("titleLabel")
    m.statusLabel = m.top.findNode("statusLabel")
    m.channelLabel = m.top.findNode("channelLabel")
    m.guideLabel = m.top.findNode("guideLabel")
    m.pollTimer = m.top.findNode("pollTimer")

    m.top.observeField("hubConfig", "onHubConfigChanged")
    m.pollTimer.observeField("fire", "onPollTimer")
    m.lastMuted = false
end sub

sub onHubConfigChanged()
    config = m.top.hubConfig
    if config = invalid
        return
    end if

    if config.pollMs <> invalid and config.pollMs > 0
        m.pollTimer.duration = config.pollMs / 1000.0
    end if

    m.client = CreateHubClient(config.baseUrl, config.token)
    refreshStatus()
    refreshGuide()
    m.pollTimer.control = "start"
end sub

sub onPollTimer()
    refreshStatus()
end sub

sub refreshStatus()
    if m.client = invalid
        return
    end if
    response = m.client.getJson("/status")
    if response.ok
        payload = response.body
        m.lastMuted = payload.audio.muted
        m.statusLabel.text = "Hub connected • " + GetPlayingText(payload)
        m.channelLabel.text = "Channel: " + payload.current_channel_name + " (" + ToDisplayString(payload.current_channel_id) + ")"
    else
        m.statusLabel.text = "Hub error: " + response.error
    end if
end sub

sub refreshGuide()
    if m.client = invalid
        return
    end if
    response = m.client.getJson("/guide?hours=2")
    if response.ok = false
        m.guideLabel.text = "Guide error: " + response.error
        return
    end if

    guide = response.body
    lines = []
    programs = guide.programs
    maxItems = 4
    for each item in programs
        title = item.title
        if title <> invalid
            lines.push("- " + title)
        end if
        if lines.count() >= maxItems
            exit for
        end if
    end for
    if lines.count() = 0
        lines.push("No guide data available")
    end if
    m.guideLabel.text = "Guide`n" + Join(lines, "`n")
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if press = false or m.client = invalid
        return false
    end if

    if key = "up"
        response = m.client.postJson("/control/channel/next")
        handleMutation(response)
        return true
    else if key = "down"
        response = m.client.postJson("/control/channel/prev")
        handleMutation(response)
        return true
    else if key = "right"
        response = m.client.postJson("/control/guide/show")
        handleMutation(response)
        refreshGuide()
        return true
    else if key = "left"
        response = m.client.postJson("/control/guide/hide")
        handleMutation(response)
        return true
    else if key = "OK"
        refreshGuide()
        return true
    else if key = "back"
        response = m.client.postJson("/control/audio/mute", { value: not m.lastMuted })
        handleMutation(response)
        return true
    end if

    return false
end function

sub handleMutation(response as Object)
    if response.ok
        payload = response.body
        m.lastMuted = payload.audio.muted
        m.statusLabel.text = "Updated • " + GetPlayingText(payload)
        m.channelLabel.text = "Channel: " + payload.current_channel_name + " (" + ToDisplayString(payload.current_channel_id) + ")"
    else
        m.statusLabel.text = "Hub error: " + response.error
    end if
end sub

function GetPlayingText(payload as Object) as String
    if payload.playing = invalid or payload.playing = true
        return "Playing"
    end if
    return "Paused"
end function

function ToDisplayString(value as Dynamic) as String
    if value = invalid
        return "-"
    end if
    if type(value) = "roString" or type(value) = "String"
        return value
    end if
    return value.ToStr()
end function
