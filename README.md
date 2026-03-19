# Wedding Flask

Flask application buit to manage RSVPs to my wedding. Handles simple authentication against invite name (similar to most commercial wedding platforms), email notification, etc. Uses Airtable as its source of truth and de facto admin interface to support non-technical users (e.g., my partner) in making changes to site language, invite lists, etc.

## Setting Up a Local Environment

This project uses the `uv` package and project manager. [Consult the documentation for installation instructions](https://github.com/astral-sh/uv). Then, from the root directory...

```bash
uv sync
uv run --env-file .env flask --app wedding_flask.app run
```

You'll need a `.env` file containing connection string parameters and keys for authentication (see [`.env.example`](https://github.com/ericrobskyhuntley/wedding-flask/blob/main/.env.example)).

```sh
AT_KEY= # Airtable key
AT_BASE_ID= # Airtable base ID
SECRET_KEY= # Flask secret key. See below.
OPENCAGE_KEY= # OpenCage API key. Only necessary if you're geocoding addresses.
MAPBOX_KEY= # Mapbox API key. Only necessary if you're geocoding addresses.
MAIL_SERVER= # Mail server for notifications.
MAIL_PORT= # Mail server port for notifications.
MAIL_USERNAME= # Mail server username for notifications.
MAIL_PASSWORD= # Mail server password for notifications.
```

 To generate a Flask secret key, copy the output of...

 ```bash
python -c 'import secrets; print(secrets.token_hex())'
```