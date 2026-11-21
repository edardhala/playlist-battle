# Playlist Battle

Friends join a shared room, submit songs, and vote. The playlist reorders
itself by a "hot" score that mixes votes with how recently a song was added.

Live: **https://ehalaieu2024ui.z38.web.core.windows.net**

The first visit after a quiet hour can take up to a minute, while the services and databases wake up (ADR 8).

IE University, Individual Assignment 2: the Assignment 1 monolith split into two services, deployed on Azure.

## Features

- **Rooms:** start a room and get a 6-character code, or join one with a code or a share link.
- **Songs and votes:** add songs, vote once per song, and take a vote back. The same song can't be added twice while it's still in the battle.
- **Hot score ranking:** songs are ranked by `(votes + 1) / (age_hours + 2) ** 1.5`, so new songs get a chance against old popular ones.
- **Play the winner:** the host plays the top song. It shows as "Now playing" and earlier winners move to a "Played" list.
- **Listen links:** every song links to a YouTube search for it.
- **Live updates:** the room page checks for changes every 5 seconds and refreshes by itself when someone joins, adds a song or votes (not while you are typing).

## How it is built

| Part | What it does | Data |
|---|---|---|
| `services/rooms` | Rooms and their members | `rooms_db`: `rooms`, `members` |
| `services/battle` | Songs, votes and played songs. Asks Rooms who is in a room before every write | `battle_db`: `songs`, `votes`, `played` |
| `ui/` | Static HTML and JavaScript that calls both services | none |

Each service is a Flask app with its own SQL Server database, its own migrations in `migrations/`, its own `Dockerfile`, tests and OpenAPI document (`openapi.yaml`). Both answer `GET /health`. The whole system is described in `system.yaml`, checked against `system.schema.json`. The decisions are in `ADR.md`.

## Run locally with compose

Requires Docker.

```bash
docker compose up --build
```

Then open http://localhost:8080. Compose starts:

- `sqlserver`: SQL Server 2022 on port 1433, data kept in the `sqlserver-data` volume;
- `db-init`: creates `rooms_db`, `battle_db` and one login per service (`db/init.sql`), then exits;
- `rooms` on http://localhost:8001 and `battle` on http://localhost:8002, which run their migrations at startup;
- `ui` on http://localhost:8080 (nginx serving `ui/`).

The passwords have local-only defaults and can be changed with `MSSQL_SA_PASSWORD`, `ROOMS_DB_PASSWORD` and `BATTLE_DB_PASSWORD`. Stop with `docker compose down` (add `-v` to delete the data).

## Run a single service

With compose, only the service and its database:

```bash
docker compose up --build rooms
```

Or with Python 3.12, against the compose database:

```bash
docker compose up -d db-init
cd services/rooms
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
DATABASE_URL=mssql://rooms_user:Rooms_Local_Only_1@localhost:1433/rooms_db PORT=8001 python app.py
```

Battle works the same way from `services/battle`, with `battle_user`, `Battle_Local_Only_1` and `battle_db`, plus `ROOMS_URL=http://localhost:8001`. Without Rooms, Battle still starts, but writes answer 503.

## Configuration

| Variable | Service | Default | Meaning |
|---|---|---|---|
| `DATABASE_URL` | both | none, required | `mssql://user:password@host:port/database` |
| `PORT` | both | `8000` | Port the server listens on |
| `CORS_ORIGIN` | both | `http://localhost:8080` | Address of the UI allowed to call the service |
| `GIT_SHA` | both | `dev` | Version shown by `/health`, set at image build |
| `ROOMS_URL` | battle | `http://rooms:8000` | Where Battle finds Rooms |
| `ROOMS_TIMEOUT_S` | battle | `2` | How long Battle waits for Rooms |

The UI reads the two service addresses from `ui/config.js`, which the deploy job overwrites.

## Tests and coverage

Unit and API tests need a SQL Server. Each test run creates its own databases and drops them at the end:

```bash
docker compose up -d sqlserver
cd services/rooms        # or services/battle
pip install -r requirements-dev.txt
ruff check .
pytest --cov=. --cov-config=.coveragerc
```

`TEST_DATABASE_URL` points the tests to another server (default `mssql://sa:Local_Dev_Only_1@localhost:1433/master`). In `services/battle`, `tests/test_cross_seam.py` tests the calls to Rooms against a stub Rooms service (ADR 9).

Latest result (2026-11-21):

| Service | Tests | Coverage |
|---|---|---|
| rooms | 31 passed | 99% |
| battle | 37 passed | 96% |

The end-to-end test runs against the whole compose stack, and stops and starts `rooms` to check that Battle degrades:

```bash
docker compose up -d --build
pip install -r tests/e2e/requirements.txt
pytest tests/e2e
```

CI runs lint, the tests of both services with coverage (at least 70%), and the `system.yaml` and OpenAPI checks on every push.

## Assignment 1 container contract check (§7)

Output of the provided checker, `./container/run.sh .`, run on 2026-10-12 with Docker 28.4.0 against the Assignment 1 monolith, kept as the Assignment 1 evidence:

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

This repository's OIDC tokens name the owner and repository with their IDs (`repo:edardhala@207720258/playlist-battle@1405785844:...`), so the subject is read from GitHub instead of typed. With the plain `repo:edardhala/playlist-battle:...` form, the login fails with `AADSTS700213`.

```sh
SUBJECT="$(gh api repos/$REPO/actions/oidc/customization/sub --jq .sub_claim_prefix):ref:refs/heads/main"
az identity create -g $RG -n $PREFIX-github
az identity federated-credential create -g $RG --identity-name $PREFIX-github -n github-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject "$SUBJECT" \
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
