import re
from collections import defaultdict, OrderedDict


def get_suffix_syns_symbs_maps(rows):
  """
  From the given data rows, extract lists of suffix symbols and suffix synonyms.
  """
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
  """
  From the given data rows, extract a map from IRIs to special labels as well as a reverse map.
  """
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
  """
  From the given data rows, extract a map from IRIs to labels as well as a reverse map.
  """
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


def get_iri_exact_label_maps(exact_rows, ishort_iris={}):
  """
  From the given data rows, extract a map from exact labels to IRIs, ommitting any that are
  already contained in ishort_iris (i.e. any exact labels that are also short labels).
  """
  # This maps exact labels to lists IRIs
  iexact_iris = defaultdict(list)

  for row in exact_rows:
    (iri, exact) = row
    # Only add the exact label to the map if it isn't already in the short labels dict:
    if not exact.lower() in ishort_iris:
      iexact_iris[exact.lower()].append(iri)

  return iexact_iris


def get_iri_short_label_maps(short_rows):
  """
  From the given data rows, extract a map from IRIs to short labels as well as a reverse map.
  """
  # This maps short labels to lists of IRIs:
  ishort_iris = defaultdict(list)
  # This maps IRIs to shorts
  iri_shorts = {}

  for row in short_rows:
    (iri, short) = row
    ishort_iris[short.lower()].append(iri)
    iri_shorts[iri] = short

  return ishort_iris, iri_shorts


def split_gate(gate, symbols):
  """
  Splits the given gate_string into a gate name and a suffix, based on the given
  list of suffix symbols.
  """
  # Reverse sort the suffix symbols by length to make sure we don't match on a substring of
  # a longer suffix symbol when we are looking for a shorter suffix symbol
  # (e.g. '+' is a substring of '++') so we need to search for '++' before searching for '+'
  for symbol in sorted(list(symbols), key=len, reverse=True):
    if gate.endswith(symbol):
      return [gate[0:-len(symbol)], symbol]
  # If we get to here then there isn't a suffix.
  return [gate, '']
