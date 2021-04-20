function downloadURI(uri, name) 
{
    var link = document.createElement("a");
    // If you don't know the name or want to use
    // the webserver default set name = ''
    link.setAttribute('download', name);
    link.href = uri;
    document.body.appendChild(link);
    link.click();
    link.remove();
}

function downloadLatest() {
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            var myObj = JSON.parse(this.responseText);
            downloadURI(myObj.zipball_url,'')
        }
    };
    xmlhttp.open("GET", "https://api.github.com/repos/bsimjoo/Telegram-RSS-Bot/releases/latest", true);
    xmlhttp.send();
}