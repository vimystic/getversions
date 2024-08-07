# version 0.0.11

import requests
import yaml
import base64
import logging
import re
import os

logging.basicConfig(level=logging.INFO)

VERSION = "0.0.11"
logging.info(f"Running script version {VERSION}")

# Read GitHub PAT from environment variable
GITHUB_PAT = os.getenv('GITHUB_PAT')

if not GITHUB_PAT:
    raise Exception("GitHub PAT not found. Please set the GITHUB_PAT environment variable.")
else:
    logging.info("GitHub PAT found and will be used for authentication.")

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Mapping of repo names to CoinGecko IDs
COINGECKO_IDS = {
    "cosmos/gaia": "cosmos",
    "ovrclk/akash": "akash-network",
    "noble-assets/noble": "noble",
    "sei-protocol/sei-chain": "sei-network",
    # Add more mappings as necessary
}

def read_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def get_latest_release(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {'Authorization': f'token {GITHUB_PAT}'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 404:
        raise Exception(f"Repository {repo} not found.")
    if response.status_code == 401:
        raise Exception(f"Unauthorized: Check your PAT and scopes.")
    if response.status_code != 200:
        raise Exception(f"Error fetching releases from {repo}: {response.json().get('message', 'Unknown error')}")

    releases = response.json()
    for release in releases:
        if not release['prerelease']:
            return release['tag_name']

    raise Exception(f"No releases found for {repo}")

def get_file_content(repo, path, ref):
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    headers = {'Authorization': f'token {GITHUB_PAT}'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 404:
        raise Exception(f"File {path} not found in repository {repo} at ref {ref}.")
    if response.status_code == 401:
        raise Exception(f"Unauthorized: Check your PAT and scopes.")
    if response.status_code != 200:
        raise Exception(f"Error fetching file {path} from {repo} at ref {ref}: {response.json().get('message', 'Unknown error')}")

    content = response.json().get('content')
    if content:
        return base64.b64decode(content).decode('utf-8')
    else:
        raise Exception(f"File {path} in {repo} at ref {ref} is empty or cannot be read.")

def search_in_content(content, search_texts):
    result = {}
    for search_text in search_texts:
        pattern = rf"{re.escape(search_text)}\s+([^\s]+)"
        match = re.search(pattern, content)
        result[search_text] = match.group(1) if match else ""
    return result

def get_market_cap(repo):
    chain_name = COINGECKO_IDS.get(repo, None)
    if not chain_name:
        logging.error(f"No CoinGecko ID mapping found for repo: {repo}")
        return "N/A"

    logging.info(f"Fetching market cap for chain: {chain_name}")
    url = f"{COINGECKO_API_URL}/coins/{chain_name}"
    response = requests.get(url)

    if response.status_code == 404:
        logging.error(f"Chain {chain_name} not found on CoinGecko.")
        return "N/A"
    if response.status_code != 200:
        logging.error(f"Error fetching market cap for {chain_name}: {response.json().get('message', 'Unknown error')}")
        return "Error"

    data = response.json()
    market_cap = data.get('market_data', {}).get('market_cap', {}).get('usd', "N/A")
    return market_cap

def generate_markdown_table(chains):
    headers = ["repo - release_version", "market_cap"] + chains[0]['search']
    rows = []

    for chain in chains:  # Process all chains
        repo = chain['repo']
        gomod_path = chain['gomod_path']
        release_version = chain['release_version']
        search_texts = chain.get('search', [])

        if release_version == "latest":
            try:
                release_version = get_latest_release(repo)
                logging.info(f"Repo: {repo}, Path: {gomod_path}, Latest Release Version: {release_version}")
            except Exception as e:
                logging.error(e)
                continue

        try:
            file_content = get_file_content(repo, gomod_path, release_version)
            search_results = search_in_content(file_content, search_texts)
            market_cap = get_market_cap(repo)
            if isinstance(market_cap, (int, float)):
                market_cap_str = f"${market_cap:,.2f}"
            else:
                market_cap_str = market_cap
            row = [f"{repo} - {release_version}", market_cap_str] + [search_results.get(term, "") for term in search_texts]
            rows.append(row)
        except Exception as e:
            logging.error(e)

    # Generate markdown table
    markdown_table = f"| {' | '.join(headers)} |\n"
    markdown_table += f"|{'|'.join(['-' * len(header) for header in headers])}|\n"
    for row in rows:
        markdown_table += f"| {' | '.join(row)} |\n"

    return markdown_table

def main():
    config_file = 'config.yaml'
    config = read_config(config_file)
    
    markdown_table = generate_markdown_table(config['chains'])
    print(markdown_table)

if __name__ == "__main__":
    main()
