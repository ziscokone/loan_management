odoo.define('loan_management.amount_validation', function (require) {
    "use strict";

    var FieldChar = require('web.basic_fields').FieldChar;

    var AmountValidationField = FieldChar.extend({
        events: _.extend({}, FieldChar.prototype.events, {
            'input': '_onInput',
        }),

        _onInput: function (event) {
            // Récupérer la valeur du champ
            var value = this.$input.val();

            // Supprimer les caractères non numériques
            value = value.replace(/[^0-9]/g, '');

            // Limiter la longueur à 7 chiffres
            if (value.length > 7) {
                value = value.slice(0, 7);
            }

            // Empêcher les valeurs négatives
            if (value < 0) {
                value = 0;
            }

            // Limiter la valeur maximale à 1,000,000
            if (value > 1000000) {
                value = 1000000;
            }

            // Mettre à jour la valeur du champ
            this.$input.val(value);
        },
    });

    // Enregistrer le widget
    require('web.field_registry').add('amount_validation', AmountValidationField);

    return {
        AmountValidationField: AmountValidationField,
    };
});