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

cache:
	mkdir $@

build/robot.jar: | build
	curl -L -o $@ "https://github.com/ontodev/robot/releases/download/v1.4.0/robot.jar"

UNAME := $(shell uname)
ifeq ($(UNAME), Darwin)
	RDFTAB_URL := https://github.com/ontodev/rdftab.rs/releases/download/v0.1.1/rdftab-x86_64-apple-darwin
	SED = sed -i.bak
else
	RDFTAB_URL := https://github.com/ontodev/rdftab.rs/releases/download/v0.1.1/rdftab-x86_64-unknown-linux-musl
	SED = sed -i
endif

build/rdftab: | build
	curl -L -o $@ $(RDFTAB_URL)
	chmod +x $@

### Project Configuration
#
# Most of the configuration is built into this Google Sheet:
# https://docs.google.com/spreadsheets/d/109FaxCDuwj9fxPqk1_haIrwo3_Y6EPU8lbNGYzmbRsU

# Download the HIPC FCS sheet
build/hipc_fcs.xlsx: | build
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/109FaxCDuwj9fxPqk1_haIrwo3_Y6EPU8lbNGYzmbRsU/export?format=xlsx&id=109FaxCDuwj9fxPqk1_haIrwo3_Y6EPU8lbNGYzmbRsU"

# Special markers for all valid markers
build/special_markers.tsv: build/hipc_fcs.xlsx
	xlsx2csv -d tab -s 5 $< $@


### Protein Synonyms
#
# We download the Protein Ontology and extract exact synonyms.

# Download pr.owl, about 1GB!
build/pr.owl: | build
	curl -k -L -o $@ "http://purl.obolibrary.org/obo/pr.owl"

# Insert pr.owl into sqlite database
build/pr.db: src/prefixes.sql build/pr.owl | build/rdftab
	rm -rf $@
	sqlite3 $@ < $<
	./build/rdftab $@ < $(word 2,$^)
	sqlite3 $@ "CREATE INDEX idx_stanza ON statements (stanza);"
	sqlite3 $@ "CREATE INDEX idx_subject ON statements (subject);"
	sqlite3 $@ "CREATE INDEX idx_predicate ON statements (predicate);"
	sqlite3 $@ "CREATE INDEX idx_object ON statements (object);"
	sqlite3 $@ "CREATE INDEX idx_value ON statements (value);"
	sqlite3 $@ "ANALYZE;"

# Extract a table of `rdfs:label`s for (proper) PR terms.
build/pr-labels.tsv: build/pr.db
	sqlite3 $< "SELECT DISTINCT subject, value FROM statements WHERE subject LIKE 'PR:%' AND predicate = 'rdfs:label' ORDER BY subject;" | sed 's/|/'$$'\t/g' > $@

# Extract a table of `oio:hasExactSynonym`s for (proper) PR terms.
build/pr-exact-synonyms.tsv: build/pr.db
	sqlite3 $< "SELECT DISTINCT subject, value FROM statements WHERE subject LIKE 'PR:%' AND predicate = 'oio:hasExactSynonym' ORDER BY subject;" | sed 's/|/'$$'\t/g' > $@

# Extract a table of pr#PRO-short-label labels for (proper) PR terms.
build/pr-pro-short-labels.tsv: src/find-pro-short-labels.sql build/pr.db
	cat $< | sqlite3 $(word 2,$^) | sed 's/|/'$$'\t/g' > $@

# Create a table of all valid markers from special markers & PR terms
build/marker.tsv: build/special_markers.tsv build/pr-labels.tsv build/pr-exact-synonyms.tsv build/pr-pro-short-labels.tsv
	cat $^ | grep "\S" > $@


### Cell Ontology
#
# We use the Cell Ontology for its logical definitions.

# Download cl.owl, about 6MB, no imports.
build/cl.owl: | build
	curl -k -L -o $@ "http://purl.obolibrary.org/obo/cl.owl"

# Inherit membrane parts
build/cl-plus.owl: build/cl.owl src/add-membrane-parts-to-children.ru | build/robot.jar
	java -jar $| query --input $< --update $(word 2,$^) --output $@

# Insert pr.owl into sqlite database
build/cl.db: src/prefixes.sql build/cl-plus.owl | build/rdftab
	rm -rf $@
	sqlite3 $@ < $<
	./build/rdftab $@ < $(word 2,$^)
	sqlite3 $@ "CREATE INDEX idx_stanza ON statements (stanza);"
	sqlite3 $@ "CREATE INDEX idx_subject ON statements (subject);"
	sqlite3 $@ "CREATE INDEX idx_predicate ON statements (predicate);"
	sqlite3 $@ "CREATE INDEX idx_object ON statements (object);"
	sqlite3 $@ "CREATE INDEX idx_value ON statements (value);"
	sqlite3 $@ "ANALYZE;"

# Extract a table of `rdfs:label`s for (proper) CL terms.
build/cl-labels.tsv: build/cl.db
	sqlite3 $< "SELECT DISTINCT subject, value FROM statements WHERE subject LIKE 'CL:0%' AND predicate = 'rdfs:label' ORDER BY subject;" | sed 's/|/'$$'\t/g' > $@

# Extract a table of `oio:hasExactSynonym`s for (proper) CL terms.
build/cl-exact-synonyms.tsv: build/cl.db
	sqlite3 $< "SELECT DISTINCT subject, value FROM statements WHERE subject LIKE 'CL:0%' AND predicate = 'oio:hasExactSynonym' ORDER BY subject;" | sed 's/|/'$$'\t/g' > $@

# Create a table of all valid cell names
build/cell.tsv: build/cl-labels.tsv build/cl-exact-synonyms.tsv
	echo -e "ID\tName" > $@
	cat $^ >> $@

# Create a table of membrane parts
build/cl-levels.tsv: build/cl.db
	python3 -m gizmos.export -d $< \
	-w "subject LIKE 'CL:%'" \
	-p CURIE \
	-p obo:RO_0002104 \
	-p obo:cl#lacks_plasma_membrane_part \
	-p obo:cl#has_high_plasma_membrane_amount \
	-p obo:cl#has_low_plasma_membrane_amount \
	-V CURIE > $@

### General Tasks

# Check python code style
# || true is appended to force make to ignore the exit code from pycodestyle
pystyle:
	pycodestyle --max-line-length=100 --ignore E129,E126,E121,E111,E114,W504 src/*.py | grep -v "indentation is not a multiple of four" || true

# Run the python delinter (make sure pyflakes is for python version 3)
pydelint:
	pyflakes src/*.py

test: build/valid-out.tsv build/invalid-out.tsv

build/empty.tsv: | build
	touch $@

build/valid-out.tsv: src/validate.py build/cell.tsv build/cl-levels.tsv build/marker.tsv examples/valid.tsv | build build/empty.tsv
	python3 $^ > $@
	diff build/valid-out.tsv build/empty.tsv

build/invalid-out.tsv: src/validate.py build/cell.tsv build/cl-levels.tsv build/marker.tsv examples/invalid.tsv | build
	python3 $^ > $@
	[ -s $@ ]

# Remove spreadsheets, keep big PRO OWL file
.PHONY: clean
clean:
	rm -f build/*.db build/*.tsv

# Remove build and cache directories
.PHONY: clobber
clobber:
	rm -rf build cache

.PHONY: all
all: build/cell.tsv build/marker.tsv build/cl-levels.tsv
