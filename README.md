# Cell Name and Marker Validation Demo

[![Build Status](https://travis-ci.com/jamesaoverton/cell-name-and-marker-validator.svg?branch=master)](https://travis-ci.com/jamesaoverton/cell-name-and-marker-validator)

This project demonstrates how data about cell populations and gating strategies can be transformed into semantically rich linked data and validated, using ontologies such as the [Protein Ontology](https://pir.georgetown.edu/pro/) and [Cell Ontology](http://obofoundry.org/ontology/cl.html). This validator is designed to implement the [Cytometry Data Standard](https://docs.google.com/document/d/1vGg3R745uuSH7bcKjukf_Mm5CIt5kgImU79wZbD-8zE).

There are two ways to use this code:

1. as a web application that validates a cell population name and gate definition against our proposed standard (under development), and compares them using information from the Protein Ontology and Cell Ontology
2. as a script that processes an existing table of cell population names and gate definitions, used as a reference for developing the proposed standard

## Usage

See the [`Makefile`](Makefile) for software requirements and build tasks.

### Web Service

The [`src/server.py`](src/server.py) script will run a simple web service allowing users to submit their cell type and gating strategy and get a validation result immediately. It uses the Python [Flask](http://flask.pocoo.org) module. The `make server` task will prepare the various tables and ontologies required for the server, then run `python3 src/server.py` and navigate to `http://localhost:5000`.

### Batch Processing

Supply a `source.tsv` file with columns: NAME, STUDY_ACCESSION, EXPERIMENT_ACCESSION, POPULATION_NAME_REPORTED, POPULATION_DEFNITION_REPORTED [sic]. Then run `make all` and look at `build/normalized.tsv`, `build/report2.tsv`, and `build/summary.tsv`.
