/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";

export class SimpleBudgetSeparator extends FloatField {
    setup() {
        super.setup();
        this.el.addEventListener("input", this.handleInput.bind(this));
    }

    handleInput(event) {
        let input = event.target;
        let value = input.value.replace(/\s/g, '');
        
        if (!isNaN(value) && value !== '') {
            const numericValue = Number(value);
            input.value = numericValue.toLocaleString('fr-FR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            this.props.update(numericValue);
        }
    }

    willUnmount() {
        this.el.removeEventListener("input", this.handleInput.bind(this));
    }
}

registry.category("fields").add("separateur_milliers", SimpleBudgetSeparator);