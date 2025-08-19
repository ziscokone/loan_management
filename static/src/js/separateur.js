/** @odoo-module **/
import { AbstractField } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class FormattedIntegerWidget extends AbstractField {
    static template = "FormattedIntegerWidget"; // Assure-toi que ce template existe

    setup() {
        super.setup();
        this.on("input", this._onInput);
    }

    _onInput(event) {
        let value = event.target.value.replace(/\s/g, ""); // Supprime les espaces existants
        if (!isNaN(value) && value !== "") {
            event.target.value = parseFloat(value).toLocaleString("fr-FR"); // Applique le séparateur
        }
    }
}

registry.category("field").add("formatted_integer", FormattedIntegerWidget);
