#!/usr/bin/env python3

import gizmos.search
import gizmos.tree
import logging
import os
import sqlite3
import subprocess

from flask import abort, Flask, render_template, request, Response
from jinja2 import Template
from tempfile import TemporaryDirectory
from tsv2html import tsv2html
from validate import validate

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/examples")
def examples():
    # TODO
    return render_template("examples.html")


@app.route("/instructions")
def instructions():
    return render_template("instructions.html")


@app.route("/terminology")
def terminology():
    # TODO
    html = "<h1>Terminology</h1>"
    html += '\n<ul><li><a href="/terminology/pr">Protein Ontology</a></li>'
    html += '\n<li><a href="/terminology/cl">Cell Ontology</a></li></ul>'
    return render_template("base.html", default=html)


@app.route("/terminology/<ont>")
def show_tree(ont):
    content = get_tree(ont, None)
    return render_template("base.html", default=content)


@app.route("/terminology/<ont>/<term_id>")
def show_tree_at(ont, term_id):
    content = get_tree(ont, term_id)
    return render_template("base.html", default=content)


@app.route("/validator", methods=["GET", "POST"])
def validator():
    if request.method == "GET":
        return render_template("validator.html")
    else:
        if "file" not in request.files:
            message = "<p class='alert alert-danger'>Please upload a file.</p>"
            return render_template("validator.html", message=message)
        f = request.files["file"]
        filename = f.filename
        if filename.endswith(".csv"):
            suffix = ".csv"
        elif filename.endswith(".tsv"):
            suffix = ".tsv"
        else:
            message = f"<p class='alert alert-danger'>Unrecognized file type for '{filename}'. Please use CSV or TSV format.</p>"
            return render_template("validator.html", message=message)

        tempdir = TemporaryDirectory()
        path = os.path.join(tempdir.name, "cell-names-and-markers" + suffix)
        f.save(path)

        messages = validate(
            "build/cell.tsv", "build/cl-levels.tsv", "build/marker.tsv", path
        )

        if messages:
            message = "<p class='alert alert-danger'>This template contains errors.</p>"
        else:
            message = "<p class='alert alert-success'>This template is valid.</p>"

        table = tsv2html(path, messages)
        message += "\n\n" + table
        return render_template("validator.html", message=message)


def get_database(resource):
    db_name = resource.lower()
    db = f"build/{db_name}.db"
    if not os.path.exists("build"):
        os.mkdir("build")
    if not os.path.exists(db):
        # TODO - make database
        logging.info("Building database for " + resource)
        rc = subprocess.call(f"make build/{db_name}.db", shell=True)
        if rc != 0:
            return abort(500, description="Unable to create database for " + resource)
    return db


def get_tree(ont, term_id):
    db = get_database(ont)
    fmt = request.args.get("format", "")
    if fmt == "json":
        label = request.args.get("text", "")
        return gizmos.search.search(db, label, limit=30)
    href = "./{curie}"
    if not term_id:
        href = ont + "/{curie}"
    if ont == "cl":
        title = "Cell Ontology Browser"
    elif ont == "pr":
        title = "Protein Ontology Browser"
    else:
        return "Unknown ontology: " + title
    return gizmos.tree.tree(
        db, term_id, title=title, href=href, include_search=True, standalone=True
    )
