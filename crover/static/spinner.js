// イベントを禁止する関数
function noScroll(event) {
    event.preventDefault();
}

// スピナーを有効にしスクロールを禁止する
function enable_spinner() {
    document.getElementsByClassName("loader")[0].style.display = "block";

    // スクロール禁止(SP)
    document.addEventListener('touchmove', noScroll, { passive: false });
    // スクロール禁止(PC)
    document.addEventListener('mousewheel', noScroll, { passive: false });
}

// スピナーを無効にしスクロールを解除する
function disable_spinner() {
    document.getElementsByClassName("loader")[0].style.display = "none";

    // スクロール禁止を解除(SP)
    document.removeEventListener('touchmove', noScroll, { passive: false });
    // スクロール禁止を解除(PC)
    document.removeEventListener('mousewheel', noScroll, { passive: false });
}