# HIPC Gates Validation Demo

This project demonstrates how [Human Immunology Project Consortium](https://www.immuneprofiling.org/hipc/page/show) (HIPC) data about cell populations and gating strategies can be transformed into semantically rich linked data and validated, using ontologies such as the [Protein Ontology](https://pir.georgetown.edu/pro/) and [Cell Ontology](http://obofoundry.org/ontology/cl.html).


## Usage

See the [`Makefile`](Makefile) for requirements and build tasks.


## Web Service

The [`src/server.py`](src/server.py) script will run a simple web service allowing users to submit their cell type and gating strategy and get a validation result immediately. It uses the Python [Flask](http://flask.pocoo.org) module.
