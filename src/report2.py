#!/usr/bin/env python3

import argparse, csv, re
from collections import defaultdict

def main():
  parser = argparse.ArgumentParser(
      description='Parse HIPC cell')
  parser.add_argument('normalized',
      type=argparse.FileType('r'),
      help='the normalized TSV file')
  parser.add_argument('labels',
      type=argparse.FileType('r'),
      help='the RDFS label TSV file')
  parser.add_argument('shorts',
      type=argparse.FileType('r'),
      help='the PRO short label TSV file')
  parser.add_argument('exacts',
      type=argparse.FileType('r'),
      help='the exact synonyms TSV file')
  parser.add_argument('specials',
      type=argparse.FileType('r'),
      help='the special gates TSV file')
  parser.add_argument('output',
      type=str,
      help='the output TSV file')
  args = parser.parse_args()

  markers = defaultdict(int)
  rows = csv.DictReader(args.normalized, delimiter='\t')
  for row in rows:
    tokenized = row['Gating tokenized']
    if tokenized:
      gates = re.split(';\s+', tokenized)
      for gate in gates:
        marker = gate.rstrip('+-~')
        markers[marker] += 1

  ilabel_iris = defaultdict(list)
  iri_labels = {}
  rows = csv.reader(args.labels, delimiter='\t')
  for row in rows:
    (iri, label) = row
    ilabel_iris[label.lower()].append(iri)
    iri_labels[iri] = label

  short_iris = defaultdict(list)
  ishort_iris = defaultdict(list)
  iri_shorts = {}
  rows = csv.reader(args.shorts, delimiter='\t')
  for row in rows:
    (iri, short) = row
    short_iris[short].append(iri)
    ishort_iris[short.lower()].append(iri)
    iri_shorts[iri] = short

  iexact_iris = defaultdict(list)
  rows = csv.reader(args.exacts, delimiter='\t')
  for row in rows:
    (iri, exact) = row
    if not exact.lower() in ishort_iris:
      iexact_iris[exact.lower()].append(iri)

  ispecial_iris = defaultdict(list)
  iri_specials = {}
  rows = csv.DictReader(args.specials, delimiter='\t')
  for row in rows:
    iri = row['Ontology ID']
    label = row['Label']
    synonyms = re.split(',\s+', row['Synonyms'])
    iri_specials[iri] = label
    ispecial_iris[label.lower()].append(iri)
    for synonym in synonyms:
      ispecial_iris[synonym.lower()].append(iri)

  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    w.writerow(['Marker name', 'Marker count', 'Multiple matches', 'Match type', 'IRI', 'PRO short label', 'Label'])
    marker_list = sorted(markers.keys(), key=lambda s: s.casefold())
    for marker in marker_list:
      matches = []
      multiple = None
      match_type = None
      iri = None
      short = None
      label = None

      if marker.lower() in ilabel_iris:
        match_type = 'label'
        matches = ilabel_iris[marker.lower()]

      if marker.lower() in ishort_iris:
        match_type = 'PRO short label'
        matches = ishort_iris[marker.lower()]

      if marker.lower() in iexact_iris:
        match_type = 'exact synonym'
        matches = iexact_iris[marker.lower()]

      if marker.lower() in ispecial_iris:
        match_type = 'special'
        matches = ispecial_iris[marker.lower()]

      if len(matches) > 1:
        multiple = 'TRUE'
        iri = ' '.join(matches)
      elif len(matches) == 1:
        iri = matches[0]
        if iri in iri_shorts:
          short = iri_shorts[iri]
        if iri in iri_labels:
          label = iri_labels[iri]
        elif iri in iri_specials:
          label = iri_specials[iri]

      w.writerow([marker, markers[marker], multiple, match_type, iri, short, label])

if __name__ == "__main__":
  main()

