# Channel Plugins

This directory is reserved for future channel modules. Each channel should provide:

```
init(state)
update(state, dt)
render(context)
```

Channels should not control the main loop. They receive state from the app and return render instructions for the UI layer.
