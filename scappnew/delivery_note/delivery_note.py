import frappe
from collections import defaultdict

@frappe.whitelist()
def add_to_out_stock_entries(delivery_note):
    dn = frappe.get_doc("Delivery Note", delivery_note)
    created = 0

    for item in dn.items:

        # ---------------- BOM CHECK ----------------
        bom_name = frappe.db.get_value(
            "BOM",
            {"item": item.item_code, "is_active": 1},
            "name"
        )

        bom_items = []

        if bom_name:
            bom = frappe.get_doc("BOM", bom_name)
            for bi in bom.items:
                bom_items.append({
                    "item_code": bi.item_code,
                    "item_name": bi.item_name,
                    "required_qty": bi.qty * item.qty
                })
        else:
            bom_items.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "required_qty": item.qty
            })

        # ---------------- PROCESS RAW MATERIALS ----------------
        for bi in bom_items:
            required_qty = bi["required_qty"]

            # ---------------- DUPLICATE CHECK (GLOBAL FOR ITEM + DN) ----------------
            duplicate_exists = frappe.db.exists(
                "Out Stock",
                {
                    "item_code": bi["item_code"],
                    "dn_number": dn.name
                }
            )

            if duplicate_exists:
                frappe.msgprint(
                    f"<b>Out Stock already exists</b> for Item "
                    f"<b>{bi['item_code']}</b> against Delivery Note "
                    f"<b>{dn.name}</b>."
                )
                continue  # ❌ Skip entire item completely

            # ---------------- GET ALL OPEN STOCK ----------------
            in_stocks = frappe.get_all(
                "In Stock",
                filters={"item_code": bi["item_code"], "status": "Open"},
                fields=["name", "balance_qty", "dc_number", "stock_date"],
                order_by="stock_date asc"
            )

            total_available = sum(d.balance_qty for d in in_stocks) if in_stocks else 0

            # ❌ Not enough stock → skip item
            if total_available < required_qty:
                frappe.msgprint(
                    f"<b>Not enough balance</b> for Item <b>{bi['item_code']}</b>.<br>"
                    f"Required: {required_qty}<br>"
                    f"Available: {total_available}.<br>"
                    "Cannot create Out Stock."
                )
                continue

            remaining_required = required_qty

            # ---------------- FIFO CONSUMPTION ----------------
            for stock_row in in_stocks:

                if remaining_required <= 0:
                    break

                in_stock = frappe.get_doc("In Stock", stock_row.name)
                available_qty = in_stock.balance_qty or 0

                if available_qty <= 0:
                    continue

                # ---------------- CONSUME STOCK ----------------
                consumed_qty = min(available_qty, remaining_required)
                new_balance = available_qty - consumed_qty
                remaining_required -= consumed_qty

                # ---------------- CREATE OUT STOCK ENTRY ----------------
                out_stock = frappe.get_doc({
                    "doctype": "Out Stock",
                    "item_code": bi["item_code"],
                    "item_name": bi["item_name"],
                    "model": item.item_code,
                    "dn_number": dn.name,
                    "dc_number": in_stock.dc_number,
                    "stock_date": dn.posting_date,
                    "invoiced_qty": required_qty,
                    "consumed_qty": consumed_qty,
                    "balance_qty": new_balance,
                    "shortage_qty": 0,
                    "status": "Open"
                })
                out_stock.insert(ignore_permissions=True)
                created += 1

                # ---------------- UPDATE IN STOCK ----------------
                in_stock.balance_qty = new_balance
                in_stock.status = "Closed" if new_balance <= 0 else "Open"
                in_stock.save(ignore_permissions=True)

    frappe.db.commit()

    if created:
        frappe.msgprint(f"{created} Out Stock entries created successfully.")
    else:
        frappe.msgprint("No Out Stock entries created.")

    return True


@frappe.whitelist()
def get_raw_material_usage(delivery_note):
    out_stock_entries = frappe.get_all(
        "Out Stock",
        filters={"dn_number": delivery_note},
        fields=["item_code", "item_name", "dc_number", "consumed_qty", "stock_date"],
        order_by="dc_number asc, item_code asc"
    )

    usage_data = []
    for entry in out_stock_entries:
        usage_data.append({
            "item_code": entry.item_code,
            "item_name": entry.item_name,
            "dc_number": entry.dc_number,
            "consumed_qty": entry.consumed_qty,
            "stock_date": entry.stock_date
        })

    return usage_data
