import frappe
from frappe.utils import today

@frappe.whitelist()
def create_out_stock_entries(delivery_note):
    """
    Create Out Stock entries from a Delivery Note.
    Prevent duplicates: same item + same DC Number will not be added twice.
    """

    dn = frappe.get_doc('Delivery Note', delivery_note)
    out_stock_entries = []

    # Fetch all existing item_codes for this DC number in Out Stock
    existing_items = set(
        frappe.get_all(
            "Out Stock",
            filters={"dc_number": dn.name},
            pluck="item_code"
        )
    )

    for item in dn.items:
        # Check if BOM exists for this item
        bom_name = frappe.db.get_value('BOM', {'item': item.item_code, 'is_active': 1}, 'name')
        if bom_name:
            bom_doc = frappe.get_doc('BOM', bom_name)
            for raw_item in bom_doc.items:
                total_qty = raw_item.qty * item.qty

                # Skip if same item + same DC exists
                if raw_item.item_code in existing_items:
                    frappe.msgprint(f"Item {raw_item.item_code} already exists in Out Stock for DC {dn.name}. Skipping.")
                    continue

                out_stock_entries.append(frappe.get_doc({
                    'doctype': 'Out Stock',
                    'item_code': raw_item.item_code,
                    'item_name': raw_item.item_name,
                    'model': item.item_code,
                    'dc_number': dn.name,
                    'stock_date': dn.posting_date,
                    'invoiced_qty': total_qty,
                    'consumed_qty': 0,
                    'balance_qty': total_qty,
                    'status': 'Open'
                }))
                existing_items.add(raw_item.item_code)  # Mark as added
        else:
            # If no BOM, just add the item itself
            if item.item_code in existing_items:
                frappe.msgprint(f"Item {item.item_code} already exists in Out Stock for DC {dn.name}. Skipping.")
                continue

            out_stock_entries.append(frappe.get_doc({
                'doctype': 'Out Stock',
                'item_code': item.item_code,
                'item_name': item.item_name,
                'model': item.item_code,
                'dc_number': dn.name,
                'stock_date': dn.posting_date,
                'invoiced_qty': item.qty,
                'consumed_qty': item.qty,
                'balance_qty': item.qty,
                'status': 'Open'
            }))
            existing_items.add(item.item_code)  # Mark as added

    # Insert all Out Stock entries
    for entry in out_stock_entries:
        entry.insert()
    frappe.db.commit()

    if out_stock_entries:
        frappe.msgprint(f"{len(out_stock_entries)} Out Stock entries created successfully for DC {dn.name}.")
    else:
        frappe.msgprint(f"No new Out Stock entries were created for DC {dn.name} (all items already exist).")

    return True

