#!/usr/bin/env python3

import argparse, csv, re
from collections import OrderedDict


def tokenize(projname, symbols, suffixes, reported):
  def any_in_projname(kwds):
    # Inner function to determine whether the given project name contains any of the given keywords
    return any([kwd in projname for kwd in kwds])

  # Ignore everything to the left of the first colon on a given line.
  if ': ' in reported:
    reported = re.sub('^.*:\s+', '', reported)

  # Every project has different types of gates and methods for delimiting gates, so parsing the
  # reported gates from the source file will in general be different for each project.
  gates = []
  if any_in_projname(['LaJolla', 'ARA06', 'Center for Human Immunology', 'Wistar']):
    # No delimiters between gates
    gates = re.findall('\w+[\-\+]*', reported)
  elif any_in_projname(['IPIRC', 'Watson', 'Ltest', 'Seattle Biomed']):
    # Gates are separated by forward slashes
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
    gate = re.sub('ý', '-', gate) # Unicode hyphen

    for suffix in suffixes.keys():
      if gate.endswith(suffix):
        gate = re.sub('\s*' + re.escape(suffix) + '$', symbols[suffixes[suffix]], gate)
        continue

    gate = re.sub(' ', '_', gate)

    tokenized.append(gate)

  return tokenized

def normalize(gates):
  pass

def main():
  # Define command-line parameters
  parser = argparse.ArgumentParser(
      description='Normalize cell population descriptions')
  parser.add_argument('excluded',
      type=argparse.FileType('r'),
      help='a TSV file with experiment accessions to be ignored')
  parser.add_argument('scale',
      type=argparse.FileType('r'),
      help='a TSV file with the value scale (e.g. high, low, negative)')
  parser.add_argument('source',
      type=argparse.FileType('r'),
      help='the source data TSV file')
  parser.add_argument('output',
      type=str,
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
  # These define suffix codes for various scaling indicators, which must be noted during parsing
  symbols = {}
  suffixes = OrderedDict()
  rows = csv.DictReader(args.scale, delimiter='\t')
  for row in rows:
    symbols[row['Name']] = row['Symbol']
    suffixes[row['Name']] = row['Name']
    for synonym in row['Synonyms'].split(','):
      synonym = synonym.strip()
      if synonym != '':
        suffixes[synonym] = row['Name']

  # Load the contents of the source file. Then for each row determine the tokenised and normalised
  # population definition based on the definition reported in the source file and our scaling
  # indicators. Then copy the row into a new file with additional columns containing the tokenised
  # and normalised definitions. Ignore any rows describing excluded experiments.
  rows = csv.DictReader(args.source, delimiter='\t')
  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    output_fieldnames = (
      rows.fieldnames + ['Gating tokenized'] + ['Gating mapped to ontologies'])
    w.writerow(output_fieldnames)
    for row in rows:
      if not row['EXPERIMENT_ACCESSION'] in excluded_experiments:
        reported = row['POPULATION_DEFNITION_REPORTED']
        gates = tokenize(row['NAME'], symbols, suffixes, reported)
        row['Gating tokenized'] = '; '.join(gates) if gates else ''
        ontologies = normalize(gates)
        row['Gating mapped to ontologies'] = ' '.join(ontologies) if ontologies else ''
        # Explicitly reference output_fieldnames here to make sure that the order in which the data
        # is written to the file matches the header order.
        w.writerow([row[fn] for fn in output_fieldnames])


if __name__ == "__main__":
  main()


def test_tokenize():
  symbols = {
    'high': '++',
    'medium': '+~',
    'low': '+-',
    'positive': '+',
    'negative': '-'
  }
  suffixes = {
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
  
  reported = 'CD14-CD56-CD3+CD4+CD8-CD45RA+CCR7+'
  assert tokenize('LaJolla', symbols, suffixes, reported) == [
    'CD14-', 'CD56-', 'CD3+', 'CD4+', 'CD8-', 'CD45RA+', 'CCR7+'
  ]

  reported = 'CD3-, CD19+, CD20-, CD27hi, CD38hi'
  assert tokenize('Emory', symbols, suffixes, reported) == [
    'CD3-', 'CD19+', 'CD20-', 'CD27++', 'CD38++'
  ]

  reported = 'CD3-/CD19+/CD20lo/CD38hi/CD27hi'
  assert tokenize('IPIRC', symbols, suffixes, reported) == [
    'CD3-', 'CD19+', 'CD20+-', 'CD38++', 'CD27++'
  ]

  reported = 'CD21hi/CD24int'
  assert tokenize('Watson', symbols, suffixes, reported) == [
    'CD21++', 'CD24+~'
  ]

  reported = 'Annexin negative'
  assert tokenize('Ltest', symbols, suffixes, reported) == [
    'Annexin-'
  ]

  reported = 'CD3+ AND CD4+ AND small lymphocyte'
  assert tokenize('VRC', symbols, suffixes, reported) == [
    'CD3+', 'CD4+', 'small_lymphocyte'
  ]

  reported = 'Lymphocytes and CD8+ and NP tet+'
  assert tokenize('Ertl', symbols, suffixes, reported) == [
    'Lymphocytes', 'CD8+', 'NP_tet+'
  ]

  reported = 'Activated T: viable/singlets/Lymph/CD3+'
  assert tokenize('Stanford', symbols, suffixes, reported) == [
    'viable', 'singlets', 'Lymph', 'CD3+'
  ]

  ## TODO: Is this right?
  reported = 'CD14-CD33-/CD3-/CD16+CD56+/CD94+'
  assert tokenize('Stanford', symbols, suffixes, reported) == [
    'CD14-', 'CD33-', 'CD3-', 'CD16+', 'CD56+', 'CD94+'
  ]

  ## TODO: Is this right?
  reported = 'Live cells/CD4 T cells/CD4+ CD45RA-/Uninfected/SSC low'
  assert tokenize('Mayo', symbols, suffixes, reported) == [
    'Live_cells', 'CD4_T_cells', 'CD4+', 'CD45RA-', 'Uninfected', 'SSC+-'
  ]

  reported = 'B220- live,doublet excluded,CD4+ CD44highCXCR5highPD1high,ICOS+'
  assert tokenize('New York Influenza', symbols, suffixes, reported) == [
    'B220-_live', 'doublet_excluded', 'CD4+', 'CD44++', 'CXCR5++', 'PD1++', 'ICOS+'
  ]

  reported = 'lymphocytes/singlets/live/CD19-CD14-/CD3+/CD8+/CD69+IFNg+IL2+TNFa+'
  assert tokenize('New York Influenza', symbols, suffixes, reported) == [
    'lymphocytes', 'singlets', 'live', 'CD19-', 'CD14-', 'CD3+', 'CD8+', 'CD69+', 'IFNg+', 'IL2+', 'TNFa+'
  ]

  reported = 'Alexa350 (high) + Alexa750 (medium)'
  assert tokenize('Modeling Viral', symbols, suffixes, reported) == [
    'Alexa350++', 'Alexa750+~'
  ]

  reported = 'TNFa+IFNg-'
  assert tokenize('Flow Cytometry Analysis', symbols, suffixes, reported) == [
    'TNFa+', 'IFNg-'
  ]
