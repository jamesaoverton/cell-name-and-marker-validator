#!/usr/bin/env python3

import argparse, csv, re
from collections import defaultdict

def main():
  parser = argparse.ArgumentParser(
      description='Find matching gates')
  parser.add_argument('recognized',
      type=argparse.FileType('r'),
      help='a TSV file with ID and synonym for recognized gates')
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
    normalized = row['Gating mapped to ontologies']
    if normalized:
      gates = re.split(';\s+', normalized)
      for gate in gates:
        gate = gate.rstrip('-+~')
        all_gates[gate] += 1

  rows = csv.reader(args.recognized, delimiter='\t')
  with open(args.gates, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    w.writerow(['Ontology ID', 'Gate', 'Count'])
    for row in rows:
      (curie, gate) = row
      curie = curie.replace('http://purl.obolibrary.org/obo/PR_', 'PR:')
      if gate in all_gates:
        count = all_gates[gate]
        if gate in matched_gates:
          print('Already matched', gate, curie)
        matched_gates.add(gate)
        w.writerow([curie, gate, count])
    for gate in sorted(set(all_gates.keys()) - matched_gates):
      if gate:
        w.writerow([None, gate, all_gates[gate]])

if __name__ == "__main__":
  main()
