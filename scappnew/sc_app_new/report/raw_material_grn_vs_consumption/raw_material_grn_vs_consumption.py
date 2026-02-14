import frappe
from collections import defaultdict


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {"label": "In Stock ID", "fieldname": "in_stock_id", "fieldtype": "Link", "options": "In Stock", "width": 140},
        {"label": "Stock Entry ID", "fieldname": "stock_entry_id", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
        {"label": "DC Number", "fieldname": "dc_number", "fieldtype": "Data", "width": 150},
        {"label": "GRN Date", "fieldname": "grn_date", "fieldtype": "Date", "width": 110},
        {"label": "Raw Material (In Stock)", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 180},
        {"label": "Qty Received", "fieldname": "qty_received", "fieldtype": "Float", "width": 110},

        {"label": "Out Stock ID", "fieldname": "out_stock_id", "fieldtype": "Link", "options": "Out Stock", "width": 140},
        {"label": "Out Stock Item", "fieldname": "out_item_code", "fieldtype": "Link", "options": "Item", "width": 180},
        {"label": "Model", "fieldname": "model", "fieldtype": "Data", "width": 180},
        {"label": "Delivery Note", "fieldname": "out_dc", "fieldtype": "Data", "width": 150},
        {"label": "Dispatch Date", "fieldname": "dispatch_date", "fieldtype": "Date", "width": 120},
        {"label": "Inv. Qty", "fieldname": "inv_qty", "fieldtype": "Float", "width": 90},
        {"label": "Qty Consumed", "fieldname": "qty_consumed", "fieldtype": "Float", "width": 110},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Float", "width": 90},
    ]


def get_data():
    data = []

    # In Stock FIFO grouped by raw material
    in_stock_map = defaultdict(list)
    for r in frappe.get_all(
        "In Stock",
        fields=[
            "name", "dc_number", "stock_date",
            "stock_entry_id", "item_code",
            "received_qty"
        ],
        order_by="stock_date asc"
    ):
        in_stock_map[r.item_code].append({
            "doc": r,
            "balance": r.received_qty
        })

    # Out Stock FIFO grouped by raw material
    out_stock_map = defaultdict(list)
    for r in frappe.get_all(
        "Out Stock",
        fields=[
            "name", "item_code", "model",
            "dc_number", "stock_date",
            "invoiced_qty", "consumed_qty"
        ],
        order_by="stock_date asc"
    ):
        out_stock_map[r.item_code].append({
            "doc": r,
            "remaining": r.consumed_qty
        })

    # FIFO allocation with controlled repetition
    for item_code, in_stocks in in_stock_map.items():
        out_stocks = out_stock_map.get(item_code)
        if not out_stocks:
            continue

        out_index = 0

        for in_stock in in_stocks:
            in_doc = in_stock["doc"]
            balance = in_stock["balance"]

            # GRN header row
            data.append({
                "in_stock_id": in_doc.name,
                "stock_entry_id": in_doc.stock_entry_id,
                "dc_number": in_doc.dc_number,
                "grn_date": in_doc.stock_date,
                "item_code": in_doc.item_code,
                "qty_received": in_doc.received_qty
            })

            while balance > 0 and out_index < len(out_stocks):
                out = out_stocks[out_index]
                out_doc = out["doc"]

                consume = min(balance, out["remaining"])
                balance -= consume
                out["remaining"] -= consume

                # Out Stock row (repeat only when crossing GRN)
                data.append({
                    "out_stock_id": out_doc.name,
                    "out_item_code": out_doc.item_code,
                    "model": out_doc.model,
                    "out_dc": out_doc.dc_number,
                    "dispatch_date": out_doc.stock_date,
                    "inv_qty": out_doc.invoiced_qty,
                    "qty_consumed": consume,
                    "balance": balance
                })

                if out["remaining"] == 0:
                    out_index += 1
                else:
                    break  # move to next In Stock

            # Total row per GRN
            data.append({
                "qty_consumed": "Total =",
                "balance": in_doc.received_qty
            })

    return data

