function reqListener () {
	console.log(this.responseText);
}

function send_xhr(url, data, f) {
	if (f == undefined) {f = reqListener;}
	var xhr = new XMLHttpRequest();
	xhr.addEventListener("load", f);
	xhr.open("POST", url, true);
	xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
	xhr.send(data);
}

function mark(filename, flag, reason) {
    if (reason == undefined) {reason = Date.now();}
	var meta = {};
	meta[filename] = reason;
	send_xhr('/_flag/'+flag, JSON.stringify(meta), markback);
}

function markback() {
	var data = JSON.parse(this.responseText);
	for (var file in data) {
		var bt = document.getElementById(file+data[file][0]);
		if (data[file][1] == false) {bt.className = "";}
		else {bt.className = "on";}
	}
}

function rebuild_handler() {
	var data = JSON.parse(this.responseText);
	if (data.status == "success") {
		location.reload();
	} else {
		alert(data);
	}
}

function rebuild() {
	send_xhr('/rebuild', '', rebuild_handler)
}