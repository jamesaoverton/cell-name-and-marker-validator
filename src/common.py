import re
from collections import defaultdict, OrderedDict


def tokenize(projname, suffixsymbs, suffixsyns, reported):
  """
  Converts a string describing gates reported in an experiment into a list of standardised tokens
  corresponding to those gates, which are determined by referencing the lists of suffix symbols and
  suffix synonyms passed to the function.

  Parameters:
       projname: the name of the project that reported the gates
       suffixsyns: OrderedDict mapping suffix synonyms to their standardised suffix name;
                   e.g. OrderedDict([('high', 'high'), ('hi', 'high'), ('bright', 'high'), etc.])
       suffixsymbs: dict mapping suffix names to their symbolic suffix representation;
                    e.g {'medium': '+~', 'negative': '-', etc.}
       reported: a string describing the gates reported in an experiment
  """

  # Inner function to determine whether the given project name contains any of the given keywords:
  def any_in_projname(kwds):
    return any([kwd in projname for kwd in kwds])

  # Ignore everything to the left of the first colon on a given line.
  if ': ' in reported:
    reported = re.sub(r'^.*:\s+', r'', reported)

  # Every project has different types of gates and methods for delimiting gates, so parsing the
  # reported gates from the source file will in general be different for each project.
  gates = []
  if any_in_projname(['LaJolla', 'ARA06', 'Center for Human Immunology', 'Wistar']):
    # These projects do not use delimiters between gates
    gates = re.findall(r'\w+[\-\+]*', reported)
  elif any_in_projname(['IPIRC', 'Watson', 'Ltest', 'Seattle Biomed']):
    # For these projects, gates are separated by forward slashes
    gates = re.split(r'\/', reported)
  elif 'Emory' in projname:
    # Gates are separated by commas followed by whitespace
    gates = re.split(r',\s+', reported)
  elif 'VRC' in projname:
    # Gates are separated by a capitalised 'AND', and surrounded by whitespace
    gates = re.split(r'\s+AND\s+', reported)
  elif 'Ertl' in projname:
    # Gates are separated by a lowercase 'and', and surrounded by whitespace
    gates = re.split(r'\s+and\s+', reported)
  elif 'Stanford' in projname:
    # First delimit any non-delimited gates with a forward slash. Then all gates will be delimited
    # by either a forward slash or a comma, followed by whitespace.
    reported = re.sub(r'([\-\+])(CD\d+|CX\w+\d+|CCR\d)', r'\1/\2', reported)
    gates = re.split(r'\/|,\s+', reported)
  elif 'Baylor' in projname:
    # First eliminate any duplicate commas. Then separate any occurrences of 'granulocyte' that
    # are preceded by a space (since these are gates which must be noted). Then delimit any
    # non-delimited gates using a forward slash. At the end of all of this, gates will be delimited
    # by either a forward slash or a comma, possibly followed by whitespace.
    reported = re.sub(r',,+', r',', reported)
    reported = re.sub(r' granulocyte', r', granulocyte', reported)
    reported = re.sub(r'([\-\+])CD(\d)', r'\1/CD\2', reported)
    gates = re.split(r'\/|,\s*', reported)
  elif 'Rochester' in projname:
    # Gates are delimited either by: (a) forward slashes, (b) semicolons possibly followed by
    # whitespace.
    gates = re.split(r';+\s*|\/', reported)
  elif 'Mayo' in projname:
    # If any 'CD' gates are not delimited by a forward slash, so delimit them; all gates should be
    # delimited by forward slashes.
    reported = re.sub(r' CD(\d)', r' /CD\1', reported)
    gates = re.split(r'\/', reported)
  elif 'Improving Kidney' in projname:
    # Delimit non-delimited gates with a forward slash; all gates should be delimited by
    # forward slashes
    reported = re.sub(r'([\-\+])CD(\d)', r'\1/CD\2', reported)
    gates = re.split(r'\/', reported)
  elif 'New York Influenza' in projname:
    # Make it such that any occurrences of 'high' is followed by a space, then delimit non-delimited
    # gates with a forward slash; all gates should then be delimited by either a forward slash or a
    # comma.
    reported = re.sub(r'high', r'high ', reported)
    reported = re.sub(r'([\-\+ ])(CD\d+|CXCR\d|BCL\d|IF\w+|PD\d+|IL\d+|TNFa)', r'\1/\2', reported)
    gates = re.split(r'\/|,', reported)
  elif 'Modeling Viral' in projname:
    # Gates are separated either by (a) 'AND' surrounded by whitespace, (b) '_AND_', (c) '+'
    # surrounded by whitespace.
    gates = re.split(r'\s+AND\s+|_AND_|\s+\+\s+', reported)
  elif 'Immunobiology of Aging' in projname:
    # First delimit non-delimited gates with a forward slash, then all gates will be delimited by
    # forward slashes.
    reported = re.sub(r'([\-\+])(CD\d+|Ig\w+)', r'\1/\2', reported)
    gates = re.split(r'\/', reported)
  elif 'Flow Cytometry Analysis' in projname:
    # First delimit non-delimited gates with a forward slash, then all gates will be delimited by
    # forward slashes.
    reported = re.sub(r'(\+|\-)(CD\d+|Ig\w+|IL\d+|IF\w+|TNF\w+|Per\w+)', r'\1/\2', reported)
    gates = re.split(r'\/', reported)
  elif 'ITN019AD' in projname:
    # Remove any occurrences of "AND R<some number>" which follow a gate. Then replace any
    # occurrences of the word 'AND' with a space. Then all gates will be delimited by spaces.
    reported = re.sub(r'(\s+AND)?\s+R\d+.*$', r'', reported)
    reported = re.sub(r'\s+AND\s+', r' ', reported)
    gates = re.split(r'\s+', reported)
  else:
    # By default, any of the following are valid delimiters: a forward slash, a comma possibly
    # followed by some whitespace, 'AND' or 'and' surrounded by whitespace.
    gates = re.split(r'\/|,\s*|\s+AND\s+|\s+and\s+', reported)

  tokenized = []
  for gate in gates:
    gate = gate.strip()
    gate = re.sub('ý', '-', gate)  # Unicode hyphen

    # Suffix synonyms are matched case-insensitively:
    for suffixsyn in suffixsyns.keys():
      if gate.casefold().endswith(suffixsyn.casefold()):
        gate = re.sub(r'\s*' + re.escape(suffixsyn) + r'$', suffixsymbs[suffixsyns[suffixsyn]],
                      gate, flags=re.IGNORECASE)
        continue

    gate = re.sub(r' ', r'_', gate)

    # It may sometimes happen that the gate is empty, for example due to a trailing comma in the
    # reported field. Ignore any such empty gates.
    if gate:
      tokenized.append(gate)

  return tokenized


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


def get_level_names():
  """
  Returns a map from level symbols (marker suffixes) to level names
  """
  return {
    '++': 'high',
    '+~': 'medium',
    '+-': 'low',
    '+': 'positive',
    '-': 'negative'
  }


def get_level_iris():
  """
  Returns a map from level symbols (marker suffixes) to IRIs
  """
  # The ordering here is important, because '+~' and '+' map to the same IRI. We will sometimes want
  # to reverse this map (see the get_iri_levels() function below). But when we do this, since
  # dictionary keys are necessarily unique, the second value will overwrite the first. Since we care
  # more about '+', it should be placed after '+~' in the map returned below.
  return OrderedDict([
    ('++', 'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount'),
    ('+~', 'http://purl.obolibrary.org/obo/RO_0002104'),
    ('+-', 'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount'),
    ('+', 'http://purl.obolibrary.org/obo/RO_0002104'),
    ('-', 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part')
  ])


def get_iri_levels():
  """
  Returns a map from IRIs to level symbols (suffixes)
  """
  # Just reverse the map returned by get_level_iris():
  return {v: k for k, v in get_level_iris().items()}


def get_basic_iri_labels():
  """
  Returns the basic IRI->label mappings that any iri_label map should contain
  """
  return {
    'http://purl.obolibrary.org/obo/RO_0002104': 'has plasma membrane part',
    'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part': 'lacks plasma membrane part',
    'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount': 'has high plasma membrane amount',
    'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount': 'has low plasma membrane amount'
  }


def extract_suffix_syns_symbs_maps(rows):
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


def extract_iri_special_label_maps(rows):
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
    synonyms = re.split(r',\s+', row['Synonyms'])
    iri_specials[iri] = label
    ispecial_iris[label.lower()].append(iri)
    # Also map any synonyms for the label to the IRI
    for synonym in synonyms:
      ispecial_iris[synonym.lower()].append(iri)

  return ispecial_iris, iri_specials


def extract_iri_label_maps(label_rows):
  """
  From the given data rows, extract a map from IRIs to labels as well as a reverse map.
  """
  # This maps labels to lists of IRIs:
  ilabel_iris = defaultdict(list)
  # This maps IRIs to labels
  iri_labels = get_basic_iri_labels()

  for row in label_rows:
    (iri, label) = row
    # Add the IRI to the list of IRIs associated with the label in the ilabel_iris dictionary
    ilabel_iris[label.lower()].append(iri)
    # Map the IRI to the label in the iri_labels dictionary
    iri_labels[iri] = label

  return ilabel_iris, iri_labels


def extract_iri_exact_label_maps(exact_rows, ishort_iris={}):
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


def extract_iri_short_label_maps(short_rows):
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


def update_iri_maps_from_owl(root, iri_gates={}, iri_parents={}, iri_labels={}, synonym_iris={}):
  """
  Given an XML tree root extracted from cl.owl, add mappings to the given IRI maps.
  If not all of the initial maps are provided, these are initialised empty, and the new maps are
  then returned to the caller.
  """
  if not iri_labels:
    iri_labels = get_basic_iri_labels()

  ns = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'obo': 'http://purl.obolibrary.org/obo/',
    'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#'
  }

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
      # for part in child.findall('owl:equivalentClass/owl:Class/owl:intersectionOf/*', ns):
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
          if value and value.startswith(obo + 'PR_') and relation in get_iri_levels():
            gate = {
              'kind': value,
              'level': relation
            }
            iri_gates[iri].append(gate)

  # If named dictionaries are passed to this function, this return statement is not needed, since
  # those dictionaries are passed 'by name' and hence modified in place. This return statement is
  # handy for the case when one or more of the dictionary parameters to this function have been
  # omitted.
  return iri_gates, iri_parents, iri_labels, synonym_iris


class MapManager:
  """
  Container for shared IRI maps. Useful when an instance of these maps needs to be shared by
  different disconnected sections of code (e.g. in the server module of this codebase).
  """
  def __init__(self):
    # Mapping of suffixes to their names
    self.level_names = get_level_names()

    # Mapping of level symbols (suffixes) to IRIs
    self.level_iris = get_level_iris()

    # Mapping of IRIs to level symbols (suffixes)
    self.iri_levels = get_iri_levels()

    # From IRIs to labels
    self.iri_labels = get_basic_iri_labels()

    # From suffix synonyms to IRIs.
    self.synonym_iris = {}

    # From IRIs to their parents
    self.iri_parents = {}

    # From IRIs to gates
    self.iri_gates = {}

    # From suffix names to their corresponding symbols:
    self.suffixsymbs = {}

    # From suffix names to their synonyms
    self.suffixsyns = OrderedDict()

    # From special labels to lists of IRIs
    self.ispecial_iris = defaultdict(list)

    # From IRIs to special labels:
    self.iri_specials = {}

    # From labels to lists of IRIs:
    self.ilabel_iris = defaultdict(list)

    # From exact labels to lists IRIs:
    self.iexact_iris = defaultdict(list)

    # From short labels to lists of IRIs:
    self.ishort_iris = defaultdict(list)

    # From IRIs to shorts:
    self.iri_shorts = {}
