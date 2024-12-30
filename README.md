# smite-builds-pro
Source code for https://smitebuilds.pomy.dev (previously https://www.smitebuilds.pro)

[SMITE](https://www.smitegame.com) is a popular video game developed by [Titan Forge Games](https://www.titanforgegames.com/), in which one has to choose a sequence of items to buy - a so-called build. This website shows builds used by professional players in the SMITE Pro League (SPL) and in the SMITE Challenger Circuit (SCC). These builds can also be filtered by god/role/player/date/item etc.

As this data is not available in the [SMITE API](https://webcdn.hirezstudios.com/hirez-studios/legal/smite-api-developer-guide.pdf), it is obtained by web scraping the following official websites:
- SPL - https://www.smiteproleague.com/schedule
- SCC - https://scc.smiteproleague.com/schedule

Update: Titan Forge Games has paused the smite league after the announcement of SMITE 2. Support for SMITE 2 is not planned, so this website has turned into an archive (for seasons 8-10).

## Technologies used
- Backend - Python, bottle (web framework), SQLite, SQLAlchemy (ORM), Selenium
- Frontend - TypeScript, Vue 3, Bulma, vite

## Hosting
The website is hosted on a VPS. Previously it was hosted using [PythonAnywhere](https://www.pythonanywhere.com). The deployment and maintenance scripts are not public.

## Alternatives
- [Blues' spreadsheet](https://docs.google.com/spreadsheets/d/1W9mQkedMvYLUMt9sPs8zwRr75aaOUNf02FeoRFvoDao/edit#gid=385314662) (this link goes to the season 10 version)
- https://prosmitebuilds.com

## Running locally

### Backend
Code is developed on Python 3.12, but lower versions would probably work too.

Setup consists of:
1. Installing the required packages - e.g. (on linux):
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Setting the required environment variables described below. This can be done easily with `cp .env.example .env`
3. (Optional) Puting [ChromeDriver](https://chromedriver.chromium.org) in PATH for the webscraping script.

Then the `run.sh` script can be used:
- `./run.sh dev` - runs the web api for development purposes. Also creates the SQLite database (`storage/backend.db`), if it doesn't exist yet.
- `./run.sh test` - runs the unit tests.
- `./run.sh updater` - runs the webscraping script.
- `./run.sh log_manager` - parses logs for warnings and errors and sends what it found to a https://ntfy.sh/ topic. Also rotates and archives logs, and makes a database backup.
- There are also some additional small helper scripts in the `backend/webapi/tools` and `backend/updater/tools` folders.

Used enviroment variables:
- `HMAC_KEY_HEX` - key used to authenticate the webscraping script with the web api, in hexadecimal.
- `SMITE_DEV_ID` & `SMITE_AUTH_KEY` - credentials for the [SMITE API](https://webcdn.hirezstudios.com/hirez-studios/legal/smite-api-developer-guide.pdf). This api is currently used only for getting the name of a new god, when their name is misprinted on the SPL website.
- `BACKEND_URL` - web api url for the webscraping script.
- `NTFY_TOPIC` - the topic to which notifications are sent.
- `MATCHES_WITH_NO_STATS` (optional) - match IDs separated by commas, which are not warned about, when they have no stats.

Created files (the SQLite database, logs, etc.) are stored in the `storage` folder, in the root of the project.

### Frontend
CD to the frontend directory and install the required packages: `cd fe && npm ci`. The development server can then be started with `npm run dev`, the static files can be built with `npm run build` and these can be previewed with `npm run serve`.
