# Implementation Plan: Production Deployment Guide

Create a detailed, step-by-step roadmap for deploying the Nexora content platform to a live production environment.

## User Review Required

> [!IMPORTANT]
> The plan assumes a standard Linux (Ubuntu) VPS deployment. If you prefer a platform-as-a-service (like Heroku or Railway), some steps (like Nginx setup) will be handled automatically by the provider.

## Proposed Changes

### [NEW] [production_deployment_plan.md](file:///C:/Users/ammar/.gemini/antigravity/brain/6d7359ce-630a-4f0c-b15a-da6f6b14c967/artifacts/production_deployment_plan.md)
Creation of a dedicated artifact containing:
- **Phase 1: Environment & Security**: Setting up `.env` and `SECRET_KEY` hygiene.
- **Phase 2: Database Migration**: Moving from SQLite to PostgreSQL.
- **Phase 3: Web Server Stack**: Configuring Gunicorn (WSGI) and Nginx (Reverse Proxy).
- **Phase 4: Automation (The Heart of Nexora)**: Setting up `Systemd` services and timers to run the Article Fetcher, Reddit Scraper, and Matcher every few hours without human intervention.
- **Phase 5: SSL & Final Polish**: Implementing Certbot for HTTPS and domain configuration.

## Open Questions
- **Hosting Preference**: Do you have a specific hosting provider in mind (e.g., DigitalOcean, AWS, Heroku)?
- **Domain Name**: Do you already have a domain name purchased for Nexora?

## Verification Plan
### Manual Verification
- Review the final deployment plan artifact to ensure it covers all Nexora-specific modules (matcher, scrapers, oauth).
