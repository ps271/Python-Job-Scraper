# Python Job Scraper with Email & Telegram Alerts

A **configurable Python-based job scraping system** designed to extract remote job listings, applies filtering logic,
stores only new jobs and sends batch alerts via Email & Telegram.  
This project implements a structured approach with retry logic, CAPTCHA detection, deduplication logic and secure 
credential management.

---

## Features

- **Category/Tag Filtering:** Scrape jobs by categories like Software, Engineering, Management, etc.
- **Retry & Backoff:** Handles network issues and rate limits with exponential backoff retries.
- **CAPTCHA Awareness:** Detects CAPTCHA responses and implements warm-up requests to avoid blocks.
- **Logging:** Tracks scraping activity, warnings, and errors in `scraper.log`.
- **Duplicate Prevention:** Keeps track of previously scraped job links to avoid duplicates.
- **CSV Output:** Structured output for easy data consumption and further analysis.
- **Lightweight & Configurable:** Only requires `requests` and `BeautifulSoup` with `lxml/html` parser.
- **Batched Telegram Alerts**
- **Batched Email Alerts**
- **User Agent Rotation**
- **Environment Variable Support**(.env)
- **Config Driven Architecture**

---

## Tech Stack

- Python 3.x
- Requests
- BeautifulSoup4
- SMTP (Gmail App Password)
- Telegram Bot API
- python-dotenv

---

## Installation

1. Clone the repository and save on your system
2. Create a virtual environment and activate it
3. Install Dependencies using command : 
pip install -r requirements.txt
4. Create 2 directories in app/ namely - logs and data respectively
5. Change directory by - cd app/
6. Run - python -m main

---

## Environment Variables Setup

Create a `.env` file in the root directory:
EMAIL_SENDER=your_email

EMAIL_PASSWORD=your_gmail_app_password
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

---

## Configuration

Edit `config.json` to control:

- Maximum jobs per run
- Delay range
- Tag filters
- Filter mode (AND / OR)
- Title keywords
- Alert enable/disable settings
- Recipient email list

---

## Example Output in Telegram and Email

59 New Jobs Found:

1. Member of Technical Staff Financial Infrastructure
     Anchorage Digital
     United States
     https://remoteok.com/remote-jobs/remote-member-of-technical-staff-financial-infrastructure-anchorage-digital-1130556
2. Senior Security Engineer
     Nansen.ai
     🌏 Probably worldwide
     https://remoteok.com/remote-jobs/remote-senior-security-engineer-nansen-ai-1130555
3. Product Engineer
     Fronted AS
     🇪🇺 Europe
     https://remoteok.com/remote-jobs/remote-product-engineer-fronted-as-1130554
4. Senior 3D Artist Monopoly GO
     Scopely
     Culver City
     https://remoteok.com/remote-jobs/remote-senior-3d-artist-monopoly-go-scopely-1130551
5. Senior User Experience Designer
     Virtru
     _
     https://remoteok.com/remote-jobs/remote-senior-user-experience-designer-virtru-1130547
     '+'54 more jobs

**Here is Summary of Jobs**

- engineering : 23
- python : 3
- linux : 0
- code : 8
- technical : 27
- developer : 11
- cloud : 8
- software : 14
- engineer : 19
- backend : 3
- api : 3
- management : 15
- senior : 23
- devops : 1
- full-time : 2
- microsoft : 2
