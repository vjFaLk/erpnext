$(document).ready(function () {
    var $renewBtn = $("#renewButton");
    var $sigdiv = $("#signature");
    if($sigdiv.length > 0)
    {
        $sigdiv.jSignature();
        $sigdiv.jSignature("reset");
    }
    $renewBtn.on("click", function () {
        frappe.call({
            method: "erpnext.crm.doctype.contract.contract.reset_token",
            args: {
                contract_name: "{{ contract.name }}",
                email: "{{ contract.email }}"
            },
            callback: function (r) {
                if (r.exc) {
                    frappe.msgprint(r.exc);
                }
            }
        })
    });

    $(".nav-item, .nav-item .nav-link").on('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
    })

    $("#step1").on("click", function () {
        $("#review").addClass("active show in");
        $("#about").removeClass("active show in");
        $(".nav-item a.review-sign, #review").addClass("active show");
        $(".nav-item a.about, #about").removeClass("active show");
        $(".modal-backdrop.fade.show").hide();
        $(window).trigger("resize"); // Ugly hack to make JSignature work
    });

    $("#step2").on("click", function () {
        var sign = $sigdiv.jSignature("getData");
        var signee = document.getElementById("signee").value;

        if (!($sigdiv.jSignature('getData', 'native').length == 0) && signee) {
            frappe.call({
                method: "erpnext.crm.doctype.contract.contract.sign_contract",
                args: {
                    signee: signee,
                    contract: "{{ contract.name }}",
                    sign: sign,
                    token: "{{ contract.token }}",

                },
                freeze: true,
                callback: function (r) {
                    $("#confirm").addClass("active show in");
                    $("#review").removeClass("active show in");
                    $(".nav-item a.confirmation").addClass("active show");
                    $(".nav-item a.review-sign").removeClass("active show not-visited");
                    $(".modal-backdrop.fade.show").hide();
                }
            })
        }
        else{
            alert('Please enter Sign and Signee ');
         }
    });

    $("#popup-generator").on("click", function () {
        $(".modal-backdrop").show();
    });


    $(document).on('click touch', function (event) {
        if (!$(event.target).parents().addBack().is('#popup-generator')) {
            $('.modal-backdrop').hide();
        }
    });

});