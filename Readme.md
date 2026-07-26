[![PyPI Version](https://img.shields.io/pypi/v/bibb)](https://pypi.org/project/bibb/)
[![Downloads](https://static.pepy.tech/badge/bibb)](https://pepy.tech/project/bibb)

# BibTeX beautifier

Beautify BibTeX files in the following way:
- main feature: replaces entries using the ones from the ACM Digital Library (ACM DL) when they exist, otherwise keeps the original entry. It uses the entry DOI when it is available, otherwise it searches for the DOI using CrossRef.
- removes the fields specified by the user from the entries.
- indents the entries in a consistent way.
- removes unnecessary line breaks between the entries.

It preserves the original order of the entries in the BibTeX file and it also preserves the original BibTeX key of the entries.

## Installation

```bash
pip install bibb
```

You also need to have Google Chrome and [node.js](https://nodejs.org/) installed. 

In Node.js, you need to install the `citeproc` package:

```bash
npm install citeproc
```

## Usage

In order to use the ACM DL feature, you need to have a recent version of Google Chrome installed, and you need to start it with the remote debugging port enabled. You can do this by running the following command in a terminal (replace with the path to your Google Chrome installation if it is different):

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 -user-data-dir="./ChromeProfile"
```

Navigate to the [https://dl.acm.org/](https://dl.acm.org/) website in the Chrome window that opens (allows to validate the Cloudflare protection), and then you can run the `bibb` command in another terminal.

```bash
bibb -i input.bib -o output.bib
```

To remove specific fields from the output BibTeX entries, you can use the `--fieldsToRemove` option followed by a comma-separated list of fields to remove. For example, to remove the `keywords` and `abstract` fields, you can run:

```bash
bibb -i input.bib -o output.bib --fieldsToRemove keywords,abstract
```

**Important:** This tool is still under development. Run a diff between the input and output files to check for any unexpected changes. 