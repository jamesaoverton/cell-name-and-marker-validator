import re
from collections import defaultdict, OrderedDict


def extract_suffix_syns_symbs(rows):
    suffixsymbs = {}
    suffixsyns = OrderedDict()
    for row in rows:
        suffixsymbs[row['Name']] = row['Symbol']
        suffixsyns[row['Name']] = row['Name']
        for synonym in row['Synonyms'].split(','):
            synonym = synonym.strip()
            if synonym != '':
                suffixsyns[synonym] = row['Name']

    return suffixsymbs, suffixsyns


def extract_iri_special_label_maps(rows):
    # This maps special labels to lists of IRIs
    ispecial_iris = defaultdict(list)
    # This maps IRIs to special labels:
    iri_specials = {}

    for row in rows:
        iri = row['Ontology ID']
        label = row['Label']
        synonyms = re.split(',\s+', row['Synonyms'])
        iri_specials[iri] = label
        ispecial_iris[label.lower()].append(iri)
        # Also map any synonyms for the label to the IRI
        for synonym in synonyms:
            ispecial_iris[synonym.lower()].append(iri)

    return ispecial_iris, iri_specials
