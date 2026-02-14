frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        // Add custom button under "Create"
        if (!frm.doc.__islocal) {
            frm.add_custom_button('Out Stock', function() {
                frappe.call({
                    method: "scappnew.doctype.delivery_note.delivery_note.create_out_stock",
                    args: {
                        dn_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.show_alert({
                                message: "Out Stock created successfully!",
                                indicator: "green"
                            });
                        }
                    }
                });
            }, "Create");
        }
    }
});

