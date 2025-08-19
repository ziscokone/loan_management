/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatFloat, parseFloat } from "@web/core/utils/numbers";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useInputField } from "@web/views/fields/input_field_hook";
import { Component, useRef } from "@odoo/owl";

export class ThousandsSeparatorWidget extends Component {
    setup() {
        console.log("✅ Widget Initialized", this.props);
        this.inputRef = useRef("numericInput");

        this.inputField = useInputField({
            getValue: () => this.formattedValue,
            refName: "numericInput",
            parse: (v) => this.parse(v),
        });
    }

    get formattedValue() {
        console.log("🔍 formattedValue called with:", this.props.value);
        if (this.props.value === false || this.props.value === undefined) {
            return "";
        }
        return formatFloat(this.props.value, {
            thousandsSep: ' ',
            decimalPoint: ',',
            digits: [16, 0],
        });
    }

    parse(value) {
        if (!value || typeof value !== "string") {
            return false;
        }
        console.log("🔄 Parsing value:", value);
        return parseFloat(value.replace(/\s+/g, '').replace(',', '.'));
    }

    onInput(ev) {
        console.log("⌨️ Input event triggered", ev.target.value);
        const input = ev.target;
        if (!input) return;

        const cleanValue = input.value.replace(/\s+/g, '').replace(',', '.');
        const numericValue = parseFloat(cleanValue);

        if (!isNaN(numericValue)) {
            this.props.update(numericValue);
        }
    }
}

ThousandsSeparatorWidget.template = 'loan_management.ThousandsSeparatorWidget';
ThousandsSeparatorWidget.props = {
    ...standardFieldProps,
};

registry.category("fields").add("thousands_separator", ThousandsSeparatorWidget);
