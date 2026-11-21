import sys, json, types
sys.path.insert(0,".")
import frappe
frappe.init(site="test", sites_path="/tmp/sites"); frappe.local.lang="en"
import frappe.translate as _t; _t.get_all_translations=lambda l:{}
from unittest import mock
from hasiruratha.patches import create_duplicate_reports as p

class WS:
    def __init__(s, content):
        s.content=json.dumps(content); s.shortcuts=[]; s.number_cards=[]; s.flags=types.SimpleNamespace(); s.saved=False
    def append(s,k,v): getattr(s,k).append(types.SimpleNamespace(**v))
    def save(s): s.saved=True
H=lambda t:{"id":"h","type":"header","data":{"text":t,"col":12}}
for label,content,expect_header in [
  ("section heading exists",[H("Welcome"),H("PLANTATION"),H("DUPLICATE DETECTION & REVIEW"),H("TREE MANAGEMENT")],False),
  ("no such heading",[H("Welcome"),H("TREE MANAGEMENT")],True)]:
    ws=WS(content)
    frappe.local.db=mock.MagicMock(); frappe.local.db.exists.return_value=True
    with mock.patch.object(frappe,"get_doc",return_value=ws), mock.patch("frappe.modules.import_file.import_file_by_path"):
        p._workspace()
    blocks=json.loads(ws.content); types_=[b["type"] for b in blocks]
    idx=[i for i,b in enumerate(blocks) if b["type"]=="number_card"]
    head=[i for i,b in enumerate(blocks) if b["type"]=="header" and "duplicate" in b["data"]["text"].lower()][0]
    assert ws.saved and len(ws.shortcuts)==2 and len(ws.number_cards)==2
    assert idx and head < idx[0] and blocks[idx[0]-1]["type"]=="header", types_
    assert blocks[0]["data"]["text"]=="Welcome"
    print("PASS workspace patch:",label,"->",[b["type"][:4] for b in blocks])
# runs once
ws=WS([H("DUPLICATE DETECTION")]); ws.shortcuts=[types.SimpleNamespace(link_to="HR Duplicate Report")]
with mock.patch.object(frappe,"get_doc",return_value=ws), mock.patch("frappe.modules.import_file.import_file_by_path"):
    p._workspace()
assert not ws.saved; print("PASS workspace patch is a no-op the second time")
