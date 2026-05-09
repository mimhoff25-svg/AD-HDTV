function CreateHubClient(baseUrl as String, token = "" as Dynamic) as Object
    client = {
        baseUrl: baseUrl
        token: token
    }

    client.getJson = function(path as String) as Object
        request = CreateObject("roUrlTransfer")
        request.SetUrl(m.baseUrl + path)
        request.AddHeader("Accept", "application/json")
        if m.token <> invalid and m.token <> ""
            request.AddHeader("Authorization", "Bearer " + m.token)
        end if
        response = request.GetToString()
        if response = invalid or response = ""
            return { ok: false, error: "Empty response" }
        end if
        return ParseHubResponse(request, response)
    end function

    client.postJson = function(path as String, body = invalid as Dynamic) as Object
        request = CreateObject("roUrlTransfer")
        request.SetUrl(m.baseUrl + path)
        request.AddHeader("Accept", "application/json")
        request.AddHeader("Content-Type", "application/json")
        if m.token <> invalid and m.token <> ""
            request.AddHeader("Authorization", "Bearer " + m.token)
        end if
        payload = "{}"
        if body <> invalid
            payload = FormatJson(body)
        end if
        response = request.PostFromString(payload)
        if response = invalid or response = ""
            return { ok: false, error: "Empty response" }
        end if
        return ParseHubResponse(request, response)
    end function

    return client
end function

function ParseHubResponse(request as Object, body as String) as Object
    statusCode = request.GetResponseCode()
    payload = invalid
    if body <> invalid and body <> ""
        payload = ParseJson(body)
    end if
    if statusCode >= 200 and statusCode < 300
        return {
            ok: true
            statusCode: statusCode
            body: payload
        }
    end if
    errorMessage = "Hub request failed"
    if payload <> invalid and payload.error <> invalid
        errorMessage = payload.error
    end if
    return {
        ok: false
        statusCode: statusCode
        error: errorMessage
        body: payload
    }
end function
