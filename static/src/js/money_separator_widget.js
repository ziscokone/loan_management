/** @odoo-module **/
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";

class CustomFormController extends FormController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async _onButtonClicked(params) {
        const { name, type } = params;
        if (name === "dummy_action" && type === "object") {
            console.log("Mon script personnalisé est exécuté !");
            this.notification.add("Action personnalisée exécutée", { type: "success" });
            // Votre code JavaScript ici
            return;
        }
        // Pour les autres boutons, appeler la méthode originale
        return super._onButtonClicked(params);
    }
}

// Enregistrer le contrôleur personnalisé
registry.category("views").add("mon_formulaire_js", {
    ...registry.category("views").get("form"),
    Controller: CustomFormController,
});