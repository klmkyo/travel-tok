Old note from apple notes. Should probably be ignored as a thing that contains some actual decisions. 
# TravelTok

2 opcje - albo fully local apka, albo backed by server:

## Backed by server

- o wiele szybsze i dokładniejsze wyniki
- musimy wykonać analizę tylko raz per video
- możemy próbować dokonać analizy nawet bez video - czytamy description i komentarze

ale:

- potencjalna potrzeba residential proxy do pobierania filmików z tiktoka (może same filmiki z CDN'u można poza proxy? milion razy taniej)
- komentarze trzeba na 100% scrapować, nie ma przez api

## Trzeba

- zrobić dataset 100 travel tiktoków, sprawdzić następujące scenariusze:
	- gemini 3.8 flash analizujący całe video
	- gemini 3.8 flash analizujący całe video, ale z agentic video processing czy coś
	- gemini 3.8 flash analizujący całe video, ale z google search grounding
	- gemini 3.8 flash analizujący całe video, ale z google maps grounding
	- powyższe 4 próbować w permutacjach, oraz z 3.5 flash lite
	- glm 5.3 flash analizujący całe video
	- użycie overture maps - do zapytań typu - wiem gdzie to jest, ale chcę koordy. Ale też czy to potrzebujemy? skoro będziemy używać google maps sdk, to potrzebujemy jedynie zrobić google maps text search
	- google maps Text Search, IDs only - co nam daje?
- Zastanowić się jak wyświetlać userowi mapę z miejscami - The current native Google Maps SDK for iOS and Android has unlimited free mobile usage. You still need billing enabled and an API key, but the Maps SDK SKU itself currently has an unlimited free usage cap.
- można zrobić abstrakcję na google / apple maps
- detect landmarks api https://docs.cloud.google.com/vision/docs/detecting-landmarks

![[.attachments/google-maps-poi-tap.png]]

## Ogólne pomysły

- Telefony użytkowników pobierają filmiki za nas i nam je dają, jeśli jesteśmy w stanie zsourcować hash filmiku jakoś - https://github.com/yt-dlp/yt-dlp/issues/7109
- Może filmiki z CDN'u można poza proxy? milion razy taniej
- jakąś miniaturkę z miejscem trzeba pokazać userowi w liście. tiktokowe oEmbed ma thumbnail_url, więc to chyba najlepsze, ewentualnie inaczej można zrobić lookup na overture, co nam da linka do Wikimedia Commons. gorzej z wikimedia dla np. losowej kawiarenki
- klasyfikacja jakaś? llm klasyfikujący miejsce jako restauracja / bar / zabytek itp
- Trzeba sprawdzić, czy TikTok podobnie jak z Instagramem pozwala udostępnić filmik tak, że nie dostajemy linku, tylko aplikacja TikToka nam tworzy filmik, który następnie jest eksportowany do aplikacji.
- jak wygląda sytuacja z ig reels?
- And importantly, current yt-dlp shows that TikTok's webpage itself can contain a hydrated itemStruct containing the video data. Its current extractor fetches the webpage, reads `__UNIVERSAL_DATA_FOR_REHYDRATION__`, and then parses `webapp.video-detail` → `itemInfo` → `itemStruct`; it separately extracts direct media URLs from the resulting video structure. https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/yt_dlp/extractor/tiktok.py
- LinkPresentation?

![[.attachments/link-presentation.png]]

![[.attachments/tiktok-embed-player.png]]

## Import z lokalnej biblioteki

- Pomysł. Użytkownicy pobierają masowo filmiki Tik Toków albo slide trolly i jeżeli pobrany filmik czy tam plik zawiera gdzieś w sobie informację o jego ID, to być może flow może być taki, że użytkownik sobie pobiera dowolną ilość Tik Toków czy coś w tym stylu. aplikacja następnie skanuje jego bibliotekę i na bazie tego importuje sobie zarówno filmiki na bazie ich ID oraz danych o embed, jak i same filmiki, bo już są pobrane.
- https://apify.com/clockworks/tiktok-comments-scraper/pricing
- https://github.com/HasData/tiktok-scraping
- https://www.tikliveapi.com/tiktok-video-download-api/ chyba potwierdza, że jak dostaniemy link cdn, to essa i pobieramy do woli

## Co robi WhoLiked?

- https://chatgpt.com/g/g-p-6aa0685b55d88191a25b1c484d3d4e0f-traveltok/c/6aa14830-ce5c-83eb-8b9b-83ac6971f765
- https://chatgpt.com/c/6aa149ce-8c20-83eb-82f1-fc3bd17df141
- https://chatgpt.com/c/6aa167fc-8f30-83ed-9b62-4d7fc24f9ff6
- The app doesn't scrape TikTok — it makes the user do it. You log into TikTok inside the app (WebView or the QR-code login flow at www.tiktok.com/login/qrcode), the app holds your own TikTok web session, and then the device itself calls www.tiktok.com's web API as you, with your cookies, fetching your liked-videos list (the one surface that literally requires being the account owner). It resolves playAddr (TikTok's CDN field) and downloads/caches the video bytes directly on-device. Fetched data is pushed to their backend via a backend_pusher service. During gameplay, players' devices resolve/download the round videos themselves (with a resolution cache repo — VideoUrlResolutionCacheRepository).
- DEFINITYWNE? - https://chatgpt.com/s/t_6aa1ad286e508191800e0f83249ca6e0

![[.attachments/wholiked-teardown-retrieval.png]]

![[.attachments/retrieval-official-apis.png]]

![[.attachments/wholiked-final-analysis.png]]

## Inne

An account which post like actual travel spots, but for example, like some of the slides are like just part of it is advertising the app

## Eksperymenty

### Video

- tiktok ma wywalone na fetchowanie video przez yt-dlp. 1700 filmików w 13 minut, ewentualnie można mullvada albo storm proxy dać żeby rotatnął go jakby jakimś cudem tiktok nas zablokował. yt-dlp używa ssr'owych stron żeby wydobyć info o filmiku
- komentarze ciężej wydobyć, wymagają autha. możemy apify albo tikhub albo coś takiego użyć. tikhub wydaje się najbardziej obiecujący. mają subskrypcje, i PAYG
