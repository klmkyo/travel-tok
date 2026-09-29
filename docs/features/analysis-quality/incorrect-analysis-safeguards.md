# Place corrections

There will probably be some cases where the analysis will fail even if we improve the algorithm in response to things detected by [[analysis-feedback]].

I see a couple of ways to handle this:

## Listening to user corrections

Whenever user edits an analyzer suggestion, we should keep track of it and potentially keep using that for new results of the same TikTok analysis.

Whenever user makes an edit, we could ask an AI to check if its plausible or not, or even better - if multiple edit a place recommendation, that's when we ask AI.

## Pull out the big guns when multiple users dislike recommendations.

We could make it so that whenever multiple users dislike a suggestion, we can have an AI which is given the place, and potential user replacements.

This AI would use for example the %%LINK TO IT%% google lens-like api, or other google apis to try and identify the place as a hail mary. Multiple dislikes would indicate that the short is popular, so pulling out big guns is justified.

Also, potentially, the AI could be agentic. It would first be given the user replacements, and if it deems that trustworthy, it just sorta accepts it. If not, it can be allowed to use the google-lens like api to try and identify the place.

Could also be marketed as pro feature. Some nice looking button - "Advanced Search", which would find the place it finds appropriate, and suggest it to the user, and potentially use it as the served place for that short.
