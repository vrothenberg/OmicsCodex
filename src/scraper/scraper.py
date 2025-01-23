import asyncio
import pandas as pd
import json
import os
import logging
from asyncio import Semaphore
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()  # Output to console as well
    ]
)

MAX_RETRIES = 1

async def fetch_html(url, geckodriver_path='/Users/vince/Salk/NeuroCircadia/utils/geckodriver', max_retries=MAX_RETRIES):
    """Fetches the HTML content of a webpage using Selenium with retries."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')
    service = Service(executable_path=geckodriver_path)

    for attempt in range(max_retries):
        driver = webdriver.Firefox(service=service, options=options)
        try:
            page_html = await asyncio.to_thread(_get_page_html, driver, url)
            logging.info(f"Successfully fetched HTML from {url}")
            return page_html
        except WebDriverException as e:
            logging.warning(f"WebDriverException occurred while fetching HTML from {url}: {e}")
            if attempt == max_retries - 1:
                logging.error(f"All retries failed to download HTML from {url} due to WebDriverException")
                return None
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed to download HTML from {url}: {e}")
            if attempt == max_retries - 1:
                logging.error(f"All retries failed to download HTML from {url}")
                return None
            await asyncio.sleep(2 ** attempt)
        finally:
            driver.quit()


def _get_page_html(driver, url):
    driver.get(url)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div#References"))
    )
    return driver.page_source


def validate_html(html_content):
    """Validates if the HTML content contains valid data."""
    if not html_content:
        return False, None

    soup = BeautifulSoup(html_content, 'html.parser')

    # Check for "insufficient data" warnings
    warning_div = soup.find('div', attrs={'data-status': 'warning'})
    if warning_div:
        return True, "Insufficient published research for high-quality article"

    warning_header = soup.find('h2', string="Warning")
    if warning_header:
        return True, "Insufficient scholarly sources found"

    # Check for presence of the info section, indicating valid data
    info_header = soup.find('h2', string='Info')
    if info_header:
        return True, None

    return False, "Missing gene info"


def extract_data(html_content, gene_name):
    """Extracts structured data from HTML content using BeautifulSoup."""
    if not html_content:
        return None, "HTML could not be fetched"

    soup = BeautifulSoup(html_content, 'html.parser')
    data = {"gene_name": gene_name}

    # Check for "insufficient data" warnings
    warning_div = soup.find('div', attrs={'data-status': 'warning'})
    if warning_div:
        data["error"] = "Insufficient published research for high-quality article"
        return data, None

    warning_header = soup.find('h2', string="Warning")
    if warning_header:
        data["error"] = "Insufficient scholarly sources found"
        return data, None

    # Extract gene info
    info_header = soup.find('h2', string='Info')
    if info_header:
        info_section = info_header.find_parent('div').find_parent('div')
        if info_section:
            info_list_items = info_section.find_all('li')
            if len(info_list_items) >= 3:
                data['gene_names'] = info_list_items[0].find('p').text.replace('gene names: ', '').strip()
                data['gene_alias'] = info_list_items[1].find('p').text.replace('gene alias: ', '').strip()
                data['gene_type'] = info_list_items[2].find('p').text.replace('type: ', '').strip()

    # Extract gene position
    position_header = soup.find('h2', string='Gene Position (hg19)')
    if position_header:
        table = position_header.find_parent('div').find_next_sibling('table')
        if table:
            rows = table.find_all('tr')
            if len(rows) > 1:
                cells = rows[1].find_all('td')
                if len(cells) == 4:
                    data['gene_position'] = {
                        'chr': cells[0].text.strip(),
                        'end': cells[1].text.strip(),
                        'start': cells[2].text.strip(),
                        'strand': cells[3].text.strip(),
                    }

    # Extract Related Genes
    related_genes_header = soup.find('h2', string='Related Genes')
    if related_genes_header:
        related_genes_div = related_genes_header.find_parent('div').find_next_sibling('div')
        if related_genes_div:
            related_genes = [div.find('p').text for div in related_genes_div.find_all('div', role='button')]
            data['related_genes'] = related_genes

    # Extract text from Overview, Structure, Functions, Interactions, Clinical Significance sections
    sections = ['Overview', 'Structure', 'Functions', 'Interactions', 'Clinical Significance']
    for section_id in sections:
        section_header = soup.find('h2', string=section_id)
        if section_header:
            section_div = section_header.find_parent('div')
            if section_div:
                text_content = " ".join([p.text for p in section_div.find_all('p')])
                data[section_id.lower()] = text_content.strip()

    # Extract references
    references_header = soup.find('h2', string='References')
    if references_header:
        references_section = references_header.find_parent('div')
        if references_section:
            references = []
            for li in references_section.find_all('li'):
                text_content = li.find('p').text
                references.append(text_content.strip())
            data['references'] = references

    return data, None


async def process_gene(gene_name, html_dir, json_dir, geckodriver_path, semaphore):
    """Processes a single gene, including fetching, extracting, and saving data."""
    async with semaphore:
        url = f"https://wikicrow.ai/{gene_name}"
        html_filename = os.path.join(html_dir, f"{gene_name}.html")
        json_filename = os.path.join(json_dir, f"{gene_name}.json")

        # Check if JSON file already exists
        if os.path.exists(json_filename):
            logging.info(f"JSON file exists: {json_filename}, skipping HTML fetch")
            return

        # Check if HTML file exists and is valid
        if os.path.exists(html_filename):
            with open(html_filename, 'r', encoding='utf-8') as f:
                html_content = f.read()
            is_valid, error_message = validate_html(html_content)
            if is_valid:
                logging.info(f"Valid HTML file exists: {html_filename}, skipping fetch")
                extracted_data, _ = extract_data(html_content, gene_name)
                if extracted_data:
                    # Save extracted data as JSON
                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump(extracted_data, f, indent=4)
                return
            else:
                logging.info(f"Invalid HTML file found: {html_filename}, refetching.")

        logging.info(f"Fetching: {url}")
        html_content = await fetch_html(url, geckodriver_path)

        # Save HTML content to file
        if html_content:
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
                is_valid, error_message = validate_html(html_content)
                if not is_valid:
                    logging.info(f"HTML file did not have valid data: {html_filename}, skipping json output")
                    return

        extracted_data, error = extract_data(html_content, gene_name)

        if error:
            if extracted_data:
                extracted_data["error"] = error
            else:
                extracted_data = {"gene_name": gene_name, "error": error}

        if extracted_data:
            # Save extracted data as JSON
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=4)


async def main():
    geckodriver_path = '/Users/vince/Salk/NeuroCircadia/utils/geckodriver'
    gene_df = pd.read_csv('gene_df.csv')
    html_dir = 'data/html'
    json_dir = 'data/json'

    # Create directories if they don't exist
    os.makedirs(html_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    semaphore = Semaphore(8)  # Limit to 4 concurrent workers
    tasks = [
        process_gene(
            row['gene_name'].upper(), html_dir, json_dir, geckodriver_path, semaphore
        )
        for index, row in gene_df.iterrows()
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
    logging.info("Data processing complete.")