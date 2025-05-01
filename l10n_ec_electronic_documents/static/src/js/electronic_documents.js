odoo.define("l10n_ec_electronica_documents.unreconcile_validation", function (require) {
    "use strict";
    var account = require("account.payment");
    var Dialog = require("web.Dialog");

    /**
     * Allows to validate the reconciliation from invoice to credit note and vice versa.
     */
    account.ShowPaymentLineWidget.include({
        _onRemoveMoveReconcile: async function (event) {
            var self = this;
            var moveId = parseInt($(event.target).attr("move-id"), 10);
            var partialId = parseInt($(event.target).attr("partial-id"), 10);

            var superFunction = this._super;
            var res = await this._rpc({
                model: "account.move",
                method: "js_validate_unreconcile",
                args: [moveId, partialId],
            }).then(function (data) {
                return data;
            });

            // If authorized is True, dont let unreconcile
            if (res) {
                Dialog.alert(
                    "Validation Error",
                    "You can not unreconcile movements that have been already authorized."
                );
            } else {
                superFunction.apply(self, arguments);
            }
        },
    });
});
