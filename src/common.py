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


def get_iri_special_label_maps(rows):
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


def get_iri_label_maps(label_rows):
  # This maps labels to lists of IRIs:
  ilabel_iris = defaultdict(list)
  # This maps IRIs to labels
  iri_labels = {}

  for row in label_rows:
    (iri, label) = row
    # Add the IRI to the list of IRIs associated with the label in the ilabel_iris dictionary
    ilabel_iris[label.lower()].append(iri)
    # Map the IRI to the label in the iri_labels dictionary
    iri_labels[iri] = label

  return ilabel_iris, iri_labels
