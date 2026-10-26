# EmailApp (template)

EmailApp is a Flask-based web application designed to manage Cloudflare email routing rules. It enables users to efficiently view, create, and delete email routing rules, incorporating authentication and security features. The application is containerized using Docker and configured for deployment with Docker Compose.

> **Self-hosted template.** This is a single-user tool: you run it yourself with **your own** Cloudflare API token, zone and domain. It does not host anyone else's domain or mailboxes, and there is no shared instance. Run it behind HTTPS, keep your `.env` private, and use it at your own risk (MIT licence, no warranty).

## Features

- **View Email Routing Rules**: Display existing Cloudflare email routing rules in a user-friendly interface.
- **Create New Rules**: Add new email routing rules seamlessly.
- **Delete Rules**: Remove unnecessary or outdated routing rules.
- **User Authentication**: Secure access to the application through user authentication mechanisms.
- **Docker Containerization**: Simplified deployment and scalability using Docker and Docker Compose.

## Prerequisites

- **Docker**: Ensure Docker is installed on your system.
- **Docker Compose**: Verify that Docker Compose is installed.

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/99Rares/EmailApp-template.git
   cd EmailApp-template
   
2. **Configure Environment Variables**:

- Create a .env file in the project root directory.
- Define the necessary environment variables, such as Cloudflare API credentials and authentication secrets.
- **Example** `.env` File
    ```env
    # Flask configuration
    SECRET_KEY='your-secret-key'
    # Set false only for local HTTP development; keep true behind HTTPS.
    SESSION_COOKIE_SECURE='false'
    RATELIMIT_STORAGE_URI='memory://'  # Use Redis in multi-instance deployments.
    RATELIMIT_DEFAULTS='5000 per day,500 per hour'
    # Passkey sign-in: the exact https origin(s) the app is served from (comma-separated).
    # Once a passkey is registered, password login is switched off; run ./reset_passkeys.sh on the server if every passkey is lost.
    # Leave empty to disable passkeys. Passkeys are stored in PASSKEY_DB_PATH (a Docker volume).
    PASSKEY_ORIGINS='https://email.example.com'
    
    # Cloudflare API configuration
    ACCOUNT_ID='your-account-id'
    CLOUDFLARE_ZONE_ID='your-cloudflare-zone-id'
    CLOUDFLARE_API_TOKEN='your-cloudflare-api-token'
    
    # Email routing configuration
    PLACEHOLDER_EMAIL_DOMAIN='your-placeholder-email-domain'
    
    # Admin and user configuration
    ADMIN_PASSWORD_HASH='your-admin-password-hash'  # Use a hashed password for security
    MY_USER='your-username'
    EMAIL_LIST='email1@example.com,email2@example.com'  # Comma-separated list of emails
3. **Build and Start the Application**:
    ```bash
    docker-compose up --build
    ```
    This command builds the Docker images and starts the application.

4. **Access the Application**:

- Open your web browser and navigate to http://localhost:5000 to access EmailApp.
## Usage
1. **Log In**: Enter your credentials to access the application.
2. **View Rules**: Browse the list of existing email routing rules.
3. **Add Rule**: Click on "Add Rule" to create a new routing rule.
4. **Delete Rule**: Use the delete option next to a rule to remove it.
   
## Project Structure
- `app.py`: Flask routes and Gunicorn entrypoint.
- `email_app/config.py`: Environment-backed settings.
- `email_app/services/`: Cloudflare client, routing rules, and word generation.
- `templates/` and `static/`: UI templates and browser assets.
- `tests/`: Pytest regression and security coverage.
- `docker-compose.yml`: Configures the Docker services.

- `Dockerfile`: Defines the Docker image for the application.

- `.env`: Stores environment variables (not included in the repository for security).
