import requests
from bs4 import BeautifulSoup
from bs4.exceptions import FeatureNotFound
from datetime import datetime
import time
import random
import logging
import os
import csv
import glob
import json
from dotenv import load_dotenv
import smtplib
import ssl
from email.message import EmailMessage


# Configure logging
logging.basicConfig(
    filename='logs/scraper.log',       # file where logs are saved
    level=logging.INFO,           # log INFO and above
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Load Environment Variables
load_dotenv()
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# Configurations
def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://remoteok.com/"
}

USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36",

    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",

    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
    "Gecko/20100101 Firefox/122.0",

    # Firefox Linux
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0",

    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.4 Safari/605.1.15",
    
    #Linux
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
]

csv_base = "data/remote_jobs"
csv_fields = [
    "title", "company_name", "location",
    "salary", "apply_link", "tags", "time", "scraped_at"
]

config = load_config()
telegram_enabled = config["telegram"]["enabled"]
email_enabled = config["email"]["enabled"]
email_recipients = config["email"]["recipient_emails"]

# Session creation
session = requests.Session()
session.headers.update(HEADERS)


# Utility Functions
def safe_text(element, default=""):
    try:
        return element.text.strip() if element else ""
    except Exception as e:
        logging.warning(f'{element} has no Attribute "text" : {e}')
        return default


def load_existing_links():
    # make a set of existing "apply_links" of jobs already in csv file
    existing_links = set()
    for file in glob.glob(f"{csv_base}_*.csv"):
        with open(file, "r", encoding="utf-8") as f:
            existing_links.update({row['apply_link'] for row in csv.DictReader(f)})
    return existing_links


def summary_of_jobs(jobs):
    if not jobs:
        logging.info(f"No new jobs found. Cancelling Alerts....")
        return None

    message = ""
    n = len(jobs)
    tag_filter = {t.lower() for t in config["remote_ok_filters"]["tags"]}
    new_filters = {key: 0 for key in tag_filter} # create a key, value pair for all tags in a job listing
    for i in range(min(5,n)):
        message += (
            f"{i+1}. {jobs[i]['title']}\n"
            f"     {jobs[i]['company_name']}\n"
            f"     {jobs[i]['location'] if jobs[i]['location'] else '_'}\n"
            f"     {jobs[i]['apply_link']}\n"
        )
    remaining = n - min(5,n)
    if remaining > 0:
        message += f"     '+'{remaining} more jobs\n\n"
    summary = f"* Here is Summary of Jobs *\n\n"
    for i in range(n):
        tags = list(jobs[i]['tags'].split(', ')) # create a list of tags in a Job
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in new_filters:
                new_filters[tag_lower] += 1
    for tag, tag_value in new_filters.items():
        summary += f"{tag} : {tag_value}\n"
    message += summary
    return message


# Generate today's CSV file
def get_today_csv():
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{csv_base}_{date_str}.csv"


# Alerts Generation
def send_telegram_batch(jobs):
    if not jobs or not telegram_enabled:
        return

    message = f"*{len(jobs)} New Jobs Found!*\n\n"
    if len(jobs)<=5:
        for i, job in enumerate(jobs, 1):
            message += (
                f"{i}. {job['title']}\n"
                f"  Company:   {job['company_name']}\n"
                f"  Location:   {job['location'] if job['location'] else '_'}\n"
                f"  Link:   {job['apply_link']}\n\n"
            )
    else:
        message += summary_of_jobs(jobs=jobs)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message[:4000],  # Telegram limit safeguard
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f'Telegram API Error: {response.status_code}')
    except Exception as e:
        logging.warning(f"Telegram batch alert failed: {e}")


def send_email_batch(jobs):
    if not jobs or not email_enabled:
        return

    msg = EmailMessage()
    msg["Subject"] = f"{len(jobs)} New Jobs Found"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_SENDER

    body = f"{len(jobs)} New Jobs Found:\n\n"
    if len(jobs)<=5:
        for i, job in enumerate(jobs, 1):
            body += (
                f"{i}. {job['title']}\n"
                f"   Company: {job['company_name']}\n"
                f"   Location: {job['location']}\n"
                f"   Link: {job['apply_link']}\n\n"
            )
    else:
        body += summary_of_jobs(jobs=jobs)

    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=context)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg, to_addrs=email_recipients)
    except Exception as e:
        logging.warning(f"Email batch alert failed: {e}")


# csv writer
def append_jobs_to_csv(jobs, existing_links, csv_file):
    file_exists = os.path.isfile(csv_file)
    new_count = 0

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)

        if not file_exists:
            writer.writeheader()

        for job in jobs:
            if job["apply_link"] not in existing_links:
                job_copy = job.copy()
                job_copy["tags"] = ", ".join(job_copy["tags"])
                writer.writerow(job_copy)
                existing_links.add(job["apply_link"])
                new_count += 1
    return new_count
def clear_csv(csv_file):
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()


# CSV Reader
def csv_reader(csv_file):
    jobs = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        jobs = list(reader)
    return jobs


#HTML Parser
def html_parser(response, base_url, tag_filter, filter_mode):
    # Try parsing as JSON (in case some responses are JSON)
    try:
        response_data = response.json()
        jobs_scraped = response_data.get("items", [])
    except ValueError:
        # Fallback: parse as HTML with BeautifulSoup
        try:
            soup = BeautifulSoup(response.text, "lxml")
        except FeatureNotFound:
            soup = BeautifulSoup(response.text, "html.parser")
        jobs_scraped = []
        jobs = soup.find_all("tr", class_="job")
        if jobs:
            filtered_jobs = [job for job in jobs if "placeholder" not in job.get("class", [])]
            for job in filtered_jobs:
                try:
                    company = job.find('td', class_='company') or job.find("td", class_="company_and_position")
                    company_tags = job.find('td', class_='tags')
                    post_time = job.find('td', class_='time')
                    location = ""
                    location_tag = company.find('div', class_='location') if company else None
                    if location_tag:
                        text = location_tag.text.strip()
                        if "Upgrade to Premium" not in text:
                            location = text
                    salary_tag = company.find('div', class_='salary') if company else None
                    salary = safe_text(salary_tag)
                    title_tag = company.find('h2') if company else None
                    title = safe_text(title_tag)
                    comp_name_tag = company.find('h3') if company else None
                    comp_name = safe_text(comp_name_tag)
                    job_data = {
                        'title' : title,
                        'company_name' : comp_name,
                        'location' : location,
                        'salary' : salary,
                        'apply_link' : base_url + company.find('a', class_='preventLink')['href'] if company else "",
                        'tags' : [tag.text.strip() for tag in company_tags.find_all("h3")] if company_tags else [],
                        'time' : post_time.find('time')['datetime'] if post_time else "",
                        "scraped_at": datetime.now().strftime("%d/%m/%Y__%H%M%S")
                    }
                    if job_data["apply_link"]: # only append valid jobs
                        job_tags_lower = {tag.lower() for tag in job_data["tags"]}

                        if tag_filter:
                            if filter_mode == "OR":
                                if not job_tags_lower.intersection(tag_filter):
                                    continue
                            elif filter_mode == "AND":
                                if not tag_filter.issubset(job_tags_lower):
                                    continue
                        jobs_scraped.append(job_data)
                except Exception as e:
                    logging.warning(f'failed to parse job Row: {e}')
                    continue
    return jobs_scraped


# Request Handling
def get_jobs_page(params, base_url, tag_filter, filter_mode, retries=3):
    for attempt in range(retries):
        try:
            response = session.get(url=base_url, params=params, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            job_rows = soup.find_all("tr", class_="job")
            if response.status_code == 200:
                if not job_rows:
                    logging.error(f'No job rows found — treating as blocked page '
                      f'{attempt + 1}/{retries}, backing off')
                    time.sleep((2 ** attempt) + random.uniform(1, 2))
                    session.headers["User-Agent"] = random.choice(USER_AGENTS)
                    continue
                jobs = html_parser(response, base_url=base_url, tag_filter=tag_filter, filter_mode=filter_mode)
                return jobs
            elif response.status_code in (429, 403): # checking rate limiting and forbidden request
                logging.warning(
                    f"Blocked (status {response.status_code}) — attempt {attempt+1}/{retries}"
                )
                time.sleep((2 ** attempt) + random.uniform(1, 2))
                session.headers["User-Agent"] = random.choice(USER_AGENTS)
                continue
            else:
                logging.warning(f"Unexpected status {response.status_code} — attempt {attempt+1}/{retries}")
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout on attempt {attempt + 1} for params {params}")
        except requests.RequestException as e:
            logging.error(f"Request failed: {e}")
        time.sleep((2 ** attempt) + random.uniform(0.1,1))
    logging.critical("Max retries reached — request permanently failed")
    return None


# main function
def main():
    base_url = config["base_url"]
    max_jobs = config["max_jobs"]
    delay_min, delay_max = config["delay_range"]

    tag_filter = {t.lower() for t in config["remote_ok_filters"]["tags"]}
    filter_mode = config["remote_ok_filters"]["mode"]

    try:
        response = session.get(url=base_url, timeout=10) # a warmup request to avoid captcha
        session.cookies.update(response.cookies)
        time.sleep(random.uniform(delay_min,delay_max))
    except Exception as e:
        logging.error(f'Failed to establish connection to server. An error {e} occurred')
    params = {'action' : 'get_jobs',
              'premium' : '0',
              'offset' : 0}
    total_scraped = 0
    success = True
    csv_file = get_today_csv()
    existing_links = load_existing_links()
    while True:
        items = get_jobs_page(params=params, base_url=base_url, tag_filter=tag_filter,
          filter_mode=filter_mode)
        if items is None:
            logging.error("Stopping due to request failure")
            success = False
            break
        elif not items:
            logging.info("No more data -- Breaking the loop.")
            break
        new_items = append_jobs_to_csv(jobs=items, existing_links=existing_links, csv_file=csv_file)
        total_scraped += new_items
        logging.info(f"Scraped {len(items)} jobs, total so far = {total_scraped}")
        if total_scraped>max_jobs:
            break
        params['offset'] += len(items)
        time.sleep(random.uniform(delay_min, delay_max))
    session.close()
    return success, total_scraped, csv_file
if __name__ == "__main__":
    # clear_csv()
    start_time = time.time()
    status, total_jobs, csv_file_latest = main()
    end_time = time.time()
    if status:
        new_jobs = csv_reader(csv_file=csv_file_latest)
        send_telegram_batch(jobs=new_jobs)
        send_email_batch(jobs=new_jobs)
        logging.info(f"Scraping finished. Total jobs: {total_jobs}, runtime = {end_time-start_time:.2f}s")
        print(f"Scraping finished. Total jobs: {total_jobs}, runtime = {end_time-start_time:.2f}s")
    else:
        print(f"Scraping Failed. Request failure, runtime = {end_time-start_time:.2f}s")