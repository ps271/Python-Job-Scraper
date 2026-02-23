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


# Configure logging
logging.basicConfig(
    filename='scraper.log',       # file where logs are saved
    level=logging.INFO,           # log INFO and above
    format='%(asctime)s - %(levelname)s - %(message)s'
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://remoteok.com/"
}

csv_base = "remote_jobs"
csv_fields = [
    "title", "company_name", "location",
    "salary", "apply_link", "tags", "time", "scraped_at"
]


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


def load_existing_links(csv_file):
    if not os.path.isfile(csv_file):
        return set()
    # make a set of existing "apply_links" of jobs already in csv file
    existing_links = set()
    for file in glob.glob(f"{csv_base}_*.csv"):
        with open(file, "r", encoding="utf-8") as f:
            existing_links.update({row['apply_link'] for row in csv.DictReader(f)})
    return existing_links

# Generate today's CSV file
def get_today_csv():
    date_str = datetime.now().strftime("%Y%m%d")
    return f"{csv_base}_{date_str}.csv"

#csv writer

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


#HTML Parser
def html_parser(response, base_url):
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
                        "scraped_at": datetime.now().strftime("%d/%m/%Y")
                    }
                    if job_data["apply_link"]: # only append valid jobs
                        jobs_scraped.append(job_data)
                except Exception as e:
                    logging.warning(f'failed to parse job Row: {e}')
                    continue
    return jobs_scraped

# Request Handling

def get_jobs_page(params, base_url, retries=3):
    for attempt in range(retries):
        try:
            response = session.get(url=base_url, params=params, timeout=10)
            if response.status_code == 200:
                if "captcha" in response.text.lower():
                    logging.warning(
                        f"CAPTCHA detected — attempt {attempt + 1}/{retries}, backing off"
                    )
                    time.sleep((2 ** attempt) + random.uniform(1,2))
                    continue
                return html_parser(response, base_url=base_url)
            elif response.status_code in (429, 403): # checking rate limiting and forbidden request
                logging.warning(
                    f"Blocked (status {response.status_code}) — attempt {attempt+1}/{retries}"
                )
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
    base_url = "https://remoteok.com"
    try:
        session.get(url=base_url, timeout=10) # a warmup request to avoid captcha
        time.sleep(random.uniform(5,8))
    except Exception as e:
        logging.error(f'Failed to establish connection to server. An error {e} occured')
    params = {'action' : 'get_jobs',
              'premium' : '0',
              'offset' : 0}
    total_scraped = 0
    success = True
    csv_file = get_today_csv()
    existing_links = load_existing_links(csv_file=csv_file)
    while True:
        items = get_jobs_page(params=params, base_url=base_url)
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
        if total_scraped>100:
            break
        params['offset'] += len(items)
        time.sleep(random.uniform(5, 10))
    session.close()
    return success, total_scraped
if __name__ == "__main__":
    # clear_csv()
    start_time = time.time()
    status, total_jobs = main()
    end_time = time.time()
    if status:
        logging.info(f"Scraping finished. Total jobs: {total_jobs}, runtime = {end_time-start_time:.2f}s")
        print(f"Scraping finished. Total jobs: {total_jobs}, runtime = {end_time-start_time:.2f}s")
    else:
        print(f"Scraping Failed. Request failure")