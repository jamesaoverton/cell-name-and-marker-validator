# Cell Name and Marker Validator Demo
# James A. Overton <james@overton.ca>
#
# This Makefile is used to check the `source.tsv` spreadsheet
# against a configuration file
# to produce a normalized/ontologized output.
#
# WARN: This file contains significant whitespace, i.e. tabs!
# Ensure that your text editor shows you those characters.
#
# Requirements:
#
# - GNU Make <https://www.gnu.org/software/make/>
# - standard Unix tools: cURL, grep, sed, cut
# - Python 3
#   - pytest-3 (https://pytest.org> for running automated tests
# - rapper <http://librdf.org/raptor/rapper.html>


### GNU Make Configuration
#
# These are standard options to make Make sane:
# <http://clarkgrubb.com/makefile-style-guide#toc2>

MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:
.SECONDARY:


### Set Up

build:
	mkdir $@


### Project Configuration
#
# Most of the configuration is built into this Google Sheet:
# https://docs.google.com/spreadsheets/d/1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI/edit#gid=0

# Download the 'Special Gates for OBI' sheet as TSV
build/special-gates.tsv: | build
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI/export?format=tsv&id=1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI&gid=1143376972"

# Download the 'Value Scale' sheet as TSV
build/value-scale.tsv: | build
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI/export?format=tsv&id=1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI&gid=225886927"

# Download the 'Excluded Experiments' sheet as TSV
build/excluded-experiments.tsv: | build
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI/export?format=tsv&id=1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI&gid=1418733338"


### Protein Synonyms
#
# We download the Protein Ontology and extract exact synonyms.

# Download pr.owl, about 1GB!
build/pr.owl: | build
	curl -k -L -o $@ "http://purl.obolibrary.org/obo/pr.owl"

# Use rapper to generate a file consisting of N-triples from pr.owl
build/pr.nt: build/pr.owl | build
	rapper $< > $@

# Extract a table of `rdfs:label`s for (proper) PR terms.
build/pr-labels.tsv: build/pr.nt | build
	grep '^<http://purl.obolibrary.org/obo/PR_0' $< \
	| grep '> <http://www.w3.org/2000/01/rdf-schema#label> "' \
	| sed 's/^<\(.*\)> <.*> "\(.*\)".*$$/\1	\2/' \
	> $@

# Extract a table of `oio:hasExactSynonym`s for (proper) PR terms.
build/pr-exact-synonyms.tsv: build/pr.nt | build
	grep '^<http://purl.obolibrary.org/obo/PR_0' $< \
	| grep '> <http://www.geneontology.org/formats/oboInOwl#hasExactSynonym> "' \
	| sed 's/^<\(.*\)> <.*> "\(.*\)".*$$/\1	\2/' \
	> $@

# Extract a table of pr#PRO-short-label labels for (proper) PR terms.
build/pr-pro-short-labels.tsv: src/find-pro-short-labels.py build/pr.nt | build
	$^ > $@


### Cell Ontology
#
# We use the Cell Ontology for its logical definitions.

# Download cl.owl, about 6MB, no imports.
build/cl.owl: | build
	curl -k -L -o $@ "http://purl.obolibrary.org/obo/cl.owl"

# Convert CL to N-triples.
build/cl.nt: build/cl.owl | build
	rapper $< > $@

# Extract a table of `rdfs:label`s for CL terms.
build/cl-labels.tsv: build/cl.nt | build
	grep '^<http://purl.obolibrary.org/obo/CL_0' $< \
	| grep '> <http://www.w3.org/2000/01/rdf-schema#label> "' \
	| sed 's/^<\(.*\)> <.*> "\(.*\)".*$$/\1	\2/' \
	> $@

# Extract a table of `oio:hasExactSynonym`s for CL terms.
build/cl-exact-synonyms.tsv: build/cl.nt | build
	grep '^<http://purl.obolibrary.org/obo/CL_0' $< \
	| grep '> <http://www.geneontology.org/formats/oboInOwl#hasExactSynonym> "' \
	| sed 's/^<\(.*\)> <.*> "\(.*\)".*$$/\1	\2/' \
	> $@


### Processing
#
# Various Python scripts are used to process the `source.tsv` file.
# See the script files for more documentation.

# Normalize the cell population strings across studies
build/normalized.tsv: src/normalize.py build/excluded-experiments.tsv build/value-scale.tsv build/gate-mappings.tsv build/special-gates.tsv build/pr-pro-short-labels.tsv source2.tsv | build
	$^ $@

# Normalize the cell population strings across studies, both population name and definition
build/normalized2.tsv: src/normalize2.py build/excluded-experiments.tsv build/value-scale.tsv build/gate-mappings.tsv build/special-gates.tsv build/pr-pro-short-labels.tsv build/cl.owl source2.tsv | build
	$^ $@

# Map gate labels to IDs and report results
build/report.tsv: src/report.py build/normalized.tsv build/gates.tsv | build
	$^ $@

# Map gate labels to IDs and report results
build/report2.tsv: src/report2.py build/normalized.tsv build/pr-labels.tsv build/pr-pro-short-labels.tsv build/pr-exact-synonyms.tsv build/special-gates.tsv | build
	$^ $@

# Build a list of ontology IDs and labels that we can recognize
build/gate-mappings.tsv: build/special-gates.tsv build/pr-exact-synonyms.tsv | build
	cat $^ | cut -f 1-2 > $@

# Build a table summarizing mapping success by centre
build/summary.tsv: src/summarize.py build/report.tsv | build
	$^ $@


### General Tasks

# Run all the important tasks
.PHONY: all
all: build/summary.tsv | build

# Run all the tasks required to run the server
.PHONY: server
server: build/pr-labels.tsv build/cl.owl build/value-scale.tsv build/special-gates.tsv build/pr-exact-synonyms.tsv | build

# Run automated tests
test: build/value-scale.tsv build/special-gates.tsv build/pr-labels.tsv build/pr-exact-synonyms.tsv build/cl.owl
	pytest src/*

# Check code style
# || true is appended to force make to ignore the exit code from pycodestyle
style:
	pycodestyle src/* | grep -v "indentation is not a multiple of four" || true

# Run the delinter
lint:
	pyflakes src/

# Remove spreadsheets, keep big PRO OWL file
.PHONY: clean
clean:
	rm -f build/*.tsv

# Remove build directory
.PHONY: clobber
clobber:
	rm -rf build
