import frappe

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

            # ---------------- GET ALL OPEN STOCK ----------------
            in_stocks = frappe.get_all(
                "In Stock",
                filters={"item_code": bi["item_code"], "status": "Open"},
                fields=["name", "balance_qty", "dc_number", "stock_date"],
                order_by="stock_date asc"
            )

            total_available = sum(d.balance_qty for d in in_stocks) if in_stocks else 0

            # ❌ Not enough stock in all open In Stock → skip item
            if total_available < required_qty:
                frappe.msgprint(
                    f"<b>Not enough balance</b> for Item <b>{bi['item_code']}</b>.<br>"
                    f"Required: {required_qty}<br>"
                    f"Available: {total_available}.<br>"
                    "Cannot create Out Stock."
                )
                continue  # skip this item completely

            remaining_required = required_qty

            # ---------------- FIFO CONSUMPTION ----------------
            for stock_row in in_stocks:

                if remaining_required <= 0:
                    break

                in_stock = frappe.get_doc("In Stock", stock_row.name)
                available_qty = in_stock.balance_qty or 0

                if available_qty <= 0:
                    continue  # skip empty stock

                # ---------------- DUPLICATE CHECK ----------------
                if frappe.db.exists(
                    "Out Stock",
                    {
                        "item_code": bi["item_code"],
                        "dc_number": in_stock.dc_number,
                        "dn_number": dn.name
                    }
                ):
                    continue  # skip this In Stock row

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
                    "shortage_qty": 0,  # ✅ No negative shortage
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
        frappe.msgprint("No Out Stock entries created due to insufficient stock.")

    return True
