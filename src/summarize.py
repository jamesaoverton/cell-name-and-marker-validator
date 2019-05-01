#!/usr/bin/env python3

import argparse
import csv
import re

from collections import defaultdict


def get_centers_info(report_rows):
  """
  Fill in the data for the various centers based on the given row from the report
  Get the center name described by the current row
  """
  centers = defaultdict(lambda: defaultdict(int))
  for row in report_rows:
    this_center_name = row['NAME']
    gates = re.split(';\s+', row['Gating mapped to ontologies'])
    # `perfect` indicates that all of the gates correspond to known ontology ids. Those that
    # aren't are prefixed with a '!'. Set it to true to begin with.
    perfect = True
    for gate in gates:
      # Augment the total number of gates for this center and also for centers in general.
      centers[this_center_name]['TOTAL_GATES'] += 1
      centers['TOTAL']['TOTAL_GATES'] += 1
      if gate.startswith('!'):
        perfect = False
      else:
        # If the gate corresponds to a known ontology id, augment the total number of matched gates
        # for this center and also for centers in general:
        centers[this_center_name]['MATCHED_GATES'] += 1
        centers['TOTAL']['MATCHED_GATES'] += 1
    # Augment the total number of populations found for this center and also for centers in general:
    centers[this_center_name]['TOTAL_POPULATIONS'] += 1
    centers['TOTAL']['TOTAL_POPULATIONS'] += 1
    if perfect:
      # If all of the gates correspond to known ontology ids, then we can say that the population as
      # a whole that is given in the row is a match, and we can augment the counters accordingly:
      centers[this_center_name]['MATCHED_POPULATIONS'] += 1
      centers['TOTAL']['MATCHED_POPULATIONS'] += 1
  return centers


def generate_centers_rows(centers, columns):
  """
  Generate a row to write to the summary report by extracting information from the given centers
  data corresponding to the given columns.
  """
  rows_to_return = []
  center_names = sorted(centers.keys())
  # Move the 'TOTAL' element of the list to the end by first removing and then appending it:
  center_names.remove('TOTAL')
  center_names.append('TOTAL')

  for center_name in center_names:
    # Generate some statistics for each center
    centers[center_name]['MATCHED_GATE_PERCENTAGE'] = int(
      centers[center_name]['MATCHED_GATES'] / centers[center_name]['TOTAL_GATES'] * 100
    )
    centers[center_name]['MATCHED_POPULATION_PERCENTAGE'] = int(
      centers[center_name]['MATCHED_POPULATIONS'] / centers[center_name]['TOTAL_POPULATIONS'] * 100
    )
    # Append the row to the list of generated rows
    rows_to_return.append([center_name] + [centers[center_name][c] for c in columns[1:]])
  # Finally return
  return rows_to_return


def main():
  parser = argparse.ArgumentParser(description='Parse HIPC cell')
  parser.add_argument('report', type=argparse.FileType('r'), help='the reported TSV file')
  parser.add_argument('output', type=str, help='the output TSV file')
  args = parser.parse_args()

  report_rows = csv.DictReader(args.report, delimiter='\t')
  centers = get_centers_info(report_rows)

  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    columns = ['NAME', 'MATCHED_GATES', 'TOTAL_GATES', 'MATCHED_GATE_PERCENTAGE',
               'MATCHED_POPULATIONS', 'TOTAL_POPULATIONS', 'MATCHED_POPULATION_PERCENTAGE']
    w.writerow(columns)
    for row in generate_centers_rows(centers, columns):
      w.writerow(row)


if __name__ == "__main__":
  main()


def test_summarize():
  centers = defaultdict(lambda: defaultdict(int))

  report_rows = [{
    'NAME': 'Center for Human Immunology, Autoimmunity and  Inflammation',
    'STUDY_ACCESSION': 'SDY80',
    'EXPERIMENT_ACCESSION': 'EXP14117',
    'POPULATION_NAME_REPORTED': 'ID98, CD86+ of IgD-CD27+ memory B cells',
    'POPULATION_DEFNITION_REPORTED': 'CD45+CD19+CD20+IgD-CD27+CD86+',
    'Gating tokenized': 'CD45+; CD19+; CD20+; IgD-; CD27+; CD86+',
    'Gating preferred definition': 'PTPRC+; CD19+; MS4A1+; !IgD-; CD27+; CD86+',
    'Gating mapped to ontologies': ('PR:000001006+; PR:000001002+; PR:000001289+; !IgD-; '
                                    'PR:000001963+; PR:000001412+'),
    'MATCHED_GATES': '5',
    'TOTAL_GATES': '6',
  }]

  centers = get_centers_info(report_rows)

  assert centers == {
    'Center for Human Immunology, Autoimmunity and  Inflammation': {
      'MATCHED_GATES': 5, 'TOTAL_GATES': 6, 'TOTAL_POPULATIONS': 1},
    'TOTAL': {'MATCHED_GATES': 5, 'TOTAL_GATES': 6, 'TOTAL_POPULATIONS': 1}}

  columns = ['NAME', 'MATCHED_GATES', 'TOTAL_GATES', 'MATCHED_GATE_PERCENTAGE',
             'MATCHED_POPULATIONS', 'TOTAL_POPULATIONS', 'MATCHED_POPULATION_PERCENTAGE']
  rows = generate_centers_rows(centers, columns)

  assert rows == [
    ['Center for Human Immunology, Autoimmunity and  Inflammation', 5, 6, 83, 0, 1, 0],
    ['TOTAL', 5, 6, 83, 0, 1, 0]
  ]
