#!/usr/bin/env python3

import argparse, csv, re
from collections import OrderedDict


def normalize(project, symbols, suffixes, reported):
  # Ignore everything to the left of the first colon on a given line.
  if ': ' in reported:
    reported = re.sub('^.*:\s+', '', reported)

  gates = []
  if 'LaJolla' in project:
    gates = re.findall('\w+[\-\+]*', reported)
  elif 'Emory' in project:
    gates = re.split(',\s+', reported)
  elif 'IPIRC' in project:
    gates = re.split('\/', reported)
  elif 'Watson' in project:
    gates = re.split('\/', reported)
  elif 'Ltest' in project:
    gates = re.split('\/', reported)
  elif 'VRC' in project:
    gates = re.split('\s+AND\s+', reported)
  elif 'Ertl' in project:
    gates = re.split('\s+and\s+', reported)
  elif 'Stanford' in project:
    reported = re.sub(r'([\-\+])(CD\d+|CX\w+\d+|CCR\d)', r'\1/\2', reported)
    gates = re.split('\/|,\s+', reported)
  elif 'Baylor' in project:
    reported = re.sub(',,+', ',', reported)
    reported = re.sub(' granulocyte', ', granulocyte', reported)
    reported = re.sub(r'([\-\+])CD(\d)', r'\1/CD\2', reported)
    gates = re.split('\/|,\s*', reported)
  elif 'Rochester' in project:
    gates = re.split(';+\s*|\/', reported)
  elif 'Mayo' in project:
    reported = re.sub(r' CD(\d)', r' /CD\1', reported)
    gates = re.split('\/', reported)
  elif 'ARA06' in project:
    gates = re.findall('\w+[\-\+]*', reported)
  elif 'Center for Human Immunology' in project:
    gates = re.findall('\w+[\-\+]*', reported)
  elif 'Seattle Biomed' in project:
    gates = re.split('\/', reported)
  elif 'Improving Kidney' in project:
    reported = re.sub(r'([\-\+])CD(\d)', r'\1/CD\2', reported)
    gates = re.split('\/', reported)
  elif 'New York Influenza' in project:
    reported = re.sub('high', 'high ', reported)
    reported = re.sub(r'([\-\+ ])(CD\d+|CXCR\d|BCL\d|IF\w+|PD\d+|IL\d+|TNFa)', r'\1/\2', reported)
    gates = re.split('\/|,', reported)
  elif 'Modeling Viral' in project:
    gates = re.split('\s+AND\s+|_AND_|\s+\+\s+', reported)
  elif 'Immunobiology of Aging' in project:
    reported = re.sub(r'([\-\+])(CD\d+|Ig\w+)', r'\1/\2', reported)
    gates = re.split('\/', reported)
  elif 'Flow Cytometry Analysis' in project:
    reported = re.sub(r'(\+|\-)(CD\d+|Ig\w+|IL\d+|IF\w+|TNF\w+|Per\w+)', r'\1/\2', reported)
    gates = re.split('\/', reported)
  elif 'Wistar' in project:
    gates = re.findall('\w+[\-\+]*', reported)
  elif 'ITN019AD' in project:
    reported = re.sub('(\s+AND)?\s+R\d+.*$', '', reported)
    reported = re.sub('\s+AND\s+', ' ', reported)
    gates = re.split('\s+', reported)
  else:
    gates = re.split('\/|,\s*|\s+AND\s+|\s+and\s+', reported)

  normalized = []
  for gate in gates:
    gate = gate.strip()
    gate = re.sub('ý', '-', gate) # Unicode hyphen

    for suffix in suffixes.keys():
      if gate.endswith(suffix):
        gate = re.sub('\s*' + re.escape(suffix) + '$', symbols[suffixes[suffix]], gate)
        continue

    gate = re.sub(' ', '_', gate)

    normalized.append(gate)

  return normalized


def main():
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
  args = parser.parse_args()

  excluded_experiments = set()
  rows = csv.DictReader(args.excluded, delimiter='\t')
  for row in rows:
    excluded_experiments.add(row['Experiment Accession'])

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

  rows = csv.DictReader(args.source, delimiter='\t')
  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    output_fieldnames = rows.fieldnames + ['POPULATION_DEFNITION_NORMALIZED']
    w.writerow(output_fieldnames)
    for row in rows:
      if not row['EXPERIMENT_ACCESSION'] in excluded_experiments:
        reported = row['POPULATION_DEFNITION_REPORTED']
        gates = normalize(row['NAME'], symbols, suffixes, reported)
        row['POPULATION_DEFNITION_NORMALIZED'] = ' '.join(gates) if gates else ''
        # Explicitly reference output_fieldnames here to make sure that the order in which the data
        # is written to the file matches the header order.
        w.writerow([row[fn] for fn in output_fieldnames])


if __name__ == "__main__":
  main()


def test_normalize():
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
  assert normalize('LaJolla', symbols, suffixes, reported) == [
    'CD14-', 'CD56-', 'CD3+', 'CD4+', 'CD8-', 'CD45RA+', 'CCR7+'
  ]

  reported = 'CD3-, CD19+, CD20-, CD27hi, CD38hi'
  assert normalize('Emory', symbols, suffixes, reported) == [
    'CD3-', 'CD19+', 'CD20-', 'CD27++', 'CD38++'
  ]

  reported = 'CD3-/CD19+/CD20lo/CD38hi/CD27hi'
  assert normalize('IPIRC', symbols, suffixes, reported) == [
    'CD3-', 'CD19+', 'CD20+-', 'CD38++', 'CD27++'
  ]

  reported = 'CD21hi/CD24int'
  assert normalize('Watson', symbols, suffixes, reported) == [
    'CD21++', 'CD24+~'
  ]

  reported = 'Annexin negative'
  assert normalize('Ltest', symbols, suffixes, reported) == [
    'Annexin-'
  ]

  reported = 'CD3+ AND CD4+ AND small lymphocyte'
  assert normalize('VRC', symbols, suffixes, reported) == [
    'CD3+', 'CD4+', 'small_lymphocyte'
  ]

  reported = 'Lymphocytes and CD8+ and NP tet+'
  assert normalize('Ertl', symbols, suffixes, reported) == [
    'Lymphocytes', 'CD8+', 'NP_tet+'
  ]

  reported = 'Activated T: viable/singlets/Lymph/CD3+'
  assert normalize('Stanford', symbols, suffixes, reported) == [
    'viable', 'singlets', 'Lymph', 'CD3+'
  ]

  ## TODO: Is this right?
  reported = 'CD14-CD33-/CD3-/CD16+CD56+/CD94+'
  assert normalize('Stanford', symbols, suffixes, reported) == [
    'CD14-', 'CD33-', 'CD3-', 'CD16+', 'CD56+', 'CD94+'
  ]

  ## TODO: Is this right?
  reported = 'Live cells/CD4 T cells/CD4+ CD45RA-/Uninfected/SSC low'
  assert normalize('Mayo', symbols, suffixes, reported) == [
    'Live_cells', 'CD4_T_cells', 'CD4+', 'CD45RA-', 'Uninfected', 'SSC+-'
  ]

  reported = 'B220- live,doublet excluded,CD4+ CD44highCXCR5highPD1high,ICOS+'
  assert normalize('New York Influenza', symbols, suffixes, reported) == [
    'B220-_live', 'doublet_excluded', 'CD4+', 'CD44++', 'CXCR5++', 'PD1++', 'ICOS+'
  ]

  reported = 'lymphocytes/singlets/live/CD19-CD14-/CD3+/CD8+/CD69+IFNg+IL2+TNFa+'
  assert normalize('New York Influenza', symbols, suffixes, reported) == [
    'lymphocytes', 'singlets', 'live', 'CD19-', 'CD14-', 'CD3+', 'CD8+', 'CD69+', 'IFNg+', 'IL2+', 'TNFa+'
  ]

  reported = 'Alexa350 (high) + Alexa750 (medium)'
  assert normalize('Modeling Viral', symbols, suffixes, reported) == [
    'Alexa350++', 'Alexa750+~'
  ]

  reported = 'TNFa+IFNg-'
  assert normalize('Flow Cytometry Analysis', symbols, suffixes, reported) == [
    'TNFa+', 'IFNg-'
  ]
