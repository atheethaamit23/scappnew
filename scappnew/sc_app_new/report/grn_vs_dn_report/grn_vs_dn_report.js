frappe.query_reports["GRN vs DN Report"] = {
    "filters": [

        // ===== Status Filter =====
        {
            "fieldname": "status",
            "label": "Status",
            "fieldtype": "Select",
            "options": "\nOpen\nClosed",
            "default": "Open",
            "on_change": function(report) {
                load_dc_numbers(report);
            }
        },

        // ===== Customer Filter =====
        {
            "fieldname": "customer",
            "label": "Customer",
            "fieldtype": "Link",
            "options": "Customer",
            "get_query": function() {
                return {
                    query: "scappnew.sc_app_new.report.grn_vs_dn_report.grn_vs_dn_report.get_customers"
                };
            }
        },

        // ===== Item Code Filter =====
        {
            "fieldname": "item_code",
            "label": "Item Code",
            "fieldtype": "Link",
            "options": "Item"
        },

        {
            "fieldname": "dc_number",
            "label": "DC Number (ID)",
            "fieldtype": "Link",
            "options": "In Stock",

            get_query: function() {

                let from_date = frappe.query_report.get_filter_value("from_date");
                let to_date = frappe.query_report.get_filter_value("to_date");
                let status = frappe.query_report.get_filter_value("status");

                let filters = [];

                if (from_date && to_date) {
                    filters.push([
                        "In Stock",
                        "stock_date",
                        "between",
                        [from_date + " 00:00:00", to_date + " 23:59:59"]
                    ]);
                }

                if (status) {
                    filters.push([
                        "In Stock",
                        "status",
                        "=",
                        status
                    ]);
                }

                return { filters: filters };
            }
        },

        {
            "fieldname": "dc_number_display",
            "label": "DC Number",
            "fieldtype": "Autocomplete",
            "options": []
        },

        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            on_change: function(report) {
                load_dc_numbers(report);
            }
        },

        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            default: frappe.datetime.get_today(),
            on_change: function(report) {
                load_dc_numbers(report);
            }
        }

    ],

    onload: function(report) {

        load_dc_numbers(report);

        // ===== Download Excel Button =====
        report.page.add_inner_button("Download Excel", function () {

            let filters = report.get_values();

            let url = "/api/method/scappnew.sc_app_new.report.grn_vs_dn_report.grn_vs_dn_report.download_excel";

            window.open(url + "?filters=" + encodeURIComponent(JSON.stringify(filters)));

        });

    }
};


function load_dc_numbers(report) {

    let from_date = report.get_filter_value("from_date");
    let to_date = report.get_filter_value("to_date");
    let status = report.get_filter_value("status");

    let filters = {};

    if (from_date && to_date) {
        filters["stock_date"] = ["between", [from_date + " 00:00:00", to_date + " 23:59:59"]];
    }

    if (status) {
        filters["status"] = status;
    }

    frappe.db.get_list("In Stock", {
        fields: ["dc_number"],
        filters: filters,
        limit_page_length: 1000
    }).then(data => {

        if (!data) return;

        let dc_list = [...new Set(
            data.map(d => d.dc_number).filter(Boolean)
        )];

        let filter = report.get_filter("dc_number_display");
        filter.df.options = dc_list;
        filter.refresh();
    });
}