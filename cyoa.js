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

function showNew() {
	if (this.responseText == undefined) {this.responseText = "{}";}
	var entries = JSON.parse(this.responseText);
	var cont = document.getElementsByClassName("container")[0];
	
	for (artist in entries) {
		cont.innerHTML += entries[artist];
		cont.innerHTML += '<input id="'+artist+'ip" type="number">\n';
		cont.innerHTML += '<button id="'+artist+'l8r" onclick="l8r(\'' + artist + '\')">l8r</button>\n';
		cont.innerHTML += '<br>\n';
	}
}

function getNew() {
	send_xhr('/cyoa', "{}", showNew);
}

function l8r(artist) {
	no = parseInt(document.getElementById(artist+'ip').value);
	mark(artist, 'l8r', no)
}