# In Stock from csappcus creating In Stock Entry
import frappe
from frappe import _

@frappe.whitelist()
def add_items_to_in_stock(stock_entry_name):
    """
    Add items from a Stock Entry (GRN type) to In Stock doctype.
    stock_date = custom_dc_date from Stock Entry
    stock_entry_id = Stock Entry ID
    """
    doc = frappe.get_doc("Stock Entry", stock_entry_name)

    if doc.stock_entry_type != "GRN":
        frappe.msgprint(_("Stock Entry is not GRN. Skipping In Stock update."))
        return

    if not getattr(doc, "custom_dc_number", None):
        frappe.throw(_("Please set the Custom DC Number before submitting this Stock Entry."))

    if not getattr(doc, "custom_dc_date", None):
        frappe.throw(_("Please set the Custom DC Date before submitting this Stock Entry."))

    added_items = []

    for item in doc.items:
        in_stock_data = {
            "dc_number": doc.custom_dc_number,
            "stock_date": doc.custom_dc_date,        # Use custom_dc_date
            "stock_entry_id": doc.name,              # Add Stock Entry ID here
            "item_code": item.item_code,
            "item_name": item.item_name,
            "received_qty": item.qty,
            "balance_qty": item.qty,
            "status": "Open"
        }

        # Check if already exists
        existing = frappe.get_all("In Stock", filters={
            "dc_number": in_stock_data["dc_number"],
            "item_code": in_stock_data["item_code"]
        })

        if existing:
            frappe.msgprint(_("Item {0} already exists in In Stock with DC Number {1}. Skipping.").format(item.item_code, doc.custom_dc_number))
            continue

        in_stock_doc = frappe.get_doc({
            "doctype": "In Stock",
            **in_stock_data
        })
        in_stock_doc.insert()
        added_items.append(item.item_code)

    frappe.db.commit()

    if added_items:
        frappe.msgprint(_("Items added to In Stock: {0}").format(", ".join(added_items)))
    else:
        frappe.msgprint(_("No new items were added to In Stock."))
    
    return True

