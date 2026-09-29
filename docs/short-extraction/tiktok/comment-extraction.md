TikTok comments are harder to fetch than videos and require authentication. Without authentication, we only see the comment count, which isn't useful.

- Comments are probably just supplemental information.
- If the TikTok doesn't mention the places in the video or description, users likely don't expect the app to figure out the place anyways.
- Fetch comments only if there's not enough information in the video or description.
- So this should likely both be a fallback and late game feature, and potentially reserved only for popular places.
- Could be part of an improved accuracy Pro feature. See [[monetization/monetization]].

## Third-party service

- Use a scraper such as TikHub, Apify, or HasData.
- TikHub looks most promising so far and offers subscription and pay-as-you-go plans.
<!-- TODO include pricing information from these services -->

## [[tiktok-web-piggybacking|Piggybacking]] on the client

Ask the signed-in TikTok client to send us the comments it fetched.

- The backend would have to trust that the client sent genuine comments.
- Comparing reports from multiple clients might help, but consensus is still a shaky check.
- A hash can show that payloads match, not that they are correct.
