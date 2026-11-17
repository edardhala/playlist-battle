# Playlist Battle

Friends join a shared room, submit songs, and vote. The playlist reorders
itself by a "hot" score that mixes votes with how recently a song was added.

Built as a single Flask process with SQLite (IE University, Individual Assignment 1).

## Features

- **Rooms:** start a room and get a 6-character code, or join one with a code or a share link.
- **Songs and votes:** add songs, vote once per song, and take a vote back. The same song can't be added twice while it's still in the battle.
- **Hot score ranking:** songs are ranked by `(votes + 1) / (age_hours + 2) ** 1.5`, so new songs get a chance against old popular ones.
- **Play the winner:** the host plays the top song. It shows as "Now playing" and earlier winners move to a "Played" list.
- **Listen links:** every song links to a YouTube search for it.
- **Live updates:** the room page checks for changes every 5 seconds and refreshes by itself when someone joins, adds a song or votes (not while you are typing).

## How to use it

1. Open http://localhost:8000, enter a room name and your name, and click **Start the battle**.
2. Send the share link on the room page to your friends. They only need to type their name.
3. Add songs and vote. The playlist reorders itself.
4. As the host, click **Play the winner** to play the top song.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open http://localhost:8000. Health check: http://localhost:8000/health

## Run with Docker

The `Dockerfile` is the course template with its four TODO lines filled in.

```bash
docker build -t playlist-battle .
docker run -p 8000:8000 -v playlist-battle-data:/data playlist-battle
```

Then open http://localhost:8000. The database is kept in the `playlist-battle-data`
volume, so it survives `docker rm`. To use another port:

```bash
docker run -e PORT=9000 -p 9000:9000 -v playlist-battle-data:/data playlist-battle
```

## Configuration

All settings come from environment variables, and every one has a default.

| Variable   | Default | Meaning                                   |
|------------|---------|-------------------------------------------|
| `PORT`     | `8000`  | Port the server listens on (on `0.0.0.0`) |
| `DATA_DIR` | `data`  | Folder for the SQLite file                |

Inside the Docker image `DATA_DIR` is `/data`. The database file is always
`$DATA_DIR/playlist_battle.db`. The folder and the tables are created
automatically on first start (`CREATE TABLE IF NOT EXISTS`), existing data is
never dropped, and no seed data is needed.

## Project structure

```
app.py              starts the app, creates the tables and registers both domains
config.py           reads PORT and DATA_DIR from environment variables
db.py               SQLite connection helpers shared by both domains
rooms/service.py    Rooms domain rules: rooms and members tables
rooms/routes.py     Rooms pages: create, join, room page
battle/service.py   Battle domain rules: songs, votes, played tables and the hot score
battle/routes.py    Battle actions: add song, vote, remove vote, play the winner
templates/          HTML pages (Jinja)
static/             CSS, logo and live.js (live updates)
tests/              pytest tests
```

The two domains (Rooms and Battle) only share ids, never tables, so they could be split into separate services later (see ADR 2 and 3).

## Tests and coverage

```bash
pytest --cov=. --cov-report=term-missing
```

Test files are left out of the coverage number (see `.coveragerc`).

Latest result: **50 tests passed, 98% coverage** of the app code.

| File | Coverage |
|---|---|
| `rooms/service.py` | 100% |
| `battle/service.py` | 100% |
| `battle/routes.py` | 100% |
| `rooms/routes.py` | 96% |
| `app.py` | 92% |
| `config.py`, `db.py` | 100% |

The only lines not covered are the `python app.py` start-up lines and one error branch in `rooms/routes.py`.

## Container contract check (§7)

Output of the provided checker, `./container/run.sh .`, run on 2026-10-12 with Docker 28.4.0:

```
=== SDD Assignment 1 contract check ===
Repository: /Users/edard/playlist-battle-1

==> Repository shape
  PASS  one Dockerfile, one manifest (requirements.txt)

==> Build from a clean context, no build args
  PASS  image built
  PASS  image size 53 MB

==> Start on PORT=8000 and reach it from the host
  PASS  HTTP 200 from http://localhost:8000/

==> SQLite file under DATA_DIR
  PASS  found in /data: playlist_battle.db 

==> Data persists, and a second boot does not re-seed
  PASS  volume at /data persists
  PASS  row counts unchanged across restart: members=0 played=0 rooms=0 songs=0 votes=0 

==> PORT override is honoured (not hardcoded)
  PASS  HTTP 200 from http://localhost:9123/

=== ALL CHECKS PASSED ===
Paste this output into your README as the §7 evidence.
```

## Deploy to Azure

### How deployment works

Every push to `main` runs the `CI` workflow. When tests, validation and image builds pass, the `deploy` job:

1. signs in to Azure as the managed identity `ehala-ieu2024-github` through OpenID Connect, so no Azure password is stored;
2. deploys `ghcr.io/edardhala/playlist-battle-rooms:<sha>` and `...-battle:<sha>` to the container apps with `infra/deploy-service.sh`, creating them on the first run. The database address is set as a Container Apps secret, and each app scales from 0 to 1 replica;
3. writes `config.js` with the two service addresses and uploads `ui/` to the `$web` container of the storage account;
4. calls `/health` on both services and fails if either does not answer 200 within about 10 minutes;
5. prints the last log lines of both services, which show the migrations applied at startup.

### Initial setup (run once)

Run these one at a time from the repository root, signed in with `az login` to the Azure for Students subscription. Pick a region from the allowed list:

```sh
az policy assignment list --query "[?displayName=='Allowed resource deployment regions'].parameters.listOfAllowedLocations.value" -o tsv
```

Variables used below:

```sh
PREFIX=ehala-ieu2024
RG=rg-$PREFIX
LOCATION=italynorth
REPO=edardhala/playlist-battle
STORAGE=ehalaieu2024ui
```

Register the providers and create the resource group:

```sh
for p in Microsoft.App Microsoft.Sql Microsoft.Storage Microsoft.ManagedIdentity; do az provider register -n $p --wait; done
az group create -n $RG -l $LOCATION
```

Managed identity for GitHub Actions, trusted only for runs on `main`, with Contributor on the resource group only:

```sh
az identity create -g $RG -n $PREFIX-github
az identity federated-credential create -g $RG --identity-name $PREFIX-github -n github-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject "repo:${REPO}:ref:refs/heads/main" \
  --audiences api://AzureADTokenExchange
az role assignment create --role Contributor \
  --assignee-object-id $(az identity show -g $RG -n $PREFIX-github --query principalId -o tsv) \
  --assignee-principal-type ServicePrincipal \
  --scope $(az group show -n $RG --query id -o tsv)
```

SQL server and one serverless database per service on the free offer. Choose an admin password and keep it in a password manager, not in the repository:

```sh
read -s SQL_ADMIN_PASSWORD
az sql server create -g $RG -n $PREFIX-sql -l $LOCATION --admin-user sqladmin --admin-password "$SQL_ADMIN_PASSWORD"
az sql server firewall-rule create -g $RG -s $PREFIX-sql -n AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
for s in rooms battle; do
  az sql db create -g $RG -s $PREFIX-sql -n $PREFIX-$s-db \
    --edition GeneralPurpose --compute-model Serverless --family Gen5 \
    --min-capacity 0.5 --capacity 1 --backup-storage-redundancy Local \
    --use-free-limit --free-limit-exhaustion-behavior AutoPause
done
```

One user per service, inside its own database only. Use passwords made of letters and digits, since they go into a URL. This needs `sqlcmd` (`brew install sqlcmd`) and your IP in the firewall for a few minutes:

```sh
read -s ROOMS_DB_PASSWORD
read -s BATTLE_DB_PASSWORD
az sql server firewall-rule create -g $RG -s $PREFIX-sql -n setup-my-ip \
  --start-ip-address $(curl -s https://api.ipify.org) --end-ip-address $(curl -s https://api.ipify.org)
sqlcmd -S $PREFIX-sql.database.windows.net -d $PREFIX-rooms-db -U sqladmin -P "$SQL_ADMIN_PASSWORD" \
  -v USER_NAME=rooms_user -v USER_PASSWORD="$ROOMS_DB_PASSWORD" -i infra/azure-users.sql
sqlcmd -S $PREFIX-sql.database.windows.net -d $PREFIX-battle-db -U sqladmin -P "$SQL_ADMIN_PASSWORD" \
  -v USER_NAME=battle_user -v USER_PASSWORD="$BATTLE_DB_PASSWORD" -i infra/azure-users.sql
az sql server firewall-rule delete -g $RG -s $PREFIX-sql -n setup-my-ip
```

Container Apps environment on the Consumption plan, without a Log Analytics workspace (logs are read with `az containerapp logs show`):

```sh
az extension add --name containerapp --upgrade
az containerapp env create -g $RG -n $PREFIX-env -l $LOCATION --logs-destination none --enable-workload-profiles false
```

Storage account with static website hosting for the UI:

```sh
az storage account create -g $RG -n $STORAGE -l $LOCATION --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false
az storage blob service-properties update --account-name $STORAGE --auth-mode key \
  --static-website --index-document index.html --404-document index.html
az storage account show -g $RG -n $STORAGE --query primaryEndpoints.web -o tsv
```

GitHub secrets read by the `deploy` job:

```sh
gh secret set AZURE_CLIENT_ID --body "$(az identity show -g $RG -n $PREFIX-github --query clientId -o tsv)"
gh secret set AZURE_TENANT_ID --body "$(az account show --query tenantId -o tsv)"
gh secret set AZURE_SUBSCRIPTION_ID --body "$(az account show --query id -o tsv)"
gh secret set ROOMS_DB_PASSWORD --body "$ROOMS_DB_PASSWORD"
gh secret set BATTLE_DB_PASSWORD --body "$BATTLE_DB_PASSWORD"
```

Reader access for grading, with the command from the setup guide:

```sh
az role assignment create --role Reader --assignee <professor email> --scope $(az group show -n $RG --query id -o tsv)
```

The container apps are created by the first `deploy` run, not by hand.
