# TikTok metadata extraction

yt-dlp gives us an `.info.json` next to the video. It's handy, but it's yt-dlp's own format, not TikTok's. yt-dlp renames the fields and throws some of them away, and some of the thrown away ones are exactly what we want (see location data below).

## Two JSONs

- `.info.json` is yt-dlp's version, with fields like `description`, `uploader`, `view_count`, `subtitles`.
- `itemStruct` is the raw TikTok post, with fields like `desc`, `author`, `stats`, and `imagePost` for slideshows. It sits in the page's `__UNIVERSAL_DATA_FOR_REHYDRATION__` blob, under `webapp.video-detail` -> `itemInfo` -> `itemStruct`.
- yt-dlp already reads `itemStruct` and builds `.info.json` from it, but there's no normal flag to get the raw one out. `--write-pages` dumps the fetched page, but it's meant for debugging.
- ! We should store both as JSONB. The app uses the yt-dlp fields, and if we later need something TikTok had but yt-dlp dropped, we don't have to refetch.

## What helps with place analysis

- Description. Often names the place, city or neighborhood straight away. Hashtags are in there too, `tags` was `null` on the videos I checked.
- Subtitles. Can mention a place the description didn't. `.info.json` only has URLs to them, so we'd have to fetch the VTT separately. Not every post has them.
- Place tag. Some TikToks have one and it can just give us the location, so always check for it.

## ! Location data

Tested on 83 videos, 82 downloaded fine. All 82 had `locationCreated`, and 37 also had `poi` and `contentLocation`. None of it made it into `.info.json`, yt-dlp reads it and then drops it.

Don't trust it blindly though:

- `poi` and `contentLocation` can have a place name, address, ID or category, but that's whatever the creator tagged, not necessarily where it was filmed.
- `locationCreated` looks like just a region code, and sometimes disagrees with the tagged place and the video itself.

To get this without a second fetch, we have to grab the raw `itemStruct` during the same yt-dlp extraction, before it gets mapped. yt-dlp's raw extractor method can do it, but it's internal. Calling it after a normal extraction fetches the page again, so that's no good. Probably another point for the custom fetcher idea from [[video-extraction]].

Sample posts: [[location-data-samples]]

## Example dumps

- Video, Madrid itinerary, with subtitles: [[.attachments/yt-dlp-info-madrid.info.json]]
- Video, Athens itinerary, with subtitles: [[.attachments/yt-dlp-info-athens.info.json]]
- Slideshow, Singapore cafes, raw `itemStruct` with `imagePost.images`: [[.attachments/tiktok-itemstruct-slideshow-singapore-cafes.info.json]]
