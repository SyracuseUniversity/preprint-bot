# Preprint Bot – Django Web Interface

A Django conversion of the Streamlit-based Preprint Bot frontend.  
Connects to the **same PostgreSQL database** used by the FastAPI backend.

## Architecture

```
                         ┌─────────────────────┐
                         │   PostgreSQL         │
                         │   (preprint_bot DB)  │
                         └──────┬──────┬────────┘
                                │      │
                 ┌──────────────┘      └──────────────┐
                 │                                    │
        ┌────────▼────────┐                 ┌─────────▼────────┐
        │  FastAPI Backend │                 │  Django Website   │
        │  (pipeline, API) │                 │  (this project)   │
        └─────────────────┘                 └──────────────────┘
```

Both the FastAPI backend (which runs the recommendation pipeline) and this
Django site read/write the same tables. Django models use `managed = False`
so `migrate` never touches the existing schema.

## Prerequisites

- **Python 3.10+**
- **PostgreSQL 16** with the **pgvector** extension

### Installing PostgreSQL (Ubuntu / WSL)

If you don't already have PostgreSQL installed:

```bash
# Add the official PostgreSQL apt repository
sudo apt install -y curl ca-certificates
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc

echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
    https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
    | sudo tee /etc/apt/sources.list.d/pgdg.list

# Install PostgreSQL 16 + pgvector
sudo apt update
sudo apt install -y postgresql-16 postgresql-16-pgvector

# Start the service (WSL doesn't use systemctl)
sudo pg_ctlcluster 16 main start

# Set a password for the postgres superuser
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'your-pg-password';"
```

### macOS

```bash
brew install postgresql@16
brew services start postgresql@16
brew install pgvector
```

## Quick Start

```bash
# 1. Set up the database (run from the project root, next to database_schema.sql)
chmod +x setup_database.sh
./setup_database.sh
#    → prompts for DB name, user, password, etc.
#    → creates the database, loads the schema, writes django_site/.env

# 2. Create a virtual environment and install dependencies
cd django_site
python3 -m venv venv
source venv/bin/activate          # On Windows WSL this is the same
pip install -r requirements.txt

# 3. Run Django migrations (creates Django's own tables: sessions, admin, etc.)
python manage.py migrate

# 4. Start the dev server
python manage.py runserver 0.0.0.0:8001
```

Visit http://localhost:8001 and sign in with any account that already
exists in the `users` table (created via the Streamlit/FastAPI frontend),
or register a new account directly.

> **WSL note:** PostgreSQL won't auto-start when you open a new terminal.
> Run `sudo pg_ctlcluster 16 main start` each time, or add it to your
> `~/.bashrc`.

## Environment Variables

| Variable             | Default          | Description                         |
|----------------------|------------------|-------------------------------------|
| `DATABASE_NAME`      | `preprint_bot`   | PostgreSQL database name            |
| `DATABASE_USER`      | `postgres`       | PostgreSQL user                     |
| `DATABASE_PASSWORD`  | (empty)          | PostgreSQL password                 |
| `DATABASE_HOST`      | `localhost`      | PostgreSQL host                     |
| `DATABASE_PORT`      | `5432`           | PostgreSQL port                     |
| `DJANGO_SECRET_KEY`  | (dev fallback)   | Set a real key in production        |
| `DJANGO_DEBUG`       | `True`           | Set to `False` in production        |
| `PDF_DATA_DIR`       | `../pdf_data`    | Root of the PDF storage tree        |

## Project Structure

```
django_site/
├── manage.py
├── requirements.txt
├── preprint_bot_web/          # Django project package
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── core/                      # Main application
    ├── models.py              # ORM models (managed=False)
    ├── views.py               # All view functions
    ├── urls.py                # URL routing
    ├── forms.py               # Django forms
    ├── auth_backend.py        # Custom PBKDF2 auth against users table
    ├── arxiv_categories.py    # Category tree data + helpers
    ├── context_processors.py  # Template context helpers
    ├── admin.py               # Django admin registration
    ├── templatetags/
    │   └── core_tags.py
    └── templates/
        ├── base.html          # Shared layout, nav, CSS
        ├── dashboard.html
        ├── settings.html
        ├── help.html
        ├── auth/
        │   ├── login.html
        │   ├── register.html
        │   ├── forgot_password.html
        │   └── reset_password.html
        ├── profiles/
        │   ├── list.html      # Profile list + paper management
        │   └── create.html    # Create / edit form + category tree
        └── recommendations/
            └── list.html      # Filtered, paginated, date-grouped
```

## Key Differences from Streamlit

| Aspect              | Streamlit version               | Django version                    |
|---------------------|---------------------------------|-----------------------------------|
| Auth                | Cookie-based API tokens         | Django sessions + PBKDF2 backend  |
| State               | `st.session_state`              | Django sessions + GET params      |
| Category picker     | `st_ant_tree` widget            | Pure JS checkbox tree             |
| Pagination          | `st.rerun()` loop               | Standard `?page=N` GET params     |
| File uploads        | Streamlit `file_uploader`       | Standard `<form enctype=…>`       |
| Real-time progress  | SSE polling                     | Not implemented (use pipeline CLI)|

## Notes

- The Django site does **not** run the recommendation pipeline itself.
  The FastAPI backend + `preprint_bot` CLI still handle fetching, embedding,
  and generating recommendations. This site is purely a frontend.

- Django's `migrate` creates its own tables (`django_session`,
  `django_content_type`, etc.) but does **not** touch the preprint_bot
  tables because all models use `managed = False`.

- The arXiv "Add from arXiv" feature in the profile page downloads PDFs
  via `requests` and saves them to the `pdf_data/user_pdfs/` directory,
  just like the Streamlit version.
