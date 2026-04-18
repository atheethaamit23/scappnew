import frappe
from frappe import _
from frappe.utils import get_datetime

@frappe.whitelist()
def add_items_to_in_stock(stock_entry_name):
    """
    Add items from a Stock Entry (GRN type) to In Stock doctype.
    Stock Date priority:
    1) Custom DC Date
    2) Posting Date
    Posting Time is mandatory (00:00:00 allowed)
    """

    # Fetch Stock Entry
    doc = frappe.get_doc("Stock Entry", stock_entry_name)

    # Validate GRN type
    if doc.stock_entry_type != "GRN":
        frappe.msgprint(_("Stock Entry is not GRN. Skipping In Stock update."))
        return False

    # Validate required fields
    if not doc.custom_dc_number:
        frappe.throw(_("Please set the Custom DC Number before submitting this Stock Entry."))

    # ✅ Get Customer
    customer = doc.custom_customer_provided

    # ✅ Optional validation for customer
    if not customer:
        frappe.throw(_("Customer is required for GRN Stock Entry."))

    # ✅ Determine stock date (fallback logic)
    stock_date = doc.custom_dc_date or doc.posting_date

    if not stock_date:
        frappe.throw(_("Either DC Date or Posting Date is required."))

    # ✅ Posting time validation (00:00:00 allowed)
    if doc.posting_time in (None, ""):
        frappe.throw(_("Posting Time is required."))

    # Combine Date + Time
    posting_datetime = get_datetime(f"{stock_date} {doc.posting_time}")

    added_items = []

    for item in doc.items:

        # Prevent duplicate entry (DC + Item)
        existing = frappe.get_all(
            "In Stock",
            filters={
                "dc_number": doc.custom_dc_number,
                "item_code": item.item_code
            },
            limit=1
        )

        if existing:
            frappe.msgprint(
                _("Item {0} already exists in In Stock with DC Number {1}. Skipping.")
                .format(item.item_code, doc.custom_dc_number)
            )
            continue

        # Create In Stock record
        in_stock_doc = frappe.get_doc({
            "doctype": "In Stock",
            "dc_number": doc.custom_dc_number,
            "stock_date": posting_datetime,   # FULL DATETIME
            "stock_entry_id": doc.name,
            "customer": customer,   # ✅ ADDED
            "item_code": item.item_code,
            "item_name": item.item_name,
            "received_qty": item.qty,
            "balance_qty": item.qty,
            "status": "Open"
        })

        in_stock_doc.insert(ignore_permissions=True)
        added_items.append(item.item_code)

    frappe.db.commit()

    if added_items:
        frappe.msgprint(_("Items added to In Stock: {0}")
                        .format(", ".join(added_items)))
    else:
        frappe.msgprint(_("No new items were added to In Stock."))

    return True