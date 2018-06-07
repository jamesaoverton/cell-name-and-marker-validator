#!/usr/bin/env python3

import argparse, csv, re

def normalize_lajolla(reported):
  gates = re.findall('\w+[\-\+]', reported)
  return gates

def normalize_emory(reported):
  gates = []
  for gate in re.split(',\s*', reported):
    gate = re.sub('hi', '+', gate)
    gates.append(gate)
  return gates

def normalize_other(reported):
  gates = []
  sections = re.split('\: ', reported)
  for section in sections:
    for parts in re.split('\/|,\s+|', section):
      parts = re.sub('ý', '+', parts)
      parts = re.sub('hi', '+', parts)
      parts = re.sub('low', '-', parts)
      parts = re.sub('lo', '-', parts)
      parts = re.sub('dim', '-', parts)
      parts = re.sub(' ', '_', parts)
      gates += re.findall('CD\w+[\-\+]|CD\w+|\w+-\w+[\-\+]|\w+-\w+|\w+[\-\+]|\w+', parts)
    if section != sections[-1]:
      gates.append(':')
  return gates

def main():
  parser = argparse.ArgumentParser(
      description='Normalize cell population descriptions')
  parser.add_argument('input',
      type=argparse.FileType('r'),
      help='the input TSV file')
  parser.add_argument('output',
      type=str,
      help='the output TSV file')
  args = parser.parse_args()

  rows = csv.DictReader(args.input, delimiter='\t')
  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    w.writerow(list(next(rows).keys()) + ['POPULATION_DEFNITION_NORMALIZED'])
    for row in rows:
      reported = row['POPULATION_DEFNITION_REPORTED']
      gates = None
      if 'LaJolla' in row['NAME']:
        gates = normalize_lajolla(reported)
      elif 'Emory' in row['NAME']:
        gates = normalize_emory(reported)
      else:
        gates = normalize_other(reported)
      if gates:
        row['POPULATION_DEFNITION_NORMALIZED'] = ' '.join(gates)
        w.writerow(row.values())

if __name__ == "__main__":
  main()

def test_normalize_lajolla():
  assert normalize_lajolla('CD14-CD56-CD3+CD4+CD8-CD45RA+CCR7+') == [
      'CD14-', 'CD56-', 'CD3+', 'CD4+', 'CD8-', 'CD45RA+', 'CCR7+'
  ]

def test_normalize_emory():
  assert normalize_emory('CD3-, CD19+, CD20-, CD27hi, CD38hi') == [
    'CD3-', 'CD19+', 'CD20-', 'CD27+', 'CD38+'
  ]

def test_normalize_other():
  assert normalize_other('NK-NKT: intact viable/singlets/Lymph/CD3-/CD16+/CD56+/Q3: CD314+CD94-') == [
   'NK-NKT', ':', 'intact_viable', 'singlets', 'Lymph', 'CD3-', 'CD16+', 'CD56+', 'Q3', ':', 'CD314+', 'CD94-'
  ]
