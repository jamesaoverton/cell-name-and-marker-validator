#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import re

from collections import OrderedDict


def tokenize(projname, suffixsymbs, suffixsyns, reported):
  """
  Converts a string describing gates reported in an experiment into a list of standardised tokens
  corresponding to those gates, which are determined by referencing the lists of suffix symbols and
  suffix synonyms passed to the function.

  Parameters:
       projname: the name of the project that reported the gates
       reported: a string describing the gates reported in an experiment
       suffixsyns: OrderedDict mapping suffix synonyms to their standardised suffix name;
                   e.g. OrderedDict([('high', 'high'), ('hi', 'high'), ('bright', 'high'), etc.])
       suffixsymbs: dict mapping suffix names to their symbolic suffix representation;
                    e.g {'medium': '+~', 'negative': '-', etc.}
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

    for suffixsyn in suffixsyns.keys():
      if gate.endswith(suffixsyn):
        gate = re.sub('\s*' + re.escape(suffixsyn) + '$', suffixsymbs[suffixsyns[suffixsyn]], gate)
        continue

    gate = re.sub(' ', '_', gate)

    # It may sometimes happen that the gate is empty, for example due to a trailing comma in the
    # reported field. Ignore any such empty gates.
    if gate:
      tokenized.append(gate)

  return tokenized


def normalize(gates, gate_mappings, special_gates, symbols):
  """
  Normalise a tokenised list of gates by replacing gate labels with ontology ids

  Parameters:
      gates: list of strings describing gates
      gate_mappings: dict containing mappings of gate labels to ontology ids
      special_gates: additional information regarding a certain number of special gates.
      symbols: list of suffix symbols
  """

  # Inner function to split the name of a gate from its suffix symbol.
  def split_gate(gate):
    # Reverse sort the suffix symbols by length to make sure we don't match on a substring of
    # a longer suffix symbol when we are looking for a shorter suffix symbol
    # (e.g. '+' is a substring of '++') so we need to search for '++' before searching for '+'
    for symbol in sorted(list(symbols), key=len, reverse=True):
      if gate.endswith(symbol):
        return [gate[0:-len(symbol)], symbol]
    # If we get to here then there isn't a suffix.
    return [gate, '']

  normalized_gates = []
  for gate in gates:
    # First try to find the ontology id in the gate_mappings map. If it isn't there, check to
    # see if it has a synonym in the map of special gates. If we don't find it there either, then
    # prefix the gate with a '!'.
    label, suffixsymb = split_gate(gate)
    ontology_id = gate_mappings.get(label)
    if not ontology_id:
      ontids_from_special = [val['Ontology ID'] for key, val in special_gates.items() if label and (
        label == key or label in val['Synonyms'].split(', ') or label == val['Toxic Synonym'])]
      if ontids_from_special and len(ontids_from_special) > 1:
        # This shouldn't happen unless there are duplicate names in the special gates file
        print("Warning: {} ontology ids found with label: '{}'"
              .format(len(ontids_from_special), gate))

      ontology_id = ontids_from_special[0] if ontids_from_special else "!{}".format(label)

    # Replace the long form of an ontology ID (which includes a URL) with its short form: 'PR:<id>'
    ontology_id = ontology_id.replace('http://purl.obolibrary.org/obo/PR_', 'PR:')
    normalized_gates.append(ontology_id + suffixsymb)

  return normalized_gates


def main():
  # Define command-line parameters
  parser = argparse.ArgumentParser(description='Normalize cell population descriptions')
  parser.add_argument('excluded', type=argparse.FileType('r'),
                      help='a TSV file with experiment accessions to be ignored')
  parser.add_argument('scale', type=argparse.FileType('r'),
                      help='a TSV file with the value scale (e.g. high, low, negative)')
  parser.add_argument('mappings', type=argparse.FileType('r'),
                      help='a TSV file which maps gate labels to ontology ids/keywords')
  parser.add_argument('special', type=argparse.FileType('r'),
                      help='a TSV file containing extra information about a subset of gates')
  parser.add_argument('source', type=argparse.FileType('r'),
                      help='the source data TSV file')
  parser.add_argument('output', type=str,
                      help='the output TSV file')

  # Parse command-line parameters
  args = parser.parse_args()

  # Load the contents of the file given by the command-line parameter args.excluded
  # These are the experiments we should ignore when reading from the source file
  excluded_experiments = set()
  rows = csv.DictReader(args.excluded, delimiter='\t')
  for row in rows:
    excluded_experiments.add(row['Experiment Accession'])

  # Load the contents of the file given by the command-line parameter args.scale.
  # This defines the suffix synonyms and sumbols for various scaling indicators,
  # which must be noted during parsing
  suffixsymbs = {}
  suffixsyns = OrderedDict()
  rows = csv.DictReader(args.scale, delimiter='\t')
  for row in rows:
    suffixsymbs[row['Name']] = row['Symbol']
    suffixsyns[row['Name']] = row['Name']
    for synonym in row['Synonyms'].split(','):
      synonym = synonym.strip()
      if synonym != '':
        suffixsyns[synonym] = row['Name']

  # Load the contents of the file given by the command-line parameter args.mappings.
  # This file associates gate laels with the ontology ids / keywords with which we populate the
  # 'Gating mapped to ontologies' column of the output file.
  rows = csv.DictReader(args.mappings, delimiter='\t')
  gate_mappings = {}
  for row in rows:
    gate_mappings[row['Label']] = row['Ontology ID']

  # Load the contents of the file given by the command-line parameter args.special.
  # This file (similary to the args.mapping file) associates certain gate labels with ontology ids
  # but also contains additional information regarding these gates.
  rows = csv.DictReader(args.special, delimiter='\t')
  special_gates = {}
  for row in rows:
    special_gates[row['Label']] = {
      'Ontology ID': row['Ontology ID'],
      'Synonyms': row['Synonyms'],
      'Toxic Synonym': row['toxic synonym']}

  # Finally, load the contents of the source file. For each row determine the tokenised and
  # normalised population definition based on the definition reported in the source file and our
  # scaling indicators. Then copy the row into a new file with additional columns containing the
  # tokenised and normalised definitions. Ignore any rows describing excluded experiments.
  rows = csv.DictReader(args.source, delimiter='\t')
  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    output_fieldnames = rows.fieldnames + ['Gating tokenized'] + ['Gating mapped to ontologies']
    w.writerow(output_fieldnames)
    for row in rows:
      if not row['EXPERIMENT_ACCESSION'] in excluded_experiments:
        # Remove any surrounding quotation marks
        reported = row['POPULATION_DEFNITION_REPORTED'].strip('"').strip("'")
        gates = tokenize(row['NAME'], suffixsymbs, suffixsyns, reported)
        row['Gating tokenized'] = '; '.join(gates)
        ontologies = normalize(gates, gate_mappings, special_gates, suffixsymbs.values())
        row['Gating mapped to ontologies'] = '; '.join(ontologies)
        # Explicitly reference output_fieldnames here to make sure that the order in which the data
        # is written to the file matches the header order.
        w.writerow([row[fn] for fn in output_fieldnames])


if __name__ == "__main__":
  main()


# Unit tests for use with the tool `pytest` are defined below. To run these, run
# `pytest normalize.py` from the command line.

def test_normalize():
  suffixsymbs = {
    'high': '++',
    'medium': '+~',
    'low': '+-',
    'positive': '+',
    'negative': '-'
  }

  suffixsyns = {
    'high': 'high',
    'hi': 'high',
    'bright': 'high',
    'Bright': 'high',
    'bri': 'high',
    'br': 'high',
    '(high)': 'high',
    'medium': 'medium',
    'med': 'medium',
    'intermediate': 'medium',
    'int': 'medium',
    '(medium)': 'medium',
    'low': 'low',
    'lo': 'low',
    'LO': 'low',
    'dim': 'low',
    'di': 'low',
    '(low)': 'low',
    'positive': 'positive',
    'negative': 'negative'
  }

  gate_mappings = {
    'Alexa350': 'PR:001',
    'Alexa750': 'PR:002',
    'Annexin': 'PR:003',
    'B220-_live': 'PR:004',
    'CCR7': 'PR:005',
    'CD14': 'PR:006',
    'CD16': 'PR:007',
    'CD19': 'PR:008',
    'CD20': 'PR:009',
    'CD21': 'PR:010',
    'CD24': 'PR:011',
    'CD27': 'PR:012',
    'CD3': 'PR:013',
    'CD33': 'PR:014',
    'CD38': 'PR:015',
    'CD4': 'PR:016',
    'CD44': 'PR:017',
    'CD45RA': 'PR:018',
    'CD4_T_cells': 'PR:019',
    'CD56': 'PR:020',
    'CD69': 'PR:021',
    'CD8': 'PR:022',
    'CD94': 'PR:023',
    'CXCR5': 'PR:024',
    'doublet_excluded': 'PR:025',
    'ICOS': 'PR:026',
    'IFNg': 'PR:027',
    'IL2': 'PR:028',
    'live': 'PR:029',
    'Live_cells': 'PR:030',
    'Lymph': 'PR:031',
    'Lymphocytes': 'PR:032',
    'lymphocytes': 'PR:033',
    'Michael': 'PR:034',
    'NP_tet': 'PR:035',
    'PD1': 'PR:036',
    'Robert': 'PR:037',
    'singlets': 'PR:038',
    'small_lymphocyte': 'PR:039',
    'SSC': 'PR:040',
    'TNFa': 'PR:041',
    'Uninfected': 'PR:042',
    'viable': 'PR:043',
  }

  special_gates = {
    'Michael': {'Ontology ID': 'PR:034', 'Synonyms': 'Mike, Mickey, Mick',
                'Toxic Synonym': 'Mikey'},
    'Robert': {'Ontology ID': 'PR:037', 'Synonyms': 'Rob, Bob, Bert',
               'Toxic Synonym': 'Bobert'}
  }

  reported = 'CD14-CD56-CD3+CD4+CD8-CD45RA+CCR7+'
  tokens = tokenize('LaJolla', suffixsymbs, suffixsyns, reported)
  assert tokens == ['CD14-', 'CD56-', 'CD3+', 'CD4+', 'CD8-', 'CD45RA+', 'CCR7+']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:006-', 'PR:020-', 'PR:013+', 'PR:016+', 'PR:022-', 'PR:018+', 'PR:005+']

  reported = 'CD3-, CD19+, CD20-, CD27hi, CD38hi'
  tokens = tokenize('Emory', suffixsymbs, suffixsyns, reported)
  assert tokens == ['CD3-', 'CD19+', 'CD20-', 'CD27++', 'CD38++']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:013-', 'PR:008+', 'PR:009-', 'PR:012++', 'PR:015++']

  reported = 'CD3-/CD19+/CD20lo/CD38hi/CD27hi'
  tokens = tokenize('IPIRC', suffixsymbs, suffixsyns, reported)
  assert tokens == ['CD3-', 'CD19+', 'CD20+-', 'CD38++', 'CD27++']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:013-', 'PR:008+', 'PR:009+-', 'PR:015++', 'PR:012++']

  reported = 'CD21hi/CD24int'
  tokens = tokenize('Watson', suffixsymbs, suffixsyns, reported)
  assert tokens == ['CD21++', 'CD24+~']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:010++', 'PR:011+~']

  reported = 'Annexin negative'
  tokens = tokenize('Ltest', suffixsymbs, suffixsyns, reported)
  assert tokens == ['Annexin-']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:003-']

  reported = 'CD3+ AND CD4+ AND small lymphocyte'
  tokens = tokenize('VRC', suffixsymbs, suffixsyns, reported)
  assert tokens == ['CD3+', 'CD4+', 'small_lymphocyte']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:013+', 'PR:016+', 'PR:039']

  reported = 'Lymphocytes and CD8+ and NP tet+'
  tokens = tokenize('Ertl', suffixsymbs, suffixsyns, reported)
  assert tokens == ['Lymphocytes', 'CD8+', 'NP_tet+']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:032', 'PR:022+', 'PR:035+']

  reported = 'Activated T: viable/singlets/Lymph/CD3+'
  tokens = tokenize('Stanford', suffixsymbs, suffixsyns, reported)
  assert tokens == ['viable', 'singlets', 'Lymph', 'CD3+']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:043', 'PR:038', 'PR:031', 'PR:013+']

  # TODO: Is this right?
  reported = 'CD14-CD33-/CD3-/CD16+CD56+/CD94+'
  tokens = tokenize('Stanford', suffixsymbs, suffixsyns, reported)
  assert tokens == ['CD14-', 'CD33-', 'CD3-', 'CD16+', 'CD56+', 'CD94+']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:006-', 'PR:014-', 'PR:013-', 'PR:007+', 'PR:020+', 'PR:023+']

  # TODO: Is this right?
  reported = 'Live cells/CD4 T cells/CD4+ CD45RA-/Uninfected/SSC low'
  tokens = tokenize('Mayo', suffixsymbs, suffixsyns, reported)
  assert tokens == ['Live_cells', 'CD4_T_cells', 'CD4+', 'CD45RA-', 'Uninfected', 'SSC+-']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:030', 'PR:019', 'PR:016+', 'PR:018-', 'PR:042', 'PR:040+-']

  reported = 'B220- live,doublet excluded,CD4+ CD44highCXCR5highPD1high,ICOS+'
  tokens = tokenize('New York Influenza', suffixsymbs, suffixsyns, reported)
  assert tokens == ['B220-_live', 'doublet_excluded', 'CD4+', 'CD44++', 'CXCR5++', 'PD1++', 'ICOS+']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:004', 'PR:025', 'PR:016+', 'PR:017++', 'PR:024++', 'PR:036++',
                        'PR:026+']

  reported = 'lymphocytes/singlets/live/CD19-CD14-/CD3+/CD8+/CD69+IFNg+IL2+TNFa+'
  tokens = tokenize('New York Influenza', suffixsymbs, suffixsyns, reported)
  assert tokens == ['lymphocytes', 'singlets', 'live', 'CD19-', 'CD14-', 'CD3+', 'CD8+', 'CD69+',
                    'IFNg+', 'IL2+', 'TNFa+']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:033', 'PR:038', 'PR:029', 'PR:008-', 'PR:006-', 'PR:013+', 'PR:022+',
                        'PR:021+', 'PR:027+', 'PR:028+', 'PR:041+']

  reported = 'Alexa350 (high) + Alexa750 (medium)'
  tokens = tokenize('Modeling Viral', suffixsymbs, suffixsyns, reported)
  assert tokens == ['Alexa350++', 'Alexa750+~']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:001++', 'PR:002+~']

  reported = 'TNFa+IFNg-'
  tokens = tokenize('Flow Cytometry Analysis', suffixsymbs, suffixsyns, reported)
  assert tokens == ['TNFa+', 'IFNg-']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:041+', 'PR:027-']

  reported = 'Mikeyhigh/Rob+/Alexa350 (high)/CD33+ý'
  tokens = tokenize('Some Project', suffixsymbs, suffixsyns, reported)
  assert tokens == ['Mikey++', 'Rob+', 'Alexa350++', 'CD33+-']
  ontologies = normalize(tokens, gate_mappings, special_gates, suffixsymbs.values())
  assert ontologies == ['PR:034++', 'PR:037+', 'PR:001++', 'PR:014+-']
