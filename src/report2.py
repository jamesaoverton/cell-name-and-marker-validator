#!/usr/bin/env python3

import argparse
import csv
import re

from collections import defaultdict


def get_markers(normalized_rows):
  # A dictionary of markers mapped to the number of times they are found as tokens
  # in the list of normalized rows
  markers = defaultdict(int)

  for row in normalized_rows:
    # Extract the tokens, strip their suffixes, and add them to the markers dict.
    tokenized = row['Gating tokenized']
    if tokenized:
      gates = re.split(';\s+', tokenized)
      for gate in gates:
        marker = gate.rstrip('+-~')
        markers[marker] += 1

  return markers


def get_iri_label_maps(label_rows):
  # This maps labels to lists of IRIs:
  ilabel_iris = defaultdict(list)
  # This maps IRIs to labels
  iri_labels = {}

  for row in label_rows:
    (iri, label) = row
    # Add the IRI to the list of IRIs associated with the label in the ilabel_iris dictionary
    ilabel_iris[label.lower()].append(iri)
    # Map the IRI to the label in the iri_labels dictionary
    iri_labels[iri] = label

  return ilabel_iris, iri_labels


def get_iri_short_label_maps(short_rows):
  # This maps short labels to lists of IRIs:
  ishort_iris = defaultdict(list)
  # This maps IRIs to shorts
  iri_shorts = {}

  for row in short_rows:
    (iri, short) = row
    ishort_iris[short.lower()].append(iri)
    iri_shorts[iri] = short

  return ishort_iris, iri_shorts


def get_iri_exact_label_maps(exact_rows, ishort_iris):
  # This maps exact labels to lists IRIs
  iexact_iris = defaultdict(list)

  for row in exact_rows:
    (iri, exact) = row
    # Only add the exact label to the map if it isn't already in the short labels dict:
    if not exact.lower() in ishort_iris:
      iexact_iris[exact.lower()].append(iri)

  return iexact_iris


def get_iri_special_label_maps(special_rows):
  # This maps special labels to lists of IRIs
  ispecial_iris = defaultdict(list)
  # This maps IRIs to special labels:
  iri_specials = {}

  for row in special_rows:
    iri = row['Ontology ID']
    label = row['Label']
    synonyms = re.split(',\s+', row['Synonyms'])
    iri_specials[iri] = label
    ispecial_iris[label.lower()].append(iri)
    # Also map any synonyms for the label to the IRI
    for synonym in synonyms:
      ispecial_iris[synonym.lower()].append(iri)

  return ispecial_iris, iri_specials


def generate_report_rows(markers, ilabel_iris, iri_labels, ishort_iris, iri_shorts,
                         iexact_iris, ispecial_iris, iri_specials):
  marker_list = sorted(markers.keys(), key=lambda s: s.casefold())
  rows_to_return = []

  for marker in marker_list:
    matches = []
    multiple = None
    match_type = None
    iri = None
    short = None
    label = None

    # Get the list of IRIs for the marker, depending on what kind of label this is. Note that a
    # given marker could be in multiple of these dictionaries, so the order of the if/elifs below
    # is important.
    if marker.lower() in ispecial_iris:
      match_type = 'special'
      matches = ispecial_iris[marker.lower()]
    elif marker.lower() in ishort_iris:
      match_type = 'PRO short label'
      matches = ishort_iris[marker.lower()]
    elif marker in ilabel_iris:
      match_type = 'label'
      matches = ilabel_iris[marker.lower()]
    elif marker.lower() in iexact_iris:
      match_type = 'exact synonym'
      matches = iexact_iris[marker.lower()]

    # If there is more than one match, then just write the list of IRIs, otherwise
    # write the IRI plus any info about its other labels (short, special, etc.) that you have.
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

    rows_to_return.append([marker, markers[marker], multiple, match_type, iri, short, label])

  return rows_to_return


def main():
  parser = argparse.ArgumentParser(description='Parse HIPC cell')
  parser.add_argument('normalized', type=argparse.FileType('r'), help='the normalized TSV file')
  parser.add_argument('labels', type=argparse.FileType('r'), help='the RDFS label TSV file')
  parser.add_argument('shorts', type=argparse.FileType('r'), help='the PRO short label TSV file')
  parser.add_argument('exacts', type=argparse.FileType('r'), help='the exact synonyms TSV file')
  parser.add_argument('specials', type=argparse.FileType('r'), help='the special gates TSV file')
  parser.add_argument('output', type=str, help='the output TSV file')
  args = parser.parse_args()

  normalized_rows = csv.DictReader(args.normalized, delimiter='\t')
  markers = get_markers(normalized_rows)

  # Read the labels file and get the maps from IRIs to labels and vice versa
  label_rows = csv.reader(args.labels, delimiter='\t')
  ilabel_iris, iri_labels = get_iri_label_maps(label_rows)

  # Read the shorts file and get the maps from IRIs to short labels and vice versa
  short_rows = csv.reader(args.shorts, delimiter='\t')
  ishort_iris, iri_shorts = get_iri_short_label_maps(short_rows)

  # Read the exact labels file and get the maps from IRIs to exact labels and vice versa
  exact_rows = csv.reader(args.exacts, delimiter='\t')
  iexact_iris = get_iri_exact_label_maps(exact_rows, ishort_iris)

  # Read the special labels file and get the maps from IRIs to special labels and vice versa
  special_rows = csv.DictReader(args.specials, delimiter='\t')
  ispecial_iris, iri_specials = get_iri_special_label_maps(special_rows)

  with open(args.output, 'w') as output:
    w = csv.writer(output, delimiter='\t', lineterminator='\n')
    # Write the column headings:
    w.writerow(['Marker name', 'Marker count', 'Multiple matches', 'Match type', 'IRI',
                'PRO short label', 'Label'])

    for row in generate_report_rows(markers, ilabel_iris, iri_labels, ishort_iris, iri_shorts,
                                    iexact_iris, ispecial_iris, iri_specials):
      w.writerow(row)


if __name__ == "__main__":
  main()


def test_report2():
  pass
