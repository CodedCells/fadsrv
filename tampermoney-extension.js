// ==UserScript==
// @name         Add check
// @namespace    http://tampermonkey.net/
// @version      0.4
// @description  try to take over the world!
// @author       You
// @match        https://www.furaffinity.net/*
// @grant        none
// ==/UserScript==
var server = "http://192.168.0.68:6990/";
var iDitIt = false;

function reqListener () {
	console.log(this.responseText);
}

function send_xhr(url, data, f) {
	//console.log(data);
	if (f == undefined) {f = reqListener;}
	var xhr = new XMLHttpRequest();
	xhr.addEventListener("load", f);
	xhr.open("POST", url, true);
	xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
	xhr.send(data);
}

function statusPostsBack() {
    var data = JSON.parse(this.responseText);
    console.log(data);
    var fig = document.getElementsByTagName("figure");
    var chk = document.createElement("style");
    chk.innerHTML = ".fadcheck {display: block; position: absolute; top: 0; left: 0; width: 24px; height: 24px;";
    chk.innerHTML += " background-image: url(" + server + "checkicons.svg); background-size: 250px 250px}";
    document.getElementsByTagName("head")[0].appendChild(chk);

    for (var i = 0; i < fig.length; i++) {
        var figi = fig[i].id.substring(4);
        chk = document.createElement("SPAN");
        chk.className = "fadcheck";
        var pos = data[figi];
        var x = (pos % 10) * -25;
        var y = Math.floor(pos / 10) * -25;
        chk.style = "background-position: " + x + "px " + y + "px";
        fig[i].childElements()[0].childElements()[0].childElements()[0].appendChild(chk);
    }

    if (inHref("view/") || inHref("full/")) {
        fig = document.getElementsByClassName('preview-gallery hideonmobile')[0].children
        for (i = 0; i < fig.length; i++) {
            figi = fig[i];
            var figs = figi.children[0].href.split("/")[4];
            if (data[figs] > 0) {
                figi.className += " fadcheckframed fadcheckframe" + data[figs];
            }
        }
    }
}

function plsWork(urlid) {
    console.log("Running");
    var postsNeeded = [];

    var fig = document.getElementsByTagName("figure");
    for (var i = 0; i < fig.length; i++) {
        postsNeeded.push(fig[i].id.substring(4));
    }

    if (urlid != null || !(postsNeeded.includes(urlid))) {
        postsNeeded.push(urlid);
    }

    console.log("Counted", postsNeeded.length);
    var data = {
        "posts": postsNeeded,
        "raw": document.documentElement.innerHTML,
        "path": window.location.pathname
    };
    send_xhr(server + "mgot_parse", JSON.stringify(data), statusPostsBack);
}

function statusSoloBack() {
    var data = JSON.parse(this.responseText);
    for (var x in data) {
        data = data[x];
        break;
    }

    console.log(data);
    var hl = document.getElementsByClassName("haslocal");
    for (x = 0; x < hl.length; x++) {
        hl[x].classList.add("checkbutton" + data)
            if (data == 1) hl[x].innerHTML = "- Local";
    }
}


function hasLocal(pid) {
    console.log("Running");
    var postsNeeded = [pid];
    send_xhr(server + "mgot", JSON.stringify(postsNeeded), statusSoloBack);
}

function posthandle() {
    // your code here
    console.log("Script Post!");
    var urlid = window.location.href.split('/')[4];

    plsWork(urlid);
    if (urlid == null) {
        return;
    }

    var outbutt = '<a class="button standard mobile-fix haslocal" href="http://copi:6970/view/'+urlid+'">+ Local</a> ';

    var buttonbar = document.getElementsByClassName("aligncenter auto_link hideonfull1 favorite-nav");
    if (buttonbar.length > 0) {
        buttonbar[0].innerHTML += outbutt;
        hasLocal(urlid);
        return
    }
    // error page
    buttonbar = document.getElementsByClassName("alignright");
    if (buttonbar.length > 0) {
        //var post = document.getElementsByName("myform")[0].getAttribute("action")
        buttonbar[0].innerHTML += outbutt;
        hasLocal(urlid);
        return
    }
}

document.onreadystatechange = newReady;
//window.addEventListener('load', function() {var x = setInterval(newReady, 1);}, false);
var x = setInterval(newReady, 1);

function inHref(a) {return window.location.href.includes(a);}

function newReady() {
    if (iDitIt) return;
    iDitIt = true;

    console.log("Running new userscripts!");
    var chk = document.createElement("style");
    chk.innerHTML = 'a:visited {color: hsla(116, 70%, 80%, 0.6)!important;;}';
    chk.innerHTML += '#submissionImg {max-height: 80vh!important;}';
    chk.innerHTML += 'a[href^="/fav/"], a[href^="/watch/"], .checkbutton0 {background: #376744!important;}';
    chk.innerHTML += 'a[href^="/unfav/"], a[href^="/unwatch/"], .checkbutton1 {background: #673737!important;}';
    chk.innerHTML += '.preview-gallery {gap: 2px;}';
    chk.innerHTML += '.fadcheckframed {margin: 0!important;}';
    chk.innerHTML += '.fadcheckframe1 {border: 1px solid #7f7;}';
    chk.innerHTML += '.fadcheckframe3 {border: 1px solid #00368C;}';
    chk.innerHTML += '.fadcheckframe6 {border: 1px solid #ff0;}';
    document.getElementsByTagName("head")[0].appendChild(chk);

    if (inHref("view/") || inHref("full/")) {posthandle()}
    //else if (inHref("user/")) {console.log("user");}
    else {plsWork(null);}
}

window.addEventListener('keydown', function (e) {
    if (!(e.ctrlKey)) return// only ctrl + key

    if (e.which == 81) {// q
        document.getElementsByClassName("fav")[0].children[0].click();
    }
}, false);