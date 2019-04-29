import re
from collections import defaultdict, OrderedDict

# The maps below all have names of the form: <from>_<to>.

# From synonyms to IRIs. Note that the keys to this dictionary are always lowercase.
synonym_iris = {}

# From IRIs to labels
iri_labels = {
  'http://purl.obolibrary.org/obo/RO_0002104': 'has plasma membrane part',
  'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part': 'lacks plasma membrane part',
  'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount': 'has high plasma membrane amount',
  'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount': 'has low plasma membrane amount'
}

# From IRIs to parents
iri_parents = {}

# From IRIs to gates
iri_gates = {}

# Mapping of suffixes to their names
level_names = {
  '++': 'high',
  '+~': 'medium',
  '+-': 'low',
  '+': 'positive',
  '-': 'negative'
}

# iri_levels is defined to be the inverse of levels_iri. Note that because both '+~' and '+' in
# level_iris map to 'http://purl.obolibrary.org/obo/RO_0002104', one needs to be careful in how
# level_iris is ordered. Dictionary keys are always unique, so when iri_levels is generated, the
# second instance of 'http://purl.obolibrary.org/obo/RO_0002104' will overwrite the first. So '+'
# must be added to level_iris last, since that is the one that we want in iri_levels.
level_iris = OrderedDict([
  ('++', 'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount'),
  ('+~', 'http://purl.obolibrary.org/obo/RO_0002104'),
  ('+-', 'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount'),
  ('+', 'http://purl.obolibrary.org/obo/RO_0002104'),
  ('-', 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part')
])
iri_levels = {v: k for k, v in level_iris.items()}


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


def get_cell_iri_gates(tree):
  """
  Given an XML tree from cl.owl, return a map from Cell Ontology class IRIs
  to arrays of gate dictionaries.
  """

  ns = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'obo': 'http://purl.obolibrary.org/obo/',
    'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#'
  }

  root = tree.getroot()
  obo = 'http://purl.obolibrary.org/obo/'
  rdf_about = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about'
  rdf_resource = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'
  rdf_description = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description'
  rdfs_label = '{http://www.w3.org/2000/01/rdf-schema#}label'
  owl_restriction = '{http://www.w3.org/2002/07/owl#}Restriction'

  for child in root.findall('owl:Class', ns):
    iri = None
    if rdf_about in child.attrib:
      iri = child.attrib[rdf_about]
    if iri and iri.startswith(obo + 'CL_'):  # and iri == obo + 'CL_0000624':
      label = child.findtext(rdfs_label)
      if label:
        iri_labels[iri] = label
        synonym_iris[label.casefold()] = iri

      for synonym in child.findall('oboInOwl:hasExactSynonym', ns):
        synonym_iris[synonym.text.casefold()] = iri

      iri_gates[iri] = []
      #for part in child.findall('owl:equivalentClass/owl:Class/owl:intersectionOf/*', ns):
      for part in child.findall('rdfs:subClassOf/*', ns):
        if part.tag == rdf_description:
          parent = part.get(rdf_about)
          if parent:
            iri_parents[iri] = parent
        elif part.tag == owl_restriction:
          relation = part.find('owl:onProperty', ns)
          if relation is not None:
            relation = relation.get(rdf_resource)
          value = part.find('owl:someValuesFrom', ns)
          if value is not None:
            value = value.get(rdf_resource)
          if value and value.startswith(obo + 'PR_') and relation in iri_levels:
            gate = {
              'kind': value,
              'level': relation
            }
            iri_gates[iri].append(gate)


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
