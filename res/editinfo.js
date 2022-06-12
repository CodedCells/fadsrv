var fields = {
	"summary": {"type": "large_text"},
	"issues": {"type": "large_text"},
	"notes": {"type": "large_text"},
	"dummy": {"type": "text"},
	"filename": {"type": "multi_text"},
	"labels": {"type": "multi_text"},
	"rate_idea": {"type": "rating"},
	"rate_composition": {"type": "rating"},
	"rate_popularity": {"type": "rating"}
}

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

function noUnd(i) {
	if (typeof i == "undefined") return "";
	return i;
}

function edit(b) {
	b.setAttribute("onclick", "save(this)");
	b.innerHTML = "Save changes";
	
	var propsrc = document.getElementsByClassName("properties");
	if (propsrc.length > 0) {
		propsrc = propsrc[0].children;
		
		prop = 'AAAA';
		
		for (var c = 0; c < propsrc.length; c++) {
			pnl = prop.slice(0, -1).toLowerCase();
			text = noUnd(dat[pnl]);
			
			if (propsrc[c].className == "label")
				prop = propsrc[c].innerHTML;
			
			else if (propsrc[c].className == "value") {
				propsrc[c].innerHTML = '<input id="' + pnl + '" class="niceinp" value="' + text + '">';
			}
			else if (propsrc[c].className == "valuebox") {
				var rows = Math.max(4, text.split('\n').length);
				propsrc[c].innerHTML = '<textarea id="' + pnl + '" class="niceinp" style="width:100%;" cols="60" rows="' + rows + '">' + text + '</textarea>';
			}
		}
	
	}
}

function save(b) {
	b.setAttribute("onclick", "");
	b.innerHTML = "Reading changes...";
	
	newdat = {}
	
	var propsrc = document.getElementsByClassName("properties");
	if (propsrc.length > 0) {
		propsrc = propsrc[0].children;
		prop = null;
		
		for (var c = 0; c < propsrc.length; c++)
			
			if (propsrc[c].className == "value") {
				i = propsrc[c].children[0];
				value = noUnd(i.value);
			}
			else if (propsrc[c].className == "valuebox")
				i = propsrc[c].children[0];
				value = noUnd(i.innerHTML);
			
			else
				continue;
			
			if (value.length == 0)
				continue;
			
			f = fields[i.id];
			if (f.type == "multi_text" && value.includes(","))
				value = value.split(",");
			
			newdat[i.id] = value;
	}
	
	b.innerHTML = "Saving...";
	
	newdat = JSON.stringify(newdat)
	
	send_xhr("/edit-" + editType + "/" + iAm, newdat, pRHandler)
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

function postReload() {
    send_xhr("/rebuild", '', pRHandler);
}

var newType = ""
var newName = ""

function makeNew(ty) {
	newType = ty;
	newName = document.getElementById("name").value;
	newdat = JSON.stringify({
		"name": newName,
		"new": true
		});
	send_xhr("/edit-" + ty + "/" + newName, newdat, makeNewBack)
}

function makeNewBack() {
    var data = JSON.parse(this.responseText);
    if (data.status == "success") {
        window.location.href = "/" + newType + "_" + newName.replaceAll(" ", "_");
    } else {
        console.log(data);
        alert(data.message);
    }
}