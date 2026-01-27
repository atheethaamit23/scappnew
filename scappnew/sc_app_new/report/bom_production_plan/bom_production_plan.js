frappe.query_reports["BOM Production Plan"] = {
    filters: [
        {
            fieldname: "bom_plan",
            label: __("BOM Plan"),
            fieldtype: "Link",
            options: "BOM Plan",
            reqd: 1
        }
    ]
};

