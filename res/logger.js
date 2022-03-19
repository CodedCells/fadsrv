var gotNewLast = true;
var wait = 1000;
var mod = 0;

function reqListener() {
    console.log(this.responseText);
}

function send_xhr(url, data, f) {
    //console.log(data);
    if (f == undefined) {
        f = reqListener;
    }
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", f);
    xhr.open("POST", url, true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
    xhr.send(data);
}

function updateListener() {
	var data = JSON.parse(this.responseText);
	//console.log(data);
	if (data.old)
		document.getElementById("fileinfo").innerHTML += ' - <span id="isOld">Old</span>';
	
	mod = data.mod;
	
	if (data.lines.length > 0) {
		gotNewLast = true;
		for (var l = 0; l < data.lines.length; l++) {
			logOutput.push(data.lines[l]);
			drawLogLine(data.lines[l]);
		}
	} else {
		gotNewLast = false;
	}
}

function updateLog() {
	if (document.body.contains(document.getElementById("isOld"))) {
		console.log("Old, no refresh");
		return;
	}
	
	lines = logOutput.length;
	
	meta = {
		"prog": document.getElementById("progName").innerHTML,
		"task": document.getElementById("taskName").innerHTML,
		"mod": 0,
		"has": lines
	}
	console.log(meta);
	send_xhr("/logupdate", JSON.stringify(meta), updateListener)
	if (gotNewLast)
		wait = 1000;
	else
		wait += 500;
	
	var x = setTimeout(updateLog, Math.min(10000, wait));
}

function drawLogLine(line) {
	lo = document.getElementById("logOutput");
	if (line.length < 1) return
	
	if (isNaN(line.charAt(0))) {// not a date probably
		row = lo.childNodes[lo.childElementCount - 1];
		row.innerHTML += '\n' + line;
		return;
	}
	
	level = line.split("\t")[1];
	line = line.replace("\\t", "\t");
	lo.innerHTML += '<code class="log' + level + '">' + line + '</code';
}

function drawLogInitReady() {
	for (var l = 0; l < logOutput.length; l++) {
		drawLogLine(logOutput[l]);
	}
}

function drawLogInit() {
	document.addEventListener('DOMContentLoaded', drawLogInitReady, false);
}

var x = setTimeout(updateLog, 1000);