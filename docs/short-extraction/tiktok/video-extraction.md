# TikTok media extraction

TikTok posts may be either video or photo slideshows.

## Just download them from tiktok lol

- Anecdotal evidence: Downloaded 1700 videos within 13 minutes directly from TikTok, using a concurrency of 5, while connected to a public Proton VPN; TikTok did not seem to react or block downloads.
- In actual production, video fetching will likely be much less frequent.
- A commercial VPN service with fixed pricing (regardless of bandwidth used) can be used, like mullvad, or storm proxy. Mullvad with its superb price of $5 might be perfect for beggining (and also has the ability to use proxies, which makes using a random one per each request easy), while if we ever actually need an upgrade we can use storm proxies.
- **How it works:** yt-dlp gets the SSR blob from the page, and that has the video URL, and also other supplemental information in json [[metadata-extraction]]
- Seems to be the most straightforward way to get videos out of TikTok.

## TikTok photo slideshows

- In a prior small test, `gallery-dl` could download the slideshow videos from Tiktok, but that resulted in redundant fetches of info.
- Instead, we can get a yt-dlp fetched JSON, which has a non-empty `imagePost.images` list, download the images from the URL lists in that JSON, in order.

## Get CDN urls / proxy the video files from users.

This uses the [[tiktok-web-piggybacking]] approach.

- Signed in users have no problem of getting a CDN url.
- This CDN URL would be sent to backend, and then backend would analyze the video. This assumes that CDN has no rate limits, which is a shaky assumption
- Alternatively the phone might download the video and send it to backend, but that feels messy.
- The backend has to trust that the client sent the video for the TikTok being analyzed. We can try and trust some attestation, or maybe there are some hashes we can use to trust validity, but I would not count on that.

Side note, but having a custom tiktok fetcher written in JS but based on yt-dlp might be a good idea, especially since often we will likely need to react quick to some tiktok changes, before a new yt-dlp release is out.
