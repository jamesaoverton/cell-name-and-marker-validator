#!/usr/bin/env python3

import argparse, csv, re


def normalize(project, replacements, reported):
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
    reported = re.sub('hi', '++', reported)
    reported = re.sub('bri', '++', reported)
    reported = re.sub('low', '+-', reported)
    reported = re.sub(r'([\-\+])(CD\d+|CX\w+\d+|CCR\d)', r'\1/\2', reported)
    gates = re.split('\/|,\s+', reported)
  elif 'Baylor' in project:
    reported = re.sub(',,+', ',', reported)
    reported = re.sub('hi', '++', reported)
    reported = re.sub('bri', '++', reported)
    reported = re.sub('br', '++', reported)
    reported = re.sub('low', '+-', reported)
    reported = re.sub('dim', '+-', reported)
    reported = re.sub(' granulocyte', ', granulocyte', reported)
    reported = re.sub(r'([\-\+])CD(\d)', r'\1/CD\2', reported)
    gates = re.split('\/|,\s*', reported)
  elif 'Rochester' in project:
    gates = re.split(';+\s*|\/', reported)
  elif 'Mayo' in project:
    reported = re.sub(r' CD(\d)', r' /CD\1', reported)
    reported = re.sub(r' high', r'++', reported)
    gates = re.split('\/', reported)
  elif 'ARA06' in project:
    gates = re.findall('\w+[\-\+]*', reported)
  elif 'Center for Human Immunology' in project:
    reported = re.sub('high', '++', reported)
    gates = re.findall('\w+[\-\+]*', reported)
  elif 'Seattle Biomed' in project:
    gates = re.split('\/', reported)
  elif 'Improving Kidney' in project:
    reported = re.sub('hi', '++', reported)
    reported = re.sub('low', '+-', reported)
    reported = re.sub(r'([\-\+])CD(\d)', r'\1/CD\2', reported)
    gates = re.split('\/', reported)
  elif 'New York Influenza' in project:
    reported = re.sub('high', '++', reported)
    reported = re.sub('low', '+-', reported)
    reported = re.sub('dim', '+-', reported)
    reported = re.sub(r'([\-\+ ])(CD\d+|CXCR\d|BCL\d|IF\w+|PD\d+|IL\d+|TNFa)', r'\1/\2', reported)
    gates = re.split('\/|,', reported)
  elif 'Modeling Viral' in project:
    gates = re.split('\s+AND\s+|_AND_|\s+\+\s+', reported)
  elif 'Immunobiology of Aging' in project:
    reported = re.sub('hi', '++', reported)
    reported = re.sub('low', '+-', reported)
    reported = re.sub(r'([\-\+])(CD\d+|Ig\w+)', r'\1/\2', reported)
    gates = re.split('\/', reported)
  elif 'Flow Cytometry Analysis' in project:
    reported = re.sub(r'(\+|\-)(CD\d+|Ig\w+|IL\d+|IF\w+|TNF\w+|Per\w+)', r'\1/\2', reported)
    gates = re.split('\/', reported)
  elif 'Wistar' in project:
    gates = re.findall('\w+[\-\+]*', reported)
  elif 'ITN019AD' in project:
    reported = re.sub('(\s+AND)?\s+R\d+.*$', '', reported)
    reported = re.sub(' Bright', '++', reported)
    reported = re.sub('\s+AND\s+', ' ', reported)
    gates = re.split('\s+', reported)
  else:
    gates = re.split('\/|,\s*|\s+AND\s+|\s+and\s+', reported)

  normalized = []
  for gate in gates:
    gate = gate.strip()
    gate = re.sub('ý', '-', gate) # Unicode hyphen
    gate = re.sub(' negative$', '-', gate)
    gate = re.sub(' low$', '+-', gate)
    gate = re.sub(' \(high\)$',  '++', gate)
    gate = re.sub(' \(low\)$', '+-', gate)
    gate = re.sub(' \(medium\)$', '+~', gate)
    gate = re.sub('-high$',  '++', gate)
    gate = re.sub('-medium$', '+~', gate)
    gate = re.sub('-low$', '+-', gate)
    gate = re.sub('high$',  '++', gate)
    gate = re.sub('hi$',  '++', gate)
    gate = re.sub('int$', '+~', gate)
    gate = re.sub('medium$',  '++', gate)
    gate = re.sub('low$', '+-', gate)
    gate = re.sub('lo$',  '+-', gate)
    gate = re.sub('LO$',  '+-', gate)
    gate = re.sub('dim$', '+-', gate)
    gate = re.sub('di$',  '+-', gate)
    gate = re.sub(' ', '_', gate)

    name = gate.rstrip('+-~')
    if name in replacements:
      level = re.search('[\-\+\~]*$', gate).group(0)
      gate = replacements[name] + level

    normalized.append(gate)

  return normalized

def main():
  parser = argparse.ArgumentParser(
      description='Normalize cell population descriptions')
  parser.add_argument('special',
      type=argparse.FileType('r'),
      help='a TSV file with special gates: ID, Label, Synonyms')
  parser.add_argument('source',
      type=argparse.FileType('r'),
      help='the source data TSV file')
  parser.add_argument('output',
      type=str,
      help='the output TSV file')
  args = parser.parse_args()

  replacements = {}
  rows = csv.DictReader(args.special, delimiter='\t')
  for row in rows:
    gate = row['Label']
    replacements[gate] = gate # Include identity
    if 'Synonyms' in row and row['Synonyms'] is not None:
      synonyms = re.split(r',\s+', row['Synonyms'])
      for synonym in synonyms:
        replacements[synonym.strip()] = gate

  rows = csv.DictReader(args.source, delimiter='\t')
  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    w.writerow(list(next(rows).keys()) + ['POPULATION_DEFNITION_NORMALIZED'])
    for row in rows:
      reported = row['POPULATION_DEFNITION_REPORTED']
      gates = normalize(row['NAME'], replacements, reported)
      if gates:
        row['POPULATION_DEFNITION_NORMALIZED'] = ' '.join(gates)
        w.writerow(row.values())


if __name__ == "__main__":
  main()


def test_normalize():
  replacements = {
    'CD3': 'CD3e',
    'CD8': 'CD8a',
    'Lymph': 'lymphocytes',
    'Lymphocytes': 'lymphocytes'
  }

  reported = 'CD14-CD56-CD3+CD4+CD8-CD45RA+CCR7+'
  assert normalize('LaJolla', replacements, reported) == [
    'CD14-', 'CD56-', 'CD3e+', 'CD4+', 'CD8a-', 'CD45RA+', 'CCR7+'
  ]

  reported = 'CD3-, CD19+, CD20-, CD27hi, CD38hi'
  assert normalize('Emory', replacements, reported) == [
    'CD3e-', 'CD19+', 'CD20-', 'CD27++', 'CD38++'
  ]

  reported = 'CD3-/CD19+/CD20lo/CD38hi/CD27hi'
  assert normalize('IPIRC', replacements, reported) == [
    'CD3e-', 'CD19+', 'CD20+-', 'CD38++', 'CD27++'
  ]

  reported = 'CD21hi/CD24int'
  assert normalize('Watson', replacements, reported) == [
    'CD21++', 'CD24+~'
  ]

  reported = 'Annexin negative'
  assert normalize('Ltest', replacements, reported) == [
    'Annexin-'
  ]

  reported = 'CD3+ AND CD4+ AND small lymphocyte'
  assert normalize('VRC', replacements, reported) == [
    'CD3e+', 'CD4+', 'small_lymphocyte'
  ]

  reported = 'Lymphocytes and CD8+ and NP tet+'
  assert normalize('Ertl', replacements, reported) == [
    'lymphocytes', 'CD8a+', 'NP_tet+'
  ]

  reported = 'Activated T: viable/singlets/Lymph/CD3+'
  assert normalize('Stanford', replacements, reported) == [
    'viable', 'singlets', 'lymphocytes', 'CD3e+'
  ]

  # TODO: Is this right?
  reported = 'CD14-CD33-/CD3-/CD16+CD56+/CD94+'
  assert normalize('Stanford', replacements, reported) == [
    'CD14-', 'CD33-', 'CD3e-', 'CD16+', 'CD56+', 'CD94+'
  ]

  # TODO: Is this right?
  reported = 'Live cells/CD4 T cells/CD4+ CD45RA-/Uninfected/SSC low'
  assert normalize('Mayo', replacements, reported) == [
    'Live_cells', 'CD4_T_cells', 'CD4+', 'CD45RA-', 'Uninfected', 'SSC+-'
  ]

  reported = 'B220- live,doublet excluded,CD4+ CD44highCXCR5highPD1high,ICOS+'
  assert normalize('New York Influenza', replacements, reported) == [
    'B220-_live', 'doublet_excluded', 'CD4+', 'CD44++', 'CXCR5++', 'PD1++', 'ICOS+'
  ]

  reported = 'lymphocytes/singlets/live/CD19-CD14-/CD3+/CD8+/CD69+IFNg+IL2+TNFa+'
  assert normalize('New York Influenza', replacements, reported) == [
    'lymphocytes', 'singlets', 'live', 'CD19-', 'CD14-', 'CD3e+', 'CD8a+', 'CD69+', 'IFNg+', 'IL2+', 'TNFa+'
  ]

  reported = 'Alexa350 (high) + Alexa750 (medium)'
  assert normalize('Modeling Viral', replacements, reported) == [
    'Alexa350++', 'Alexa750+~'
  ]

  reported = 'TNFa+IFNg-'
  assert normalize('Flow Cytometry Analysis', replacements, reported) == [
    'TNFa+', 'IFNg-'
  ]
