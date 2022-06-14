function reqListener() {
	console.log(this.responseText);
}

function send_xhr(url, data, f) {
	console.log(data);
	if (f == undefined) {
		f = reqListener;
	}
	var xhr = new XMLHttpRequest();
	xhr.addEventListener("load", f);
	xhr.open("POST", url, true);
	xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
	xhr.send(data);
}

function mark(filename, flag, reason) {
	if (reason == undefined) {
		reason = Date.now();
	}
	var meta = {};
	meta[filename] = reason;
	send_xhr('/_flag/' + flag, JSON.stringify(meta), markback);
}

function markback() {
	var data = JSON.parse(this.responseText);
	for (var item in data) {
		console.log(item, data[item]);
		var bt = document.getElementsByName(item + "@" + data[item][0]);

		for (var b = 0; b < bt.length; b++) {
			if (data[item][1])
				bt[b].classList.add("on");
			else
				bt[b].classList.remove("on");
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

function postReload(e, addr) {
	send_xhr(addr, '', pRHandler);
	
	console.log(e);
	e.classList.add("on");
	c = e.parentElement.children;
	
	for (var i = 0; i < c.length; i++) {
		c[i].classList.add("disabled");
	}
	c = document.getElementsByClassName("markbutton")
	for (var i = 0; i < c.length; i++) {
		c[i].classList.add("disabled");
	}
	
	document.getElementById("rebuildLoad").classList.remove("hide");
}

function searchBut (nm, ns, nt) {
	return '<a class="btn ' + nm + '" onclick="page' + ns + ';populateSearch();">' + nt + '</a>';
}

function populateSearch() {
	var srl = searchResult.length;
	var last = Math.ceil(srl / listCount);

	var head = document.getElementsByClassName("head")[0];
	head.innerHTML = "";
	if (srl > listCount) {
		if (page > 1)
			head.innerHTML += searchBut("nav-prev", "-=1", "&lt;");
		else
			head.innerHTML += searchBut("nav-last", "=" + last, "&gt;|");
	}
	head.innerHTML += '<h2 class="pagetitle">Search - ' + page + '</h2>';
	if (srl > listCount) {
		if (page < last)
			head.innerHTML += searchBut("nav-next", "+=1", "&gt;");
		else
			head.innerHTML += searchBut("nav-first", "=1", "|&lt;");
	}
	document.getElementsByClassName("foot")[0].innerHTML = head.innerHTML;

	var cont = document.getElementsByClassName("container")[0];
	var stat = "<h2>" + searchResult.length + " result";
	if (searchResult.length != 1) stat += "s"
	cont.innerHTML = stat + "</h2><br>";

	for (var c = 0; c < listCount; c++) {
		var r = c + (page - 1) * listCount;
		if (searchResult[r] == undefined) break;
		cont.innerHTML += searchResult[r];
	}
}

var searchResult = [];
var searchItems = []

function searchBack() {
	if (this.responseText == undefined) {
		this.responseText = "{'result': []}";
	}
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
	var meta = {
		"query": query,
		"of": tof
	}
	send_xhr('/search', JSON.stringify(meta), searchBack);
}

function cfg(key, mode) {
	ele = document.getElementById(key);
	console.log(ele.type);
	if (ele.type == "checkbox") value = ele.checked;
	else if (ele.type == "number") value = parseInt(ele.value);
	else if (ele.type == "text") value = ele.value;
	else {
		alert("Undhandled input type: " + ele.type);
		return
	}
	mark(key, mode, value);
}

sets = [];
svcon = undefined;
setsFor = null;
closeAfterSetMark = true;
searchQ = "";

function populateSets() {
	var setl = document.getElementById("sets-list");
	setl.scrollTop = 0;
	setl.innerHTML = "";

	for (var pos in sets) {
		if (searchQ != "")
			if (!(sets[pos][0].toLowerCase().includes(searchQ)))
				continue// don't list unmatching
		
		var nbtn = document.createElement("BUTTON");
		nbtn.id = "status" + sets[pos][0];
		nbtn.className = "mbutton item";
		if (sets[pos][2] == true)
			nbtn.className += " on";
		
		var sym = "";
		
		if (sets[pos][3] == true)// lock
			sym += "&#x1F512; ";
		else
			nbtn.onclick = setMarkMagic;
		
		if (sets[pos][4] == true)// pin
			sym += "&#x1F4CC; ";
		
		nbtn.innerHTML = sets[pos][0] + "<span>" + sym + sets[pos][1].toLocaleString() + "</span>";
		setl.appendChild(nbtn);
	}
}

function setsGetMagic(a, provided) {
	p = a;
	if (a.tagName != "DIV")
		p = a.parentElement;

	thing = p.getAttribute("name").split('@');
	mark = thing.splice(-1, 1)[0];
	thing = thing.join('@');

	console.log(thing, mark);
	setsGet(thing, mark);
}

function setsGet(file, loco) {
	svcon = loco;
	bt = document.getElementsByName(file + "@" + svcon);

	for (var b = 0; b < bt.length; b++) {
		bt[b].classList.add("disabled");
		//bt[b].style.backgroundPositionX = (-bt[b].offsetWidth * 8).toString() + "px";
	}

	setsFor = file;
	var meta = {
		"query": file,
		"con": svcon
	};
	send_xhr('/collections/for', JSON.stringify(meta), setsGetBack);
}

function setsGetBack() {
	var data = JSON.parse(this.responseText);
	sets = data["sets"];
	bt = document.getElementsByName(setsFor + "@" + svcon);
	
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
		sets = [
			[name, 0, false]
		].concat(sets);
		document.getElementById("setsName").value = "";
		setSearch();
	}
}

function setsNew() {
	var name = document.getElementById("setsName").value;
	var fail = false;
	if (name == "") {
		fail = true;
	}
	for (var pos in sets) {
		if (sets[pos][0].toLowerCase() == name.toLowerCase()) {
			fail = true;
			break;
		}
	}
	if (!(fail)) {
		var meta = {
			"name": name,
			"time": Date.now(),
			"con": svcon
		};
		send_xhr('/collections/new', JSON.stringify(meta), setsNewBack);
	}
}

function setMarkMagic() {
	var flag = this.innerHTML.split("<span>")[0];
	setMark(setsFor, flag);
}

function setMarkBack() {
	var data = JSON.parse(this.responseText);

	for (var file in data) {
		if (file == "status") continue;
		bt = file + "@" + data[file][0];
		console.log(file, bt, data[file]);
		var bt = document.getElementsByName(bt);

		for (var b = 0; b < bt.length; b++) {
			if (data[file][1])
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
	send_xhr('/collections/_flag', JSON.stringify(meta), setMarkBack);
}

function setsProp(name, prop) {
	var meta = {
		"name": name,
		"prop": prop,
		"con": con,
		"time": Date.now()
	}
	send_xhr('/collections/prop', JSON.stringify(meta), markback);
}

function setDelete(name) {
	if (confirm("Delete \"" + name + "\" permanently?")) {
		alert("Deleted");
		setsProp(name, "delete");
	} else {
		console.log("Nuclear Crisis Averted");
	}
}

function setSort(name) {
	if (confirm("Sort this collection by ID?")) {
		alert("Sorted");
		setsProp(name, "sortmepls");
	} else {
		console.log("Nuclear Crisis Averted Maybe");
	}
}

function setSearch() {
	searchQ = document.getElementById("setsName").value.toLowerCase();
	populateSets();
}

function propMagic(a, provided) {
	thing = a.getAttribute("name").split('@');
	mark = thing.splice(-1, 1)[0];
	thing = thing.join('@');

	console.log(thing, mark);
	
	if (mark == "sortmepls") setSort(thing);
	else if (mark == "delete") setDelete(thing);
	else setsProp(thing, mark);
}

function aprefAllRead(a) {
	for (var i = 0; i < posts.length; i++) {
		aprefMagic(a, posts[i]);
	}
}

function folderToSetMakeBack() {
	var data = JSON.parse(this.responseText);
	console.log("BACK!", data);
	if (data.status == "success") {
		setMark(posts, data.name);
	} else {
		folderToSet("Nah fam, give it a differeent name")
	}
}

function folderToSet(pr, addto) {
	title = prompt(pr, defaultSetName);
	if (title == null) {
		return;
	}
	
	svcon = addto;
	var meta = {
		"name": title,
		"time": Date.now(),
		"con": addto
	};
	send_xhr('/collections/new', JSON.stringify(meta), folderToSetMakeBack);
}

function aprefMagic(a, provided) {
	p = a;
	if (a.tagName != "DIV")
		p = a.parentElement;

	thing = p.getAttribute("name").split('@');
	mark = thing.splice(-1, 1)[0];
	thing = thing.join('@');

	console.log(thing, mark);

	if (p.children.length > 1)
		value = p.children[1].value
	else {
		thing = thing.split('@');
		value = thing.splice(-1, 1)[0];
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

	send_xhr('/_apref/' + mark, JSON.stringify(meta), aprefBack);
}

function aprefBack() {// why didn't i comment this
	var data = JSON.parse(this.responseText);
	
	for (var item in data) {
		console.log(item, data[item]);
		target = item + "@" + data[item][1] + "@" + data[item][0];
		
		var bt = document.getElementsByName(item + "@" + data[item][0]);
		if (bt.length < 1)
			continue

		for (var b = 0; b < bt.length; b++) {
			if (bt[b].tagName == "SPAN") {
				ct = bt[b].children;
				for (var c = 0; c < ct.length; c++) {
					if (ct[c].getAttribute("name") == target)
						ct[c].classList.add("on");
					else
						ct[c].classList.remove("on");
				}
			} else {
				if (data[item][1] == null || data[item][1] == "n/a") {
					bt[b].classList.remove("on");
					bt[b].children[1].value = "";
				} else {
					bt[b].classList.add("on");
					bt[b].children[1].value = data[item][1];
				}
			}
		}
	}
}

function processFilterElement(e) {
	if (e.classList.contains("filterTab") || e.classList.contains("filterWidgets")){
		return processFilterChildren(e);
	}
	else if (e.tagName == "SELECT") {
		n = e.id.substr(3);
		return [n + ":" + e.value];
	}
	else if (e.tagName == "INPUT") {
		n = e.id.substr(3);
		if (e.type == "checkbox") {
			if (e.checked)
				return ["@" + n];
		}
		
		else if (e.type == "radio") {
			if (e.checked)
				return ["@" + n];
		}
		
		else if (e.type == "text") {
			if (e.value.length > 0)
				return [e.value.trim()];
		}
	}
	
	return [];
}

function processFilterChildren(e) {
	var ch = e.children;
	var path = [];
	
	for (var i = 0; i < ch.length; i++) {
		path.push(...processFilterElement(ch[i]));
	}
	
	return path;
}

function filterGo() {
	var path = processFilterChildren(document.getElementById("filterParams"))
	mode = document.location.pathname.split("/")[3];
	
	if (isNaN(Number(mode)))
		mode = "/" + mode
	else
		mode = ""
	
	document.location = "/filter/" + path.join(" ") + mode + "/1";
}

var faActionInfo = null;

function setFAction() {
	ele = document.getElementsByClassName("t-image");
	sel = document.getElementById("action")
	amode = sel.value;
	action = sel.options[sel.selectedIndex].text;
	
	col = null;
	if (action.startsWith("Modify")) {
		faActionInfo = amode.substr(4);
		amode = "collection";
	}
	else if (action == "Open FADSRV page")
		action = "/view/";
	
	else if (amode == "link")
		action = "http://furaffinity.net/view/"
	
	//console.log({action, amode});
	
	for (var i = 0; i < ele.length; i++) {
		e = ele[i];
		postid = e.id.substr(4);
		if (amode == "link")
			e.children[0].href = action + postid;
		
		else e.children[0].removeAttribute("href");
		
		if (amode == "collection")
			e.children[0].onclick = FActionColMagic;
		
		else e.children[0].onclick = null;
	}
}

function FActionColMagic() {
	if (faActionInfo == null) return;
	
	setsGet(this.parentElement.id.substr(4), faActionInfo);
}

function editMenuDisplay(menuname) {
	var data = menuPages[menuname];
	console.log(data);
	document.getElementsByName("title")[0].value = data.title;
	document.getElementsByName("item-style")[0].value = data.mode;
	
	var items = menuButtons[data.buttons];
	var elemItems = document.getElementById("items");
	elemItems.innerHTML = "";
	for (var i = 1; i < items.length + 1; i++) {
		var item = items[i - 1];
		elemItems.innerHTML += '<label for="item-' + i + '-link">Link ' + i + '<br><input name="item-' + i + '-link" class="niceinp" value="' + item.href + '"></label>';
		elemItems.innerHTML += '<label for="item-' + i + '-label">Label ' + i + '<br><input name="item-' + i + '-label" class="niceinp" value="' + item.label + '"></label>';
		if (data.mode.includes("icons")) {
			var x = item.x * -60;
			var y = item.y * -60;
			elemItems.innerHTML += '<button id="' + menuname + i + '" class="iconsheet" style="background-position: ' + x + 'px ' + y + 'px;" onclick="editIcon(\'' + menuname + i + '\', ' + item.x + ', ' + item.y + ')"></button>';
		}
		elemItems.innerHTML += '</br>';
	}
}

function markWarpFloat(side) {
	
	eles = document.getElementsByClassName("floatingmark");
	for (var i = 0; i < eles.length; i++)
		eles[i].style = "text-align: " + side;
	
	eles = document.getElementsByClassName("floaty");
	
	for (var i = 0; i < eles.length; i++) {
		eles[i].style = "";
		if (eles[i].className.includes("floaty" + side))
			eles[i].style = "display: none";
	}
	
	if (side == defaultMarkAlignment) return
	
	if (updateMarkAlignment)
		mark('mark_button_align', 'cfg', side);
	
	defaultMarkAlignment = side
	
}

function page_load() {
	if (doMarkAlignStuff) {
		eles = document.getElementsByClassName("floatingmark");
		fl =  '<a class="floaty floatyleft" onclick="markWarpFloat(\'left\')"></a>'
		fl += '<a class="floaty floatycenter" onclick="markWarpFloat(\'center\')"></a>'
		fl += '<a class="floaty floatyright" onclick="markWarpFloat(\'right\')"></a>'
		for (var i = 0; i < eles.length; i++)
			eles[i].innerHTML = fl + eles[i].innerHTML;	
	}
	markWarpFloat(defaultMarkAlignment);
	
}

function profileHandler() {
	var data = JSON.parse(this.responseText);
	if (data.status == "success") {
		window.location.href = data.href;
	} else {
		console.log(data);
		alert(data.message);
	}
}

function setProfile(idx) {
	meta = {"set": idx};
	send_xhr("/profiles", JSON.stringify(meta), profileHandler);
}