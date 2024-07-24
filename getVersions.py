# version 0.0.1

import requests
import yaml
import base64
import logging
import re

logging.basicConfig(level=logging.INFO)

def read_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def get_latest_release(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    response = requests.get(url)
    
    if response.status_code == 404:
        raise Exception(f"Repository {repo} not found.")
    if response.status_code != 200:
        raise Exception(f"Error fetching releases from {repo}: {response.json().get('message', 'Unknown error')}")

    releases = response.json()
    for release in releases:
        if not release['prerelease']:
            return release['tag_name']

    raise Exception(f"No releases found for {repo}")

def get_file_content(repo, path, ref):
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    response = requests.get(url)
    
    if response.status_code == 404:
        raise Exception(f"File {path} not found in repository {repo} at ref {ref}.")
    if response.status_code != 200:
        raise Exception(f"Error fetching file {path} from {repo} at ref {ref}: {response.json().get('message', 'Unknown error')}")

    content = response.json().get('content')
    if content:
        return base64.b64decode(content).decode('utf-8')
    else:
        raise Exception(f"File {path} in {repo} at ref {ref} is empty or cannot be read.")

def search_in_content(content, search_texts):
    lines = content.split('\n')
    matching_lines = [line for line in lines if any(re.search(search_text, line) for search_text in search_texts) and not line.strip().startswith('//')]
    return matching_lines

def process_chain(chain):
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
            return
    
    try:
        file_content = get_file_content(repo, gomod_path, release_version)
        if search_texts:
            matching_lines = search_in_content(file_content, search_texts)
            if matching_lines:
                print(f"Contents of {gomod_path} in {repo} at version {release_version} containing any of {search_texts}:")
                for line in matching_lines:
                    print(f"    {line}")
        else:
            print(f"Contents of {gomod_path} in {repo} at version {release_version}:\n{file_content}")
    except Exception as e:
        logging.error(e)

def main():
    config_file = 'config.yaml'
    config = read_config(config_file)
    
    for chain in config['chains']:
        process_chain(chain)

if __name__ == "__main__":
    main()
