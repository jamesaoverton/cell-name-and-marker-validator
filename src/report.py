#!/usr/bin/env python3

import argparse
import csv
import re


def generate_report_row(row):
  """
  For a given row from the normalized tsv file, extract the normalized column, and count the
  number of gates in the column that are not prefixed with '!'. Gates so prefixed do not correspond
  to any known ontology ids.
  """
  normalized = row['Gating mapped to ontologies']
  if not normalized:
    return None

  ids = re.split(';\s+', normalized)
  matched_gates = 0
  total_gates = 0
  for i in ids:
    total_gates += 1
    if not i.startswith('!'):
      matched_gates += 1
  row['MATCHED_GATES'] = matched_gates
  row['TOTAL_GATES'] = total_gates
  return row


def main():
  parser = argparse.ArgumentParser(description='Parse HIPC cell')
  parser.add_argument('normalized', type=argparse.FileType('r'), help='the normalized TSV file')
  parser.add_argument('gates', type=argparse.FileType('r'), help='the gates TSV file')
  parser.add_argument('output', type=str, help='the output TSV file')
  args = parser.parse_args()

  rows = csv.DictReader(args.normalized, delimiter='\t')
  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    output_fieldnames = rows.fieldnames + ['MATCHED_GATES', 'TOTAL_GATES']
    w.writerow(output_fieldnames)
    for row in rows:
      report_row = generate_report_row(row)
      if report_row:
        w.writerow([row[fn] for fn in output_fieldnames])


if __name__ == "__main__":
  main()


def test_report():
  from copy import copy

  inrow = {
    'EXPERIMENT_ACCESSION': 'EXP14857',
    'Gating mapped to ontologies': 'PR:000001889-; PR:000001892-; !CD3+; PR:000001004+',
    'Gating preferred labels': 'CD14-; CD33-; !CD3+; CD4+',
    'Gating tokenized': 'CD14-; CD33-; CD3+; CD4+',
    'NAME': 'HIPC Stanford Project',
    'POPULATION_DEFNITION_REPORTED': 'CD14-CD33-/CD3+/CD4+',
    'POPULATION_NAME_REPORTED': 'CD4+ T cells',
    'STUDY_ACCESSION': 'SDY887'}
  expected_outrow = copy(inrow)
  expected_outrow.update({'MATCHED_GATES': 3, 'TOTAL_GATES': 4})
  actual_outrow = generate_report_row(inrow)
  assert len(actual_outrow) == len(expected_outrow)
  for k, v in expected_outrow.items():
    assert actual_outrow[k] == v
