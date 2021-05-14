import os
import csv
import re

from collections import defaultdict


def a1_to_rowcol(a1):
    m = re.compile(r"([A-Za-z]+)([1-9]\d*)").match(a1)
    if m:
        column_label = m.group(1).upper()
        ridx = int(m.group(2))
        cidx = 0
        for i, c in enumerate(reversed(column_label)):
            cidx += (ord(c) - 64) * (26 ** i)
        return ridx, cidx
    return None


def render_html(headers, rows, messages):
    html = '<table class="table table-bordered table-light"><thead class="thead-dark"><tr>'
    for h in headers:
        html += f"\n<th>{h}</th>"
    html += "\n</tr></thead><tbody>"
    row_idx = 1
    for row in rows:
        html += "<tr>"
        row_idx += 1
        col_idx = 0
        for h in headers:
            col_idx += 1
            itm = row[h]
            msg = messages.get(col_idx, {}).get(row_idx, None)
            if not msg:
                html += f"\n<td>{itm}</td>"
                continue

            rule_id = msg.get("rule ID", "")
            rule_text = msg.get("rule", "")
            rule_message = msg.get("message", "")
            suggest = msg.get("suggestion", "")
            level = msg.get("level", "error").lower()

            if level == "error":
                td_class = "table-danger"
            elif level == "warn":
                td_class = "table-warning"
            else:
                td_class = "table-info"

            full_msg = ""
            if rule_id and rule_text:
                full_msg += f"{rule_id}: {rule_text}"
            elif rule_id:
                full_msg += rule_id
            elif rule_text:
                full_msg += rule_text

            if rule_message and full_msg != "":
                full_msg += f"<br>{rule_message}"
            elif rule_message:
                full_msg += rule_message

            if suggest and full_msg != "":
                full_msg += f"<br>Suggestion: '{suggest}'"
            elif suggest:
                full_msg += f"Suggestion: '{suggest}'"

            if full_msg:
                html += f'\n<td class="{td_class}" data-toggle="tooltip" data-placement="bottom" data-html="true" title="{full_msg}">{itm}</td>'
            else:
                html += f'\n<td class="{td_class}">{itm}</td>'
        html += "\n</tr>"
    html += "\n</tbody></table>"
    return html


def tsv2html(path, messages):
    table_name = os.path.splitext(path)[0]
    table_messages = defaultdict(dict)
    for row in messages:
        table = row["table"]
        loc = row["cell"]
        row_idx, col_idx = a1_to_rowcol(loc)
        if col_idx not in table_messages:
            table_messages[col_idx] = dict()
        table_messages[col_idx].update(
            {
                row_idx: {
                    "level": row.get("level", "error"),
                    "rule ID": row.get("rule ID"),
                    "rule": row.get("rule"),
                    "message": row.get("message"),
                    "suggestion": row.get("suggestion"),
                }
            }
        )
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        headers = reader.fieldnames
        for row in reader:
            rows.append(row)
    return render_html(headers, rows, table_messages)
