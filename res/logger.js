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
	lines = data.lines;
	
	if (data.output.length > 0) {
		gotNewLast = true;
		prev = "2000-01-01";// the past, hacky
		for (var l = 0; l < data.output.length; l++) {
			logOutput.push(data.output[l]);
			prev = drawLogLine(data.output[l], prev);
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
	
	meta = {
		"prog": document.getElementById("progName").innerHTML,
		"task": document.getElementById("taskName").innerHTML,
		"mod": 0,
		"has": lines,
		"level": level
	}
	console.log(meta);
	send_xhr("/logupdate", JSON.stringify(meta), updateListener)
	if (gotNewLast)
		wait = 1000;
	else
		wait += 500;
	
	var x = setTimeout(updateLog, Math.min(10000, wait));
}

function logDateParse(d) {
	return Date.parse(d.replace(",", "."));
}

function notDate(v) {
	return (v == " " || isNaN(v))
}

function drawLogLine(line, prev) {
	lo = document.getElementById("logOutput");
	if (line.length < 1) return
	
	if (notDate(line.charAt(0))) {// not a date probably
		row = lo.childNodes[lo.childElementCount - 1];
		row.innerHTML += '\n' + line;
		return row.innerHTML.split("\t")[0];
	}
	
	gap = "";
	dline = line.split("\t")[0];
	if (logDateParse(prev) + 1000 < logDateParse(dline))
		gap = " gap";
	
	linel = line.split("\t")[1];
	line = line.replace("\\t", "\t");
	lo.innerHTML += '<code class="log' + linel + gap + '">' + line + '</code>';
	return dline;
}

function drawLogInitReady() {
	prev = "";
	for (var l = 0; l < logOutput.length; l++) {
		prev = drawLogLine(logOutput[l], prev);
	}
}

function drawLogInit() {
	document.addEventListener('DOMContentLoaded', drawLogInitReady, false);
}

var x = setTimeout(updateLog, 1000);