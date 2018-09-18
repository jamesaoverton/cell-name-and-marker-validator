#!/usr/bin/env python3

import argparse
import csv
import re

from collections import defaultdict


def get_gates_from_normalized_row(normalized_row, all_gates):
  # Split up the given normalized_row into gates and add them all to all_gates
  if normalized_row:
    gates = re.split(';\s+', normalized_row)
    for gate in gates:
      gate = gate.rstrip('-+~')
      all_gates[gate] += 1


def find_recognized_gate(row, all_gates, matched_gates):
  # `row` consists of two fields: an ontology id and a gate name.
  # If the gate is found in all_gates, then return a list consisting of its
  # ontology id, the gate name, and the number of times it is in all_gates
  (curie, gate) = row
  curie = curie.replace('http://purl.obolibrary.org/obo/PR_', 'PR:')
  if gate in all_gates:
    count = all_gates[gate]
    if gate in matched_gates:
      print('Already matched', gate, curie)
    matched_gates.add(gate)
    return [curie, gate, count]


def get_unmatched_gates_rows(all_gates, matched_gates):
  # return a list of any gates in all_gates that are not in matched_gates
  # None signifies the ontology id, which is blank since it was not found.
  unmatched_gates_rows = []
  for gate in sorted(set(all_gates.keys()) - matched_gates):
    if gate:
      unmatched_gates_rows.append([None, gate, all_gates[gate]])
  return unmatched_gates_rows


def main():
  parser = argparse.ArgumentParser(description='Find matching gates')
  parser.add_argument('recognized', type=argparse.FileType('r'),
                      help='a TSV file with ID and synonym for recognized gates')
  parser.add_argument('normalized', type=argparse.FileType('r'),
                      help='a TSV file with normalized gates')
  parser.add_argument('gates', type=str, help='the output table of IDs and gates')
  args = parser.parse_args()

  all_gates = defaultdict(int)
  matched_gates = set()

  with open(args.gates, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    w.writerow(['Ontology ID', 'Gate', 'Count'])

    # First add all of the normalized gates to `all_gates`
    norm_rows = csv.DictReader(args.normalized, delimiter='\t')
    for norm_row in norm_rows:
      get_gates_from_normalized_row(norm_row['Gating mapped to ontologies'], all_gates)

    # Now read in all of the mappings of ontology ids to recognized gates.
    recgate_maps = csv.reader(args.recognized, delimiter='\t')

    for recgate_map in recgate_maps:
      # For each mapping, check if the mapped gate is in `all_gates`. If it is, then add it to
      # `matched_gates`, and write it to the output file.
      gate_row = find_recognized_gate(recgate_map, all_gates, matched_gates)
      if gate_row:
        w.writerow(gate_row)

    # Finally, if any gates in `all_gates` were not found in the gate mappings, write those
    # to the output file as well.
    for row in get_unmatched_gates_rows(all_gates, matched_gates):
      w.writerow(row)


if __name__ == "__main__":
  main()


def test_find_gates():
  all_gates = defaultdict(int)
  matched_gates = set()

  normalized = 'alternate_ontid+; PR:000001002+; PR:000001289+; !IgD-; PR:000001963+; PR:000001412+'

  get_gates_from_normalized_row(normalized, all_gates)
  assert all_gates == {'alternate_ontid': 1, 'PR:000001002': 1, 'PR:000001289': 1, '!IgD': 1,
                       'PR:000001963': 1, 'PR:000001412': 1}

  gate_row = find_recognized_gate(
    ['http://purl.obolibrary.org/obo/PR_000001002', 'alternate_ontid'],
    all_gates, matched_gates)
  assert gate_row == ['PR:000001002', 'alternate_ontid', 1]

  unmatched_gates = sorted(get_unmatched_gates_rows(all_gates, matched_gates))
  assert unmatched_gates == [[None, '!IgD', 1], [None, 'PR:000001002', 1],
                             [None, 'PR:000001289', 1], [None, 'PR:000001412', 1],
                             [None, 'PR:000001963', 1]]
