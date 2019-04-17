$(document).ready(function () {
    var $signContract = $("#submitBtn");
    var contract = $('#contract').data();

    var $sigdiv = $("#signature")
    $sigdiv.jSignature();
    $sigdiv.jSignature("reset")

    $signContract.on("click", function () {
        var sign = $sigdiv.jSignature("getData")
        var signee = document.getElementById("signee").value;
        if (sign && signee) {
            frappe.call({
                method: "erpnext.crm.doctype.contract.contract.sign_contract",
                args: {
                    signee: signee,
                    contract: contract.contractname,
                    sign: sign,
                    token: "{{ contract.token }}"
                },
                freeze: true,
                callback: function (r) {
                    if (!r.exc) {
                        location.reload(forcedReload=true);
                    }
                    else {
                        frappe.msgprint(r.exc)
                    }
                }
            })
        }
    });
})