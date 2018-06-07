#!/usr/bin/env python3

import argparse, csv, re


ignore = [':']

def report(gate_types, normalized):
  gates = re.split('\s+', normalized)
  ids = []
  for gate in gates:
    if gate in ignore:
      ids.append(gate)
    else:
      match = re.search('^(.*?)([\-\+]?)$', gate)
      name = match.group(1)
      level = match.group(2)
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
    w.writerow(list(next(rows).keys()) + ['POPULATION_DEFNITION_TYPES'])
    for row in rows:
      normalized = row['POPULATION_DEFNITION_NORMALIZED']
      ids = report(gate_types, normalized)
      row['POPULATION_DEFNITION_TYPES'] = ' '.join(ids)
      w.writerow(row.values())

if __name__ == "__main__":
  main()

def test_report():
  assert report({'foo': 'PR:0'}, 'foo+ : bar+ foo- bat foo') == [
      'PR:0+', ':', '[bar]+', 'PR:0-', '[bat]', 'PR:0'
  ]
