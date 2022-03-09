
function editMenu(menuname) {
    var data = menudata[menuname];
    console.log(data);
    document.getElementsByName("title")[0].value = data.title;
    document.getElementsByName("item-style")[0].value = data.mode;

    var elemItems = document.getElementById("items");
    elemItems.innerHTML = "";
    for (var i = 1; i < data.items.length + 1; i++) {
        var item = data.items[i - 1];
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

function editIcon(eid, x, y) {
    console.log(eid);
    sidiv = document.getElementById("selectIcon");
    sidiv.style.display = "block";
    for (var cy = 0; cy < 9; cy++) {
        for (var cx = 0; cx < 9; cx++) {
            if (x == cx && y == cy) {
                sidiv.children[cx + (cy * 10)].style.backgroundColor = "#c00";
            } else {
                sidiv.children[cx + (cy * 10)].style.backgroundColor = null;
            }
        }
    }
}

function useIcon(x, y) {

}

function createMenu(failed) {
    var menuid = prompt("Menu technical id:").toLowerCase();
    if (menuid == null || menuid == "") {
        return;
    }
    console.log(menuid);
}


function menuEdit() {
    var mb = document.getElementsByClassName("menubtn");
    for (var m = 0; m < mb.length; m++) {
        console.log(mb[m].getAttribute("name"));
    }
}