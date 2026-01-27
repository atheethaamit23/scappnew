import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []

    bom_plan = filters.get("bom_plan")
    if not bom_plan:
        return columns, data

    # Parent BOM Plan
    plan_doc = frappe.get_doc("BOM Plan", bom_plan)
    default_warehouse = plan_doc.get("warehouse")

    running_balance = {}

    # Fetch BOM Plan Items IN YOUR CUSTOM ORDER
    plan_items = frappe.get_all(
        "BOM Plan Item",
        filters={"parent": bom_plan},
        fields=["bom", "qty", "`order`"],
        order_by="`order` asc"
    )

    for plan in plan_items:
        if not plan.bom:
            continue

        # Manufacturing item of BOM
        manufactured_item = frappe.db.get_value(
            "BOM", plan.bom, "item"
        )

        # Explode BOM
        bom_items = frappe.get_all(
            "BOM Item",
            filters={"parent": plan.bom},
            fields=["item_code", "qty"],
            order_by="idx"
        )

        for bi in bom_items:
            if not bi.item_code:
                continue

            required_qty = bi.qty * plan.qty

            # Initialize available stock once per item
            if bi.item_code not in running_balance:
                stock = 0
                if default_warehouse:
                    stock = frappe.db.get_value(
                        "Bin",
                        {
                            "item_code": bi.item_code,
                            "warehouse": default_warehouse
                        },
                        "actual_qty"
                    ) or 0

                running_balance[bi.item_code] = stock

            available_qty = running_balance[bi.item_code]

            shortage_qty = max(required_qty - available_qty, 0)
            excess_qty = max(available_qty - required_qty, 0)

            # Reduce stock for next occurrence
            running_balance[bi.item_code] -= required_qty

            data.append({
                "order_no": plan.order,
                "manufactured_item": manufactured_item,
                "raw_item": bi.item_code,
                "required_qty": required_qty,
                "available_qty": available_qty,
                "shortage_qty": shortage_qty,
                "excess_qty": excess_qty,
                "warehouse": default_warehouse,
            })

    return columns, data


def get_columns():
    return [
        {
            "label": _("Order"),
            "fieldname": "order_no",
            "fieldtype": "Int",
            "width": 80
        },
        {
            "label": _("Manufactured Item"),
            "fieldname": "manufactured_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 200
        },
        {
            "label": _("Raw Material"),
            "fieldname": "raw_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 200
        },
        {
            "label": _("Required Qty"),
            "fieldname": "required_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Available Qty"),
            "fieldname": "available_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Shortage Qty"),
            "fieldname": "shortage_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Excess Qty"),
            "fieldname": "excess_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 160
        },
    ]
