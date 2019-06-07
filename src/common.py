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
    reported = re.sub('^.*:\s+', '', reported)

  # Every project has different types of gates and methods for delimiting gates, so parsing the
  # reported gates from the source file will in general be different for each project.
  gates = []
  if any_in_projname(['LaJolla', 'ARA06', 'Center for Human Immunology', 'Wistar']):
    # These projects do not use delimiters between gates
    gates = re.findall('\w+[\-\+]*', reported)
  elif any_in_projname(['IPIRC', 'Watson', 'Ltest', 'Seattle Biomed']):
    # For these projects, gates are separated by forward slashes
    gates = re.split('\/', reported)
  elif 'Emory' in projname:
    # Gates are separated by commas followed by whitespace
    gates = re.split(',\s+', reported)
  elif 'VRC' in projname:
    # Gates are separated by a capitalised 'AND', and surrounded by whitespace
    gates = re.split('\s+AND\s+', reported)
  elif 'Ertl' in projname:
    # Gates are separated by a lowercase 'and', and surrounded by whitespace
    gates = re.split('\s+and\s+', reported)
  elif 'Stanford' in projname:
    # First delimit any non-delimited gates with a forward slash. Then all gates will be delimited
    # by either a forward slash or a comma, followed by whitespace.
    reported = re.sub(r'([\-\+])(CD\d+|CX\w+\d+|CCR\d)', r'\1/\2', reported)
    gates = re.split('\/|,\s+', reported)
  elif 'Baylor' in projname:
    # First eliminate any duplicate commas. Then separate any occurrences of 'granulocyte' that
    # are preceded by a space (since these are gates which must be noted). Then delimit any
    # non-delimited gates using a forward slash. At the end of all of this, gates will be delimited
    # by either a forward slash or a comma, possibly followed by whitespace.
    reported = re.sub(',,+', ',', reported)
    reported = re.sub(' granulocyte', ', granulocyte', reported)
    reported = re.sub(r'([\-\+])CD(\d)', r'\1/CD\2', reported)
    gates = re.split('\/|,\s*', reported)
  elif 'Rochester' in projname:
    # Gates are delimited either by: (a) forward slashes, (b) semicolons possibly followed by
    # whitespace.
    gates = re.split(';+\s*|\/', reported)
  elif 'Mayo' in projname:
    # If any 'CD' gates are not delimited by a forward slash, so delimit them; all gates should be
    # delimited by forward slashes.
    reported = re.sub(r' CD(\d)', r' /CD\1', reported)
    gates = re.split('\/', reported)
  elif 'Improving Kidney' in projname:
    # Delimit non-delimited gates with a forward slash; all gates should be delimited by
    # forward slashes
    reported = re.sub(r'([\-\+])CD(\d)', r'\1/CD\2', reported)
    gates = re.split('\/', reported)
  elif 'New York Influenza' in projname:
    # Make it such that any occurrences of 'high' is followed by a space, then delimit non-delimited
    # gates with a forward slash; all gates should then be delimited by either a forward slash or a
    # comma.
    reported = re.sub('high', 'high ', reported)
    reported = re.sub(r'([\-\+ ])(CD\d+|CXCR\d|BCL\d|IF\w+|PD\d+|IL\d+|TNFa)', r'\1/\2', reported)
    gates = re.split('\/|,', reported)
  elif 'Modeling Viral' in projname:
    # Gates are separated either by (a) 'AND' surrounded by whitespace, (b) '_AND_', (c) '+'
    # surrounded by whitespace.
    gates = re.split('\s+AND\s+|_AND_|\s+\+\s+', reported)
  elif 'Immunobiology of Aging' in projname:
    # First delimit non-delimited gates with a forward slash, then all gates will be delimited by
    # forward slashes.
    reported = re.sub(r'([\-\+])(CD\d+|Ig\w+)', r'\1/\2', reported)
    gates = re.split('\/', reported)
  elif 'Flow Cytometry Analysis' in projname:
    # First delimit non-delimited gates with a forward slash, then all gates will be delimited by
    # forward slashes.
    reported = re.sub(r'(\+|\-)(CD\d+|Ig\w+|IL\d+|IF\w+|TNF\w+|Per\w+)', r'\1/\2', reported)
    gates = re.split('\/', reported)
  elif 'ITN019AD' in projname:
    # Remove any occurrences of "AND R<some number>" which follow a gate. Then replace any
    # occurrences of the word 'AND' with a space. Then all gates will be delimited by spaces.
    reported = re.sub('(\s+AND)?\s+R\d+.*$', '', reported)
    reported = re.sub('\s+AND\s+', ' ', reported)
    gates = re.split('\s+', reported)
  else:
    # By default, any of the following are valid delimiters: a forward slash, a comma possibly
    # followed by some whitespace, 'AND' or 'and' surrounded by whitespace.
    gates = re.split('\/|,\s*|\s+AND\s+|\s+and\s+', reported)

  tokenized = []
  for gate in gates:
    gate = gate.strip()
    gate = re.sub('ý', '-', gate)  # Unicode hyphen

    # Suffix synonyms are matched case-insensitively:
    for suffixsyn in suffixsyns.keys():
      if gate.casefold().endswith(suffixsyn.casefold()):
        gate = re.sub('\s*' + re.escape(suffixsyn) + '$', suffixsymbs[suffixsyns[suffixsyn]], gate,
                      flags=re.IGNORECASE)
        continue

    gate = re.sub(' ', '_', gate)

    # It may sometimes happen that the gate is empty, for example due to a trailing comma in the
    # reported field. Ignore any such empty gates.
    if gate:
      tokenized.append(gate)

  return tokenized


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


class SharedMapManager:
  """
  Manages the maps that are shared across modules. The names of these maps should be of the form:
  <from>_<to>.
  """
  def __init__(self):
    # Mapping of suffixes to their names
    self.level_names = {
      '++': 'high',
      '+~': 'medium',
      '+-': 'low',
      '+': 'positive',
      '-': 'negative'
    }

    # iri_levels is defined to be the inverse of levels_iri. Note that because both '+~' and '+' in
    # level_iris map to 'http://purl.obolibrary.org/obo/RO_0002104', one needs to be careful in how
    # level_iris is ordered. Dictionary keys are always unique, so when iri_levels is generated, the
    # second instance of 'http://purl.obolibrary.org/obo/RO_0002104' will overwrite the first. So
    # '+' must be added to level_iris last, since that is the one that we want in iri_levels.
    self.level_iris = OrderedDict([
      ('++', 'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount'),
      ('+~', 'http://purl.obolibrary.org/obo/RO_0002104'),
      ('+-', 'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount'),
      ('+', 'http://purl.obolibrary.org/obo/RO_0002104'),
      ('-', 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part')
    ])
    self.iri_levels = {v: k for k, v in self.level_iris.items()}

    # From synonyms to IRIs. Note that the keys to this dictionary are always lowercase.
    self.synonym_iris = {}

    # From IRIs to labels
    self.iri_labels = {
      'http://purl.obolibrary.org/obo/RO_0002104': 'has plasma membrane part',
      'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part': 'lacks plasma membrane part',
      'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount': 'has high plasma membrane amount',
      'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount': 'has low plasma membrane amount'
    }

    # From IRIs to parents
    self.iri_parents = {}

    # From IRIs to gates
    self.iri_gates = {}

  def populate_iri_maps(self, root):
    """
    Given an XML tree root extracted from cl.owl, populate the following maps:
    - iri_gates
    - iri_parents
    - iri_labels
    - synonym_iris
    """

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
          self.iri_labels[iri] = label
          self.synonym_iris[label.casefold()] = iri

        for synonym in child.findall('oboInOwl:hasExactSynonym', ns):
          self.synonym_iris[synonym.text.casefold()] = iri

        self.iri_gates[iri] = []
        # for part in child.findall('owl:equivalentClass/owl:Class/owl:intersectionOf/*', ns):
        for part in child.findall('rdfs:subClassOf/*', ns):
          if part.tag == rdf_description:
            parent = part.get(rdf_about)
            if parent:
              self.iri_parents[iri] = parent
          elif part.tag == owl_restriction:
            relation = part.find('owl:onProperty', ns)
            if relation is not None:
              relation = relation.get(rdf_resource)
            value = part.find('owl:someValuesFrom', ns)
            if value is not None:
              value = value.get(rdf_resource)
            if value and value.startswith(obo + 'PR_') and relation in self.iri_levels:
              gate = {
                'kind': value,
                'level': relation
              }
              self.iri_gates[iri].append(gate)
