#!/usr/bin/env python3

import argparse
import csv
import re

from collections import defaultdict # maybe eventually remove this import
from common import get_iri_special_label_maps, get_iri_label_maps, get_iri_exact_label_maps


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
    elif marker.lower() in ilabel_iris:
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

  # Pull all the markers (tokenized gates stripped of their suffixes) from the normalized file
  normalized_rows = csv.DictReader(args.normalized, delimiter='\t')
  markers = get_markers(normalized_rows)

  # Read the labels file to construct maps from IRIs to labels and vice versa
  label_rows = csv.reader(args.labels, delimiter='\t')
  ilabel_iris, iri_labels = get_iri_label_maps(label_rows)

  # Read the shorts file to construct maps from IRIs to short labels and vice versa
  short_rows = csv.reader(args.shorts, delimiter='\t')
  ishort_iris, iri_shorts = get_iri_short_label_maps(short_rows)

  # Read the exact labels file to construct maps from IRIs to exact labels and vice versa
  exact_rows = csv.reader(args.exacts, delimiter='\t')
  iexact_iris = get_iri_exact_label_maps(exact_rows, ishort_iris)

  # Read the special labels file to construct maps from IRIs to special labels and vice versa
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
  normalized_rows = [
    {'EXPERIMENT_ACCESSION': 'EXP13892',
     'Gating tokenized': ('Intact_cells; intact_singlets; viable_singlets; CD14-; CD33-; CD3+; '
                          'CD4+; CD8-; Non-naive_CD4+; CXCR5+'),
     'NAME': 'HIPC Stanford Project',
     'Gating preferred labels': ('!Intact_cells; intact_singlets; !viable_singlets; CD14-; CD33-; '
                                 '!CD3+; CD4+; !CD8-; !Non-naive_CD4+; CXCR5+'),
     'POPULATION_DEFNITION_REPORTED': ('Intact cells/intact singlets/viable singlets/CD14-CD33-'
                                       '/CD3+/CD4+CD8-/Non-naive CD4+/CXCR5+'),
     'Gating mapped to ontologies': ('!Intact_cells; intact_singlets; !viable_singlets; '
                                     'PR:000001889-; PR:000001892-; !CD3+; PR:000001004+; !CD8-; '
                                     '!Non-naive_CD4+; PR:000001209+'),
     'POPULATION_NAME_REPORTED': 'TFH CD4+ T cells',
     'STUDY_ACCESSION': 'SDY478'}
  ]

  markers = get_markers(normalized_rows)
  assert markers == {'Intact_cells': 1, 'Non-naive_CD4': 1, 'CD33': 1, 'intact_singlets': 1,
                     'CD4': 1, 'CD14': 1, 'CXCR5': 1, 'CD3': 1, 'CD8': 1, 'viable_singlets': 1}

  label_rows = [
    ['http://purl.obolibrary.org/obo/PR_000001892', 'CD33 molecule'],
    ['http://purl.obolibrary.org/obo/PR_000046634', 'myeloid CD33, signal (human)'],
    ['http://purl.obolibrary.org/obo/PR_000003070', 'CD4 molecule isoform 1 unmodified form'],
    ['http://purl.obolibrary.org/obo/PR_000003071', 'CD4 molecule isoform 1 phosphorylated form'],
    ['http://purl.obolibrary.org/obo/PR_000003072', 'CD4 molecule isoform 1 phosphorylated 1'],
    ['http://purl.obolibrary.org/obo/PR_000018303', 'obsolete CD4 molecule, full-length form'],
    ['http://purl.obolibrary.org/obo/PR_000018304', 'CD4 molecule, signal peptide removed form'],
  ]

  ilabel_iris, iri_labels = get_iri_label_maps(label_rows)

  assert ilabel_iris == {
    'cd33 molecule': ['http://purl.obolibrary.org/obo/PR_000001892'],
    'myeloid cd33, signal (human)': ['http://purl.obolibrary.org/obo/PR_000046634'],
    'cd4 molecule isoform 1 unmodified form': ['http://purl.obolibrary.org/obo/PR_000003070'],
    'cd4 molecule isoform 1 phosphorylated form': ['http://purl.obolibrary.org/obo/PR_000003071'],
    'cd4 molecule isoform 1 phosphorylated 1': ['http://purl.obolibrary.org/obo/PR_000003072'],
    'obsolete cd4 molecule, full-length form': ['http://purl.obolibrary.org/obo/PR_000018303'],
    'cd4 molecule, signal peptide removed form': ['http://purl.obolibrary.org/obo/PR_000018304'],
  }

  assert iri_labels == {
    'http://purl.obolibrary.org/obo/PR_000001892': 'CD33 molecule',
    'http://purl.obolibrary.org/obo/PR_000046634': 'myeloid CD33, signal (human)',
    'http://purl.obolibrary.org/obo/PR_000003070': 'CD4 molecule isoform 1 unmodified form',
    'http://purl.obolibrary.org/obo/PR_000003071': 'CD4 molecule isoform 1 phosphorylated form',
    'http://purl.obolibrary.org/obo/PR_000003072': 'CD4 molecule isoform 1 phosphorylated 1',
    'http://purl.obolibrary.org/obo/PR_000018303': 'obsolete CD4 molecule, full-length form',
    'http://purl.obolibrary.org/obo/PR_000018304': 'CD4 molecule, signal peptide removed form',
  }

  short_rows = [
    ['http://purl.obolibrary.org/obo/PR_000001892', 'CD33'],
    ['http://purl.obolibrary.org/obo/PR_000001893', 'CD33'],
    ['http://purl.obolibrary.org/obo/PR_000001004', 'CD4'],
  ]

  ishort_iris, iri_shorts = get_iri_short_label_maps(short_rows)

  assert ishort_iris == {
    'cd4': ['http://purl.obolibrary.org/obo/PR_000001004'],
    'cd33': ['http://purl.obolibrary.org/obo/PR_000001892',
             'http://purl.obolibrary.org/obo/PR_000001893']
  }

  assert iri_shorts == {
    'http://purl.obolibrary.org/obo/PR_000001004': 'CD4',
    'http://purl.obolibrary.org/obo/PR_000001892': 'CD33',
    'http://purl.obolibrary.org/obo/PR_000001893': 'CD33',
  }

  exact_rows = [
    ['http://purl.obolibrary.org/obo/PR_000001892', 'CD33'],
    ['http://purl.obolibrary.org/obo/PR_000001892', 'myeloid cell surface antigen CD33'],
    ['http://purl.obolibrary.org/obo/PR_000001927', 'CD33 antigen-like 2'],
    ['http://purl.obolibrary.org/obo/PR_000001928', 'CD33 antigen-like 1'],
    ['http://purl.obolibrary.org/obo/PR_000014868', 'CD33 antigen-like 3'],
  ]

  iexact_iris = get_iri_exact_label_maps(exact_rows, ishort_iris)

  assert iexact_iris == {
    'myeloid cell surface antigen cd33': ['http://purl.obolibrary.org/obo/PR_000001892'],
    'cd33 antigen-like 2': ['http://purl.obolibrary.org/obo/PR_000001927'],
    'cd33 antigen-like 1': ['http://purl.obolibrary.org/obo/PR_000001928'],
    'cd33 antigen-like 3': ['http://purl.obolibrary.org/obo/PR_000014868'],
  }

  special_rows = [
    {'Label': 'intact_cells', 'Valid': 'TRUE', 'Type': 'cell type, scatter', 'toxic synonym': '',
     'comment': '', 'Synonyms': 'intact_cells_population', 'Ontology ID': 'intact_cells'},
    {'Label': 'intact_singlets', 'Valid': 'TRUE', 'Type': 'cell type, scatter', 'toxic synonym': '',
     'comment': '', 'Synonyms': '', 'Ontology ID': 'intact_singlets'},
    {'Label': 'singlets', 'Valid': 'TRUE', 'Type': 'cell type, scatter', 'toxic synonym': 'WBC/2-',
     'comment': '', 'Synonyms': 'sing, singlet, doublet_excluded, sing-F',
     'Ontology ID': 'singlets'},
  ]

  ispecial_iris, iri_specials = get_iri_special_label_maps(special_rows)

  assert ispecial_iris == {'': ['intact_singlets'],
                           'intact_cells': ['intact_cells'],
                           'intact_cells_population': ['intact_cells'],
                           'singlets': ['singlets'],
                           'sing-f': ['singlets'],
                           'intact_singlets': ['intact_singlets'],
                           'doublet_excluded': ['singlets'],
                           'singlet': ['singlets'],
                           'sing': ['singlets']}

  assert iri_specials == {'singlets': 'singlets',
                          'intact_cells': 'intact_cells',
                          'intact_singlets': 'intact_singlets'}

  rows = generate_report_rows(markers, ilabel_iris, iri_labels, ishort_iris, iri_shorts,
                              iexact_iris, ispecial_iris, iri_specials)

  assert rows == [
    ['CD14', 1, None, None, None, None, None],
    ['CD3', 1, None, None, None, None, None],
    ['CD33', 1, 'TRUE', 'PRO short label',
     'http://purl.obolibrary.org/obo/PR_000001892 http://purl.obolibrary.org/obo/PR_000001893',
     None, None],
    ['CD4', 1, None, 'PRO short label', 'http://purl.obolibrary.org/obo/PR_000001004',
     'CD4', None],
    ['CD8', 1, None, None, None, None, None],
    ['CXCR5', 1, None, None, None, None, None],
    ['Intact_cells', 1, None, 'special', 'intact_cells', None, 'intact_cells'],
    ['intact_singlets', 1, None, 'special', 'intact_singlets', None, 'intact_singlets'],
    ['Non-naive_CD4', 1, None, None, None, None, None],
    ['viable_singlets', 1, None, None, None, None, None]
  ]
