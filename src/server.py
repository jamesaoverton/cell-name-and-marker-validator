#!/usr/bin/env python3
#
# Use [Flask](http://flask.pocoo.org) to serve a validation page.

import copy
import csv
import re
import xml.etree.ElementTree as ET
from collections import OrderedDict
from flask import Flask, request, render_template
from os import path

from common import (iri_labels, iri_parents, iri_gates, synonym_iris, level_names, level_iris, iri_levels,
                    get_suffix_syns_symbs_maps, get_iri_special_label_maps, get_iri_label_maps,
                    get_iri_exact_label_maps, get_cell_iri_gates, split_gate)


pwd = path.dirname(path.realpath(__file__))
app = Flask(__name__)

# dict mapping suffix names to their symbolic suffix representation:
suffixsymbs = {}
# OrderedDict mapping suffix synonyms to their standardised suffix name:
suffixsyns = OrderedDict()



def populate_maps():
  """
  Read data from various files in the build directory and use it to populate the maps (dicts)
  that will be used by the server.
  """
  def update_main_maps(to_iris={}, from_iris={}):
    # This inner function updates the synonyms_iris map with the contents of to_iris, and the
    # iri_labels map with the contents of from_iris.
    iri_labels.update(from_iris)
    # to_iris maps labels to lists of iris, so flatten the lists here:
    for key in to_iris:
      #synonym_iris.update({'{}'.format(key): '{}'.format(','.join(to_iris[key]))})
      synonym_iris.update({'{}'.format(key): '{}'.format(to_iris[key][0])})

  # Read suffix symbols and suffix synonyms:
  with open(pwd + '/../build/value-scale.tsv') as f:
    rows = csv.DictReader(f, delimiter='\t')
    tmp_1, tmp_2 = get_suffix_syns_symbs_maps(rows)
    suffixsymbs.update(tmp_1)
    suffixsyns .update(tmp_2)

  # Read special gates and update the synonym_iris and iris_labels maps
  with open(pwd + '/../build/special-gates.tsv') as f:
    rows = csv.DictReader(f, delimiter='\t')
    to_iris, from_iris = get_iri_special_label_maps(rows)
    update_main_maps(to_iris, from_iris)

  # Read PR labels and update the synonym_iris and iris_labels maps
  with open(pwd + '/../build/pr-labels.tsv') as f:
    rows = csv.reader(f, delimiter='\t')
    to_iris, from_iris = get_iri_label_maps(rows)
    update_main_maps(to_iris, from_iris)

  # Read PR synonyms and update the synonym_iris and iris_labels maps
  with open(pwd + '/../build/pr-exact-synonyms.tsv') as f:
    rows = csv.reader(f, delimiter='\t')
    to_iris = get_iri_exact_label_maps(rows)
    update_main_maps(to_iris)

  tree = ET.parse(pwd + '/../build/cl-plus.owl')
  get_cell_iri_gates(tree)


def decorate_gate(kind, level):
  """
  Create and return a dictionary with information on the supplied gate type and level
  """
  gate = {
    'kind': kind,
    'kind_recognized': False,
    'level': level,
    'level_recognized': False,
  }

  if kind in iri_labels:
    gate['kind_recognized'] = True
    gate['kind_label'] = iri_labels[kind]
  if kind and not kind.startswith('http'):
    gate['kind'] = '?gate=' + kind

  if level in iri_labels:
    gate['level_recognized'] = True
    gate['level_label'] = iri_labels[level]

  return gate


def process_gate(gate_string):
  """
  In the given gate, replace any suffix synonym with the standard suffix, decorate the
  gate, and then add the gate string, kind, and level information.
  """
  # If the gate string has a suffix which is a synonym of one of the standard suffixes, then replace
  # it with the standard suffix:
  for suffix in suffixsyns.keys():
    if gate_string.casefold().endswith(suffix.casefold()):
      gate_string = re.sub('\s*' + re.escape(suffix) + '$', suffixsymbs[suffixsyns[suffix]],
                           gate_string, flags=re.IGNORECASE)

  # The 'kind' is the root of the gate string without the suffix, and the 'level' is the suffix
  kind_name, level_name = split_gate(gate_string, suffixsymbs.values())
  # Anything in square brackets should be thought of as a 'comment' and not part of the kind.
  kind_name = re.sub('\s*\[.*\]\s*', '', kind_name)
  kind = None
  if kind_name.casefold() in synonym_iris:
    kind = synonym_iris[kind_name.casefold()]
  level = None
  if level_name == '':
    level_name = '+'
  if level_name in level_iris:
    level = level_iris[level_name]
  gate = {}

  has_errors = False
  gate = decorate_gate(kind, level)
  if not kind:
    has_errors = True
  gate['gate'] = gate_string
  gate['kind_name'] = kind_name
  gate['level_name'] = level_names[level_name]

  return gate, has_errors


def get_cell_name_and_gates(cells_field):
  """
  Parse out the name and gate list from the given cells field
  """
  cell_gates = []
  if '&' in cells_field:
    cells_fields = cells_field.split('&', maxsplit=1)
    # Remove any enclosing quotation marks and collapse extra spaces inside the string:
    cell_name = re.sub("^(\"|\')|(\"|\')$", '', cells_fields[0].strip())
    cell_name = re.sub("\s\s+", " ", cell_name)
    cell_gating = cells_fields[1].strip()

    if cell_gating:
      # Gates are assumed to be separated by commas
      gate_strings = list(csv.reader([cell_gating], quotechar='"', delimiter=',',
                                     quoting=csv.QUOTE_ALL, skipinitialspace=True)).pop()
      for gate_string in gate_strings:
        gate, has_errors = process_gate(gate_string.strip("'"))
        cell_gates.append(gate)
  else:
    cell_name = cells_field.strip().strip('"\'')

  return cell_name, cell_gates


def get_cell_core_info(cell_gates, cell_iri):
  """
  Initialise a dictionary which will contain information about this cell
  """
  cell = {'recognized': False, 'conflicts': False, 'has_cell_gates': len(cell_gates) > 0,
          'cell_gates': cell_gates}
  if cell_iri in iri_gates:
    # If the cell IRI is in the IRI->Gates map, then add its IRI and flag it as recognised.
    cell['recognized'] = True
    cell['iri'] = cell_iri
    if cell_iri in iri_labels:
      # If the cell is in the IRI->Labels map, then add its label
      cell['label'] = iri_labels[cell_iri]
    if cell_iri in iri_parents:
      # It it is in the IRI->Parents map, then add its parent's IRI
      cell['parent'] = iri_parents[cell_iri]
      if cell['parent'] in iri_labels:
        # If its parent's IRI is in the IRI->Labels map, then add its parent's label
        cell['parent_label'] = iri_labels[cell['parent']]

  return cell


def get_gate_info_for_cell(cell_iri):
  """
  For each gate associated with the cell IRI, create a dictionary with information about it
  and append it to a list which is eventually returned.
  """
  cell_results = []

  if cell_iri:
    for gate in iri_gates[cell_iri]:
      gate = decorate_gate(gate['kind'], gate['level'])
      if gate['level'] in iri_levels:
        gate['level_name'] = level_names[iri_levels[gate['level']]]
      cell_results.append(gate)

  return cell_results


def get_cell_iri(cell_name):
  """
  Find the IRI for the cell based on cell_name, which can be a: label/synonym, ID, or IRI.
  """
  if cell_name.casefold() in synonym_iris:
    cell_iri = synonym_iris[cell_name.casefold()]
  elif cell_name in iri_labels:
    cell_iri = cell_name
  else:
    iri = re.sub('^CL:', 'http://purl.obolibrary.org/obo/CL_', cell_name)
    cell_iri = iri if iri in iri_labels else None

  return cell_iri


def parse_cells_field(cells_field):
  """
  Create and return a dictionary with information about the cell extracted from the given
  cells_field: its name, its associated gates, its IRI, and other core information about the cell.
  """
  cell = {}
  # Extract the cell name and the gates specified in the cells field of the request string
  cell_name, cell_gates = get_cell_name_and_gates(cells_field)
  # Get the cell and gate information for the gates specified in the cells field
  cell_iri = get_cell_iri(cell_name)
  cell['core_info'] = get_cell_core_info(cell_gates, cell_iri)
  # Include the information from cell_gates (the gates specified in the request) to cell_results
  # (the list of gates extracted based on the cell's IRI)
  cell['results'] = get_gate_info_for_cell(cell_iri) + cell_gates
  return cell


def parse_gates_field(gates_field, cell):
  """
  Parses the gates field submitted through the web form for a given cell.
  The gates field should be a list of gates separated by commas.
  Also check for and indicate any discrepancies between the gates information and the extracted
  cell info.
  """
  gating = {'results': [], 'conflicts': [], 'has_errors': False}
  # Assume gates are separated by commas
  gate_strings = list(csv.reader([gates_field], quotechar='"', delimiter=',', quoting=csv.QUOTE_ALL,
                                 skipinitialspace=True)).pop()
  for gate_string in gate_strings:
    gate, has_errors = process_gate(gate_string)
    if has_errors and not gating['has_errors']:
      gating['has_errors'] = True

    # Check for any discrepancies between what has been given through the request and the gate info
    # that has been extracted (cell_results) based on a lookup of the cell IRIs. Indicate any such
    # in the info for the gate, and append the gate info to a list of gates with conflicts. Either
    # way, append the gate into to the gate_results list.
    for cell_result in cell['results']:
      if gate['kind'] == cell_result['kind'] and gate['level'] != cell_result['level']:
        gate['conflict'] = True
        cell_result['conflict'] = True
        cell['core_info']['conflicts'] = True
        conflict = copy.deepcopy(gate)
        conflict['cell_level'] = cell_result['level']
        conflict['cell_level_name'] = cell_result['level_name']
        gating['conflicts'].append(conflict)
    gating['results'].append(gate)

  return gating


@app.route('/', methods=['GET'])
def my_app():
  if 'gate' in request.args:
    special_gate = request.args['gate'].strip()
    return render_template('/gate.html', special_gate=special_gate)

  # cells_field holds cell population names from the cell ontology database; if not specified, it's
  # initialised to the following default value. Otherwise we get it from the request
  cells_field = 'CD4-positive, alpha-beta T cell & CD19-'
  if 'cells' in request.args:
    cells_field = request.args['cells'].strip().replace("‘", "'").replace("’","'")

  # Parse the cells_field
  cell = parse_cells_field(cells_field)

  # gates_field holds gate names from the protein ontology database; if not specified, it gets
  # initialised to the following default value, otherwise get it from the request.
  gates_field = 'CD4-, CD19+, CD20-, CD27++, CD38+-, CD56[glycosylated]+'
  if 'gates' in request.args:
    gates_field = request.args['gates'].strip().replace("‘", "'").replace("’","'")

  # Parse the gates_field
  gating = parse_gates_field(gates_field, cell)

  # Serve the web page back with the generated info
  return render_template(
    '/index.html',
    cells=cells_field,
    gates=gates_field,
    cell=cell['core_info'],
    cell_results=cell['results'],
    gate_results=gating['results'],
    gate_errors=gating['has_errors'],
    conflicts=gating['conflicts'])


if __name__ == '__main__':
  """
  At startup, the main function reads information from files in the build directory and uses it to
  populate our global dictionaries. It then starts the Flask application.
  """
  populate_maps()
  app.debug = True
  app.run()


def test_server():
  populate_maps()
  cells_field = 'CD4-positive, alpha-beta T cell & CD19-'
  gates_field = 'CD4-, CD19+, CD20-, CD27++, CD38+-, infected[Dengue virus], CD56[glycosylated]+'
  cell = parse_cells_field(cells_field)
  gating = parse_gates_field(gates_field, cell)

  assert cell == {
    'core_info': {
      'cell_gates': [
        {'conflict': True,
         'gate': 'CD19-',
         'kind': 'http://purl.obolibrary.org/obo/PR_000001002',
         'kind_label': 'CD19 molecule',
         'kind_name': 'CD19',
         'kind_recognized': True,
         'level': 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part',
         'level_label': 'lacks plasma membrane part',
         'level_name': 'negative',
         'level_recognized': True}],
      'conflicts': True,
      'has_cell_gates': True,
      'iri': 'http://purl.obolibrary.org/obo/CL_0000624',
      'label': 'CD4-positive, alpha-beta T cell',
      'recognized': True},
    'results': [
      {'conflict': True,
       'kind': 'http://purl.obolibrary.org/obo/PR_000001004',
       'kind_label': 'CD4 molecule',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/RO_0002104',
       'level_label': 'has plasma membrane part',
       'level_name': 'positive',
       'level_recognized': True},
      {'kind': 'http://purl.obolibrary.org/obo/PR_000025402',
       'kind_label': 'T cell receptor co-receptor CD8',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part',
       'level_label': 'lacks plasma membrane part',
       'level_name': 'negative',
       'level_recognized': True},
      {'conflict': True,
       'gate': 'CD19-',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001002',
       'kind_label': 'CD19 molecule',
       'kind_name': 'CD19',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part',
       'level_label': 'lacks plasma membrane part',
       'level_name': 'negative',
       'level_recognized': True}]}

  assert gating == {
    'conflicts': [
      {'cell_level': 'http://purl.obolibrary.org/obo/RO_0002104',
       'cell_level_name': 'positive',
       'conflict': True,
       'gate': 'CD4-',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001004',
       'kind_label': 'CD4 molecule',
       'kind_name': 'CD4',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part',
       'level_label': 'lacks plasma membrane part',
       'level_name': 'negative',
       'level_recognized': True},
      {'cell_level': 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part',
       'cell_level_name': 'negative',
       'conflict': True,
       'gate': 'CD19+',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001002',
       'kind_label': 'CD19 molecule',
       'kind_name': 'CD19',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/RO_0002104',
       'level_label': 'has plasma membrane part',
       'level_name': 'positive',
       'level_recognized': True}],
    'has_errors': False,
    'results': [
      {'conflict': True,
       'gate': 'CD4-',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001004',
       'kind_label': 'CD4 molecule',
       'kind_name': 'CD4',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part',
       'level_label': 'lacks plasma membrane part',
       'level_name': 'negative',
       'level_recognized': True},
      {'conflict': True,
       'gate': 'CD19+',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001002',
       'kind_label': 'CD19 molecule',
       'kind_name': 'CD19',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/RO_0002104',
       'level_label': 'has plasma membrane part',
       'level_name': 'positive',
       'level_recognized': True},
      {'gate': 'CD20-',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001289',
       'kind_label': 'membrane-spanning 4-domains subfamily A member 1',
       'kind_name': 'CD20',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part',
       'level_label': 'lacks plasma membrane part',
       'level_name': 'negative',
       'level_recognized': True},
      {'gate': 'CD27++',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001963',
       'kind_label': 'CD27 molecule',
       'kind_name': 'CD27',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount',
       'level_label': 'has high plasma membrane amount',
       'level_name': 'high',
       'level_recognized': True},
      {'gate': 'CD38+-',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001408',
       'kind_label': 'ADP-ribosyl cyclase/cyclic ADP-ribose hydrolase 1',
       'kind_name': 'CD38',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount',
       'level_label': 'has low plasma membrane amount',
       'level_name': 'low',
       'level_recognized': True},
      {'gate': 'infected[Dengue virus]',
       'kind': '?gate=infected',
       'kind_label': 'infected',
       'kind_name': 'infected',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/RO_0002104',
       'level_label': 'has plasma membrane part',
       'level_name': 'positive',
       'level_recognized': True},
      {'gate': 'CD56[glycosylated]+',
       'kind': 'http://purl.obolibrary.org/obo/PR_000001024',
       'kind_label': 'neural cell adhesion molecule 1',
       'kind_name': 'CD56',
       'kind_recognized': True,
       'level': 'http://purl.obolibrary.org/obo/RO_0002104',
       'level_label': 'has plasma membrane part',
       'level_name': 'positive',
       'level_recognized': True}]}
