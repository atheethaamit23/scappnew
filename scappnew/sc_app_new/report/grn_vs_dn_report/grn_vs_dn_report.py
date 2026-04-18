import frappe
from frappe import _
import openpyxl
import json
from datetime import datetime, date


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Customer DC No.", "fieldname": "dc_number", "width": 150},
        {"label": "DC Date", "fieldname": "dc_date", "width": 120},

        {
            "label": "Stock Entry ID",
            "fieldname": "stock_entry_id",
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 160
        },

        {"label": "Part No.", "fieldname": "item_code", "width": 150},
        {"label": "Received Quantity", "fieldname": "received_qty", "width": 150},
        {"label": "Model", "fieldname": "model", "width": 180},

        {
            "label": "Delivery Note",
            "fieldname": "dn_link",
            "fieldtype": "Link",
            "options": "Delivery Note",
            "width": 180
        },

        {"label": "SCCPL Invoice/DC No.", "fieldname": "dn_number", "width": 180},
        {"label": "Date of Despatch", "fieldname": "dn_date", "width": 150},
        {"label": "GRN Number", "fieldname": "grn_number", "width": 150},
        {"label": "Invoice Qty", "fieldname": "inv_qty_display", "width": 120},
        {"label": "Consumed Quantity", "fieldname": "consumed_qty", "width": 140},
        {"label": "Balance", "fieldname": "balance_qty", "width": 120},
    ]


def get_data(filters):
    data = []

    if not filters:
        return data

    conditions = {}

    if filters.get("dc_number"):
        conditions["dc_number"] = filters.get("dc_number")

    if filters.get("dc_number_display"):
        conditions["dc_number"] = filters.get("dc_number_display")

    if filters.get("item_code"):
        conditions["item_code"] = filters.get("item_code")

    if filters.get("from_date") and filters.get("to_date"):
        conditions["stock_date"] = ["between", [filters.get("from_date"), filters.get("to_date")]]

    if filters.get("status"):
        conditions["status"] = filters.get("status")

    if not conditions:
        return data

    in_stock_entries = frappe.get_all(
        "In Stock",
        filters=conditions,
        fields=[
            "name",
            "dc_number",
            "stock_entry_id",
            "stock_date",
            "item_code",
            "received_qty",
            "status",
            "customer"
        ],
        order_by="dc_number asc, item_code asc"
    )

    last_dc = None

    for ins in in_stock_entries:

        customer = ins.get("customer")

        if not customer and ins.stock_entry_id:
            customer = frappe.db.get_value(
                "Stock Entry",
                ins.stock_entry_id,
                "custom_customer_provided"
            )

        if filters.get("customer") and customer != filters.get("customer"):
            continue

        if last_dc != ins.dc_number:
            dc_display = ins.dc_number
            last_dc = ins.dc_number
        else:
            dc_display = ""

        dc_date = ins.stock_date.date() if isinstance(ins.stock_date, datetime) else ins.stock_date

        if dc_display:
            dc_date_display = dc_date
        else:
            dc_date_display = ""

        data.append({
            "dc_number": dc_display,
            "dc_date": dc_date_display,
            "stock_entry_id": ins.stock_entry_id,
            "item_code": ins.item_code,
            "received_qty": ins.received_qty,
            "status": ins.status
        })

        out_stock_entries = frappe.db.sql("""
            SELECT 
                os.model,
                os.dn_number,
                COALESCE(dn.custom_invoice_number, dn.name) AS dn_invoice_number,
                dn.posting_date AS dn_date,
                dn.custom_delivery_type,
                os.consumed_qty,
                os.balance_qty
            FROM `tabOut Stock` os
            LEFT JOIN `tabDelivery Note` dn
                ON os.dn_number = dn.name
            WHERE 
                os.dc_number = %s
                AND os.item_code = %s
            ORDER BY os.balance_qty DESC, dn.posting_date ASC, os.name ASC
        """, (ins.dc_number, ins.item_code), as_dict=True)

        total_consumed = 0

        for outs in out_stock_entries:
            total_consumed += outs.consumed_qty or 0

            inv_qty_display = 0 if outs.custom_delivery_type == "RTV" else outs.consumed_qty or 0

            dn_date = (
                outs.dn_date.date()
                if isinstance(outs.dn_date, datetime)
                else outs.dn_date
            )

            model_value = "MRTV" if outs.custom_delivery_type == "RTV" else outs.model

            data.append({
                "dc_number": "",
                "dc_date": "",
                "stock_entry_id": "",
                "item_code": "",
                "received_qty": "",
                "model": model_value,
                "dn_link": outs.dn_number,
                "dn_number": outs.dn_invoice_number,
                "dn_date": dn_date,
                "inv_qty_display": inv_qty_display,
                "consumed_qty": outs.consumed_qty,
                "balance_qty": outs.balance_qty
            })

        data.append({
            "dc_number": "",
            "dc_date": "",
            "stock_entry_id": "",
            "item_code": "",
            "received_qty": "",
            "model": "",
            "dn_link": "",
            "dn_number": "Total =",
            "consumed_qty": total_consumed
        })

    return data


def get_customer_address(customer):
    if not customer:
        return ""

    address = frappe.db.sql("""
        SELECT 
            CONCAT_WS(', ',
                a.address_line1,
                a.address_line2,
                a.city,
                a.state,
                a.pincode
            ) AS full_address
        FROM `tabAddress` a
        INNER JOIN `tabDynamic Link` dl
            ON dl.parent = a.name
        WHERE
            dl.link_doctype = 'Customer'
            AND dl.link_name = %s
        ORDER BY a.is_primary_address DESC
        LIMIT 1
    """, customer, as_dict=True)

    return address[0].full_address if address else ""


@frappe.whitelist()
def download_excel(filters=None):

    if isinstance(filters, str):
        filters = json.loads(filters)

    columns, data = execute(filters)

    dc_group = {}
    current_dc = None
    customer_name = ""
    customer_address = ""

    for row in data:
        dc = row.get("dc_number")
        if dc:
            current_dc = dc

            stock_entry = frappe.db.get_value(
                "In Stock",
                {"dc_number": dc},
                "stock_entry_id"
            )

            customer_name = frappe.db.get_value(
                "Stock Entry",
                stock_entry,
                "custom_customer_provided"
            )

            customer_address = get_customer_address(customer_name)

        dc_group.setdefault(current_dc, []).append(row)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for dc, rows in dc_group.items():
        sheet = wb.create_sheet(title=str(dc)[:31])

        sheet.append([f"Customer Name : {customer_name or ''}"])
        sheet.append([f"Customer Address : {customer_address or ''}"])
        sheet.append([])

        headers = [
            col["label"] for col in columns
            if col["fieldname"] not in ("stock_entry_id", "dn_link")
        ]
        sheet.append(headers)

        # ✅ FIXED: Model column is 'E', not 'D'
        sheet.column_dimensions['E'].width = 30

        for r in rows:
            sheet.append([
                r.get("dc_number"),
                r.get("dc_date"),
                r.get("item_code"),
                r.get("received_qty"),
                r.get("model"),
                r.get("dn_number"),
                r.get("dn_date"),
                r.get("grn_number"),
                r.get("inv_qty_display"),
                r.get("consumed_qty"),
                r.get("balance_qty"),
            ])

    file_path = "/tmp/dc_stock_report.xlsx"
    wb.save(file_path)

    with open(file_path, "rb") as f:
        filedata = f.read()

    frappe.response["filename"] = "DC_Stock_Report.xlsx"
    frappe.response["filecontent"] = filedata
    frappe.response["type"] = "binary"


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_customers(doctype, txt, searchfield, start, page_len, filters):

    return frappe.db.sql("""
        SELECT DISTINCT dn.customer
        FROM `tabOut Stock` os
        INNER JOIN `tabDelivery Note` dn
            ON os.dn_number = dn.name
        WHERE dn.customer LIKE %s
        ORDER BY dn.customer
        LIMIT %s, %s
    """, ("%{}%".format(txt), start, page_len))