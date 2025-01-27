import asyncio
import pandas as pd
import json
import os
import logging
from asyncio import Semaphore
from pyppeteer import launch
from bs4 import BeautifulSoup

# Get the absolute path to the directory containing the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Get the absolute path to the parent directory
project_dir = os.path.dirname(os.path.dirname(script_dir))
# Construct the absolute path to the data directory
data_dir = os.path.join(project_dir, "data")

html_dir = os.path.join(data_dir, 'wikicrow/html')
json_dir = os.path.join(data_dir, 'wikicrow/json')

# Create directories if they don't exist
os.makedirs(html_dir, exist_ok=True)
os.makedirs(json_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_pyppeteer.log"),
        logging.StreamHandler()  # Output to console as well
    ]
)

MAX_RETRIES = 1


async def fetch_html(url, max_retries=MAX_RETRIES):
    """Fetches the HTML content of a webpage using Pyppeteer with retries."""
    for attempt in range(max_retries):
        browser = None
        try:
            logging.info(f"Attempting to launch browser for {url}, attempt {attempt+1}")
            browser = await launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])  # Added headless mode and sandbox
            page = await browser.newPage()
            await page.setViewport({'width': 1920, 'height': 1080})
            await page.goto(url, {'waitUntil': 'domcontentloaded'})  # Wait for page content to load.
            await page.waitForSelector("div#References", {'timeout': 10000})
            page_html = await page.content()
            logging.info(f"Successfully fetched HTML from {url}")
            return page_html
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed to download HTML from {url}: {e}")
            if attempt == max_retries - 1:
                logging.error(f"All retries failed to download HTML from {url} - unable to retrieve the page.")
                return None
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception as close_err:
                  logging.error(f"Error during browser close for {url}: {close_err}")



def validate_html(html_content):
    """Validates if the HTML content contains valid data."""
    if not html_content:
        return False, None

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Check for "insufficient data" warnings
        warning_div = soup.find('div', attrs={'data-status': 'warning'})
        if warning_div:
            return True, "Insufficient published research for high-quality article"

        warning_header = soup.find('h2', string="Warning")
        if warning_header:
            return True, "Insufficient scholarly sources found"
        
        return True, None
    except Exception as e:
        logging.error(f"Error validating HTML: {e}")
        return False, f"Error validating HTML: {e}"



def extract_data(html_content, gene_name):
    """Extracts structured data from HTML content using BeautifulSoup."""
    if not html_content:
        return None, "HTML could not be fetched"

    data = {"gene_name": gene_name}

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

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
                    # Check that the elements and their children are there before accessing .text
                    if info_list_items[0].find('p'):
                        data['gene_names'] = info_list_items[0].find('p').text.replace('gene names: ', '').strip()
                    if info_list_items[1].find('p'):
                        data['gene_alias'] = info_list_items[1].find('p').text.replace('gene alias: ', '').strip()
                    if info_list_items[2].find('p'):
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
                            'chr': cells[0].text.strip() if cells[0] else None,
                            'end': cells[1].text.strip() if cells[1] else None,
                            'start': cells[2].text.strip() if cells[2] else None,
                            'strand': cells[3].text.strip() if cells[3] else None,
                            }

        # Extract Related Genes
        related_genes_header = soup.find('h2', string='Related Genes')
        if related_genes_header:
            related_genes_div = related_genes_header.find_parent(
                'div').find_parent('div').find_next_sibling('div')
            if related_genes_div:
                related_genes = [div.find('p').text for div in related_genes_div.find_all('div', role='button') if div.find('p')]
                data['related_genes'] = related_genes

        # Extract text from Overview, Structure, Functions, Interactions, Clinical Significance sections
        sections = ['Overview', 'Structure', 'Functions', 'Interactions', 'Clinical Significance']
        for section_id in sections:
            section_header = soup.find('h2', string=section_id)
            if section_header:
                section_div = section_header.find_parent('div')
                if section_div:
                    text_content = " ".join([p.text for p in section_div.find_all('p') if p])
                    data[section_id.lower()] = text_content.strip()

        # Extract references
        references_header = soup.find('h2', string='References')
        if references_header:
            references_section = references_header.find_parent('div')
            if references_section:
                references = []
                for li in references_section.find_all('li'):
                    if li.find('p'):
                        text_content = li.find('p').text
                        references.append(text_content.strip())
                data['references'] = references

        return data, None
    except Exception as e:
        logging.error(f"Error extracting data for {gene_name}: {e}")
        data["error"] = f"Extraction error: {e}"
        return data, f"Extraction error: {e}"



async def process_gene(gene_name, html_dir, json_dir, semaphore):
    """Processes a single gene, including fetching, extracting, and saving data."""
    async with semaphore:
        url = f"https://wikicrow.ai/{gene_name}"
        html_filename = os.path.join(html_dir, f"{gene_name}.html")
        json_filename = os.path.join(json_dir, f"{gene_name}.json")

        try:
            # Check if JSON file already exists
            if os.path.exists(json_filename):
                logging.info(f"JSON file exists: {json_filename}, skipping HTML fetch")
                return

            # Check if HTML file exists and is valid
            if os.path.exists(html_filename):
                try:
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
                        logging.info(f"Invalid HTML file found: {html_filename}, refetching. Error: {error_message}")
                except Exception as file_error:
                    logging.error(f"Error reading or validating existing HTML file: {html_filename}, refetching. Error: {file_error}")

            logging.info(f"Fetching: {url}")
            html_content = await fetch_html(url)

            # Save HTML content to file
            if html_content:
                try:
                    with open(html_filename, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                        is_valid, error_message = validate_html(html_content)
                        if not is_valid:
                            logging.info(f"HTML file did not have valid data: {html_filename}, skipping json output. Error: {error_message}")
                            return
                except Exception as save_html_err:
                    logging.error(f"Error saving HTML file: {html_filename}. Error: {save_html_err}")
                    return

            extracted_data, error = extract_data(html_content, gene_name)
            
            if error:
                if extracted_data:
                    extracted_data["error"] = error
                else:
                    extracted_data = {"gene_name": gene_name, "error": error}

            if extracted_data:
                # Save extracted data as JSON
                try:
                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump(extracted_data, f, indent=4)
                except Exception as save_json_err:
                    logging.error(f"Error saving JSON file: {json_filename}. Error: {save_json_err}")
        except Exception as main_error:
            logging.error(f"Error processing gene {gene_name}: {main_error}")


async def main():
    try:
        gene_df = pd.read_csv(os.path.join(data_dir, 'gene_df.csv'))

        semaphore = Semaphore(10)
        tasks = [
            process_gene(
                row['gene_name'].upper(), html_dir, json_dir, semaphore
            )
            for index, row in gene_df.iterrows()
        ]
        await asyncio.gather(*tasks)
    except Exception as e:
        logging.error(f"An error occured during execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
    logging.info("Data processing complete.")