# Gery Casiez
# https://gery.casiez.net/
# 2026 

import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter, SortingStrategy, ENTRY_TO_BIBTEX_IGNORE_ENTRIES
from tqdm import tqdm
import subprocess
import argparse
import sys
import os

def getBibInfo(driver, doi: str):
    """
        Fetch bibliographic information for a given DOI using the ACM Digital Library export API.
    """
    url = f"https://dl.acm.org/action/exportCiteProcCitation?dois={doi}&targetFile=custom-bibtex&format=bibTex"
    driver.get(url)
    try:
        content = driver.find_element("tag name", "pre").text
        return json.loads(content)
    except Exception as e:
        return None


def getDOI(title):
    """
        Fetch DOI for a given title using CrossRef API.
    """
    #  There is a rate limit of 50 requests per second for the CrossRef API.
    time.sleep(1)
    title = title.strip().replace(' ', '+').replace('&', '')

    url = f"https://api.crossref.org/works?query.title={title}&select=DOI,title"

    result = requests.get(url)
    try:
        result.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching DOI for title '{title}' using {url}: {e}")
        sys.exit(1)
        return None

    try:
        result = result.json()
    except Exception as e:
        print(result)
        print(f"Error parsing JSON response for title '{title}': {e}")
        return None

    for item in result["message"]["items"]:
        if item.get("title", [None])[0] == title:
            return item.get("DOI", None)
    return None


def getCiteprocPath():
    """
        Get the path to the citeproc.js file in the bibb package.
    """
    path = os.path.dirname(requests.__file__)
    path_site_packages = os.path.split(path)[0]
    return os.path.join(path_site_packages, "bibb", "citeproc.js")


def stripCiteprocWarnings(text: str) -> str:
    """
        Remove lines starting with "citeproc-js warning" from the given text.
    """
    return "\n".join(
        line for line in text.splitlines()
        if not line.startswith("citeproc-js warning")
    ).strip()


class ReverseFieldOrderWriter(BibTexWriter):
    def _entry_to_bibtex(self, entry):
        # Create a per-entry reverse order for fields while keeping ENTRYTYPE/ID out.
        self.display_order = [
            key for key in reversed(list(entry.keys()))
            if key not in ENTRY_TO_BIBTEX_IGNORE_ENTRIES
        ]
        self.display_order_sorting = SortingStrategy.PRESERVE
        return super()._entry_to_bibtex(entry)


def loadBibtexAllowNonStandard(bibtex_text: str) -> BibDatabase:
    """
        Load a BibTeX string into a BibDatabase, allowing non-standard entry types, like online.
    """
    parser = BibTexParser(ignore_nonstandard_types=False)
    return bibtexparser.loads(bibtex_text, parser=parser)


def dumpBibPreserveOrder(bib_db: BibDatabase) -> str:
    """
        Dump a BibDatabase to a BibTeX string, preserving the order of entries and fields.
    """
    writer = ReverseFieldOrderWriter()
    # Keep entry order as inserted in bib_db.entries.
    writer.order_entries_by = None
    writer.indent = "  "
    return bibtexparser.dumps(bib_db, writer).strip()

def getBibEntryTxt(entry, fieldsToRemove=None):
    """
        Get the BibTeX string for a single entry, preserving order.
    """
    bib_db = BibDatabase()
    bib_db.entries = [entry]
    for field in fieldsToRemove or []:
        bib_db.entries[0].pop(field, None)
    return dumpBibPreserveOrder(bib_db)

def cleanBibEntry(entry):
    """
        Clean up the BibTeX entry, replacing characters.
    """
    for key in entry.keys():
        if isinstance(entry[key], str):
            entry[key] = entry[key].replace("&amp;", "\\&").replace("’", "'").replace("–", "--")
    return entry

def getBibFromACM(bibinfo, source_entry, fieldsToRemove=None):
    """
        Convert ACM Digital Library bibliographic information to a BibTeX entry, preserving order and keywords.
    """
    citeproc_path = getCiteprocPath()
    result = subprocess.run(["node", citeproc_path, "-"], input=json.dumps(bibinfo), text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error running citeproc.js: {result.stderr}")
    entry = stripCiteprocWarnings(result.stdout)
    bibentry = loadBibtexAllowNonStandard(entry)
    if bibentry.entries:
        bibentry.entries[0]['ID'] = source_entry.get('ID', 'unknown')
        # Preserve source keyword ordering/content when present.
        if source_entry.get('keywords'):
            bibentry.entries[0]['keywords'] = source_entry['keywords']
        if fieldsToRemove:
            for field in fieldsToRemove:
                bibentry.entries[0].pop(field, None)
        bibentry.entries[0] = cleanBibEntry(bibentry.entries[0])
        return dumpBibPreserveOrder(bibentry)
    else:
        return None


def getBibEntryFromDOI(info, entry, fieldsToRemove=None):
    """
        Get the BibTeX entry from ACM Digital Library info if available, otherwise return the original entry."""
    if info is not None:
        res = getBibFromACM(info, entry, fieldsToRemove=fieldsToRemove)
        if res is None:
            res = getBibEntryTxt(entry, fieldsToRemove=fieldsToRemove)
    else:
        res = getBibEntryTxt(entry, fieldsToRemove=fieldsToRemove)
    return res


def main():
    parser = argparse.ArgumentParser(description="Clean a bibtex file by using BibTeX information from the  ACM DL.")
    parser.add_argument("-i", required=True, help="Input BibTeX file")
    parser.add_argument("-o", required=True, help="Output BibTeX file")
    parser.add_argument("--fieldsToRemove", default="", help="Fields to remove from the output BibTeX entries as a list separated by commas (e.g., --fieldsToRemove url,abstract)")
    args = parser.parse_args()

    # Check if node is installed
    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Node.js is not installed or not found in PATH")
        sys.exit(1)
    
    # Check if citeproc-js node module is installed
    try:
        subprocess.run(["node", "-e", "require('citeproc');"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("citeproc.js node module is not installed")
        sys.exit(1)

    # Check if Chrome is running with remote debugging enabled
    try:
        response = requests.get("http://127.0.0.1:9222")
    except requests.RequestException:
        print("Chrome is not running with remote debugging enabled.")
        print("Go on https://github.com/casiez/bibb and follow the instructions.")
        sys.exit(1)


    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)

    with open(args.i, "r") as f:
        bib_content = f.read()
    entries = loadBibtexAllowNonStandard(bib_content)

    s = ""
    fieldsToRemove = [field.strip() for field in args.fieldsToRemove.split(",") if field.strip()]

    for entry in tqdm(entries.entries):
        doi = entry.get('doi')
        if doi:
            info = getBibInfo(driver, doi)
            s += getBibEntryFromDOI(info, entry, fieldsToRemove=fieldsToRemove)
        else:
            title = entry.get('title')
            doi = getDOI(title) if title else None
            if doi:
                info = getBibInfo(driver, doi)
                s += getBibEntryFromDOI(info, entry, fieldsToRemove=fieldsToRemove)
            else:
                s += getBibEntryTxt(entry, fieldsToRemove=fieldsToRemove)

        s += "\n\n"
    
    with open(args.o, "w") as f:
        f.write(s)


if __name__ == "__main__":
    main()