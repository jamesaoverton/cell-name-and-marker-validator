#!/usr/bin/env python3

import argparse
import csv
import getpass
import json
import os
import re
import requests
import sys
import time

from common import IriMaps, split_gate, tokenize


def get_study_ids(studiesinfo, technique):
  """
  Given a list of records containing study information, return those which are instances of the
  given experimental measurement technique.
  """
  study_ids = set()
  for row in studiesinfo:
    techniques = row['Experiment Measurement Techniques']
    if re.search(technique, techniques, flags=re.IGNORECASE):
      study_ids.add(row['Supporting Data'].strip())

  print("Found {} {} studies: {}".format(len(study_ids), technique, study_ids))
  return study_ids


def filter_study_ids(all_ids, requested_ids):
  """
  Given the list `all_ids` of available study ids, and the list `requested_ids`, return those in
  the latter that exist in the former.
  """
  print("Validation of {} requested ...".format(requested_ids))
  bad_ids = [sid for sid in requested_ids if sid not in all_ids]
  requested_ids = [sid for sid in requested_ids if sid not in bad_ids]
  if bad_ids:
    print("{} are not valid studies of this type; ignoring ...".format(bad_ids))
  print("Validating: {} ...".format(requested_ids))
  return requested_ids


def get_gate_mappings(mappings_file):
  """
  Given a mappings file, return a map which contains, for each row in the file, a mapping from its
  'Label' column to its 'Ontology ID' column.
  """
  rows = csv.DictReader(mappings_file, delimiter='\t')
  gate_mappings = {}
  for row in rows:
    gate_mappings[row['Label']] = row['Ontology ID']
  return gate_mappings


def get_special_gates(special_file):
  """
  Given special_file, return a map which contains, for each row in the file, a mapping from its
  'Label' column to a structure composed of its 'Ontology ID', 'Synonyms', and 'Toxic Synonym'
  columns.
  """
  rows = csv.DictReader(special_file, delimiter='\t')
  special_gates = {}
  for row in rows:
    special_gates[row['Label']] = {
      'Ontology ID': row['Ontology ID'],
      'Synonyms': row['Synonyms'],
      'Toxic Synonym': row['toxic synonym']}
  return special_gates


def get_preferred(preferred_file):
  """
  Given preferred_file, return a map which contains, for each row in the file, a mapping from its
  'Ontology ID' column to its 'Preferred Label' column.
  """
  rows = csv.DictReader(preferred_file, delimiter='\t')
  preferred = {}
  for row in rows:
    preferred[row['Ontology ID']] = row['Preferred Label']
  return preferred


def fetch_auth_token(username, password):
  """
  Retrieve an authentication token from ImmPort using the given username and password.
  """
  print("Retrieving authentication token from ImmPort ...")
  resp = requests.post('https://auth.immport.org/auth/token',
                       data={'username': username, 'password': password})
  if resp.status_code != requests.codes.ok:
    resp.raise_for_status()
  return resp.json()['token']


def fetch_immport_data(auth_token, sid, jsonpath):
  """
  Fetches the data for the given `sid` from ImmPort, caching it in the file at the location
  `jsonpath` for later reuse before returning the data to the caller.
  """
  print("Fetching JSON data for {} from ImmPort ...".format(sid))
  # Send the request:
  query = ("https://api.immport.org/data/query/result/fcsAnalyzed?studyAccession={}".format(sid))
  resp = requests.get(query, headers={"Authorization": "bearer " + auth_token})
  if resp.status_code != requests.codes.ok:
    resp.raise_for_status()

  # Save the JSON data from the response, and write it to a file at the location `jsonpath` that
  # can be reused later if this script is called again.
  data = resp.json()
  with open(jsonpath, 'w') as f:
    json.dump(data, f)
  return data


def preferize(gates, gate_mappings, special_gates, preferred, symbols):
  """
  'Preferize' a tokenised list of gates by replacing gate labels with preferred labels

  Parameters:
      gates: list of strings describing gates
      gate_mappings: dict containing mappings of gate labels to ontology ids
      special_gates: additional information regarding a certain number of special gates.
      symbols: list of suffix symbols
  """
  preferred_label_gates = []
  for gate in gates:
    label, suffixsymb = split_gate(gate, symbols)
    # Get any label / ontology id pairs corresponding to the synonym represented by `gate` from
    # the special_gates dictionary. Note that we match case-insensitively to the special_gates
    # dictionary
    special_entries = [
      {'label': key, 'ontid': val['Ontology ID']}
      for key, val in special_gates.items()
      if label and (
          label.casefold() == key.casefold() or
          label.casefold() in [v.casefold() for v in val['Synonyms'].split(', ')] or
          label.casefold() in [v.casefold() for v in val['Toxic Synonym'] .split(', ')])]

    # This shouldn't happen unless there are duplicate names in the special gates file:
    if special_entries and len(special_entries) > 1:
      print("Warning: {} ontology ids found with label: '{}'"
            .format(len(special_entries), gate))

    # Now try to find the ontology id in the gate_mappings map. If it isn't there, check to
    # see if it has a synonym in the map of special gates. If we don't find it there either, then
    # prefix the gate with a '!'.
    ontology_id = gate_mappings.get(label)
    if not ontology_id:
      # If this gate is a synonym of a special gate, then look up its ontology id there:
      ontology_id = special_entries[0]['ontid'] if special_entries else "!{}".format(label)

    # Look up the preferred label for a gate based on the ontology id. If we can't find it in the
    # preferred gates list, check to see if it is the synonym of a special gate and if so, use that
    # label. Otherwise prefix it with a '!'.
    preferred_label = (preferred.get(ontology_id, special_entries[0]['label']
                                     if special_entries else '!{}'.format(label)))
    preferred_label_gates.append(preferred_label + suffixsymb)

  return preferred_label_gates


def validate(reported, project, suffixsymbs, suffixsyns, gate_mappings, special_gates, preferred,
             symbols):
  # First, tokenize the reported string, and then replace the reported tokens with preferred
  # tokens:
  tokenized_gates = tokenize(project, suffixsymbs, suffixsyns, reported)
  preferized_gates = preferize(tokenized_gates, gate_mappings, special_gates, preferred, symbols)
  return ', '.join(preferized_gates)


def write_records(records, headers, outfile, project, suffixsymbs, suffixsyns,
                  gate_mappings, special_gates, preferred, symbols):
  """
  Writes the given records, for which their keys are given in `headers`, to the given outfile.
  In addition, validate the population name and definition for each record and write the validation
  comments to the row corresponding to the record in the file.
  """
  validated = {}

  for record in records:
    # First write all the headers for data not generated by us:
    for header in headers:
      print('"{}"'.format(record[header]), end='\t', file=outfile)

    # Now generate the validation fields for populationNameReported, populationNamePreferred,
    # populationDefnitionReported, and populationDefnitionPreferred. Note the misspelling of
    # 'Defnition'. This is the way it is defined in ImmPort.
    for prefix in ['populationName', 'populationDefnition']:
      key = (record[prefix + 'Reported'], record[prefix + 'Preferred'])
      # Only validate a given reported-preferred combination if it hasn't already been validated:
      if key not in validated:
        validated[key] = {
          'Reported': validate(record[prefix + 'Reported'] or '',
                               project, suffixsymbs, suffixsyns, gate_mappings,
                               special_gates, preferred, symbols),
          'Preferred': validate(record[prefix + 'Preferred'] or '',
                                project, suffixsymbs, suffixsyns, gate_mappings,
                                special_gates, preferred, symbols)}

      print('"{}"\t"{}"'.format(validated[key]['Reported'], validated[key]['Preferred']),
            end='\t', file=outfile)

      if validated[key]['Reported'] == validated[key]['Preferred']:
        print('"Y"', end='\t', file=outfile)
      else:
        print('"N"', end='\t', file=outfile)

    # Write a new line to end off the record:
    print(file=outfile)


def main():
  # Basic command-line arguments:
  parser = argparse.ArgumentParser(description='''
  Fetches data for Cytometry studies from ImmPort (using ImmPort's 'fcsAnalyzed' endpoint), and
  for each study, the population name and definition reported fields in the study are validated.
  The output of this script is a TSV file with information regarding the validity of these fields.
  In the report, the population name and definition reported in the study as well as the 'preferred'
  name and definition (i.e. the name and definition automatically generated by ImmPort when the
  study was submitted) are indcated. In addition to these columns, this script adds six extra
  columns: (a) the result of validating the reported population name, (b) the result of validating
  the preferred population name, (c) a comparison of the results of these two validations, (d) the
  result of validating the reported population definition, (b) the result of validating the
  preferred population definition, (c) a comparison of the results of these two validations.''')

  parser.add_argument('studiesinfo', type=argparse.FileType(mode='r', encoding='ISO-8859-1'),
                      help='A TSV file containing general information on various studies')
  parser.add_argument('scale', type=argparse.FileType('r'),
                      help='a TSV file with the value scale (e.g. high, low, negative)')
  parser.add_argument('mappings', type=argparse.FileType('r'),
                      help='a TSV file which maps gate labels to ontology ids/keywords')
  parser.add_argument('special', type=argparse.FileType('r'),
                      help='a TSV file containing extra information about a subset of gates')
  parser.add_argument('preferred', type=argparse.FileType('r'),
                      help='a TSV file which maps ontology ids to preferred labels')
  parser.add_argument('output_dir', type=str,
                      help='directory for output TSV files')
  parser.add_argument('cache_dir', type=str,
                      help='directory containing cached JSON files')
  # It is arguably silly to have a mutually exclusive group with only one member, but we do this
  # in case we want to add other validation tasks in the future:
  required = parser.add_argument_group('required arguments')
  required.add_argument('--fcsAnalyzed', metavar='SDYID', required=True, nargs='*',
                        help='List of Flow Cytometry studies to validate separated by whitespace '
                        '(e.g. SDY74 SDY113). If an empty list is passed to --fcsAnalyzed, all '
                        'Flow Cytometry studies will be validated')
  args = vars(parser.parse_args())

  # If the username and/or password haven't aren't set in environment variables, prompt for them:
  username = os.environ.get('IMMPORT_USERNAME')
  if not username:
    username = input("IMMPORT_USERNAME not set. Enter ImmPort username: ")
  password = os.environ.get('IMMPORT_PASSWORD')
  if not password:
    password = getpass.getpass('IMMPORT_PASSWORD not set. Enter ImmPort password: ')

  # Get the start time of the execution for later logging the total elapsed time:
  start = time.time()

  outpath = os.path.normpath(args['output_dir'] + '/fcsAnalyzed.tsv')

  # Read in the information from the file containing general info on studies.
  studiesinfo = list(csv.DictReader(args['studiesinfo'], delimiter='\t'))

  # Find all of the Flow Cytometry studies to validate:
  print("Validating Flow Cytometry studies")
  fcsAnalyzed = get_study_ids(studiesinfo, 'Flow Cytometry')
  # But validate only those that the user has requested (if none are specified, validate them all):
  if len(args['fcsAnalyzed']) > 0:
    fcsAnalyzed = filter_study_ids(fcsAnalyzed, args['fcsAnalyzed'])

  # Extract the suffix synonyms and symbols from the scale TSV file:
  rows = csv.DictReader(args['scale'], delimiter='\t')
  suffixsymbs, suffixsyns = IriMaps.extract_suffix_syns_symbs_maps(rows)
  symbols = suffixsymbs.values()

  # Load the contents of the file given by the command-line parameter args.mappings.
  # This file associates gate laels with the ontology ids
  gate_mappings = get_gate_mappings(args['mappings'])

  # Load the contents of the file given by the command-line parameter args.special.
  # This file (similary to the args.mapping file) associates certain gate labels with ontology ids
  # but also contains additional information regarding these gates.
  special_gates = get_special_gates(args['special'])

  # Load the contents of the file given by the command-line parameter args.preferred.
  # This file associates ontology ids with preferred gate labels (i.e. pr#PRO-short-label).
  preferred = get_preferred(args['preferred'])

  # Get the study data from the local filesystem if it is present, otherwise fetch it from ImmPort:
  data = {}
  auth_token = None
  for sid in fcsAnalyzed:
    cachedir = '{}/fcsAnalyzed/'.format(args['cache_dir'])
    os.makedirs(cachedir, exist_ok=True)
    jsonpath = os.path.normpath('{}/{}.json'.format(cachedir, sid))
    # Check to see if there is an existing file for this study id. If so, reuse it, otherwise
    # send an API call to ImmPort to retrieve the data:
    try:
      with open(jsonpath) as f:
        data[sid] = json.load(f)
        print("Retrieved JSON data for {} from cached file {}".format(sid, jsonpath))
    except FileNotFoundError:
      print("No cached data for {} found ({} does not exist)".format(sid, jsonpath))
      # Reuse the existing auth token if it has already been generated:
      if not auth_token:
        auth_token = fetch_auth_token(username, password)
      data[sid] = fetch_immport_data(auth_token, sid, jsonpath)

  if not any([data[sid] for sid in data]):
    print("No data found")
    sys.exit(1)

  # Write the header of the output TSV file by using the data returned plus extra fields
  # determined on its basis. Every sid in the data set should have the same fields, so we can just
  # use the first one (that has data) to get the header fields from. We can assume that there will
  # be at least one of these since we checked for this above.
  first_sid_with_data = [sid for sid in data if data[sid]].pop()
  headers = sorted([key for key in data[first_sid_with_data][0]])
  with open(outpath, 'w') as outfile:
    for header in headers:
      print('"{}"'.format(header), end='\t', file=outfile)
    print('"Validated populationNameReported"', end='\t', file=outfile)
    print('"Validated populationNamePreferred"', end='\t', file=outfile)
    print('"Population name validations match"', end='\t', file=outfile)
    print('"Validated populationDefinitionReported"', end='\t', file=outfile)
    print('"Validated populationDefinitionPreferred"', end='\t', file=outfile)
    print('"Population definition validations match"', file=outfile)

    # Now write the actual data:
    for sid in fcsAnalyzed:
      records = data.get(sid)
      if not records:
        print("No data found for " + sid)
        continue
      try:
        project = [s['Pis'] for s in studiesinfo if s['Supporting Data'].strip() == sid].pop()
      except IndexError:
        print("Could not find project corresponding to {}; skipping".format(sid))
        continue
      print("Processing {} records for fcsAnalyzed ID: {} ...".format(len(records), sid))
      write_records(records, headers, outfile, project, suffixsymbs, suffixsyns,
                    gate_mappings, special_gates, preferred, symbols)

  end = time.time()
  print("Processing completed. Total execution time: {0:.2f} seconds.".format(end - start))


if __name__ == "__main__":
  main()


# Unit tests:

def test_validate():
  suffixsymbs = {
    'high': '++',
    'medium': '+~',
    'low': '+-',
    'positive': '+',
    'negative': '-'
  }

  symbols = suffixsymbs.values()

  suffixsyns = {
    'high': 'high',
    'hi': 'high',
    'bright': 'high',
    'Bright': 'high',
    'bri': 'high',
    'br': 'high',
    '(high)': 'high',
    'medium': 'medium',
    'med': 'medium',
    'intermediate': 'medium',
    'int': 'medium',
    '(medium)': 'medium',
    'low': 'low',
    'lo': 'low',
    'LO': 'low',
    'dim': 'low',
    'di': 'low',
    '(low)': 'low',
    'positive': 'positive',
    'negative': 'negative'
  }

  gate_mappings = {
    'Alexa350': 'http://purl.obolibrary.org/obo/PR_001',
    'Alexa750': 'http://purl.obolibrary.org/obo/PR_002',
    'Annexin': 'http://purl.obolibrary.org/obo/PR_003',
    'B220-_live': 'http://purl.obolibrary.org/obo/PR_004',
    'CCR7': 'http://purl.obolibrary.org/obo/PR_005',
    'CD14': 'http://purl.obolibrary.org/obo/PR_006',
    'CD16': 'http://purl.obolibrary.org/obo/PR_007',
    'CD19': 'http://purl.obolibrary.org/obo/PR_008',
    'CD20': 'http://purl.obolibrary.org/obo/PR_009',
    'CD21': 'http://purl.obolibrary.org/obo/PR_010',
    'CD24': 'http://purl.obolibrary.org/obo/PR_011',
    'CD27': 'http://purl.obolibrary.org/obo/PR_012',
    'CD3': 'http://purl.obolibrary.org/obo/PR_013',
    'CD33': 'http://purl.obolibrary.org/obo/PR_014',
    'CD38': 'http://purl.obolibrary.org/obo/PR_015',
    'CD4': 'http://purl.obolibrary.org/obo/PR_016',
    'CD44': 'http://purl.obolibrary.org/obo/PR_017',
    'CD45RA': 'http://purl.obolibrary.org/obo/PR_018',
    'CD4_T_cells': 'http://purl.obolibrary.org/obo/PR_019',
    'CD56': 'http://purl.obolibrary.org/obo/PR_020',
    'CD69': 'http://purl.obolibrary.org/obo/PR_021',
    'CD8': 'http://purl.obolibrary.org/obo/PR_022',
    'CD94': 'http://purl.obolibrary.org/obo/PR_023',
    'CXCR5': 'http://purl.obolibrary.org/obo/PR_024',
    'doublet_excluded': 'http://purl.obolibrary.org/obo/PR_025',
    'ICOS': 'http://purl.obolibrary.org/obo/PR_026',
    'IFNg': 'http://purl.obolibrary.org/obo/PR_027',
    'IL2': 'http://purl.obolibrary.org/obo/PR_028',
    'live': 'http://purl.obolibrary.org/obo/PR_029',
    'Live_cells': 'http://purl.obolibrary.org/obo/PR_030',
    'Lymph': 'http://purl.obolibrary.org/obo/PR_031',
    'Lymphocytes': 'http://purl.obolibrary.org/obo/PR_032',
    'lymphocytes': 'http://purl.obolibrary.org/obo/PR_033',
    'Michael': 'http://purl.obolibrary.org/obo/PR_034',
    'NP_tet': 'http://purl.obolibrary.org/obo/PR_035',
    'PD1': 'http://purl.obolibrary.org/obo/PR_036',
    'Robert': 'http://purl.obolibrary.org/obo/PR_037',
    'singlets': 'http://purl.obolibrary.org/obo/PR_038',
    'small_lymphocyte': 'http://purl.obolibrary.org/obo/PR_039',
    'SSC': 'http://purl.obolibrary.org/obo/PR_040',
    'TNFa': 'http://purl.obolibrary.org/obo/PR_041',
    'Uninfected': 'http://purl.obolibrary.org/obo/PR_042',
    'viable': 'http://purl.obolibrary.org/obo/PR_043',
  }

  special_gates = {
    'Michael': {'Ontology ID': 'PR:034', 'Synonyms': 'mike, mickey, mick',
                'Toxic Synonym': 'mikey'},
    'Robert': {'Ontology ID': 'PR:037', 'Synonyms': 'rob, bob, bert',
               'Toxic Synonym': 'bobert'}
  }

  preferred = {
    'http://purl.obolibrary.org/obo/PR_001': 'Axexa350',
    'http://purl.obolibrary.org/obo/PR_002': 'Alexa750',
    'http://purl.obolibrary.org/obo/PR_003': 'Annexin',
    'http://purl.obolibrary.org/obo/PR_004': 'B220-_live',
    'http://purl.obolibrary.org/obo/PR_005': 'CCR7',
    'http://purl.obolibrary.org/obo/PR_006': 'CD14',
    'http://purl.obolibrary.org/obo/PR_007': 'CD16',
    'http://purl.obolibrary.org/obo/PR_008': 'CD19',
    'http://purl.obolibrary.org/obo/PR_009': 'CD20',
    'http://purl.obolibrary.org/obo/PR_010': 'CD21',
    'http://purl.obolibrary.org/obo/PR_011': 'CD24',
    'http://purl.obolibrary.org/obo/PR_012': 'CD27',
    'http://purl.obolibrary.org/obo/PR_013': 'CD3',
    'http://purl.obolibrary.org/obo/PR_014': 'CD33',
    'http://purl.obolibrary.org/obo/PR_015': 'CD38',
    'http://purl.obolibrary.org/obo/PR_016': 'CD4',
    'http://purl.obolibrary.org/obo/PR_017': 'CD44',
    'http://purl.obolibrary.org/obo/PR_018': 'CD45RA',
    'http://purl.obolibrary.org/obo/PR_019': 'CD4_T_cells',
    'http://purl.obolibrary.org/obo/PR_020': 'CD56',
    'http://purl.obolibrary.org/obo/PR_021': 'CD69',
    'http://purl.obolibrary.org/obo/PR_022': 'CD8',
    'http://purl.obolibrary.org/obo/PR_023': 'CD94',
    'http://purl.obolibrary.org/obo/PR_024': 'CXCR5',
    'http://purl.obolibrary.org/obo/PR_025': 'doublet_excluded',
    'http://purl.obolibrary.org/obo/PR_026': 'ICOS',
    'http://purl.obolibrary.org/obo/PR_027': 'IFNg',
    'http://purl.obolibrary.org/obo/PR_028': 'IL2',
    'http://purl.obolibrary.org/obo/PR_029': 'live',
    'http://purl.obolibrary.org/obo/PR_030': 'Live_cells',
    'http://purl.obolibrary.org/obo/PR_031': 'Lymph',
    'http://purl.obolibrary.org/obo/PR_032': 'Lymphocytes',
    'http://purl.obolibrary.org/obo/PR_033': 'lymphocytes',
    'http://purl.obolibrary.org/obo/PR_035': 'NP_tet',
    'http://purl.obolibrary.org/obo/PR_036': 'PD1',
    'http://purl.obolibrary.org/obo/PR_038': 'singlets',
    'http://purl.obolibrary.org/obo/PR_039': 'small_lymphocyte',
    'http://purl.obolibrary.org/obo/PR_040': 'SSC',
    'http://purl.obolibrary.org/obo/PR_041': 'TNFa',
    'http://purl.obolibrary.org/obo/PR_042': 'Uninfected',
  }

  reported = 'CD14-CD56-CD3+CD4+CD8-CD45RA+CCR7+'
  preferized = validate(reported, 'LaJolla', suffixsymbs, suffixsyns, gate_mappings, special_gates,
                        preferred, symbols)
  assert preferized == 'CD14-, CD56-, CD3+, CD4+, CD8-, CD45RA+, CCR7+'
