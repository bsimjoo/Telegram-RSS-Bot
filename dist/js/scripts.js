window.onload = function ()  {
    let loading = document.getElementById("loading-screen");
    this.sleep(2000);
    loading.style.display = "none";
  };

  function sleep(milliseconds) {
    const date = Date.now();
    let currentDate = null;
    do {
      currentDate = Date.now();
    } while (currentDate - date < milliseconds);
  }