#!/usr/bin/env python3

import argparse, csv, re

def report(gate_types, normalized):
  gates = re.split('\s+', normalized)
  ids = []
  for gate in gates:
    name = gate.rstrip('+-~')
    level = re.search('[\-\+\~]*$', gate).group(0)
    if name in gate_types:
      ids.append(gate_types[name] + level)
    else:
      ids.append('[' + name + ']' + level)
  return ids

def main():
  parser = argparse.ArgumentParser(
      description='Parse HIPC cell')
  parser.add_argument('normalized',
      type=argparse.FileType('r'),
      help='the normalized TSV file')
  parser.add_argument('gates',
      type=argparse.FileType('r'),
      help='the gates TSV file')
  parser.add_argument('output',
      type=str,
      help='the output TSV file')
  args = parser.parse_args()

  gate_types = {}
  rows = csv.reader(args.gates, delimiter='\t')
  for row in rows:
    if row[1] and row[0] and row[0] != '':
      gate_types[row[1]] = row[0]

  rows = csv.DictReader(args.normalized, delimiter='\t')
  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    w.writerow(list(next(rows).keys()) + ['POPULATION_DEFNITION_TYPES', 'MATCHED_GATES', 'TOTAL_GATES'])
    for row in rows:
      normalized = row['POPULATION_DEFNITION_NORMALIZED']
      ids = report(gate_types, normalized)
      matched_gates = 0
      total_gates = 0
      for i in ids:
        total_gates += 1
        if not i.startswith('['):
          matched_gates += 1
      row['POPULATION_DEFNITION_TYPES'] = ' '.join(ids)
      row['MATCHED_GATES'] = matched_gates
      row['TOTAL_GATES'] = total_gates
      w.writerow(row.values())

if __name__ == "__main__":
  main()

def test_report():
  assert report({'foo': 'PR:0'}, 'foo+ : bar+ foo- bat foo') == [
      'PR:0+', '[:]', '[bar]+', 'PR:0-', '[bat]', 'PR:0'
  ]
