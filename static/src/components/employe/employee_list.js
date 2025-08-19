/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { useState } from "@odoo/owl"; // Modification ici : import depuis @odoo/owl

export class EmployeeListRenderer extends ListRenderer {
    static template = "loan_management.EmployeeListView";

    setup() {
        super.setup();
        this.state = useState({
            searchQuery: "",
            selectedDepartment: "all",
        });
    }

    getDepartments() {
        const departments = new Set();
        this.props.list.records.forEach((record) => {
            if (record.data.departement) {
                departments.add(record.data.departement);
            }
        });
        return Array.from(departments);
    }

    filterRecords() {
        return this.props.list.records.filter((record) => {
            const matchesSearch =
                !this.state.searchQuery ||
                record.data.nom.toLowerCase().includes(this.state.searchQuery.toLowerCase()) ||
                record.data.prenoms.toLowerCase().includes(this.state.searchQuery.toLowerCase()) ||
                record.data.matricule.toLowerCase().includes(this.state.searchQuery.toLowerCase());

            const matchesDepartment = this.state.selectedDepartment === "all" || record.data.departement === this.state.selectedDepartment;

            return matchesSearch && matchesDepartment;
        });
    }

    getSexeClass(sexe) {
        return sexe === "M" ? "bg-blue-100" : "bg-pink-100";
    }

    getAgeClass(age) {
        if (age < 30) return "text-green-600";
        if (age < 45) return "text-blue-600";
        return "text-orange-600";
    }
}

export const EmployeeListView = {
    ...listView,
    Renderer: EmployeeListRenderer,
    Controller: EmployeeListController,
};

registry.category("views").add("paa_employee_list", EmployeeListView);
