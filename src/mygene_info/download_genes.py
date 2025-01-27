import os
import sys
import json
import time
import mygene
import pandas as pd
import logging
import httpx

# Get the absolute path to the directory containing the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Get the absolute path to the parent directory
project_dir = os.path.dirname(os.path.dirname(script_dir))
# Construct the absolute path to the data directory
data_dir = os.path.join(project_dir, "data")

gene_csv_path = os.path.join(data_dir, "gene_df.csv")

# Setup logging to file in script directory
log_file = os.path.join(script_dir, "download_genes.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)

mg = mygene.MyGeneInfo()


def fetch_gene_data(gene_names):
    """Fetches gene data using mygene with retries and backoff."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            query_results = mg.querymany(
                gene_names, scopes="symbol", fields="all", returnall=True,
            )
            # Filter out failed queries
            hits = [hit for hit in query_results['out'] if 'notfound' not in hit]
            return hits, query_results['missing']

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                delay = min(2 ** attempt, 10)  # cap the delay at 10 seconds
                logging.error(
                    f"Error fetching data for {gene_names}: Client error "
                    f"'{e.response.status_code} {e.response.reason_phrase}' "
                    f"for url '{e.request.url}'. Retrying in {delay} seconds."
                )
                time.sleep(delay)
                continue
            else:
                logging.error(
                    f"Error fetching data for {gene_names}: Client error "
                    f"'{e.response.status_code} {e.response.reason_phrase}' "
                    f"for url '{e.request.url}'"
                )
                return None, gene_names

        except Exception as e:
            logging.error(f"Unexpected error fetching data for {gene_names}: {e}")
            return None, gene_names
    logging.error(f"Max retries reached for {gene_names}. Giving up.")
    return None, gene_names


def save_gene_json(gene_name, gene_data, json_dir):
    """Saves gene data to a JSON file."""
    if gene_data is None:
        return
    filename = os.path.join(json_dir, f"{gene_name}.json")
    try:
        with open(filename, "w") as outfile:
            json_string = json.dumps(gene_data, indent=4)
            outfile.write(json_string)
        logging.info(f"Saved data for {gene_name} to {filename}")
    except Exception as e:
        logging.error(f"Error saving data for {gene_name} to {filename}: {e}")


def process_genes(gene_names, json_dir, last_request_time):
    """Processes a list of genes: fetches and saves data."""
    # Implement rate limiting (minimum 1 second between requests)
    now = time.time()
    time_since_last_request = now - last_request_time.get('global', 0)
    wait_time = max(0, 1 - time_since_last_request)
    if wait_time > 0:
        logging.info(
            f"Rate limited, waiting {wait_time:.2f} seconds before fetching {gene_names}"
        )
        time.sleep(wait_time)

    results, missing_genes = fetch_gene_data(gene_names)
    last_request_time['global'] = time.time()

    if results:
        for hit in results:
            save_gene_json(hit['query'], hit, json_dir)

    for gene in missing_genes:
        logging.info(f"No results found for {gene}")


def main():
    try:
        gene_df = pd.read_csv(gene_csv_path)
        json_dir = os.path.join(data_dir, "mygene_info")

        # Create directories if they don't exist
        os.makedirs(json_dir, exist_ok=True)

        last_request_time = {}
        gene_names = [row["gene_name"].upper() for _, row in gene_df.iterrows()]

        # Process genes in batches
        batch_size = 10  # Adjust batch size as needed for optimal performance
        for i in range(0, len(gene_names), batch_size):
            batch = gene_names[i:i+batch_size]
            process_genes(batch, json_dir, last_request_time)

    except Exception as e:
        logging.error(f"An error occurred during execution: {e}")


if __name__ == "__main__":
    main()
    logging.info("Data processing complete.")