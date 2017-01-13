var separator = $('<div class="demo-separator mdl-cell--1-col"></div>')
var s = '  <div class="mdl-list__item attribute-list-item template">    <div class=".mdl-list__item-primary-content">    <form action="#">      <div class="mdl-textfield mdl-js-textfield">        <input class="mdl-textfield__input attribute-title" type="text" id="sample1">        <label class="mdl-textfield__label" for="sample1">Text...</label>      </div>    </form>    </div>    <span class="mdl-list__item-secondary-content">      <a class="mdl-list__item-secondary-action delete-attribute" href="#"><i class="material-icons">star</i></a>    </span>  </div>'

var attributeListItemTemplate = $(s)

var processes = []
var currentAttributes = []
var attributesLoaded = false
var selectedProcess = -1

var saving = false

$(document).ready(function () {

	initMomos()
	setup()

	var nameMomo = makeMomo("process", {}, "name", true, false)
	var codeMomo = makeMomo("process", {}, "code", true, false)

	nameMomo.data()["save"] = saveProcess
	codeMomo.data()["save"] = saveProcess

	$(".processForm").append(nameMomo).append(codeMomo)

	$(".processForm").clone(true, true).removeClass("processForm").addClass("new-process-form").appendTo(".appendHere").hide()
	$(".new-process-form h2").text("New Process")


	getProcesses(function () {
		reloadProcessView()
		$(".process-list-item").eq(0).click()
	}, function () {})

	$(".process-list-item").click(function (e) {
		e.preventDefault()

		// if you selected the same thing again then dont do anything
		var select = parseInt($(this).attr("id"))
		if (selectedProcess == select) 
			return

		var p = $(this)

		showContinueDialog(function () {
			saving = false
			selectedProcess = select
			clickOnProcess(p)
		})
	})

	$(".add-attribute").mousedown(function (e) {
		e.preventDefault()

		if ($(".new-momo").length == 0) 
			addAttribute()
	})


})


var deleteAttribute = function (data, callback, failure) {
  showAreYouSureDialog("Are you sure you want to delete this attribute?", 
  	"You'll also be deleting it for ALL the tasks!", 
  	function () {
  		saving = true

  		$.ajax("../ics/attributes/" + data.id + "/", {
			method: "DELETE",
		}).done(function (data) {
			if (!saving) return
			callback()
		}).fail(function (data, res, error) {
			if (!saving) return
			failure()
			showError("Something went wrong", "Looks like something isn't working. Try again later.")
		}).always(function () {
			saving = false
		})
  	}, failure)
}


var saveAttribute = function (data, callback, failure) {
  showAreYouSureDialog("Are you sure you want to edit this attribute?", 
  	"You'll also be editing it for ALL the tasks!", 
  	function () {
  		saving = true

  		$.ajax("../ics/attributes/" + data.id + "/", {
			method: "PUT",
			data: data
		}).done(function (data) {
			if (!saving) return
			callback()
		}).fail(function (data, res, error) {
			if (!saving) return
				failure()
			showError("Something went wrong", "Looks like something isn't working. Try again later.")
		}).always(function () {
			saving = false
		})
  	}, failure)
}

var createAttribute = function (data, callback, failure) {
	saving = true

	$.ajax("../ics/attributes/", {
		method: "POST",
		data: data
	}).done(function (data) {
		if (!saving) return
		callback(data)
	}).fail(function (data, res, error) {
		if (!saving) return
		failure()
		showError("Something went wrong", "Looks like something isn't working. Try again later.")
	}).always(function () {
		saving = false
	})
}

var saveProcess = function (data, callback, failure) {
	saving = true 

	$.ajax("../ics/processes/" + data.id + "/", {
		method: "PUT",
		data: data
	}).done(function (data) {
		if (!saving) return
		refreshProcess(data)
		callback()
	}).fail(function (data, res, error) {
		if (!saving) return
		failure()
		showError("Something went wrong", "Looks like something isn't working. Try again later.")
	}).always(function () {
		saving = false
	})
}

function collectData(momo) {
}

function getProcesses(success, failure) {
	processes = []
	$.get("../ics/processes")
		.done(function (data) {
			processes = data
			success()
		})
		.fail(function () {
			showError("Something went wrong", "Looks like something isn't working. Try again later.")
		})
}

function getAttributes(id, success, failure) {

	attributes = []
	attributesLoaded = false

	$("#attribute-list").empty()

	$.get("../ics/attributes/?process_type=" + id)
		.done(function (data) {
			success(data)
			componentHandler.upgradeDom()
		})
		.fail(function () {
			attributesLoaded = false
			showError("Something went wrong", "Looks like something isn't working. Try again later.")
		})
}


function upgrade(jq) {
	componentHandler.upgradeElement(jq.eq(0));
}


//---------------------------------------------

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}


function setup() {

	var csrftoken = getCookie('csrftoken');

	$.ajaxSetup({
    	beforeSend: function(xhr, settings) {
        	if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            	xhr.setRequestHeader("X-CSRFToken", csrftoken);
        	}
    	}
	})
}