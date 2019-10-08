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

function set () {
	if (this.responseText == undefined) {this.responseText = "{}";}
	var entries = JSON.parse(this.responseText);
	var cont = document.getElementsByClassName("container")[0];
	cont.innerHTML = "<h2>" + Object.keys(entries).length + " result(s).</h2><br>"
	
	for (artist in entries) {
		cont.innerHTML += entries[artist];
	}
}

function search() {
	var query = document.getElementsByTagName("input")[0].value;
	if (query.length == 0) {set();return;}
	var meta = {"query": query}
	send_xhr('/search', JSON.stringify(meta), set);
}

window.onload = function() {
	search();
}