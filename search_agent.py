import json
import requests
from urllib.parse import urlencode
from time import sleep


# Build query from PICO

def build_query(protocol):
    population_terms = " OR ".join(protocol["keywords"]["population_terms"])
    intervention_terms = " OR ".join(
        protocol["keywords"]["intervention_terms"])
    outcome_terms = " OR ".join(protocol["keywords"]["outcome_terms"])
    query = f"(({population_terms}) AND ({intervention_terms}) AND ({outcome_terms}))"
    return query


#  Search PubMed

def search_pubmed(query, retmax=1000, date_from="2000/01/01", date_to="2025/10/17"):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax,
        "datetype": "pdat",
        "mindate": date_from,
        "maxdate": date_to
    }
    url = f"{base_url}?{urlencode(params)}"
    print(f"Querying PubMed API...\n{url}\n")

    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    pmids = data.get("esearchresult", {}).get("idlist", [])
    count = int(data.get("esearchresult", {}).get("count", "0"))
    return pmids, count


def fetch_metadata(pmids, batch_size=200):
    all_metadata = []
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i+batch_size]
        data = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "json"
        }
        response = requests.post(base_url, data=data)
        response.raise_for_status()
        batch_data = response.json().get("result", {})
        for pid in batch:
            if pid in batch_data:
                record = batch_data[pid]
                # Add 'id' field for compatibility with screening module
                record["id"] = f"PMID:{record.get('uid', pid)}"
                all_metadata.append(record)
        sleep(0.1)  
    return all_metadata


def deduplicate_records(records):
    seen = set()
    unique = []
    for r in records:
        if r["uid"] not in seen:
            seen.add(r["uid"])
            unique.append(r)
    return unique


def save_bibtex(records, filename="library.bib"):
    with open(filename, "w", encoding="utf-8") as f:
        for r in records:
            title = r.get("title", "").replace("{", "").replace("}", "")
            authors = " and ".join([a.get("name")
                                   for a in r.get("authors", [])])
            year = r.get("pubdate", "")[:4]
            pmid = r.get("uid")
            bib_entry = f"@article{{pmid{pmid},\n  title={{ {title} }},\n  author={{ {authors} }},\n  year={{ {year} }},\n  journal={{ {r.get('source', '')} }},\n}}\n\n"
            f.write(bib_entry)
    print(f"Saved BibTeX to {filename}")



def save_ris(records, filename="library.ris"):
    with open(filename, "w", encoding="utf-8") as f:
        for r in records:
            f.write("TY  - JOUR\n")
            f.write(f"TI  - {r.get('title', '')}\n")
            for a in r.get("authors", []):
                f.write(f"AU  - {a.get('name')}\n")
            f.write(f"PY  - {r.get('pubdate', '')}\n")
            f.write(f"JO  - {r.get('source', '')}\n")
            f.write(f"ID  - {r.get('uid')}\n")
            f.write("ER  - \n\n")
    print(f"Saved RIS to {filename}")



def run_search(protocol_file="protocol.json"):
    # Load protocol
    with open(protocol_file, "r", encoding="utf-8") as f:
        protocol = json.load(f)

    # Build query
    query = build_query(protocol)

    # Extract search params
    retmax = protocol["search_parameters"]["retmax_per_db"]
    date_from = protocol["search_parameters"]["date_range"]["from"]
    date_to = protocol["search_parameters"]["date_range"]["to"]

    # Search PubMed
    pmids, count = search_pubmed(query, retmax, date_from, date_to)
    print(f"Found {count} articles.")

    # Fetch metadata in batches
    metadata = fetch_metadata(pmids)
    print(f"Fetched metadata for {len(metadata)} articles.")

    # Deduplicate
    unique_metadata = deduplicate_records(metadata)
    print(f"Unique articles: {len(unique_metadata)}")

    # Save JSON
    output = {
        "query": query,
        "total_found": count,
        "unique_articles": unique_metadata
    }
    with open("search_results_pubmed.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print("Saved results to search_results_pubmed.json")

    # Save BibTeX & RIS
    save_bibtex(unique_metadata)
    save_ris(unique_metadata)



# Run if executed

if __name__ == "__main__":
    run_search("protocol.json")
