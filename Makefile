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
# - pytest <https://pytest.org> for running automated tests
# - Flask for web server
# - rapper <http://librdf.org/raptor/rapper.html>
# - Java Runtime Environment 8 or later
# - ROBOT <http://robot.obolibrary.org>


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

build/robot.jar:
	curl -L -o $@ "https://github.com/ontodev/robot/releases/download/v1.4.0/robot.jar"

# File containing general info on various HIPC studies:
build/HIPC_Studies.tsv:
	curl -k -L -o $@ "https://www.immport.org/documentation/data/hipc/HIPC_Studies.tsv"

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

build/cl-plus.owl: build/cl.owl src/add-membrane-parts-to-children.ru | build/robot.jar
	java -jar $| query --input $< --update $(word 2,$^) --output $@

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

# Normalize the cell population strings across studies, both population name and definition
build/normalized.tsv: src/normalize.py build/excluded-experiments.tsv build/value-scale.tsv build/gate-mappings.tsv build/special-gates.tsv build/pr-pro-short-labels.tsv build/cl-plus.owl source.tsv | build
	$^ $@

# Map gate labels to IDs and report results
build/report.tsv: src/report.py build/normalized.tsv build/pr-labels.tsv build/pr-pro-short-labels.tsv build/pr-exact-synonyms.tsv build/special-gates.tsv | build
	$^ $@

# Build a list of ontology IDs and labels that we can recognize
build/gate-mappings.tsv: build/special-gates.tsv build/pr-exact-synonyms.tsv | build
	cat $^ | cut -f 1-2 > $@

# Run batch validation
# Note that if the environment variables IMMPORT_USERNAME and IMMPORT_PASSWORD are not set, then the
# batch_validate script will prompt for them.
.PHONY: batch_validate
batch_validate: build/HIPC_Studies.tsv build/value-scale.tsv build/gate-mappings.tsv build/special-gates.tsv build/pr-pro-short-labels.tsv
	src/batch_validate.py --clobber --studiesinfo build/HIPC_Studies.tsv --scale build/value-scale.tsv \
	--mappings build/gate-mappings.tsv --special build/special-gates.tsv \
	--preferred build/pr-pro-short-labels.tsv --output_dir build/

### General Tasks

# Run all the important tasks
.PHONY: all
all: build/report.tsv | build

# Run all the tasks required to run the server
.PHONY: server
server: build/pr-labels.tsv build/cl-plus.owl build/value-scale.tsv build/special-gates.tsv build/pr-exact-synonyms.tsv | build

# Run automated tests (make sure pytest is for python version 3)
.PHONY: test
test:
	pytest src/*.py

# Check python code style
# || true is appended to force make to ignore the exit code from pycodestyle
pystyle:
	pycodestyle src/*.py | grep -v "indentation is not a multiple of four" || true

# Run the python delinter (make sure pyflakes is for python version 3)
pydelint:
	pyflakes src/*.py

# Remove spreadsheets, keep big PRO OWL file
.PHONY: clean
clean:
	rm -f build/*.tsv build/*.csv build/*.json build/taxdmp.zip build/*.dmp build/gc.prt build/readme.txt

# Remove build directory
.PHONY: clobber
clobber:
	rm -rf build
