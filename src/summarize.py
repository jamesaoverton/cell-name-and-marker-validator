#!/usr/bin/env python3

import argparse, csv, re
from collections import defaultdict

def main():
  parser = argparse.ArgumentParser(
      description='Parse HIPC cell')
  parser.add_argument('report',
      type=argparse.FileType('r'),
      help='the reported TSV file')
  parser.add_argument('output',
      type=str,
      help='the output TSV file')
  args = parser.parse_args()

  columns = ['NAME', 'MATCHED_GATES', 'TOTAL_GATES', 'MATCHED_GATE_PERCENTAGE', 'MATCHED_POPULATIONS', 'TOTAL_POPULATIONS', 'MATCHED_POPULATION_PERCENTAGE']
  centers = defaultdict(lambda: defaultdict(int))
  rows = csv.DictReader(args.report, delimiter='\t')
  for row in rows:
    center = row['NAME']
    gates = re.split('\s+', row['POPULATION_DEFNITION_TYPES'])
    perfect = True
    for gate in gates:
      centers[center]['TOTAL_GATES'] += 1
      centers['TOTAL']['TOTAL_GATES'] += 1
      if gate.startswith('['):
        perfect = False
      else:
        centers[center]['MATCHED_GATES'] += 1
        centers['TOTAL']['MATCHED_GATES'] += 1
    centers[center]['TOTAL_POPULATIONS'] += 1
    centers['TOTAL']['TOTAL_POPULATIONS'] += 1
    if perfect:
      centers[center]['MATCHED_POPULATIONS'] += 1
      centers['TOTAL']['MATCHED_POPULATIONS'] += 1

  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    w.writerow(columns)
    center_names = sorted(centers.keys())
    center_names.remove('TOTAL')
    center_names.append('TOTAL')
    for center in center_names:
      centers[center]['MATCHED_GATE_PERCENTAGE'] = int(
        centers[center]['MATCHED_GATES'] / centers[center]['TOTAL_GATES'] * 100
      )
      centers[center]['MATCHED_POPULATION_PERCENTAGE'] = int(
        centers[center]['MATCHED_POPULATIONS'] / centers[center]['TOTAL_POPULATIONS'] * 100
      )
      w.writerow([center] + [centers[center][c] for c in columns[1:]])

if __name__ == "__main__":
  main()
