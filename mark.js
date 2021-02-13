function reqListener () {
	console.log(this.responseText);
}

function send_xhr(url, data, f) {
	console.log(data);
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
	for (var item in data) {
		console.log(item, data[item]);
		var bt = document.getElementsByName(item + "@" + data[item][0]);
		
		for (var b = 0; b < bt.length; b++) {
			if (data[item][1] == false) 
				{bt[b].classList.remove("on");
			}
			else {
				bt[b].classList.add("on");
			}
		}
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

function populateSearch() {
	var srl = searchResult.length;
	var last = Math.ceil(srl / listCount);
	
	var head = document.getElementsByClassName("head")[0];
	head.innerHTML = "";
	if (srl > listCount) {
		if (page > 1)
			head.innerHTML += '<a class="btn" onclick="page-=1;populateSearch();">&lt;</a>';
		else
			head.innerHTML += '<a class="btn" onclick="page='+last+';populateSearch();">&gt;|</a>';
	}
	head.innerHTML += '<h2 class="btn wide">Search - ' + page + '</h2>';
	if (srl > listCount) {
		if (page < last)
			head.innerHTML += '<a class="btn" onclick="page+=1;populateSearch();">&gt;</a>';
		else
			head.innerHTML += '<a class="btn" onclick="page=1;populateSearch();">|&lt;</a>';
	}
	document.getElementsByClassName("foot")[0].innerHTML = head.innerHTML;
	
	var cont = document.getElementsByClassName("container")[0];
	cont.innerHTML = "<h2>" + searchResult.length + " result(s</h2><br>"
	
	for (var c = 0; c < listCount; c++) {
		var r = c + (page-1)*listCount;
		if (searchResult[r] == undefined) break;
		cont.innerHTML += searchResult[r];
	}
}

var searchResult = [];
var searchItems = []
function searchBack() {
	if (this.responseText == undefined) {this.responseText = "{'result': []}";}
	searchResult = JSON.parse(this.responseText).result;
	searchItems = JSON.parse(this.responseText).items;
	page = 1;
	populateSearch();
}

function search(force) {
	var query = document.getElementById("searchbar").value.toLowerCase();
	var tof = document.getElementById("searchOF").value.toLowerCase();
	
	if (query.length < 3 && !(force))
		return;
	
	if (query.length == 0) {
		return;
	}
	var meta = {"query": query, "of": tof}
	send_xhr('/search', JSON.stringify(meta), searchBack);
}

function cfg(key) {
	ele = document.getElementById(key);
	console.log(ele.type);
	if (ele.type == "checkbox") value = ele.checked;
	else if (ele.type == "number") value = parseInt(ele.value);
	else {alert("UNHANDLED INPUT TYPE: " + ele.type); return}
	mark(key, 'cfg', value);
}

sets = [];
svcon = undefined;
setsFor = null;
closeAfterSetMark = true;
searchQ = "";

function populateSets() {
	var setl = document.getElementById("sets-list");
	setl.innerHTML = "";
	
	for (var pos in sets) {
		if (searchQ != "") {
			if (!(sets[pos][0].toLowerCase().includes(searchQ))) {
				continue// don't list unmatching
			}
		}
		var nbtn = document.createElement("BUTTON");
		nbtn.id = "status"+sets[pos][0];
		nbtn.className = "mbutton item";
		if (sets[pos][2] == true) {nbtn.className += " on";}
		var sym = "";
		if (sets[pos][3] == true) {sym += "&#x1F512;";}
		else {nbtn.onclick = setMarkMagic;}
		nbtn.innerHTML = sets[pos][0] + "<span>" + sets[pos][1] + sym + "</span>";
		setl.appendChild(nbtn);
	}
}

function setsGet(file, loco) {
svcon = loco;
	bt = document.getElementsByName(file + "@"+svcon);
	
	for (var b = 0; b < bt.length; b++) {
		bt[b].classList.add("disabled");
		//bt[b].style.backgroundPositionX = (-bt[b].offsetWidth * 8).toString() + "px";
	}
	
	setsFor = file;
	var meta = {"query": file, "con": svcon};
	send_xhr('/sets/for', JSON.stringify(meta), setsGetBack);
}

function setsGetBack() {
	var data = JSON.parse(this.responseText);
	sets = data["sets"];
	bt = document.getElementsByName(setsFor + "@"+svcon);
	
	for (var b = 0; b < bt.length; b++) {
		bt[b].classList.remove("disabled");
		//bt[b].style.backgroundPositionX = (-bt[b].offsetWidth * 7).toString() + "px";
	}
	
	var setl = document.getElementById("sets-man");
	setl.className = "";
	
	populateSets();
}

function setsClose() {
	var setl = document.getElementById("sets-man");
	setl.className = "hidden";
	
	var setl = document.getElementById("sets-list");
	setl.innerHTML = "BLANKED";
}

function setsNewBack() {
	var data = JSON.parse(this.responseText);
	if (data.status == "success") {
		var name = document.getElementById("setsName").value;
		sets = [[name, 0, false]].concat(sets);
		document.getElementById("setsName").value = "";
		setSearch();
	}
}

function setsNew() {
	var name = document.getElementById("setsName").value;
	var fail = false;
	if (name == "") {fail = true;}
	for (var pos in sets) {
		if (sets[pos][0].toLowerCase() == name.toLowerCase()) {
			fail = true;
			break;
		}
	}
	if (!(fail)) {
		var meta = {"name": name, "time": Date.now(), "con": svcon};
		send_xhr('/sets/new', JSON.stringify(meta), setsNewBack);
	}
}

function setMarkMagic() {
	var flag = this.innerHTML.split("<span>")[0];
	setMark(setsFor, flag);
}

function setMarkBack() {
	var data = JSON.parse(this.responseText);
	
	for (var file in data) {
		var bt = document.getElementById(file+data[file][0]);
		
		var bt = document.getElementById(file+data[file][0]);
		var c = parseInt(bt.children[0].innerHTML);
		if (data[file][1]) {
			bt.classList.add("on");
			c += 1
		} else {
			bt.classList.remove("on");
			c -= 1
		}
		
		bt.children[0].innerHTML = c;
		
		amMarked = false;
		for (var pos in sets) {
			if (sets[pos][0] == data[file][0]) {
				sets[pos][1] = c;
				sets[pos][2] = data[file][1];
			}
			
			amMarked = amMarked || sets[pos][2];
		}
		
		var bt = document.getElementsByName(setsFor + "@" + svcon);
		for (var b = 0; b < bt.length; b++) {
			if (amMarked)
				bt[b].classList.add("on");
			else
				bt[b].classList.remove("on");
		}
	}
	if (closeAfterSetMark) {
		setsClose();
	}
}

function setMark(file, flag) {
	var meta = {
		"flag": flag,
		"file": file,
		"con": svcon,
		"time": Date.now()
	};
	send_xhr('/sets/_flag', JSON.stringify(meta), setMarkBack);
}

function setsProp(name, prop) {
	var meta = {
		"name": name,
		"prop": prop,
  "con": con,
		"time": Date.now()
	}
	send_xhr('/sets/prop', JSON.stringify(meta), markback);
}

function setDelete(name) {
	if (confirm("Delete \"" + name + "\" permanently?")) {
		alert("Deleted");
		setsProp(name, "delete");
	} else {console.log("Nuclear Crisis Averted");}
}

function setSearch() {
	searchQ = document.getElementById("setsName").value.toLowerCase();
	populateSets();
}

var popdownState = false;
function popdown() {
	if (popdownState) {
		document.getElementById("popdown").className = "up";
		document.getElementById("popdownbtn").className = "mbutton up";
		document.getElementById("popdownbtn").innerHTML = "&#x1F53B;";
	} else {
		document.getElementById("popdown").className = "down";
		document.getElementById("popdownbtn").className = "mbutton down";
		document.getElementById("popdownbtn").innerHTML = "&#x1F53A;";
	}
	popdownState = !(popdownState);
}

function editMenu(menuname) {
	var data = menudata[menuname];
	console.log(data);
	document.getElementsByName("title")[0].value = data.title;
	document.getElementsByName("item-style")[0].value = data.mode;
	
	var elemItems = document.getElementById("items");
	elemItems.innerHTML = "";
	for (var i = 1; i < data.items.length+1; i++) {
		var item = data.items[i-1];
		elemItems.innerHTML += '<label for="item-'+i+'-link">Link '+i+'<br><input name="item-'+i+'-link" class="niceinp" value="'+item.href+'"></label>';
		elemItems.innerHTML += '<label for="item-'+i+'-label">Label '+i+'<br><input name="item-'+i+'-label" class="niceinp" value="'+item.label+'"></label>';
		if (data.mode.includes("icons")) {
			var x = item.x*-60;
			var y = item.y*-60;
			elemItems.innerHTML += '<button id="'+menuname+i+'" class="iconsheet" style="background-position: '+x+'px '+y+'px;" onclick="editIcon(\''+menuname+i+'\', '+item.x+', '+item.y+')"></button>';
		}
		elemItems.innerHTML += '</br>';
	}
}

function editIcon(eid, x, y) {
	console.log(eid);
	sidiv = document.getElementById("selectIcon");
	sidiv.style.display = "block";
	for (var cy = 0; cy < 9; cy++) {
		for (var cx = 0; cx < 9; cx++) {
			if (x == cx && y == cy) {
				sidiv.children[cx+(cy*10)].style.backgroundColor = "#c00";
			} else {
				sidiv.children[cx+(cy*10)].style.backgroundColor = null;
			}
		}
	}
}

function useIcon(x, y) {
	
}

function createMenu(failed) {
	var menuid = prompt("Menu technical id:").toLowerCase();
	if (menuid == null || menuid == "") {return;}
	console.log(menuid);
}

function aprefAllRead(a) {
	for (var i = 0; i < posts.length; i++) {
		aprefMagic(a, posts[i]);
	}
}

function addAllToSet(setid, f) {
	for (var i = 0; i < f.length; i++) {
		setMark(f[i], setid);
	}
}

function folderToSetMakeBack() {
	svcon = "sets";
	var data = JSON.parse(this.responseText);
	if (data.status == "success") {
		addAllToSet(defaultSetName, posts);
	} else {
		folderToSet("Nah fam, give it a differeent name")
	}
}

function folderToSet(pr) {
	defaultSetName = title = prompt(pr, defaultSetName);
	if (title == null) {return;}
	var meta = {"name": defaultSetName, "time": Date.now(), "con": "sets"};
	send_xhr('/sets/new', JSON.stringify(meta), folderToSetMakeBack);
}

function aprefMagic(a, provided) {
	p = a.parentElement;
	
	thing = p.getAttribute("name").split('@');
	mark = thing.splice(-1,1)[0];
	thing = thing.join('@');
	
	console.log(thing, mark);
	
	if (p.children.length > 1)
		value = p.children[1].value
	else {
		thing = thing.split('@');
		value = thing.splice(-1,1)[0];
		thing = thing.join('@');
		
		if (p.className.includes(" on"))
			value = null;
	}
	
	if (value == "") {
		value = null;
	}
	
	if (provided != undefined)
		thing = provided;
	
	var meta = [
		[thing, value, Date.now()]
	];
	
	send_xhr('/_apref/'+mark, JSON.stringify(meta), aprefBack);
}

function aprefBack() {
	var data = JSON.parse(this.responseText);
	for (var item in data) {
		console.log(item, data[item]);
		target = item + "@" + data[item][1] + "@" + data[item][0];
		var bt = document.getElementsByName(item + "@" + data[item][0]);
		if (bt.length < 1)
			continue;
		
		for (var b = 0; b < bt.length; b++) {
			if (bt[b].tagName.toLowerCase() == "span") {
				ct = bt[b].children;
				for (var c = 0; c < ct.length; c++) {
					if (ct[c].getAttribute("name") == target)
						ct[c].classList.add("on");
					else
						ct[c].classList.remove("on");
				}
			} else {
				if (data[item][1] == null) {
					bt[b].classList.remove("on");
					bt[b].children[1].value = "";
				}
				else {
					bt[b].classList.add("on");
					bt[b].children[1].value = data[item][1];
				}
			}
		}
	}
}

function menuEdit() {
	var mb = document.getElementsByClassName("menubtn");
	for (var m = 0; m < mb.length; m++) {
		console.log(mb[m].getAttribute("name"));
	}
}