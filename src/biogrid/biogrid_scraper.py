import requests
import pandas as pd
import io
import os
import asyncio
import logging
from dotenv import load_dotenv
from asyncio import Semaphore

# Load environment variables
load_dotenv()

# Get API key from environment
access_key = os.getenv("BIOGRID_API_KEY")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("biogrid.log"),
        logging.StreamHandler()  # Output to console as well
    ]
)

async def fetch_and_process_biogrid_data(gene_name, access_key, output_dir, semaphore):
    """
    Fetches interaction data for a given gene from BioGRID API, processes it, and saves to CSV.

    Args:
        gene_name (str): The gene name to query.
        access_key (str): The BioGRID API access key.
        output_dir (str): The directory to save the CSV output.
        semaphore (asyncio.Semaphore): Semaphore to limit concurrent requests
    """
    async with semaphore: # Limit the number of requests
        output_filename = os.path.join(output_dir, f"{gene_name}_interactions.csv")
        url = f"https://webservice.thebiogrid.org/interactions/?accesskey={access_key}&searchNames=true&geneList={gene_name}"
        
        try:
            logging.info(f"Fetching data for gene: {gene_name}")
            response = requests.get(url)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            tsv_data = response.text

            # Use io.StringIO to treat the string like a file
            tsv_file = io.StringIO(tsv_data)

            # Read the data into a DataFrame
            df = pd.read_csv(tsv_file, sep="\t", comment="#")

            # Optionally, you can rename columns if the header is not provided:
            column_names = [
                "BioGRID Interaction ID",
                "Entrez Gene ID for Interactor A",
                "Entrez Gene ID for Interactor B",
                "BioGRID ID for Interactor A",
                "BioGRID ID for Interactor B",
                "Systematic name for Interactor A",
                "Systematic name for Interactor B",
                "Official symbol for Interactor A",
                "Official symbol for Interactor B",
                "Synonyms/Aliases for Interactor A",
                "Synonyms/Aliases for Interactor B",
                "Experimental System Name",
                "Experimental System Type",
                "First author surname of the publication",
                "Pubmed ID of the publication",
                "Organism ID for Interactor A",
                "Organism ID for Interactor B",
                "Interaction Throughput",
                "Quantitative Score",
                "Post Translational Modification",
                "Phenotypes",
                "Qualifications",
                "Tags",
                "Source Database"
            ]
            df.columns = column_names
            filtered_column_names = [
                "Official symbol for Interactor A",
                "Official symbol for Interactor B",
                "Synonyms/Aliases for Interactor A",
                "Synonyms/Aliases for Interactor B",
                "Quantitative Score",
            ]
            df = df[filtered_column_names]

            df["Quantitative Score"] = df["Quantitative Score"].replace("-", "0").astype(float)

            df = df.sort_values("Quantitative Score", ascending=False)
            df = df[df["Quantitative Score"] > 0]

            # Save to CSV
            df.to_csv(output_filename, index=False)
            logging.info(f"Successfully saved data for {gene_name} to {output_filename}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data for gene {gene_name}: {e}")
        except pd.errors.EmptyDataError:
            logging.warning(f"No data was found for {gene_name}")
        except Exception as e:
            logging.error(f"An unexpected error occurred processing gene {gene_name}: {e}")

async def main():
    gene_df = pd.read_csv('gene_df.csv')
    output_dir = 'data/csv'
    os.makedirs(output_dir, exist_ok=True)

    semaphore = Semaphore(1)  # Limit to 10 concurrent requests
    tasks = [
        fetch_and_process_biogrid_data(
            row['gene_name'].upper(), access_key, output_dir, semaphore
        )
        for index, row in gene_df.iterrows()
    ]
    await asyncio.gather(*tasks)
if __name__ == "__main__":
    asyncio.run(main())