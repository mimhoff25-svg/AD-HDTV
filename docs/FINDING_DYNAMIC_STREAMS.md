# Finding Dynamic Video Streams

Many modern websites (like kiiitv.com/tower-cam) use **dynamic video players** that generate blob URLs on-the-fly. These cannot be extracted directly from the HTML source code.

## 🔍 How to Find Real Stream URLs

### Method 1: Browser Developer Tools (Recommended)

1. **Open the webpage** in your browser (Chrome/Firefox)
2. **Open Developer Tools** (F12 or Right-click → Inspect)
3. **Go to the Network tab**
4. **Filter by media types**: Click "Media" or "XHR"
5. **Refresh the page** (Ctrl+R) to capture all network requests
6. **Look for these file types**:
   - `.m3u8` (HLS streams) - Most common for live cameras
   - `.mp4` (Direct video files)
   - `.ts` (Transport stream segments)
   - `.webm`, `.mkv` (Other video formats)

7. **Right-click the stream URL** → Copy → Copy URL
8. **Paste into WebGridPlayer** using "Add URL"

### Example: kiiitv.com/tower-cam

For this site specifically:

1. Open https://www.kiiitv.com/tower-cam in Chrome
2. Open DevTools (F12) → Network tab
3. Filter by "Media" 
4. Refresh the page
5. You should see requests like:
   ```
   https://api.wetmet.net/camera/[id]/stream.m3u8
   https://cdn.wetmet.net/live/[camera-id]/index.m3u8
   ```
6. Copy the `.m3u8` URL and add it to WebGridPlayer

### Method 2: Video Element Inspection

When WebGridPlayer shows:
```
🎬 Dynamic Video #1 (SV360mediaplayer_html5_api) - Check browser DevTools Network tab
```

This means the video uses a blob URL like:
```html
<video id="SV360mediaplayer_html5_api" src="blob:https://...">
```

**The blob URL won't work outside the page**, but the real stream URL is in the Network tab!

## 🎥 Common Video Player Types

### VideoJS / Video.js
- Look for: `<video class="vjs-tech">`
- Stream URL in: `sources: [{src: "https://..."}]` in JavaScript
- Network tab: `.m3u8` files

### JW Player
- Look for: `jwplayer()` in JavaScript
- Stream URL in: `file: "https://..."` in config
- Network tab: `.mp4` or `.m3u8` files

### Brightcove
- Look for: `<video data-video-id="...">`
- Stream URL in: Network tab → `.m3u8` files from `brightcove.com` domain

### Custom Players (like WetMet API)
- Look for: API calls in Network tab
- Pattern: `api.wetmet.net`, `api.company.com/camera/`
- Stream format: Usually `.m3u8` (HLS)

## 📋 Step-by-Step for kiiitv.com

1. **Open** https://www.kiiitv.com/tower-cam
2. **F12** → Network tab
3. **Click** "Media" filter
4. **Refresh** page
5. **Wait** for video to load
6. **Look for** entries with:
   - Type: `application/x-mpegurl` or `video/mp2t`
   - Name: `*.m3u8` or `*.ts`
7. **Right-click** the `.m3u8` file → Copy → Copy URL
8. **In WebGridPlayer**: Right-click → Add URL → Paste
9. **Video plays!**

## 🚫 Why Some Videos Don't Extract Automatically

### Blob URLs
- **Problem**: Generated in browser memory, not in HTML
- **Solution**: Use Network tab to find real source

### Token-Based Authentication
- **Problem**: Stream URL requires authentication token that expires
- **Solution**: Extract URL from Network tab (may expire after time)

### DRM Protected Content
- **Problem**: Video uses Digital Rights Management
- **Solution**: Cannot be played in external players like WebGridPlayer

### CORS Restrictions
- **Problem**: Server blocks cross-origin requests
- **Solution**: May work if you use the direct stream URL from Network tab

## 💡 Pro Tips

1. **Look for .m3u8 first** - This is the most common streaming format
2. **Check multiple cameras** - If a site has several cameras, they often use the same URL pattern
3. **Copy URL quickly** - Some tokens expire within minutes
4. **Use browser's Copy as cURL** - Then extract the URL from the command

## 🔗 Common Stream URL Patterns

```
# Wetmet API (used by kiiitv.com)
https://api.wetmet.net/camera/{id}/stream.m3u8
https://api.wetmet.net/live/{camera-id}/playlist.m3u8

# Generic patterns
https://stream.example.com/live/{id}/index.m3u8
https://cdn.example.com/cameras/{name}/playlist.m3u8
https://example.com/hls/{id}/stream.m3u8
```

## ✅ Testing Your Stream URL

Once you find a URL:

1. **Paste it** in WebGridPlayer using "Add URL"
2. **If preview shows** → URL works! ✅
3. **If preview fails** → Try finding another .m3u8 file in Network tab
4. **If still fails** → Stream may be DRM-protected or token-expired

## 📞 Need Help?

If WebGridPlayer shows dynamic video placeholders:
1. Follow the Network tab instructions above
2. Look for `.m3u8` files specifically
3. Copy the full URL including any `?token=` parameters
4. Add to WebGridPlayer immediately (tokens can expire)

---

**Last Updated**: January 5, 2026  
**Applies to**: WebGridPlayer video stream extraction
