# metadata_enricher.py

from config import DOMAIN_TERMS

class MetadataEnricher:
    def enrich(self, text, raw):
        result = {
            "people": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "key_terms": [],
            "domain_terms": []
        }

        for e in raw["entities"]:
            t = e["Type"]
            val = e["Text"]

            if t == "PERSON":
                result["people"].append(val)
            elif t == "ORGANIZATION":
                result["organizations"].append(val)
            elif t == "LOCATION":
                result["locations"].append(val)
            elif t == "DATE":
                result["dates"].append(val)

        result["key_terms"] = [k["Text"] for k in raw["key_phrases"]]

        text_lower = text.lower()
        result["domain_terms"] = [
            t for t in DOMAIN_TERMS if t.lower() in text_lower
        ]

        return result