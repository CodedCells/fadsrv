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

function pRHandler() {
	var data = JSON.parse(this.responseText);
	if (data.status == "success") {
		location.reload();
	} else {
		console.log(data);
		alert(data.message);
	}
}

function postReload(addr, ctn) {
	send_xhr(addr, ctn, pRHandler);
}

function showCYOA() {
	if (this.responseText == undefined) {this.responseText = "{'artists': {}}"}
	var entries = JSON.parse(this.responseText);
	if (entries['results'] == 0) {return;}
	var cont = document.getElementsByClassName("container")[0];
	cont.innerHTML = "<h2>Unknown Length (" + entries['results'] + ")</h2>";
	entries = entries['artists'];
	
	for (artist in entries) {
		e = '<div class="thumbw">'
		e += entries[artist];
		e += '<input class="niceinp" id="'+artist+'ip" type="number">\n';
		e += '<button id="'+artist+'l8r" onclick="l8r(\'' + artist + '\')">l8r</button>\n';
		e += '</div>\n';
		cont.innerHTML += e;
	}
}

function getCYOA(count) {
	send_xhr('/cyoa', JSON.stringify({"count": count}), showCYOA);
}

function l8r(artist) {
	no = parseInt(document.getElementById(artist+'ip').value);
	mark(artist, 'l8r', no)
}

function set() {
	if (this.responseText == undefined) {this.responseText = "{}";}
	var entries = JSON.parse(this.responseText);
	var cont = document.getElementsByClassName("container")[0];
	cont.innerHTML = "<h2>" + Object.keys(entries).length + " result(s).</h2><br>"
	
	for (artist in entries) {
		cont.innerHTML += entries[artist];
	}
}

function search(force) {
	var query = document.getElementsByTagName("input")[0].value.toLowerCase();
	if (query.length < 3 && !(force))
		return;
	if (query.length == 0) {set();return;}
	var meta = {"query": query}
	send_xhr('/search', JSON.stringify(meta), set);
}
