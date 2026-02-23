import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "DC Number", "fieldname": "dc_number", "width": 150},
        {"label": "Date", "fieldname": "stock_date", "width": 110},
        {"label": "Item Code", "fieldname": "item_code", "width": 150},
        {"label": "Received Quantity", "fieldname": "received_qty", "width": 150},
        {"label": "Model", "fieldname": "model", "width": 180},
        {"label": "DN Number", "fieldname": "dn_number", "width": 150},
        {"label": "Out Stock Date", "fieldname": "out_stock_date", "width": 120},
        {"label": "DC Number", "fieldname": "out_dc_number", "width": 150},
        {"label": "Inv.Qty", "fieldname": "invoiced_qty", "width": 100},
        {"label": "Qty.cons", "fieldname": "consumed_qty", "width": 100},
        {"label": "Balance", "fieldname": "balance_qty", "width": 120},
    ]


def get_data(filters):
    data = []

    if not filters or not filters.get("dc_number"):
        return data   # Don't show anything until DC is selected

    # Get filtered In Stock entries
    in_stock_entries = frappe.get_all(
        "In Stock",
        filters={
            "dc_number": filters.get("dc_number")
        },
        fields=[
            "name",
            "dc_number",
            "stock_date",
            "item_code",
            "received_qty"
        ],
        order_by="item_code asc"
    )

    for ins in in_stock_entries:

        # Main GRN Row
        data.append({
            "dc_number": ins.dc_number,
            "stock_date": ins.stock_date,
            "item_code": ins.item_code,
            "received_qty": ins.received_qty
        })

        # Matching Out Stock rows
        out_stock_entries = frappe.get_all(
            "Out Stock",
            filters={
                "dc_number": ins.dc_number,
                "item_code": ins.item_code
            },
            fields=[
                "model",
                "dn_number",
                "stock_date",
                "dc_number",
                "invoiced_qty",
                "consumed_qty",
                "balance_qty"
            ],
            order_by="stock_date asc"
        )

        total_consumed = 0

        for outs in out_stock_entries:
            total_consumed += outs.consumed_qty or 0

            data.append({
                "model": outs.model,
                "dn_number": outs.dn_number,
                "out_stock_date": outs.stock_date,
                "out_dc_number": outs.dc_number,
                "invoiced_qty": outs.invoiced_qty,
                "consumed_qty": outs.consumed_qty,
                "balance_qty": outs.balance_qty
            })

        # Total Row
        data.append({
            "dn_number": "Total =",
            "consumed_qty": total_consumed
        })

    return data
    

