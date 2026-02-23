frappe.query_reports["Raw Material GRN vs Consumption"] = {
    "filters": [
        {
            "fieldname": "dc_number",
            "label": "DC Number",
            "fieldtype": "Select",
            "reqd": 1,
            "options": "\n",  // blank as first option
        }
    ],
    onload: function(report) {
        // fetch unique dc_number from In Stock
        frappe.db.get_list('In Stock', {
            fields: ['dc_number'],
            limit_page_length: 1000
        }).then(r => {
            if (r && r.length) {
                // get unique DC numbers
                let unique_dc = [...new Set(r.map(d => d.dc_number))];
                // add blank option at start
                unique_dc.unshift("");  
                // set options for filter dropdown
                let filter = report.get_filter('dc_number');
                filter.df.options = unique_dc.join('\n'); // newline separated
                filter.refresh();
            }
        });
    }
};
