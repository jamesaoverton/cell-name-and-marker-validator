#!/usr/bin/env python3

import argparse, csv, re
from collections import defaultdict

ignore = [':']

def main():
  parser = argparse.ArgumentParser(
      description='Find matching gates')
  parser.add_argument('synonyms',
      type=argparse.FileType('r'),
      help='a TSV file with ID and synonym')
  parser.add_argument('normalized',
      type=argparse.FileType('r'),
      help='a TSV file with normalized gates')
  parser.add_argument('gates',
      type=str,
      help='the output table of IDs and gates')
  args = parser.parse_args()

  all_gates = defaultdict(int)
  matched_gates = set()

  rows = csv.DictReader(args.normalized, delimiter='\t')
  for row in rows:
    normalized = row['POPULATION_DEFNITION_NORMALIZED']
    gates = re.split('\s+', normalized)
    for gate in gates:
      if gate not in ignore:
        gate = gate.rstrip('-+')
        all_gates[gate] += 1

  rows = csv.reader(args.synonyms, delimiter='\t')
  with open(args.gates, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    w.writerow(['ID', 'gate', 'count'])
    for row in rows:
      if row[1] in all_gates:
        if row[1] in matched_gates:
          print('Already matched', row[1], row[0])
        matched_gates.add(row[1])
        w.writerow([row[0], row[1], all_gates[row[1]]])
    for gate in sorted(set(all_gates.keys()) - matched_gates):
      if gate:
        w.writerow([None, gate, all_gates[gate]])

if __name__ == "__main__":
  main()
