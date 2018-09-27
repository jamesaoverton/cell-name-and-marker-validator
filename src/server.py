#!/usr/bin/env python3
#
# Use [Flask](http://flask.pocoo.org) to serve a validation page.

import copy
import csv
import re
import xml.etree.ElementTree as ET
from collections import OrderedDict
from flask import Flask, request, render_template, redirect, url_for
from os import path

from common import extract_suffix_syns_symbs, extract_iri_special_label_maps


pwd = path.dirname(path.realpath(__file__))

app = Flask(__name__)

synonym_iris = {}

iri_labels = {
  'http://purl.obolibrary.org/obo/RO_0002104': 'has plasma membrane part',
  'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part': 'lacks plasma membrane part',
  'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount': 'has high plasma membrane amount',
  'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount': 'has low plasma membrane amount'
}
 
iri_parents = {}

iri_gates = {}

level_names = {
  '++': 'high',
  '+~': 'medium',
  '+-': 'low',
  '+': 'positive',
  '-': 'negative'
}

level_iris = {
  '++': 'http://purl.obolibrary.org/obo/cl#has_high_plasma_membrane_amount',
  '+~': 'http://purl.obolibrary.org/obo/RO_0002104',
  '+-': 'http://purl.obolibrary.org/obo/cl#has_low_plasma_membrane_amount',
  '+': 'http://purl.obolibrary.org/obo/RO_0002104',
  '-': 'http://purl.obolibrary.org/obo/cl#lacks_plasma_membrane_part'
}

iri_levels = {v: k for k, v in level_iris.items()}

def decorate_gate(kind, level):
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
  for suffix in suffixsyns.keys():
    if gate_string.endswith(suffix):
      gate_string = re.sub('\s*' + re.escape(suffix) + '$', suffixsymbs[suffixsyns[suffix]], gate_string)
      continue

  kind_name = gate_string.rstrip('+-~')
  kind_name = re.sub('\[.*\]', '', kind_name)
  level_name = re.search('[\-\+\~]*$', gate_string).group(0)
  kind = None
  if kind_name in synonym_iris:
    kind = synonym_iris[kind_name]
  level = None
  if level_name == '':
    level_name = '+'
  if level_name in level_iris:
    level = level_iris[level_name]
  gate = {}

  gate = decorate_gate(kind, level)
  if not kind:
    gate_errors = True
  gate['gate'] = gate_string
  gate['kind_name'] = kind_name
  gate['level_name'] = level_names[level_name]

  return gate


@app.route('/', methods=['GET'])
def my_app():
  if 'gate' in request.args:
    special_gate = request.args['gate'].strip()
    return render_template('/gate.html', special_gate=special_gate)

  cells_field = 'CD4-positive, alpha-beta T cell & CD19-'
  if 'cells' in request.args:
    cells_field = request.args['cells'].strip()
  cell_gates = []
  if '&' in cells_field:
    cells_fields = cells_field.split('&', maxsplit=1)
    cell_name = cells_fields[0].strip()
    cell_gating = cells_fields[1].strip()
    gate_strings = re.split(r';\s*', cell_gating)
    for gate_string in gate_strings:
      gate = process_gate(gate_string)
      cell_gates.append(gate)
  else:
    cell_name = cells_field

  gates_field = 'CD4-; CD19+; CD20-; CD27++; CD38+-; infected[Dengue virus]; CD56[glycosylated]+'
  if 'gates' in request.args:
    gates_field = request.args['gates'].strip()

  cell_results = []
  gate_results = []
  conflicts = []

  # Submit a: label, synonym, ID, or IRI
  cell_iri = None
  if cell_name in synonym_iris:
    cell_iri = synonym_iris[cell_name]
  elif cell_name in iri_labels:
    cell_iri = cell_name
  else:
    iri = re.sub('^CL:', 'http://purl.obolibrary.org/obo/CL_', cell_name)
    if iri in iri_labels:
      cell_iri = iri

  cell = {
    'recognized': False,
    'conflicts': False,
    'has_cell_gates': len(cell_gates) > 0,
    'cell_gates': cell_gates
  }
  if cell_iri in iri_gates:
    cell['recognized'] = True
    cell['iri'] = cell_iri
    if cell_iri in iri_labels:
      cell['label'] = iri_labels[cell_iri]
    if cell_iri in iri_parents:
      cell['parent'] = iri_parents[cell_iri]
      if cell['parent'] in iri_labels:
        cell['parent_label'] = iri_labels[cell['parent']]
    for gate in iri_gates[cell_iri]:
      gate = decorate_gate(gate['kind'], gate['level'])
      if gate['level'] in iri_levels:
        gate['level_name'] = level_names[iri_levels[gate['level']]]
      cell_results.append(gate)
    cell_results = cell_results + cell_gates

  gate_strings = re.split(r';\s*', gates_field)
  gate_errors = False
  for gate_string in gate_strings:
    gate = process_gate(gate_string)

    for cell_result in cell_results:
      if gate['kind'] == cell_result['kind'] and gate['level'] != cell_result['level']:
        gate['conflict'] = True
        cell_result['conflict'] = True
        cell['conflicts'] = True
        conflict = copy.deepcopy(gate)
        conflict['cell_level'] = cell_result['level']
        conflict['cell_level_name'] = cell_result['level_name']
        conflicts.append(conflict)
    gate_results.append(gate)

  return render_template('/index.html',
      cells=cells_field,
      gates=gates_field,
      cell=cell,
      cell_results=cell_results,
      gate_results=gate_results,
      gate_errors=gate_errors,
      conflicts=conflicts)


if __name__ == '__main__':
  # Read suffix symbols and suffix synonyms:
  with open(pwd + '/../build/value-scale.tsv') as f:
    rows = csv.DictReader(f, delimiter='\t')
    suffixsymbs, suffixsyns = extract_suffix_syns_symbs(rows)

  # Read special gates:
  with open(pwd + '/../build/special-gates.tsv') as f:
    rows = csv.DictReader(f, delimiter='\t')
    ispecial_iris, iri_specials = extract_iri_special_label_maps(rows)
    iri_labels.update(iri_specials)
    # ispecial_iris maps special labels to lists of iris, so flatten the lists here:
    for key in ispecial_iris:
      synonym_iris.update({'{}'.format(key): '{}'.format(','.join(ispecial_iris[key]))})

  # Read PR labels
  with open(pwd + '/../build/pr-labels.tsv') as f:
    rows = csv.reader(f, delimiter='\t')
    for row in rows:
      iri = row[0]
      label = row[1]
      if iri and label:
        iri_labels[iri] = label
        synonym_iris[label] = iri

  # Read PR synonyms
  with open(pwd + '/../build/pr-exact-synonyms.tsv') as f:
    rows = csv.reader(f, delimiter='\t')
    for row in rows:
      iri = row[0]
      synonym = row[1]
      if iri and synonym:
        synonym_iris[synonym] = iri

  # Read CL
  ns = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'obo': 'http://purl.obolibrary.org/obo/',
    'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#'
  }
  tree = ET.parse(pwd + '/../build/cl.owl')
  root = tree.getroot()
  obo = 'http://purl.obolibrary.org/obo/'
  rdf_about = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about'
  rdf_resource = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'
  rdf_description = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description'
  rdfs_label = '{http://www.w3.org/2000/01/rdf-schema#}label'
  owl_restriction = '{http://www.w3.org/2002/07/owl#}Restriction'

  for child in root.findall('owl:Class', ns):
    iri = None
    if rdf_about in child.attrib:
      iri = child.attrib[rdf_about]
    if iri and iri.startswith(obo + 'CL_'): # and iri == obo + 'CL_0000624':
      label = child.findtext(rdfs_label)
      if label:
        iri_labels[iri] = label
        synonym_iris[label] = iri

      for synonym in child.findall('oboInOwl:hasExactSynonym', ns):
        synonym_iris[synonym.text] = iri

      iri_gates[iri] = []
      for part in child.findall('owl:equivalentClass/owl:Class/owl:intersectionOf/*', ns):
        if part.tag == rdf_description:
          parent = part.get(rdf_about)
          if parent:
            iri_parents[iri] = parent
        elif part.tag == owl_restriction:
          relation = part.find('owl:onProperty', ns)
          if relation is not None:
            relation = relation.get(rdf_resource)
          value = part.find('owl:someValuesFrom', ns)
          if value is not None:
            value = value.get(rdf_resource)
          if value and relation in iri_levels:
            gate = {
              'kind': value,
              'level': relation
            }
            iri_gates[iri].append(gate)

  label_iris = {v: k for k, v in iri_labels.items()}

  app.debug = True
  app.run()

