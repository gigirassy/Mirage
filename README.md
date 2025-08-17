# Mirage
Mirage is an open privacy frontend to Miraheze, heavily WIP. A lot of it was "vibecoded", so having a human or programmer turtle help out would be a nice idea!

## Features
* Pages visited are only logged in the case the frontend explodes, aka for debugging.
* Search function.
* Light mode/dark mode.
* Font size can be increased.
* Configuration is done with cookies.
* Cached pages are encrypted by default.
* URLS use the exact same format as Breezewiki, and custom URLs are also accounted for.

## How to host

Docker is recommended.

1. Clone this repo, ``cd`` into it
2.  ``echo "MIRAGE_CACHE_KEY=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=')" > .env && chmod 600 .env``
3. ``mkdir -p ./cache && chmod 700 cache``
4. Modify compose file to your liking. You can change host port, cache length, etc...
5. ``docker compose up -d``

## Instances
Cloudflare is not allowed.
| Instance         | In?  | Note           |
| ---------------- | ---- | -------------- |
| mirage.blitzw.in | 🇩🇰 | Main instance. |


<img width="1270" height="863" alt="image" src="https://github.com/user-attachments/assets/65b8348a-3bf6-484f-882e-ab95e2aa55a1" />
