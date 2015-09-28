$(function(){
    if (window.location.hash) {
        hash = window.location.hash;
        hashlist = hash.split('_', 2);
        expand_methods(hashlist[0]);

        if (hashlist[1]) {
            load_handler(hash);
        }
        else {
            divlist = $(".handlerdiv")
            for (var i = 0; i < divlist.length; i++) {
                tempvar = '#' + divlist[i].id;
                if (tempvar.indexOf(hashlist[0]) === 0) {
                    load_handler(tempvar);
                    i = divlist.length;
                }
            }
        }
    }
});
var current_viewed = '';
var current_expanded = '';
var value_factory = {

    random_email: function(){
        var ret = '';
        for (var i = 0; i < 5; i++) {
            ret += get_random_letter();
        }
        ret += '@'
        for (var i = 0; i < 5; i++) {
            ret += get_random_letter();
        }
        ret += ".com"
        return ret
    }

}
function prep_params(params){
    ret = {};
    for (key in params) {
        if (params.hasOwnProperty(key)) {
            if (is_template(params[key])) {
                ret[key] = value_factory[params[key].replace(/%/g, '')]()
            }
            else {
                ret[key] = params[key]
            }
        }
    }
    return ret;
}

function is_template(value){
    return value[0] == "%" && value[value.length - 1] == "%"

}


function login(callback){
    var callback = callback ||
    function(){
    };
    var params;
    var test;
    var links = $(".test_link");
    for (var i = 0; i < links.length; i++) {
        var elem = links[i];
        if ($(elem).attr('auth_test')) {
            test = JSON.parse($(elem).attr('test_data'))
            params = test.params
        }
    }
    if (TEST_USER.username && TEST_USER.password) {
        params = TEST_USER;
    }
    $.ajax({
        url: test.path,
        data: params,
        type: test.method,
        complete: function(){
            callback();
        }
    })
}

function is_logged_in(){
    return document.cookie.indexOf('sessionid=') !== -1
}

function get_random_letter(){
    var letters = 'abcdefghijklmnopqrsqtuvwxyz';
    return letters[Math.floor(Math.random() * 26)]
}

function create_test(handler, method){
    var form = $("#" + handler + method + "_form :input[value]")
    var url = $("#" + handler + method + "_url").val();
    var data;
    var headers = {};
    for (var i=0;i<form.length;i++){
        if(form[i].name === "body"){
            data = $(form[i]).val();
            headers['Content-Type'] = "application/json";
        }
    }
    if (!data){
        data = form.serialize();
    }

    $.ajax({
        url: url,
        data: data,
        type: method,
        headers: headers,
        complete: function(response){
            var result_div = '#' + handler + method + "_response_div";
            var close_control_id = handler + method + "_X";
            if (response.getResponseHeader('content-type').indexOf('xml') != -1) {
                var data = formatXML(response.responseText);
            }
            else {
                var data = response.responseText;
            }
            var html = "<span class='closing_x' id='" + close_control_id + "';'>Hide X</span>";
            html += "Result: <br /><pre>" + data + "</pre>";
            $(result_div).show();
            $(result_div).html(html);
            $("#" + close_control_id).click(function(){
                $(result_div).toggle();
            })
        }
    })
}

function load_handler(div_id){
    if (current_viewed != '') {
        $(current_viewed).hide();
        current_viewed = '';
    }
    $(div_id).show();
    current_viewed = div_id;
}

function expand_methods(handler){
    var div_id = handler + "_methods";
    if (div_id == current_expanded) {
        return;
    }
    if (current_expanded != '') {
        $(current_expanded).slideUp(100);
        current_expanded = '';
    }
    $(div_id).slideDown(100);
    current_expanded = div_id;

    var divlist = $(".handlerdiv");
    for (var i = 0; i < divlist.length; i++) {
        var tempvar = '#' + divlist[i].id;
        if (tempvar.indexOf(handler) === 0) {
            load_handler(tempvar);
            i = divlist.length;
        }
    }
    window.location.hash = handler;
}

function formatXML(string){
    return string.replace(/>/g, "&gt;").replace(/</g, "&lt;");

}
