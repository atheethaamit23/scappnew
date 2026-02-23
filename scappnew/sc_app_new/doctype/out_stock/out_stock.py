import frappe
from frappe.model.document import Document

class OutStock(Document):

    def on_trash(self):
        """
        Restore In Stock balance when Out Stock is deleted
        (uses item_code + dc_number mapping)
        """

        # Safety
        if not self.item_code or not self.consumed_qty:
            return

        if not self.dc_number:
            frappe.msgprint(
                f"DC Number missing in Out Stock {self.name}. Cannot restore stock."
            )
            return

        # 🔑 Fetch the EXACT In Stock row used earlier
        in_stock_list = frappe.get_all(
            "In Stock",
            filters={
                "item_code": self.item_code,
                "dc_number": self.dc_number
            },
            fields=["name", "balance_qty", "status"],
            limit=1
        )

        if not in_stock_list:
            frappe.msgprint(
                f"In Stock not found for Item {self.item_code} with DC {self.dc_number}. Restore skipped."
            )
            return

        in_stock = frappe.get_doc("In Stock", in_stock_list[0].name)

        # ✅ Restore balance
        in_stock.balance_qty = (in_stock.balance_qty or 0) + self.consumed_qty
        in_stock.status = "Open"

        in_stock.save(ignore_permissions=True)
