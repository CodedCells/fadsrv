var gotNewLast = true;
var wait = 1000;
var mod = 0;

var progress_score = 0;
var progress_goal = 0;

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
	//console.log(meta);
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

function progressUpdate() {
	var progressbar = document.getElementById("taskProgress");
	
	if (progressbar == null) {// new bar
		cont = document.getElementById("fileinfo");
		var perca = document.createElement("span");
        perca.id = "taskProgressCount";
		cont.appendChild(perca);
		
		var percb = document.createElement("progress");
        percb.id = "taskProgress";
        percb.style = "width:80%;";
		cont.appendChild(percb);
		
		progressbar = document.getElementById("taskProgress");
		progressbar.value = progress_score;
	}
	
	progressco = document.getElementById("taskProgressCount")
	progressco.innerHTML = " - " + progress_score + " of " + progress_goal;
	
	progressbar.max = progress_goal;
	if (progress_score >= progress_goal)
		progressbar.value = progress_score;
}

function isNum(val) {// js is bad
	return !isNaN(val)
}

function progressMeasure(line) {
	line = line.split("\t")[2];
	out = line.split(" ");
	if (line.startsWith("Adding ")) {
		ld = line.split(" ")[1];
		if (isNum(ld))
			if (parseInt(ld) < 1000)
				progress_goal += parseInt(ld) * 2;
	}
	else if (["ADDGOAL", "ADDSCORE", "SETGOAL", "SETSCORE"].includes(out[0])) {
		val = isNum(out[1]);
		if (!val) return;// no val
		
		if (out[0] == "ADDGOAL")
			progress_goal += val;
		else if (out[0] == "ADDSCORE")
			progress_score += val;
		
		else if (out[0] == "SETGOAL")
			progress_goal = val;
		else if (out[0] == "SETSCORE")
			progress_score = val;
	}
	
	if (progress_goal < 1) return;
	
	if (line.startsWith("get ") || line.startsWith("COPY")) {
		progress_score += 1;
	}
	
	progressUpdate()
}

function progressAnim() {
	if (progress_score == 0) return
	
	var progressbar = document.getElementById("taskProgress");
	
	if (progressbar.value < progress_score)
		progressbar.value += 0.1;
	
	if (progressbar.value+1 < progress_score)
		progressbar.value += 0.4;
	
	if (progressbar.value+10 < progress_score)
		progressbar.value += .5;
	
	if (progressbar.value+20 < progress_score)
		progressbar.value += 1;
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
	
	progressMeasure(line);
	
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
var p = setInterval(progressAnim, 33);
