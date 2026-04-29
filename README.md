# LabSafe
Authors:
- Max Hannah
- Muhammad Hassan
- Roy Hritaban
- Stephanos Papatsaras
- Moth Robson
- Ben Soroos

# Sample Instance
A running instance is available at [https://colony-management.staging.up.railway.app](https://colony-management.staging.up.railway.app).

Some example data is available in this repository:
- Files suitable to test the data import functionality can be found in [`mousemetrics/mouse_import/tests/`](./mousemetrics/mouse_import/tests/) ([`sheet.xlsx`](./mousemetrics/mouse_import/tests/sheet.xlsx), [`sheet.csv`](./mousemetrics/mouse_import/tests/sheet.csv)).
- example mice can be loaded with `uv run python mousemetrics/manage.py loaddata mice` and `uv run python mousemetrics/manage.py loaddata family_tree_test_data` (to load a more complex set of mice used to test the family tree).

# Deployment
In order to deploy an instance of LabSafe, fairly little is necessary.

The only dependencies that must be manually installed are Python 3.13 (or newer) and [`uv`](https://docs.astral.sh/uv/).

With those available, and the source code for the application in the current working directory, the server can be started with `uv run ./start.sh`, with environment variables as follows:
- `MOUSEMETRICS_ENVIRONMENT` must be set to `production`.
- `MOUSEMETRICS_HOST` must be set to the hostname under which the application is to be served.
- `MOUSEMETRICS_SECRET_KEY` must be set to a stable, but secure and random, value.
- `RESEND_API_KEY` must be set to an API key for [Resend](https://resend.com), configured with an appropriate domain.
- `MOUSEMETRICS_EMAIL` must be an email address from which email can be sent using the above `RESEND_API_KEY`.
- `MOUSEMETRICS_ROOT_PASSWORD` *may* be set to automatically create a user with email `root@$MOUSEMETRICS_HOST`.
		If left unset, a root user must be created manually with `uv run python mousemetrics/manage.py createsuperuser`.
- `PORT`. If left unset, the server will bind to `127.0.0.1:8000`; otherwise, it will bind to `0.0.0.0:$PORT`.
- `WEB_CONCURRENCY` sets the number of worker processes with which to handle requests. The default is 1.

Additionally, a database must be configured, either SQLite or PostgreSQL.
To use SQLite, set an environment variable `MOUSEMETRICS_DB_PATH` to a writable path where the database may be placed.
To use PostgreSQL, set environment variables as follows:
- `MOUSEMETRICS_PG_HOST` to the hostname or IP address of the PostgreSQL instance;
- `MOUSEMETRICS_PG_DBNAME` to the name of the database to be used;
- `MOUSEMETRICS_PG_USER` to the username to be used for the database;
- and `MOUSEMETRICS_PG_PASSWORD` to the password to be used for the database.

This start command can be orchestrated in any way appropriate for the deployment environment, and a reverse proxy can (and should) be configured to forward traffic for the host to `127.0.0.1:8000`.

Once these are configured, projects can be created and users can be invited by logging in as the configured root user and using the Create Project and Invite Members buttons (see the user manual [here](https://colony-management.staging.up.railway.app/manual/) or in your locally-deployed instance at `/manual/`)

## Upgrading

Upgrading an instance of LabSafe requires only updating the source code and restarting the `uv run ./start.sh` process.
All dependency updates will be automatically handled by `uv`, and database migrations are automatically applied by `start.sh`.



## Dependencies
Dependencies are, as stated above, managed using `uv`, so only Python 3.13 (or newer) and `uv` are necessary to run the application.
The following dependencies are installed by `uv`, however:

<details>
<summary>Direct Dependencies</summary>

- `django>=5.2.7`
- `openpyxl>=3.1.5`
- `pandas>=2.3.3`
- `django-anymail>=13.1`
- `gunicorn>=23.0.0`
- `whitenoise>=6.11.0`
- `psycopg>=3.3.2`
- `pyrefly>=0.50.1`
- `jinja2>=3.1.6`
- `django-csp>=4.0`
- `scikit-learn>=1.4`
- `joblib>=1.5.3`

</details>
<details>
<summary>Development Dependencies</summary>

- `black>=25.9`
- `django-stubs>=5.2.7`
- `django-upgrade>=1.29`
- `djhtml>=3.0.10`
- `pre-commit>=4.3`
- `pre-commit-update>=0.8.0`
- `pyrefly>=0.50.1`
- `pytest>=8.4.2`
- `pytest-cov>=7.0.0`
- `pytest-django>=4.11.1`
- `ruff>=0.13.3`
- `types-jinja2>=2.11.9`

</details>

<details>
<summary>All Dependencies</summary>

- `asgiref==3.10.0`
- `black==25.9.0`
- `certifi==2025.10.5`
- `cfgv==3.4.0`
- `charset-normalizer==3.4.4`
- `click==8.3.0`
- `coverage==7.12.0`
- `distlib==0.4.0`
- `django==5.2.7`
- `django-anymail==13.1`
- `django-csp==4.0`
- `django-stubs==5.2.7`
- `django-stubs-ext==5.2.7`
- `django-upgrade==1.29.0`
- `djhtml==3.0.10`
- `et-xmlfile==2.0.0`
- `filelock==3.19.1`
- `gitdb==4.0.12`
- `gitpython==3.1.45`
- `gunicorn==23.0.0`
- `identify==2.6.15`
- `idna==3.11`
- `iniconfig==2.1.0`
- `jinja2==3.1.6`
- `joblib==1.5.3`
- `markupsafe==3.0.3`
- `mypy-extensions==1.1.0`
- `nodeenv==1.9.1`
- `numpy==2.3.4`
- `openpyxl==3.1.5`
- `packaging==25.0`
- `pandas==2.3.3`
- `pathspec==0.12.1`
- `platformdirs==4.4.0`
- `pluggy==1.6.0`
- `pre-commit==4.3.0`
- `pre-commit-update==0.8.0`
- `psycopg==3.3.2`
- `pygments==2.19.2`
- `pyrefly==0.50.1`
- `pytest==8.4.2`
- `pytest-cov==7.0.0`
- `pytest-django==4.11.1`
- `python-dateutil==2.9.0.post0`
- `pytokens==0.1.10`
- `pytz==2025.2`
- `pyyaml==6.0.3`
- `requests==2.32.5`
- `ruamel-yaml==0.18.15`
- `ruamel-yaml-clib==0.2.14`
- `ruff==0.13.3`
- `scikit-learn==1.8.0`
- `scipy==1.17.0`
- `six==1.17.0`
- `smmap==5.0.2`
- `sqlparse==0.5.3`
- `threadpoolctl==3.6.0`
- `tokenize-rt==6.2.0`
- `tomli==2.3.0`
- `types-jinja2==2.11.9`
- `types-markupsafe==1.1.10`
- `types-pyyaml==6.0.12.20250915`
- `typing-extensions==4.15.0`
- `tzdata==2025.2`
- `urllib3==2.5.0`
- `virtualenv==20.34.0`
- `whitenoise==6.11.0`

</details>
